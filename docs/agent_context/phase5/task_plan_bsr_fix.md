# BSR 解析器修正 — 任務規劃

> **觸發**: Phase 5 Stage 5 E2E 測試中發現 BSR 網站回傳格式變更
> **發現日期**: 2026-05-14
> **預計工時**: 3h
> **優先級**: 🔴 高 (資料源修復)

---

## 1. 問題描述

### 1.1 症狀

```
BsrClient.fetch_broker_data("2330") 拋錯:
  BsrParseError: 找不到 table_blue 表格
```

### 1.2 Root Cause

BSR 網站 (`https://bsr.twse.com.tw/bshtm/`) 改變了查詢結果的回傳方式：

| 項目 | 舊行為 (目前程式) | 新行為 (實際) |
|------|----------------|-------------|
| POST 回傳 | 含 `<table class='table_blue'>` 的 HTML | 表單頁 + `bsContent.aspx` 下載連結 |
| 資料位置 | 直接在 POST response 的 HTML 中 | 在 `bsContent.aspx?StkNo=XXX&RecCount=NN` 的 CSV 中 |
| 資料格式 | HTML `<table>` 已彙總每家券商 | CSV 逐筆明細 (依價格排列)，需自行加總 |
| Content-Type | `text/html` | `Application/octet-stream; charset=big5` |

### 1.3 實際測試驗證

手動測試確認新流程完全可行：

```
POST bsMenu.aspx (captcha=EE4ue, symbol=2330)
  → 回傳含「下載 2330 CSV」連結的表單頁
  → GET bsContent.aspx?StkNo=2330&RecCount=62
  → 成功解析出 434 家券商資料 ✅
```

---

## 2. 變更範圍

### 2.1 受影響檔案

| 檔案 | 操作 | 說明 | 變更行數 |
|------|------|------|---------|
| `src/spiders/bsr_client.py` | 📝 修改 | `_parse_result()` + 新增 CSV 下載/解析方法 | ~80 行 |
| `tests/test_bsr_client.py` | 📝 修改 | 更新測試 fixtures + 新增 CSV 測試 | ~100 行 |
| `docs/agent_context/phase5/development_log.md` | 📝 更新 | 記錄 BSR 變更與修復 | ~20 行 |

### 2.2 不受影響

| 模組 | 原因 |
|------|------|
| `src/spiders/broker_breakdown_spider.py` | 只調用 `BsrClient.fetch_broker_data()`，介面不變 |
| `src/spiders/ocr_solver.py` | captcha 流程不變 |
| `src/analytics/chip_profiler.py` | 讀 `broker_breakdown` 表，不受 BSR 格式影響 |
| `src/analytics/risk_assessor.py` | 同上 |
| `src/run_daily.py` | step_spiders 不變 |

---

## 3. 實作規劃

### 3.1 Stage A — BsrClient 修改 (1.5h)

#### A.1 新增 `_extract_csv_url(html)` 方法

從 POST 回傳的 HTML 中提取 `bsContent.aspx?StkNo=XXX&RecCount=NN` 連結。

```python
def _extract_csv_url(self, html: str) -> Optional[str]:
    """從 POST 回傳的 HTML 中提取 CSV 下載 URL

    Args:
        html: POST bsMenu.aspx 的回傳 HTML

    Returns:
        bsContent.aspx 的完整 URL，或 None
    """
    soup = BeautifulSoup(html, "lxml")
    # 尋找「下載 XXX CSV」連結
    for a in soup.find_all("a", href=re.compile(r"bsContent\.aspx")):
        href = a.get("href", "")
        if href:
            return urljoin(BASE_URL, href)
    return None
```

#### A.2 新增 `_download_csv(url)` 方法

下載 CSV 檔案，處理 big5 編碼。

```python
def _download_csv(self, url: str) -> Optional[str]:
    """下載 bsContent.aspx CSV 檔案

    Args:
        url: bsContent.aspx 完整 URL

    Returns:
        CSV 文字內容 (utf-8)，或 None
    """
    self._throttle()
    try:
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        # BSR 回傳 big5 編碼
        content = resp.content.decode("big5", errors="replace")
        logger.debug("CSV downloaded: %d chars", len(content))
        return content
    except requests.RequestException as e:
        logger.error("CSV download error: %s", e)
        return None
```

#### A.3 新增 `_parse_csv(csv_text)` 方法

解析 CSV 格式，逐券商加總買/賣量。

**CSV 格式**:
```
券商買賣股票成交價量資訊
股票代碼,="2330"
序號,券商,價格,買進股數,賣出股數,,序號,券商,價格,買進股數,賣出股數
1,1020合　　庫,2235.00,1260,1000,,2,1020合　　庫,2240.00,403,50
3,1020合　　庫,2245.00,458,172,,4,1020合　　庫,2250.00,2467,8155
...
```

**解析邏輯**:
1. 跳過前 3 行 header
2. 每行有雙欄位 (左/右，以 `,,` 分隔)
3. 左: `seq, broker, price, buy_vol, sell_vol`
4. 右: `seq, broker, price, buy_vol, sell_vol` (可能為空)
5. 從 broker 欄位提取 ID + 名稱
6. 依 broker_id 彙總 buy_volume, sell_volume
7. 計算 net_volume = buy - sell
8. 依 buy_volume 排序給 seq

```python
def _parse_csv(self, csv_text: str) -> List[Dict[str, Any]]:
    """解析 BSR CSV 格式，彙總各家券商買賣量

    Returns:
        同 _parse_result 格式:
        [{seq, broker_name, broker_id, buy_volume, sell_volume, net_volume}, ...]
    """
    lines = csv_text.split('\n')
    broker_data: Dict[str, Dict] = {}

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 跳過 header
        if any(line.startswith(h) for h in ("券商買賣", "股票代碼", "序號")):
            continue

        parts = line.split(",")
        if len(parts) < 5:
            continue

        # 解析左側
        self._parse_csv_row(parts[0:5], broker_data)

        # 解析右側 (如有)
        if len(parts) >= 10 and parts[6].strip():
            self._parse_csv_row(parts[6:11], broker_data)

    # 排序並輸出
    sorted_brokers = sorted(
        broker_data.items(),
        key=lambda x: x[1]["buy_volume"] + x[1]["sell_volume"],
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
```

#### A.4 修改 `_parse_result(html)` 方法

改為新流程：
1. 先從 HTML 中找 `bsContent.aspx` 下載連結
2. 若有 → 下載 CSV → 解析 CSV → 回傳
3. 若無 → 嘗試舊的 `table_blue` 解析 (向後相容)
4. 若都沒有 → 拋 `BsrParseError`

```python
def _parse_result(self, html: str) -> List[Dict[str, Any]]:
    # 新流程: 檢查 CSV 下載連結
    csv_url = self._extract_csv_url(html)
    if csv_url:
        csv_text = self._download_csv(csv_url)
        if csv_text:
            return self._parse_csv(csv_text)

    # 向後相容: 檢查舊的 table_blue
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", class_="table_blue")
    if table is not None:
        return self._parse_table_blue(table)

    raise BsrParseError("找不到 table_blue 表格或 CSV 下載連結")
```

### 3.2 Stage B — 測試更新 (1h)

#### B.1 更新測試 Fixtures

```python
_SAMPLE_CSV_URL = "bsContent.aspx?StkNo=2330&RecCount=62"

_SAMPLE_POST_RESPONSE_HTML = """\
<html><body>
<form>
<input type="hidden" id="__VIEWSTATE" value="..." />
<div><a href="bsContent.aspx?StkNo=2330&RecCount=62">下載  2330 CSV</a></div>
</form>
</body></html>"""

_SAMPLE_CSV_DATA = """\
券商買賣股票成交價量資訊
股票代碼,="2330"
序號,券商,價格,買進股數,賣出股數,,序號,券商,價格,買進股數,賣出股數
1,1020合　　庫,2235.00,1260,1000,,2,1020合　　庫,2240.00,403,50
3,1020合　　庫,2245.00,458,172,,4,1020合　　庫,2250.00,2467,8155
"""

_SAMPLE_OLD_HTML = """\
<html><body>
<table class='table_blue'>
<tr><td>1</td><td>凱基-台北(9200)</td><td>1,234,567</td><td>567,890</td><td>666,677</td></tr>
</table>
</body></html>"""
```

#### B.2 更新測試案例

| 測試 | 說明 | 類型 |
|------|------|------|
| `test_extract_csv_url_found` | 從 HTML 提取 CSV URL | 新測試 |
| `test_extract_csv_url_not_found` | 無 CSV 連結回傳 None | 新測試 |
| `test_csv_parse_success` | CSV 正確解析出券商資料 | 新測試 |
| `test_csv_parse_aggregation` | 同一券商多筆價格正確加總 | 新測試 |
| `test_csv_parse_empty` | CSV 無資料回傳 [] | 新測試 |
| `test_csv_parse_header_only` | 只有 header 無資料 | 新測試 |
| `test_parse_result_new_format` | `_parse_result` 走 CSV 新流程 | 新測試 |
| `test_parse_result_fallback_old` | `_parse_result` 無 CSV 時 fallback 到 table_blue | 更新既有 |
| `test_parse_result_no_data` | 兩種格式都沒有拋錯誤 | 更新既有 |
| `test_fetch_broker_data_csv_flow` | 完整流程用 CSV 格式 | 更新既有 |
| `test_fetch_broker_data_fallback_old` | 完整流程 fallback 到舊格式 | 更新既有 |

**進度: 既有 8 個 parse 測試更新 + 6 個新測試 = 14 個**

### 3.3 Stage C — 文件更新 (0.5h)

1. 更新 `docs/agent_context/phase5/development_log.md`
2. 更新 `docs/agent_context/phase5/task_plan_stage5.md` (E2E 測試失敗原因說明)

---

## 4. 完成標準

| 檢查項 | 通過條件 |
|--------|---------|
| CSV 解析 | 可解析真實 BSR CSV 並正確加總券商買賣量 |
| 舊格式向後相容 | 仍可解析 `table_blue` HTML |
| BsrClient 測試 | 全部通過 (59 + 新測試) |
| BrokerBreakdownSpider 測試 | 全部通過 (18) |
| Stage 4 測試 | 全部通過 (72) |
| E2E test_fetch_bsr_data | ✅ 通過 (不再拋找不到 table_blue) |

---

## 5. 禁止事項

- ❌ 禁止修改 BrokerBreakdownSpider 的對外介面 (`fetch_broker_breakdown` 的參數/回傳值)
- ❌ 禁止修改 DB schema
- ❌ 禁止修改 `_parse_broker_text` 和 `_parse_volume` (可重用)
- ❌ 禁止移除舊的 `table_blue` 解析邏輯 (向後相容)

---

## 6. 風險評估

| 風險 | 機率 | 影響 | 緩解 |
|------|------|------|------|
| BSR CSV 格式再次變更 | 低 | 高 | 已有 circuit breaker + retry，新格式改為先抓 CSV 再 fallback 舊格式 |
| big5 解碼部分亂碼 | 低 | 低 | `errors="replace"` 確保不回傳 None |
| 非交易時段 CSV 回傳空資料 | 中 | 低 | CSV 無券商資料時回傳 `[]`，不拋錯 |
| BSR 同時支援新舊兩種格式 | 中 | 低 | `_parse_result` 先檢查 CSV 再 fallback table_blue |

---

## 7. 時程

| 階段 | 工時 | 說明 |
|------|------|------|
| A: BsrClient 修改 | 1.5h | CSV 下載/解析 + `_parse_result` 重構 |
| B: 測試更新 | 1.0h | 更新 fixtures + 新增 6 測試 |
| C: 文件更新 | 0.5h | development_log |
| **總計** | **3.0h** | |
