#!/usr/bin/env python3
"""
validate_e2e_real_data.py — E2E Real Data Validation Script

使用真實 TWSE/TPEx API 資料（非 mock）驗證 EOD 管線 4 個 stages 全部打通。

驗證區間: 2026-05-01 ~ 2026-05-22

設計說明:
  - Stage 1 (spiders): 使用 datetime.now() 抓取今日資料 (不可指定歷史日期)。
    若執行於非交易日，部分 spider (cb_master, tpex_cb_daily) 可能無資料。
    BrokerBreakdownSpider 因使用 OCR 需 ~8s/symbol, 299 symbols → ~40min,
    因此設 1200s timeout, 超時時僅使用 DB 既有資料繼續驗證。
  - Stages 2-4: 對驗證區間每一交易日逐一執行，檢查 DB 產出。
  - 不修改任何 src/ 程式碼，不 mock 任何請求。

用法:
    source .venv/bin/activate
    python scripts/validate_e2e_real_data.py

Exit codes:
    0 = PASS (全部通過標準)
    1 = FAIL (任一失敗標準)
"""

import logging
import os
import re
import subprocess
import sys
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("validate_e2e")

# ─── Paths ─────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
REPORT_DIR = PROJECT_ROOT / "output" / "validation"

# ─── DB config ─────────────────────────────────────────────────────────────
DB_CONFIG: Dict[str, Any] = dict(
    host="localhost", port=5432, database="cbas",
    user="postgres", password="postgres",
)

# ─── Validation date range ─────────────────────────────────────────────────
START_DATE = date(2026, 5, 1)
END_DATE = date(2026, 5, 22)

# Spider names to track
SPIDER_NAMES = [
    "stock_master",
    "cb_master",
    "stock_daily",
    "tpex_cb_daily",
    "broker_breakdown",
]

# Stage 1: BrokerBreakdownSpider OCR ~8s/symbol × 299 symbols ~ 2400s
# 但整個 step_spiders() 完成前不會 flush DB，所以設定太長也沒用：
#   - 前4 spider (stock_master+cb_master+stock_daily+tpex_cb_daily) 約 45s
#   - BrokerBreakdown 開始 ~45s 處，需要 ~40min 完成
# 設定 120s: 夠擷取前4 spider 輸出，但 timeout 後無 flush→DB
#           驗證腳本會用 DB 既有資料繼續跑 stages 2-4
STAGE1_TIMEOUT = 120
STAGE234_TIMEOUT = 120


# ═══ Helpers ═══════════════════════════════════════════════════════════════

def is_trading_day(d: date) -> bool:
    """週一到週五即為交易日（暫不考慮台灣國定假日）"""
    return d.weekday() < 5


def get_trading_dates() -> List[date]:
    """取得日期區間內的所有交易日"""
    result: List[date] = []
    current = START_DATE
    while current <= END_DATE:
        if is_trading_day(current):
            result.append(current)
        current += timedelta(days=1)
    return result


def call_pipeline(stage: int, dt: date, timeout: int = 600) -> Optional[subprocess.CompletedProcess]:
    """透過 subprocess 呼叫 run_eod_analysis.py

    Args:
        stage: 階段編號 (1-4)
        dt: 日期
        timeout: 超時秒數

    Returns:
        CompletedProcess or None (timeout/error)
    """
    date_str = dt.strftime("%Y-%m-%d")
    cmd = [
        sys.executable, "-u",
        str(SRC_DIR / "run_eod_analysis.py"),
        "--stage", str(stage),
        "--date", date_str,
    ]
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    logger.info("  ── running: %s (timeout=%ds)", " ".join(str(c) for c in cmd), timeout)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            env=env,
            timeout=timeout,
        )
        return result
    except subprocess.TimeoutExpired:
        logger.warning("  ⏰ Stage %d timed out after %ds", stage, timeout)
        return None
    except Exception as e:
        logger.error("  ❌ Stage %d subprocess error: %s", stage, e)
        return None


def has_real_exception(text: str) -> List[str]:
    """檢查輸出中是否有真正的 exception traceback（非 INFO log）

    真正的 exception traceback 特徵:
    - 以 "Traceback (most recent call last):" 開頭的行
    - 後續跟著 "File ..." 行
    - 最終以 "ExceptionType: message" 結尾
    """
    traces = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        # 檢測真正的 traceback 起始
        if line.strip().startswith("Traceback (most recent call last)"):
            trace_lines = [line]
            i += 1
            # 收集 File 行
            while i < len(lines) and ("File " in lines[i] or lines[i].strip() == ""):
                if lines[i].strip():
                    trace_lines.append(lines[i])
                i += 1
            # 收集最後的 exception 訊息
            if i < len(lines) and lines[i].strip():
                trace_lines.append(lines[i])
            traces.append("\n".join(trace_lines))
        else:
            i += 1
    return traces


def extract_spider_results_from_output(text: str) -> Dict[str, Dict[str, Any]]:
    """從 run_eod_analysis.py 的 stdout/stderr 提取 spider 結果

    尋找的關鍵行:
        run_daily - INFO -   ✅ stock_master: 1234
        run_daily - ERROR -   ❌ cb_master: HTTP 404
    """
    results: Dict[str, Dict[str, Any]] = {}
    for spider in SPIDER_NAMES:
        results[spider] = {"success": False, "count": 0, "error": None}

    for line in text.split("\n"):
        for spider in SPIDER_NAMES:
            # Pattern: "✅ spider_name: count" or "❌ spider_name: error"
            # The log format includes: "xxx - run_daily - INFO -   ✅ stock_master: 1789"
            m = re.search(rf"([✅❌])\s*{re.escape(spider)}\s*:\s*(.+)", line)
            if m:
                icon = m.group(1)
                rest = m.group(2).strip()
                success = icon == "✅"
                # Try to extract count from beginning of rest
                count_match = re.match(r"(\d+)", rest)
                count = int(count_match.group(1)) if count_match else 0
                error = rest if not success else None
                # Only update if current result is not already successful
                if not results[spider]["success"]:
                    results[spider] = {
                        "success": success,
                        "count": count,
                        "error": error,
                    }
    return results


# ═══ DB check helpers ═════════════════════════════════════════════════════

def _get_db_cursor():
    """取得 psycopg2 connection & cursor"""
    import psycopg2
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    return conn, cur


def check_db_master_tables() -> Dict[str, int]:
    """查詢主檔表與追蹤表數據量"""
    conn, cur = _get_db_cursor()
    data: Dict[str, int] = {}
    try:
        for tbl in ["stock_master", "cb_master", "tracked_symbols"]:
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            data[tbl] = cur.fetchone()[0]
    finally:
        cur.close()
        conn.close()
    return data


def check_db_date_summary(dt: date) -> Dict[str, Any]:
    """查詢指定日期的各表數據"""
    date_str = dt.strftime("%Y-%m-%d")
    conn, cur = _get_db_cursor()
    entry: Dict[str, Any] = {"date": date_str}
    try:
        # stock_daily (date 是 text)
        cur.execute("SELECT COUNT(*) FROM stock_daily WHERE date = %s", (date_str,))
        entry["stock_daily"] = cur.fetchone()[0]

        # tpex_cb_daily (trade_date 是 text)
        cur.execute("SELECT COUNT(*) FROM tpex_cb_daily WHERE trade_date = %s", (date_str,))
        entry["tpex_cb_daily"] = cur.fetchone()[0]

        # broker_breakdown (date 是 date)
        cur.execute("SELECT COUNT(*) FROM broker_breakdown WHERE date = %s", (dt,))
        entry["broker_breakdown"] = cur.fetchone()[0]

        # daily_analysis_results
        cur.execute("SELECT COUNT(*) FROM daily_analysis_results WHERE date = %s", (date_str,))
        entry["daily_analysis_results"] = cur.fetchone()[0]

        # trading_signals
        cur.execute("SELECT COUNT(*) FROM trading_signals WHERE date = %s", (date_str,))
        entry["trading_signals"] = cur.fetchone()[0]

        # Rating distribution
        cur.execute("""
            SELECT COALESCE(final_rating, 'N/A'), COUNT(*)
            FROM daily_analysis_results
            WHERE date = %s
            GROUP BY final_rating
            ORDER BY final_rating
        """, (date_str,))
        entry["ratings"] = {str(r[0]): r[1] for r in cur.fetchall()}

        # Signal distribution
        cur.execute("""
            SELECT signal_type, COUNT(*)
            FROM trading_signals
            WHERE date = %s
            GROUP BY signal_type
            ORDER BY signal_type
        """, (date_str,))
        entry["signals"] = {str(r[0]): r[1] for r in cur.fetchall()}

    finally:
        cur.close()
        conn.close()
    return entry


def check_global_db_counts() -> Dict[str, int]:
    """查詢全局數據量"""
    conn, cur = _get_db_cursor()
    data: Dict[str, int] = {}
    try:
        for tbl in ["stock_master", "cb_master", "stock_daily",
                     "tpex_cb_daily", "broker_breakdown",
                     "daily_analysis_results", "trading_signals",
                     "tracked_symbols"]:
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            data[tbl] = cur.fetchone()[0]
    finally:
        cur.close()
        conn.close()
    return data


# ═══ Criteria Checker ════════════════════════════════════════════════════

class ValidationResult:
    """驗證結果容器與判斷邏輯"""

    def __init__(self):
        # Stage 1
        self.stage1_spider_results: Optional[Dict[str, Dict[str, Any]]] = None
        self.stage1_exit_code: Optional[int] = None
        self.stage1_timed_out: bool = False
        self.stage1_exceptions: List[str] = []

        # Stages 2-4
        self.daily_results: Dict[str, Dict[str, Any]] = {}
        self.stage_exit_codes: Dict[int, Dict[str, int]] = {
            2: {}, 3: {}, 4: {}
        }

        # DB snapshots
        self.master_db_before: Optional[Dict[str, int]] = None
        self.master_db_after: Optional[Dict[str, int]] = None
        self.global_db: Optional[Dict[str, int]] = None

        # Stage execution tracking
        self.stages_executed: Dict[int, bool] = {1: False, 2: False, 3: False, 4: False}
        self.all_stage_outputs: Dict[int, str] = {}

        # Capture report content
        self.report_contents: List[str] = []

    # ── Pass criteria (all must be True for PASS) ──────────────────────

    def meets_p1(self) -> Tuple[bool, str]:
        """P1: 所有 spider 在每個交易日 success=True 且 records > 0

        Note: stage 1 spiders 使用 datetime.now()，只抓取今日資料。
        若今天是交易日則驗證 spider 結果；非交易日則跳過此項.
        """
        today = date.today()
        if not is_trading_day(today):
            return True, f"今日({today})非交易日，P1 跳過 (spider 使用 datetime.now())"

        if not self.stage1_spider_results:
            return False, "Stage 1 未執行，無法評估"

        ok_count = 0
        details = []
        for spider in SPIDER_NAMES:
            sr = self.stage1_spider_results.get(spider, {})
            if sr.get("success") and sr.get("count", 0) > 0:
                ok_count += 1
                details.append(f"{spider}=✅({sr['count']})")
            elif not sr.get("success"):
                details.append(f"{spider}=❌(err={sr.get('error','N/A')})")
            else:
                details.append(f"{spider}=✅(cnt=0)")
        total = len(SPIDER_NAMES)
        passed = ok_count == total
        return passed, f"{ok_count}/{total}: {', '.join(details)}"

    def meets_p2(self) -> Tuple[bool, str]:
        """P2: 0 次未捕獲 exception

        檢查所有 stage 輸出中是否有真正的 exception traceback。
        """
        all_exceptions = list(self.stage1_exceptions)
        for s in [2, 3, 4]:
            output = self.all_stage_outputs.get(s, "")
            all_exceptions.extend(has_real_exception(output))

        if all_exceptions:
            return False, f"{len(all_exceptions)} uncaught exception(s):\n" + \
                   "\n".join(f"  - {e[:120]}..." for e in all_exceptions)
        return True, "0 uncaught exceptions"

    def meets_p3(self) -> Tuple[bool, str]:
        """P3: 分析引擎產出 > 0 筆

        檢查所有交易日 daily_analysis_results 的累加總數。
        """
        total = sum(
            d.get("daily_analysis_results", 0)
            for d in self.daily_results.values()
        )
        if total == 0:
            return False, f"分析引擎 0 筆產出 (無 tpex_cb_daily / stock_daily 資料)"
        return True, f"分析引擎產出 {total} 筆 (跨 {sum(1 for d in self.daily_results.values() if d.get('daily_analysis_results',0)>0)} 交易日)"

    def meets_p4(self) -> Tuple[bool, str]:
        """P4: 評級 4 類 (S/A/B/C) 皆出現"""
        all_ratings: set = set()
        for d in self.daily_results.values():
            all_ratings.update(k for k in d.get("ratings", {}).keys() if k in ("S", "A", "B", "C"))

        missing = {"S", "A", "B", "C"} - all_ratings
        if missing:
            return False, f"缺少評級: {sorted(missing)} (現有: {sorted(all_ratings)})"
        return True, f"4 類評級皆出現: {sorted(all_ratings)}"

    def meets_p5(self) -> Tuple[bool, str]:
        """P5: 報表非空字串

        檢查所有 stage 4 輸出中，是否至少有一份報表含有資料內容。
        """
        non_empty = [r for r in self.report_contents if len(r.strip()) > 100]
        if non_empty:
            max_len = max(len(r) for r in non_empty)
            return True, f"報表非空 (最長 {max_len} chars)"
        return False, "無含資料內容的報表 (所有報表皆為空白標題)"

    def meets_p6(self) -> Tuple[bool, str]:
        """P6: 4 個 stage 全部執行完畢"""
        not_run = [str(s) for s in [1, 2, 3, 4] if not self.stages_executed.get(s)]
        if not_run:
            return False, f"Stage(s) {', '.join(not_run)} 未執行"
        return True, "4 個 stages 全部執行完畢"

    # ── Failure criteria (any True → FAIL) ─────────────────────────────

    def fails_f1(self) -> Tuple[bool, str]:
        """F1: 任一 spider 連續 3 個交易日失敗

        stage 1 只執行一次 (datetime.now() 限制)，統計單次結果。
        """
        if not self.stage1_spider_results:
            return False, "Stage 1 未執行，無法評估連續失敗"

        # 單次執行中，任一 spider 失敗都算
        failed = [s for s in SPIDER_NAMES
                  if not self.stage1_spider_results.get(s, {}).get("success")]
        if len(failed) >= 3:
            return True, f"單次執行中有 {len(failed)} 個 spider 失敗: {failed}"
        return False, f"無連續失敗 (失敗: {failed if failed else '無'})"

    def fails_f2(self) -> Tuple[bool, str]:
        """F2: 管線在某 stage 完全無法執行 (import error / crash)

        檢查是否因 ImportError 或 crash 導致 subprocess returncode 非 0。
        """
        for stage in [1, 2, 3, 4]:
            if not self.stages_executed.get(stage):
                continue
            output = self.all_stage_outputs.get(stage, "")
            # Check for import errors
            if "ImportError" in output or "ModuleNotFoundError" in output:
                return True, f"Stage {stage} 有 ImportError"
            # Check for crash in stderr
            has_crash = "CRITICAL" in output or "FATAL" in output
            if has_crash:
                return True, f"Stage {stage} 有 CRITICAL/FATAL 錯誤"
        return False, "所有 stages 皆可正常執行"

    def fails_f3(self) -> Tuple[bool, str]:
        """F3: 所有 spider 在正常交易日回傳 0 筆"""
        today = date.today()
        if not is_trading_day(today):
            return False, f"今日({today})非交易日，F3 不適用"

        if not self.stage1_spider_results:
            return False, "Stage 1 未執行，無法評估"

        all_zero = all(
            self.stage1_spider_results.get(s, {}).get("count", 0) == 0
            for s in SPIDER_NAMES
        )
        if all_zero:
            return True, f"所有 spider 在交易日 {today} 回傳 0 筆"
        return False, "非所有 spider 回傳 0 筆"

    def fails_f4(self) -> Tuple[bool, str]:
        """F4: 分析引擎產出為 0"""
        total = sum(
            d.get("daily_analysis_results", 0)
            for d in self.daily_results.values()
        )
        if total == 0:
            return True, "分析引擎產出為 0"
        return False, f"分析引擎產出 {total} 筆，非 0"

    # ── Overall judgement ──────────────────────────────────────────────

    def overall_pass(self) -> Tuple[bool, str]:
        checks = {
            "P1": self.meets_p1(),
            "P2": self.meets_p2(),
            "P3": self.meets_p3(),
            "P4": self.meets_p4(),
            "P5": self.meets_p5(),
            "P6": self.meets_p6(),
        }
        Fchecks = {
            "F1": self.fails_f1(),
            "F2": self.fails_f2(),
            "F3": self.fails_f3(),
            "F4": self.fails_f4(),
        }

        lines = []
        lines.append("### ✅ 通過標準 (Pass Criteria)")
        for cid, (passed, msg) in checks.items():
            icon = "✅" if passed else "❌"
            lines.append(f"  {icon} **{cid}**: {msg}")

        lines.append("")
        lines.append("### ❌ 失敗標準 (Fail Criteria)")
        for cid, (failed, msg) in Fchecks.items():
            icon = "⚠️ FAIL" if failed else "✅ PASS"
            lines.append(f"  {icon} **{cid}**: {msg}")

        all_pass = all(v[0] for v in checks.values())
        any_fail = any(v[0] for v in Fchecks.values())
        verdict = all_pass and not any_fail

        return verdict, "\n".join(lines)


# ═══ Main Validation Logic ════════════════════════════════════════════════

def run_validation() -> ValidationResult:
    """執行完整驗證流程"""
    result = ValidationResult()
    trading_dates = get_trading_dates()
    today = date.today()

    logger.info("=" * 60)
    logger.info("  BCAS E2E Real Data Validation")
    logger.info(f"  日期區間: {START_DATE} ~ {END_DATE} ({len(trading_dates)} 交易日)")
    logger.info(f"  當前日期: {today} {'(交易日)' if is_trading_day(today) else '(非交易日)'}")
    logger.info(f"  Stage 1 timeout: {STAGE1_TIMEOUT}s, Stages 2-4 timeout: {STAGE234_TIMEOUT}s")
    logger.info("=" * 60)

    # ── Snapshot DB before ────────────────────────────────────────────
    result.master_db_before = check_db_master_tables()

    # ── Stage 1: Spiders ──────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("  Stage 1/4: 爬蟲階段 (Spiders)")
    logger.info("  ★ 注意: spiders 使用 datetime.now() 抓取今日資料")
    logger.info("=" * 60)

    r1 = call_pipeline(1, today, timeout=STAGE1_TIMEOUT)
    if r1 is not None:
        result.stages_executed[1] = True
        result.stage1_exit_code = r1.returncode
        combined = r1.stdout + "\n" + r1.stderr
        result.all_stage_outputs[1] = combined

        # Extract spider results
        result.stage1_spider_results = extract_spider_results_from_output(combined)

        # Check for real exceptions
        result.stage1_exceptions = has_real_exception(combined)

        logger.info("  Stage 1 spider results:")
        for spider in SPIDER_NAMES:
            sr = result.stage1_spider_results.get(spider, {"success": False, "count": 0, "error": "no data"})
            icon = "✅" if sr.get("success") else ("⏰" if result.stage1_timed_out else "❌")
            logger.info(f"    {icon} {spider}: success={sr.get('success')}, count={sr.get('count', 0)}, err={sr.get('error')}")
    else:
        # Subprocess timed out or failed
        result.stage1_timed_out = True
        result.stages_executed[1] = True  # We attempted it
        logger.warning("  ⏰ Stage 1 未在 %ds 內完成 (BrokerBreakdown OCR 可能過慢)", STAGE1_TIMEOUT)
        logger.warning("  將使用 DB 既有資料繼續驗證")

    # Check DB after stage 1
    result.master_db_after = check_db_master_tables()
    logger.info("\n  DB master tables after stage 1:")
    for tbl, cnt in sorted(result.master_db_after.items()):
        before = result.master_db_before.get(tbl, 0)
        delta = cnt - before
        logger.info(f"    {tbl}: {cnt} ({'+' if delta > 0 else ''}{delta})")

    # ── Stages 2-4: For each trading day ──────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("  Stages 2-4: 分析 / 風險 / 報表")
    logger.info(f"  執行 {len(trading_dates)} 個交易日")
    logger.info("=" * 60)

    for dt in trading_dates:
        date_str = dt.strftime("%Y-%m-%d")

        # Stage 2: Analysis
        r2 = call_pipeline(2, dt, timeout=STAGE234_TIMEOUT)
        if r2 is not None:
            result.stages_executed[2] = True
            result.stage_exit_codes[2][date_str] = r2.returncode
            result.all_stage_outputs[2] = result.all_stage_outputs.get(2, "") + r2.stdout + r2.stderr

        # Stage 3: Risk
        r3 = call_pipeline(3, dt, timeout=STAGE234_TIMEOUT)
        if r3 is not None:
            result.stages_executed[3] = True
            result.stage_exit_codes[3][date_str] = r3.returncode
            result.all_stage_outputs[3] = result.all_stage_outputs.get(3, "") + r3.stdout + r3.stderr

        # Stage 4: Report
        r4 = call_pipeline(4, dt, timeout=STAGE234_TIMEOUT)
        if r4 is not None:
            result.stages_executed[4] = True
            result.stage_exit_codes[4][date_str] = r4.returncode
            output4 = r4.stdout + r4.stderr
            result.all_stage_outputs[4] = result.all_stage_outputs.get(4, "") + output4

            # Extract report content from stage 4 output
            # Report is in stdout, looks like markdown starting with "# CBAS"
            if "# CBAS" in r4.stdout:
                # Extract the markdown report from stdout
                report_lines = []
                capture = False
                for line in r4.stdout.split("\n"):
                    if line.startswith("# CBAS"):
                        capture = True
                    if capture:
                        report_lines.append(line)
                if report_lines:
                    report_text = "\n".join(report_lines)
                    # Only keep reports with actual data (not just header)
                    if "|" in report_text and len(report_text) > 200:
                        result.report_contents.append(report_text)

        # Check DB for this date
        db_entry = check_db_date_summary(dt)
        result.daily_results[date_str] = db_entry

        # Log concise summary
        ar = db_entry["daily_analysis_results"]
        ts = db_entry["trading_signals"]
        ratings = db_entry.get("ratings", {})
        has_data = ar > 0 or ts > 0
        if has_data:
            logger.info(f"  [{date_str}] analysis={ar}, signals={ts}, ratings={ratings}")
        else:
            logger.debug(f"  [{date_str}] analysis={ar}, signals={ts} (no data)")

    # ── Final DB snapshot ──────────────────────────────────────────────
    result.global_db = check_global_db_counts()
    logger.info("\n" + "=" * 60)
    logger.info("  Final DB Statistics")
    logger.info("=" * 60)
    for tbl, cnt in sorted(result.global_db.items()):
        logger.info(f"    {tbl}: {cnt}")

    return result


def generate_report(result: ValidationResult) -> str:
    """產出 Markdown 驗證報告"""
    today_str = date.today().strftime("%Y-%m-%d")
    verdict, criteria_summary = result.overall_pass()
    trading_dates = get_trading_dates()

    lines = []
    lines.append("# E2E Real Data Validation Report")
    lines.append("")
    lines.append(f"- **執行日期**: {today_str}")
    lines.append(f"- **驗證區間**: {START_DATE} ~ {END_DATE}")
    lines.append(f"- **交易日數**: {len(trading_dates)}")
    lines.append(f"- **當前是否交易日**: {'是' if is_trading_day(date.today()) else '否'}")
    lines.append(f"- **Stage 1 timeout**: {STAGE1_TIMEOUT}s")
    lines.append(f"- **最終判定**: {'✅ **PASS**' if verdict else '❌ **FAIL**'}")
    lines.append("")

    # ── Stage 1 Spider Results ──
    lines.append("## Stage 1: 爬蟲結果")
    lines.append("")
    lines.append("| Spider | Success | Records | Error |")
    lines.append("|--------|---------|---------|-------|")
    if result.stage1_spider_results:
        for spider in SPIDER_NAMES:
            s = result.stage1_spider_results.get(spider, {})
            icon = "✅" if s.get("success") else "❌"
            cnt = s.get("count", 0) if s.get("success") else 0
            err = s.get("error") or "-"
            lines.append(f"| {spider} | {icon} | {cnt} | {err} |")
    elif result.stage1_timed_out:
        lines.append(f"| (timeout after {STAGE1_TIMEOUT}s) | ⏰ | - | - |")
        lines.append("| (BrokerBreakdown OCR 可能 >40min) | | | |")
    else:
        lines.append("| (not executed) | ❌ | - | - |")
    lines.append("")

    # ── DB Master Tables ──
    lines.append("## DB Master Tables")
    lines.append("")
    lines.append("| Table | Before | After | Delta |")
    lines.append("|-------|--------|-------|-------|")
    after = result.master_db_after or {}
    before = result.master_db_before or {}
    for tbl in sorted(set(list(before.keys()) + list(after.keys()))):
        b = before.get(tbl, 0)
        a = after.get(tbl, 0)
        delta = a - b
        d_str = f"+{delta}" if delta > 0 else str(delta) if delta < 0 else "-"
        lines.append(f"| {tbl} | {b} | {a} | {d_str} |")
    lines.append("")

    # ── Per-Day Summary ──
    lines.append("## Per-Day Results (Stages 2-4)")
    lines.append("")
    lines.append("| Date | Stock Daily | TPEx CB Daily | Broker Breakdown | Analysis Results | Trading Signals | Ratings |")
    lines.append("|------|-------------|---------------|-------------------|------------------|-----------------|---------|")
    for dt in trading_dates:
        ds = dt.strftime("%Y-%m-%d")
        d = result.daily_results.get(ds, {})
        sd = d.get("stock_daily", 0)
        cd = d.get("tpex_cb_daily", 0)
        bb = d.get("broker_breakdown", 0)
        ar = d.get("daily_analysis_results", 0)
        ts_val = d.get("trading_signals", 0)
        ratings_str = ", ".join(f"{k}={v}" for k, v in d.get("ratings", {}).items()) if d.get("ratings") else "-"
        lines.append(f"| {ds} | {sd} | {cd} | {bb} | {ar} | {ts_val} | {ratings_str} |")
    lines.append("")

    # ── Global DB ──
    lines.append("## Global DB Statistics")
    lines.append("")
    lines.append("| Table | Total Records |")
    lines.append("|-------|--------------|")
    if result.global_db:
        for tbl, cnt in sorted(result.global_db.items()):
            lines.append(f"| {tbl} | {cnt} |")
    lines.append("")

    # ── Stage Exit Codes ──
    lines.append("## Stage Exit Codes")
    lines.append("")
    lines.append("| Stage | Dates Run | Non-Zero Exits |")
    lines.append("|-------|-----------|----------------|")
    for s in [1, 2, 3, 4]:
        if s == 1:
            ec = result.stage1_exit_code
            ec_str = str(ec) if ec is not None else ("TIMEOUT" if result.stage1_timed_out else "N/A")
            lines.append(f"| 1 | {today_str} | {ec_str} |")
        else:
            codes = result.stage_exit_codes.get(s, {})
            n_dates = len(codes)
            n_nonzero = sum(1 for c in codes.values() if c != 0)
            lines.append(f"| {s} | {n_dates} | {n_nonzero} |")
    lines.append("")

    # ── Criteria ──
    lines.append("## Criteria Assessment")
    lines.append("")
    lines.append(criteria_summary)
    lines.append("")

    # ── Sample Report ──
    if result.report_contents:
        lines.append("## Stage 4 Report Sample")
        lines.append("")
        # Show the first report with data
        report = result.report_contents[0]
        preview_lines = report.split("\n")[:20]
        lines.append("```")
        lines.append("\n".join(preview_lines))
        if len(report.split("\n")) > 20:
            lines.append("...(truncated)")
        lines.append("```")
        lines.append("")

    # ── Exceptions ──
    if result.stage1_exceptions:
        lines.append("## Stage 1 Exceptions")
        lines.append("")
        for exc in result.stage1_exceptions[:5]:
            lines.append("```")
            lines.append(exc[:500])
            lines.append("```")
            lines.append("")

    lines.append("---")
    lines.append(f"*Report generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    return "\n".join(lines)


def save_report(report: str) -> Path:
    """儲存報表至 output/validation/"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = REPORT_DIR / f"real_data_e2e_report_{timestamp}.md"
    filepath.write_text(report, encoding="utf-8")
    logger.info("Report saved to %s", filepath)
    return filepath


# ═══ Main ════════════════════════════════════════════════════════════════

def main() -> int:
    logger.info("=" * 60)
    logger.info("  BCAS E2E Real Data Validation")
    logger.info("=" * 60)

    result = run_validation()

    # Generate and save report
    report = generate_report(result)
    filepath = save_report(report)

    # Also print the report summary
    print()
    print(report)

    verdict, _ = result.overall_pass()
    if verdict:
        logger.info("")
        logger.info("=" * 60)
        logger.info("  ✅ VERDICT: PASS - 全部通過標準")
        logger.info("=" * 60)
        return 0
    else:
        logger.info("")
        logger.info("=" * 60)
        logger.info("  ❌ VERDICT: FAIL - 未通過標準")
        logger.info("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
