"""
BSR (Basic Securities Report) 網站客戶端
封裝完整查詢流程: session 管理、ASP.NET state 解析、captcha 辨識、資料提交與結果解析
"""
from __future__ import annotations

import logging
import re
import time
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from src.spiders.ocr_solver import OcrSolver

logger = logging.getLogger(__name__)

BASE_URL = "https://bsr.twse.com.tw/bshtm/"


class BsrError(Exception):
    """BSR 客戶端基底異常"""


class BsrConnectionError(BsrError):
    """網路連線相關異常"""


class BsrCaptchaError(BsrError):
    """驗證碼錯誤異常"""


class BsrParseError(BsrError):
    """HTML 解析異常"""


class BsrCircuitBreakerOpen(BsrError):
    """Circuit Breaker 開啟，拒絕請求"""


class BsrClient:
    """
    BSR 網站客戶端，封裝完整查詢流程

    Attributes:
        max_retries: 最大重試次數
        request_interval: 請求間隔 (秒)
        session: requests.Session
        ocr: OcrSolver 實例
        _viewstate: ASP.NET __VIEWSTATE
        _eventvalidation: ASP.NET __EVENTVALIDATION
        _viewstategenerator: ASP.NET __VIEWSTATEGENERATOR
        _captcha_guid: 當前 captcha GUID
        _cb_failures: circuit breaker 連續失敗次數
        _cb_state: circuit breaker 狀態 (CLOSED / OPEN / HALF_OPEN)
        _cb_last_open_time: circuit breaker 開啟時間戳
    """

    FAILURE_THRESHOLD = 5
    RECOVERY_TIMEOUT = 60

    def __init__(self, max_retries: int = 3, request_interval: float = 2.0) -> None:
        """
        初始化 BsrClient

        Args:
            max_retries: captcha 錯誤最大重試次數
            request_interval: 每次 HTTP 請求間隔 (秒)
        """
        self.max_retries = max_retries
        self.request_interval = request_interval

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
            "Content-Type": "application/x-www-form-urlencoded",
        })

        self.ocr = OcrSolver()

        self._viewstate: Optional[str] = None
        self._eventvalidation: Optional[str] = None
        self._viewstategenerator: Optional[str] = None
        self._captcha_guid: Optional[str] = None

        self._cb_failures: int = 0
        self._cb_state: str = "CLOSED"
        self._cb_last_open_time: float = 0.0

        logger.info(
            "BsrClient initialized: max_retries=%d, request_interval=%.1f",
            max_retries, request_interval,
        )

    # ─── Circuit Breaker ─────────────────────────────────────────────

    def _cb_allow_request(self) -> bool:
        """
        檢查 circuit breaker 是否允許發送請求

        Returns:
            True 允許請求，False 拒絕
        """
        if self._cb_state == "CLOSED":
            return True

        if self._cb_state == "OPEN":
            if time.time() - self._cb_last_open_time >= self.RECOVERY_TIMEOUT:
                logger.info("Circuit breaker HALF_OPEN after recovery timeout")
                self._cb_state = "HALF_OPEN"
                return True
            return False

        if self._cb_state == "HALF_OPEN":
            return True

        return True

    def _cb_on_success(self) -> None:
        """請求成功時更新 circuit breaker 狀態"""
        self._cb_failures = 0
        if self._cb_state == "HALF_OPEN":
            logger.info("Circuit breaker CLOSED after successful request")
            self._cb_state = "CLOSED"

    def _cb_on_failure(self) -> None:
        """請求失敗時更新 circuit breaker 狀態"""
        self._cb_failures += 1
        if self._cb_failures >= self.FAILURE_THRESHOLD:
            logger.warning(
                "Circuit breaker OPEN after %d consecutive failures",
                self._cb_failures,
            )
            self._cb_state = "OPEN"
            self._cb_last_open_time = time.time()

    # ─── ASP.NET State ───────────────────────────────────────────────

    def _refresh_session(self) -> bool:
        """
        GET bsMenu.aspx → 解析 __VIEWSTATE, __EVENTVALIDATION,
        __VIEWSTATEGENERATOR, captcha GUID

        Returns:
            True 成功，False 失敗
        """
        self._throttle()
        url = urljoin(BASE_URL, "bsMenu.aspx")

        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            html = resp.text
        except requests.RequestException as e:
            logger.error("Session refresh network error: %s", e)
            return False

        if not self._parse_aspnet_state(html):
            return False

        guid = self._extract_captcha_guid(html)
        if guid is None:
            logger.error("Failed to extract captcha GUID")
            return False

        self._captcha_guid = guid
        logger.debug("Session refreshed: viewstate=%s..., guid=%s",
                      self._viewstate[:20] if self._viewstate else "None",
                      guid)
        return True

    def _parse_aspnet_state(self, html: str) -> bool:
        """
        用 BeautifulSoup 從 HTML 解析 ASP.NET 隱藏欄位

        Args:
            html: HTML 原始碼

        Returns:
            True 成功，False 缺少必要欄位
        """
        soup = BeautifulSoup(html, "lxml")

        def _find_value(_id: str) -> Optional[str]:
            tag = soup.find("input", {"id": _id})
            if tag and tag.get("value"):
                return tag["value"]
            return None

        self._viewstate = _find_value("__VIEWSTATE")
        self._eventvalidation = _find_value("__EVENTVALIDATION")
        self._viewstategenerator = _find_value("__VIEWSTATEGENERATOR")

        if not all([self._viewstate, self._eventvalidation, self._viewstategenerator]):
            logger.error(
                "Missing ASP.NET state fields: viewstate=%s, ev=%s, gen=%s",
                bool(self._viewstate),
                bool(self._eventvalidation),
                bool(self._viewstategenerator),
            )
            return False

        return True

    def _extract_captcha_guid(self, html: str) -> Optional[str]:
        """
        從 HTML 提取 captcha GUID

        <img src='CaptchaImage.aspx?guid=XXX'>

        Args:
            html: HTML 原始碼

        Returns:
            GUID 字串，或 None
        """
        match = re.search(r'CaptchaImage\.aspx\?(?:amp;)?guid=([^"\'& ]+)', html)
        if not match:
            return None
        return match.group(1)

    def _get_captcha_image(self) -> Optional[bytes]:
        """
        GET CaptchaImage.aspx?guid=XXX 下載 captcha 圖片

        Returns:
            PNG bytes，或 None
        """
        if not self._captcha_guid:
            logger.error("No captcha GUID available")
            return None

        self._throttle()
        url = urljoin(BASE_URL, f"CaptchaImage.aspx?guid={self._captcha_guid}")

        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            content = resp.content
            if len(content) < 100:
                logger.warning("Captcha image too small: %d bytes", len(content))
                return None
            logger.debug("Captcha image downloaded: %d bytes", len(content))
            return content
        except requests.RequestException as e:
            logger.error("Captcha download error: %s", e)
            return None

    def _solve_captcha(self) -> Optional[str]:
        """
        refresh → download → OCR 完整流程

        Returns:
            captcha 文字，或 None
        """
        if not self._refresh_session():
            return None

        img_bytes = self._get_captcha_image()
        if img_bytes is None:
            return None

        captcha_text = self.ocr.solve(img_bytes)
        logger.debug("Captcha solved: %s", captcha_text)
        return captcha_text

    # ─── Form Submit ─────────────────────────────────────────────────

    def _submit_query(self, symbol: str, captcha_code: str) -> Optional[str]:
        """
        POST bsMenu.aspx 提交查詢

        Args:
            symbol: 股票代號
            captcha_code: 驗證碼文字

        Returns:
            HTML 響應文字，或 None
        """
        self._throttle()
        url = urljoin(BASE_URL, "bsMenu.aspx")

        data = {
            "__VIEWSTATE": self._viewstate or "",
            "__EVENTVALIDATION": self._eventvalidation or "",
            "__VIEWSTATEGENERATOR": self._viewstategenerator or "",
            "RadioButton_Normal": "RadioButton_Normal",
            "TextBox_Stkno": symbol,
            "CaptchaControl1": captcha_code,
            "btnOK": "查詢",
        }

        try:
            resp = self.session.post(url, data=data, timeout=30)
            resp.raise_for_status()
            logger.debug("Submit query response: %d bytes", len(resp.text))
            return resp.text
        except requests.RequestException as e:
            logger.error("Submit query network error: %s", e)
            return None

    def _check_is_captcha_error(self, html: str) -> bool:
        """
        檢查回傳 HTML 是否包含驗證碼錯誤

        Args:
            html: HTML 原始碼

        Returns:
            True 為驗證碼錯誤
        """
        return "驗證碼" in html and "錯誤" in html

    def _extract_csv_url(self, html: str) -> Optional[str]:
        """從 POST 回傳的 HTML 中提取 CSV 下載 URL

        Args:
            html: POST bsMenu.aspx 的回傳 HTML

        Returns:
            bsContent.aspx 的完整 URL，或 None
        """
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=re.compile(r"bsContent\.aspx")):
            href = a.get("href", "")
            if href:
                return urljoin(BASE_URL, href)
        return None

    def _download_csv(self, url: str) -> Optional[str]:
        """下載 bsContent.aspx CSV 檔案 (big5 → utf-8)

        Args:
            url: bsContent.aspx 完整 URL

        Returns:
            CSV 文字內容 (utf-8)，或 None
        """
        self._throttle()
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            content = resp.content.decode("big5", errors="replace")
            logger.debug("CSV downloaded: %d chars", len(content))
            return content
        except requests.RequestException as e:
            logger.error("CSV download error: %s", e)
            return None

    @staticmethod
    def _parse_csv_row(parts: list, broker_data: dict) -> None:
        """解析 CSV 單列資料，彙總到 broker_data 字典"""
        try:
            broker_raw = parts[1].strip()
            buy_vol = int(parts[3].replace(",", "")) if parts[3].strip() else 0
            sell_vol = int(parts[4].replace(",", "")) if parts[4].strip() else 0

            # 從 broker 文字提取 ID 和名稱 (e.g. "1020合　　庫" → id="1020", name="合庫")
            match = re.match(r'(\d+)(.*)', broker_raw)
            if match:
                bid = match.group(1)
                bname = match.group(2).strip()

                if bid not in broker_data:
                    broker_data[bid] = {"name": bname, "buy": 0, "sell": 0}
                broker_data[bid]["buy"] += buy_vol
                broker_data[bid]["sell"] += sell_vol
        except (ValueError, IndexError, AttributeError):
            pass

    def _parse_csv(self, csv_text: str) -> List[Dict[str, Any]]:
        """解析 BSR CSV，彙總各家券商買賣量

        CSV 格式:
          券商買賣股票成交價量資訊
          股票代碼,="2330"
          序號,券商,價格,買進股數,賣出股數,,序號,券商,價格,買進股數,賣出股數
          1,1020合庫,2235.00,1260,1000,,2,1020合庫,2240.00,403,50

        每行有左右雙欄位 (以 ,, 分隔)，各含 seq, broker, price, buy_vol, sell_vol
        需逐券商加總買/賣量得到最終結果

        Returns:
            [{seq, broker_name, broker_id, buy_volume, sell_volume, net_volume}, ...]
        """
        lines = csv_text.split('\n')
        broker_data: Dict[str, Dict] = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 跳過 header 行
            if any(line.startswith(h) for h in ("券商買賣", "股票代碼", "序號")):
                continue

            parts = line.split(",")
            if len(parts) < 5:
                continue

            # 解析左側
            self._parse_csv_row(parts[0:5], broker_data)

            # 解析右側 (第 7 欄起，如果非空)
            if len(parts) >= 10 and parts[6].strip():
                self._parse_csv_row(parts[6:11], broker_data)

        # 依總交易量排序
        sorted_brokers = sorted(
            broker_data.items(),
            key=lambda x: x[1]["buy"] + x[1]["sell"],
            reverse=True
        )

        result = []
        for seq, (bid, info) in enumerate(sorted_brokers, 1):
            result.append({
                "seq": seq,
                "broker_name": info["name"],
                "broker_id": bid,
                "buy_volume": info["buy"],
                "sell_volume": info["sell"],
                "net_volume": info["buy"] - info["sell"],
            })

        return result

    def _parse_result(self, html: str) -> List[Dict[str, Any]]:
        """解析 BSR 查詢結果

        新流程: 檢查 CSV 下載連結 → 下載 CSV → 解析 CSV
        舊流程 (向後相容): 解析 table_blue HTML table

        Raises:
            BsrParseError: 無法解析
        """
        # 1. 嘗試新格式: CSV 下載
        csv_url = self._extract_csv_url(html)
        if csv_url:
            csv_text = self._download_csv(csv_url)
            if csv_text:
                return self._parse_csv(csv_text)

        # 2. 向後相容: 舊的 table_blue
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table", class_="table_blue")
        if table is not None:
            return self._parse_table_blue(table)

        raise BsrParseError("找不到 table_blue 表格或 CSV 下載連結")

    def _parse_table_blue(self, table) -> List[Dict[str, Any]]:
        """解析舊格式 table_blue (向後相容)"""
        rows = table.find_all("tr")
        if len(rows) < 2:
            return []

        result: List[Dict[str, Any]] = []
        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) < 5:
                continue

            try:
                seq = int(cells[0].get_text(strip=True))
            except (ValueError, TypeError):
                seq = 0

            broker_text = cells[1].get_text(strip=True)
            broker_name, broker_id = self._parse_broker_text(broker_text)

            buy_volume = self._parse_volume(cells[2].get_text(strip=True))
            sell_volume = self._parse_volume(cells[3].get_text(strip=True))
            net_volume = self._parse_volume(cells[4].get_text(strip=True))

            result.append({
                "seq": seq,
                "broker_name": broker_name,
                "broker_id": broker_id,
                "buy_volume": buy_volume,
                "sell_volume": sell_volume,
                "net_volume": net_volume,
            })

        return result

    @staticmethod
    def _parse_broker_text(text: str) -> tuple:
        """
        解析券商名稱文字 "名稱(代號)"

        Args:
            text: 券商名稱字串

        Returns:
            (broker_name, broker_id)
        """
        match = re.match(r'^(.+?)\((\d+)\)$', text)
        if match:
            return match.group(1), match.group(2)
        return text, ""

    @staticmethod
    def _parse_volume(text: str) -> int:
        """
        解析股數字串，移除逗號後轉 int

        Args:
            text: 股數字串，可能含逗號

        Returns:
            整數股數
        """
        try:
            return int(text.replace(",", ""))
        except (ValueError, AttributeError):
            return 0

    # ─── Main API ────────────────────────────────────────────────────

    def fetch_broker_data(self, symbol: str) -> List[Dict[str, Any]]:
        """
        完整查詢流程: refresh → captcha → submit → parse，含重試與 circuit breaker

        Args:
            symbol: 股票代號

        Returns:
            解析結果列表

        Raises:
            BsrCircuitBreakerOpen: circuit breaker 開啟
            BsrConnectionError: 網路連線錯誤
            BsrCaptchaError: 驗證碼錯誤重試耗盡
        """
        if not self._cb_allow_request():
            raise BsrCircuitBreakerOpen(
                f"Circuit breaker is OPEN, request rejected for symbol {symbol}"
            )

        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            logger.info("Fetch broker data attempt %d/%d for symbol %s",
                        attempt, self.max_retries, symbol)

            try:
                captcha_text = self._solve_captcha()
                if captcha_text is None:
                    raise BsrConnectionError("Failed to solve captcha")

                html = self._submit_query(symbol, captcha_text)
                if html is None:
                    raise BsrConnectionError("Query submission failed")

                if self._check_is_captcha_error(html):
                    logger.warning("Captcha error on attempt %d/%d", attempt, self.max_retries)
                    if attempt < self.max_retries:
                        self._throttle()
                        delay = min(2 ** attempt, 10)
                        time.sleep(delay)
                        continue
                    raise BsrCaptchaError(
                        f"Captcha verification failed after {self.max_retries} attempts"
                    )

                result = self._parse_result(html)
                self._cb_on_success()
                return result

            except (BsrConnectionError, BsrCaptchaError):
                raise
            except requests.RequestException as e:
                last_error = BsrConnectionError(f"Network error: {e}")
                logger.error("Network error on attempt %d: %s", attempt, e)
                self._cb_on_failure()
                if attempt < self.max_retries:
                    delay = min(2 ** attempt, 10)
                    time.sleep(delay)
                continue
            except BsrParseError:
                raise
            except Exception as e:
                last_error = BsrConnectionError(f"Unexpected error: {e}")
                logger.error("Unexpected error on attempt %d: %s", attempt, e)
                self._cb_on_failure()
                if attempt < self.max_retries:
                    delay = min(2 ** attempt, 10)
                    time.sleep(delay)
                continue

        raise last_error or BsrConnectionError("Unknown error")

    # ─── Helpers ─────────────────────────────────────────────────────

    def _throttle(self) -> None:
        """請求間隔控制"""
        time.sleep(self.request_interval)

    def close(self) -> None:
        """關閉 session"""
        self.session.close()
        logger.info("BsrClient session closed")

    def __enter__(self) -> BsrClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()
