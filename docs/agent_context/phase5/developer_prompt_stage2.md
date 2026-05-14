# Phase 5 Stage 2 — 開發者 Prompt

## 任務: BSR 客戶端實作 (OcrSolver + BsrClient)

> 你是一個 Python 開發者，負責實作 Phase 5 Stage 2 的 BSR 客戶端模組。
> ddddocr 已安裝 (v1.6.1)，Stage 1 OCR 測試已通過 (100% 辨識率，26/26)。
> 請實作以下模組與對應的測試，並確保所有測試通過。

---

## 一、工作目錄

```
專案根目錄: /home/ubuntu/projects/bcas_quant
```

## 二、你必須實作的檔案

### 2.1 `src/spiders/ocr_solver.py` — ddddocr 封裝模組

**規格:**
```python
class OcrSolver:
    """
    ddddocr 封裝，提供統一的 captcha 解碼介面
    
    用法:
        solver = OcrSolver()
        code = solver.solve(image_bytes)  # "A3B9K"
        code = solver.solve_with_preprocess(image_bytes, threshold=128)
    """
    
    def __init__(self, gpu: bool = False):
        """初始化 ddddocr 實例"""
    
    def solve(self, image_bytes: bytes) -> str:
        """
        辨識 captcha 圖片
        
        Args:
            image_bytes: PNG 圖片 bytes
        
        Returns:
            辨識結果字串 (BSR Captcha 預期 5 碼)
        """
    
    def solve_with_preprocess(self, image_bytes: bytes, threshold: int = 128) -> str:
        """
        先進行圖片預處理再辨識 (降級方案)
        
        1. PIL 轉灰階
        2. 二值化 (threshold)
        3. OCR 辨識
        
        Args:
            image_bytes: PNG 圖片 bytes
            threshold: 二值化門檻值 (0-255)
        
        Returns:
            辨識結果字串
        """
```

### 2.2 `src/spiders/bsr_client.py` — BSR 網站客戶端

**自訂義異常:**
```python
class BsrError(Exception): pass
class BsrConnectionError(BsrError): pass      # 網路問題
class BsrCaptchaError(BsrError): pass         # 驗證碼錯誤（重試用）
class BsrParseError(BsrError): pass           # HTML 解析失敗
class BsrCircuitBreakerOpen(BsrError): pass    # Circuit Breaker 開啟中
```

**BsrClient 類別:**

```python
class BsrClient:
    """
    BSR 網站客戶端
    
    封裝 BSR 的完整查詢流程:
    Session → Captcha → OCR → 表單提交 → 結果解析
    
    用法:
        client = BsrClient()
        data = client.fetch_broker_data("2330")
        # [{"broker_id": "9200", "broker_name": "凱基-台北", ...}, ...]
        client.close()
    """
    
    BASE_URL = "https://bsr.twse.com.tw/bshtm/"
    # Circuit Breaker 常數
    FAILURE_THRESHOLD = 5
    RECOVERY_TIMEOUT = 60
    
    def __init__(self, max_retries: int = 3, request_interval: float = 2.0):
        """
        Args:
            max_retries: captcha 錯誤最大重試次數 (預設 3)
            request_interval: 每次 request 間隔秒數 (預設 2s)
        """
    
    # ─── Session 管理 ──────────────────────────────────
    
    def _refresh_session(self) -> bool:
        """
        GET bsMenu.aspx 取得最新的 ASP.NET state
        
        流程:
        1. GET https://bsr.twse.com.tw/bshtm/bsMenu.aspx
        2. 用 BeautifulSoup 解析 HTML
        3. 提取 __VIEWSTATE, __EVENTVALIDATION, __VIEWSTATEGENERATOR
        4. 提取 captcha GUID (from <img src='CaptchaImage.aspx?guid=XXX'>)
        
        Returns:
            True 表示成功，False 表示失敗
        """
    
    def _parse_aspnet_state(self, html: str) -> dict:
        """
        從 HTML 解析 ASP.NET Web Forms 隱藏欄位
        
        Args:
            html: bsMenu.aspx 的 HTML
        
        Returns:
            {
                "viewstate": "...",
                "eventvalidation": "...",
                "viewstategenerator": "...",
            }
        
        使用 BeautifulSoup + lxml 解析器:
            soup.find("input", {"name": "__VIEWSTATE"})["value"]
        """
    
    def _extract_captcha_guid(self, html: str) -> Optional[str]:
        """
        從 HTML 提取 Captcha GUID
        
        <img src='CaptchaImage.aspx?guid=70edbdfe-7f8d-4bc5-a922-a1e4dc44cd47'>
        
        Returns:
            GUID 字串 (UUID v4)，找不到回傳 None
        """
    
    # ─── Captcha 流程 ──────────────────────────────────
    
    def _get_captcha_image(self) -> Optional[bytes]:
        """
        下載 Captcha 圖片
        
        GET CaptchaImage.aspx?guid={self.captcha_guid}
        
        Returns:
            PNG bytes，失敗回傳 None
        """
    
    def _solve_captcha(self) -> Optional[str]:
        """
        完整 captcha 流程 (一輪)
        
        1. 確保 session 已刷新 (若 viewstate 為 None 則自動 refresh)
        2. 下載 captcha 圖片
        3. OCR 辨識
        
        Returns:
            5 碼驗證碼字串，失敗回傳 None
        """
    
    # ─── 表單提交 ──────────────────────────────────────
    
    def _submit_query(self, symbol: str, captcha_code: str) -> Optional[str]:
        """
        提交查詢表單
        
        POST https://bsr.twse.com.tw/bshtm/bsMenu.aspx
        Content-Type: application/x-www-form-urlencoded
        
        Body 參數:
            __VIEWSTATE: self.viewstate
            __EVENTVALIDATION: self.eventvalidation
            __VIEWSTATEGENERATOR: self.viewstategenerator
            RadioButton_Normal: "RadioButton_Normal"
            TextBox_Stkno: symbol (如 "2330")
            CaptchaControl1: captcha_code (如 "A3B9K")
            btnOK: "查詢"
        
        Returns:
            結果 HTML 字串，失敗回傳 None
        """
    
    def _check_is_captcha_error(self, html: str) -> bool:
        """
        檢查回傳 HTML 是否表示驗證碼錯誤
        
        搜尋 "驗證碼" 和 "錯誤" 關鍵字
        
        Returns:
            True 表示驗證碼錯誤，需要重試
        """
    
    # ─── 結果解析 ──────────────────────────────────────
    
    def _parse_result(self, html: str) -> List[Dict]:
        """
        解析 BSR 回傳的結果 HTML
        
        BSR 結果頁面包含 <table> 格式的買賣超資料。
        需解析的欄位:
            - 排名 (序號)
            - 券商名稱 (含代號)
            - 買進股數 (可能包含逗號)
            - 賣出股數 (可能包含逗號)
            - 淨買超股數 (可能包含逗號)
        
        解析策略:
        1. 使用 BeautifulSoup 查找結果表格
        2. 遍歷 <tr> 跳過表頭
        3. 從 <td> 提取各欄位
        4. 券商名稱格式: "券商名稱(代號)" → 需拆分為 broker_name 和 broker_id
        
        Args:
            html: BSR 回傳的結果 HTML
        
        Returns:
            List[Dict]:
                [
                    {
                        "broker_id": "9200",
                        "broker_name": "凱基-台北",
                        "buy_volume": 123456,
                        "sell_volume": 78901,
                        "net_volume": 44555,
                    },
                    ...
                ]
        
        Raises:
            BsrParseError: HTML 解析失敗
        """
    
    # ─── 完整流程 ──────────────────────────────────────
    
    def fetch_broker_data(self, symbol: str) -> List[Dict]:
        """
        完整查詢流程 (含重試與 Circuit Breaker)
        
        流程:
        1. 檢查 Circuit Breaker 狀態 (若開啟則拋錯)
        2. 刷新 Session
        3. 下載 Captcha + OCR
        4. 提交查詢
        5a. 若驗證碼錯誤 → 重試 (最多 max_retries 次)
        5b. 若成功 → 解析結果
        6. 成功時重置 failure_count，失敗時遞增
        
        Circuit Breaker 邏輯:
        - 連續 FAILURE_THRESHOLD 次失敗 → 開啟 (OPEN)
        - OPEN 狀態持續 RECOVERY_TIMEOUT 秒
        - 之後允許一次嘗試 (HALF_OPEN)
        - 若成功 → 關閉 (CLOSED)
        - 若失敗 → 重新開啟
        
        Args:
            symbol: 股票代號 (如 "2330")
        
        Returns:
            List[Dict] BrokerBreakdown 格式
        
        Raises:
            BsrConnectionError: 網路連線失敗
            BsrCaptchaError: 超過最大重試次數
            BsrParseError: HTML 解析失敗
            BsrCircuitBreakerOpen: Circuit Breaker 開啟中
        """
    
    def _handle_retry(self, attempt: int, error: str) -> None:
        """
        重試等待處理
        
        指數退避: wait = 2^attempt 秒
        但最多 10 秒
        
        Args:
            attempt: 當前重試次數 (0-based)
            error: 錯誤訊息 (僅用於日誌)
        """
    
    # ─── 資源清理 ──────────────────────────────────────
    
    def close(self):
        """關閉 session，釋放資源"""
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
```

### 2.3 `tests/test_bsr_client.py` — 完整測試套件

**測試策略:**
- 全部使用 mock (`unittest.mock.patch`) 避免真實網路請求
- 使用 fixture HTML 字串模擬 BSR 回傳
- 測試所有正常/異常/邊界情況

**最少測試案例 (30+):**

| 測試類別 | 案例 | 說明 |
|---------|------|------|
| **OcrSolver** | `test_solve_returns_string` | `solve()` 回傳 str |
| | `test_solve_with_bytes` | 傳入 PNG bytes 正常運作 |
| | `test_solve_with_preprocess` | 預處理路徑正常 |
| | `test_solve_empty_bytes` | 空 bytes 不拋錯 |
| | `test_ocr_initialization` | `__init__` 建立 ddddocr 實例 |
| **BsrClient Init** | `test_init_default_params` | 預設參數正確 |
| | `test_init_custom_params` | 自訂參數 |
| | `test_session_created` | session 為 requests.Session |
| | `test_ocr_instance` | ocr 為 OcrSolver 實例 |
| **Session Refresh** | `test_refresh_session_success` | 成功解析 HTML |
| | `test_refresh_session_sets_viewstate` | viewstate 正確設定 |
| | `test_refresh_session_network_error` | 網路錯誤回傳 False |
| | `test_refresh_session_missing_viewstate` | 缺少 viewstate 回傳 False |
| **Captcha Extract** | `test_extract_guid_success` | 正確提取 GUID |
| | `test_extract_guid_no_img_tag` | 無 img 標籤回傳 None |
| | `test_extract_guid_no_guid_param` | 無 guid 參數回傳 None |
| **Captcha Download** | `test_get_captcha_image_success` | 成功下載 PNG |
| | `test_get_captcha_image_no_guid` | 無 GUID 回傳 None |
| | `test_get_captcha_image_http_error` | HTTP 錯誤回傳 None |
| **Form Submit** | `test_submit_query_success` | 成功提交並回傳 HTML |
| | `test_submit_query_network_error` | 網路錯誤回傳 None |
| | `test_submit_query_http_error` | HTTP 錯誤回傳 None |
| **Captcha Error Check** | `test_check_captcha_error_true` | 包含驗證碼錯誤訊息 |
| | `test_check_captcha_error_false` | 無錯誤訊息 |
| | `test_check_captcha_error_empty_html` | 空 HTML 回傳 False |
| **Result Parse** | `test_parse_result_success` | 正確解析完整表格 |
| | `test_parse_result_empty_table` | 無資料表格 |
| | `test_parse_result_malformed_html` | HTML 結構異常拋 BsrParseError |
| | `test_parse_result_broker_name_format` | 券商名稱 "名稱(代號)" 正確拆分 |
| | `test_parse_result_volume_with_commas` | 股數含逗號正確解析 |
| **Fetch Broker Data** | `test_fetch_broker_data_success` | 完整流程成功 |
| | `test_fetch_broker_data_captcha_retry` | Captcha 錯誤後重試成功 |
| | `test_fetch_broker_data_all_retries_fail` | 全部重試失敗拋 BsrCaptchaError |
| | `test_fetch_broker_data_parse_error` | 解析失敗拋 BsrParseError |
| **Circuit Breaker** | `test_circuit_breaker_opens_after_threshold` | 連續失敗後開啟 |
| | `test_circuit_breaker_closes_after_success` | 成功後關閉 |
| | `test_circuit_breaker_raises_when_open` | 開啟時請求拋錯 |
| | `test_circuit_breaker_half_open_recovers` | 半開狀態成功後關閉 |

---

## 三、實作要求

### 3.1 程式碼規範

- 所有 class/method 須有完整 docstring (Args/Returns/Raises)
- 使用 type hints
- 遵循現有專案風格 (參考 `src/spiders/broker_breakdown_spider.py`)
- 錯誤處理完整，不讓未處理的 exception 穿透
- 日誌使用 `logging.getLogger(__name__)`，不要用 `print()`

### 3.2 BSR ASP.NET 注意事項

1. **__VIEWSTATE**: 在 `<input type="hidden" name="__VIEWSTATE" value="...">` 中
2. **__EVENTVALIDATION**: 同上，name="__EVENTVALIDATION"
3. **__VIEWSTATEGENERATOR**: 同上，name="__VIEWSTATEGENERATOR"
4. **Captcha GUID**: 在 `<img src='CaptchaImage.aspx?guid=...'>` 中，是 UUID v4 格式
5. **表單提交**: POST 到 `bsMenu.aspx`，Content-Type: `application/x-www-form-urlencoded`
6. **結果頁面**: BSR 使用 frameset，結果在另一個 frame (bsResult.aspx)，但 form submit 後回傳的 HTML 包含結果表格

### 3.3 BSR 結果 HTML 解析

由於尚未擷取真實的 BSR 結果 HTML，測試中使用以下 Mock HTML：

```python
SAMPLE_BSR_RESULT_HTML = """
<html>
<body>
<table class='table_blue'>
  <tr>
    <td>序號</td>
    <td>券商名稱</td>
    <td>買進股數</td>
    <td>賣出股數</td>
    <td>淨買超</td>
  </tr>
  <tr>
    <td>1</td>
    <td>凱基-台北(9200)</td>
    <td>1,234,567</td>
    <td>567,890</td>
    <td>666,677</td>
  </tr>
  <tr>
    <td>2</td>
    <td>美商高盛(1020)</td>
    <td>987,654</td>
    <td>432,100</td>
    <td>555,554</td>
  </tr>
</table>
</body>
</html>
"""
```

> ⚠️ **重要**: 以上 HTML 是根據推測的 BSR 結構。實作 `_parse_result()` 時，使用彈性的選擇器（如 `soup.find_all("tr")` + 啟發式欄位比對），以便後續根據真實 HTML 調整。

### 3.4 測試環境

```bash
# 安裝相依套件
pip install ddddocr beautifulsoup4 lxml requests pytest

# 執行測試
cd /home/ubuntu/projects/bcas_quant
python -m pytest tests/test_bsr_client.py -v

# 只看失敗
python -m pytest tests/test_bsr_client.py -v --tb=short

# 特定測試
python -m pytest tests/test_bsr_client.py::TestOcrSolver::test_solve_returns_string -v
```

### 3.5 驗收標準

1. `python -m pytest tests/test_bsr_client.py -v` 全部通過 (30+ 測試)
2. `python -m pytest tests/ -v` 不影響現有測試 (回歸)
3. `python -c "from src.spiders.ocr_solver import OcrSolver; print(OcrSolver().solve(b'test'))"` 可執行
4. `python -c "from src.spiders.bsr_client import BsrClient; c=BsrClient(); print(c.BASE_URL); c.close()"` 可 import

---

## 四、檔案變更摘要

| 操作 | 檔案 | 說明 |
|------|------|------|
| ✨ 新增 | `src/spiders/ocr_solver.py` | ddddocr 封裝模組 |
| ✨ 新增 | `src/spiders/bsr_client.py` | BSR 客戶端 (核心) |
| ✨ 新增 | `tests/test_bsr_client.py` | 完整測試套件 (30+) |
| 📝 修改 | `requirements.txt` | 新增 ddddocr 依賴 (若尚未存在) |

## 五、邊界與禁止事項

- ❌ 不要修改 `src/spiders/broker_breakdown_spider.py` (Stage 3 再做)
- ❌ 不要修改 `src/analytics/risk_assessor.py` (Stage 4 再做)
- ❌ 不要修改 `src/analytics/chip_profiler.py`
- ❌ 不要修改 `src/run_daily.py`
- ❌ 不要修改 `src/framework/` 下的任何檔案
- ❌ 不要直接寫入資料庫
- ❌ 不要建立 `BrokerBreakdownItem` (BsrClient 回傳 dict，Stage 3 才轉 Item)
- ❌ 不要在 `bsr_client.py` 中使用 feapder 相關程式碼
