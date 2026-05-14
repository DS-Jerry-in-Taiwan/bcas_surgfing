# Phase 5 Stage 2 — 任務規劃文件

> 建立日期: 2026-05-13
> 階段: Phase 5 Stage 2 — BSR 客戶端實作
> 預估工時: 6h (核心) + 4h (buffer) = 10h

---

## 1. 需求確認

### 1.1 任務目標

將 BSR 網站 (`https://bsr.twse.com.tw/bshtm/`) 的完整查詢流程封裝為可測試的 Python 模組，包含 Session 管理、Captcha 下載與 OCR、表單提交、結果解析、重試與錯誤處理。

### 1.2 成功標準

| 標準 | 說明 | 驗證方式 |
|------|------|---------|
| OcrSolver 可正確封裝 ddddocr | `solve(image_bytes)` 回傳 5 碼字串 | 單元測試 (mock ddddocr) |
| BsrClient 可建立並維持 Session | GET bsMenu.aspx 成功解析 ASP.NET state | 整合測試 (mock requests) |
| Captcha 下載流程正確 | 提取 GUID → 下載 PNG → OCR → 提交 | 整合測試 (mock requests) |
| 表單提交與結果解析 | POST 正確參數 → 解析 HTML table → 回傳 dict list | 單元測試 + mock HTML |
| 重試機制 | captcha 錯誤自動重試 (max 3)，指數退避 | 單元測試 |
| Circuit Breaker | 連續 5 次失敗暫停 60s | 單元測試 |
| 所有測試通過 | `pytest tests/test_bsr_client.py -v` | ✅ Green |

### 1.3 任務邊界

**範圍內:**
- ✅ `src/spiders/ocr_solver.py` — ddddocr 封裝模組 (新建立)
- ✅ `src/spiders/bsr_client.py` — BSR 客戶端 (新建立)
- ✅ `tests/test_bsr_client.py` — 單元測試與整合測試
- ✅ `requirements.txt` — 新增 `ddddocr` 依賴

**範圍外:**
- ❌ 不改寫 `broker_breakdown_spider.py` (這是 Stage 3)
- ❌ 不修改任何 DB schema
- ❌ 不修改 `run_daily.py`
- ❌ 不修改 `RiskAssessor` (這是 Stage 4)
- ❌ 不處理鉅額交易 (`RadioButton_Excd`)
- ❌ 不訓練自定義 OCR 模型

---

## 2. 架構掃描

### 2.1 相關模組

| 模組 | 說明 | 相依關係 |
|------|------|---------|
| `src/spiders/broker_breakdown_spider.py` | 目標 spider (Stage 3 改寫) | Stage 2 完成後才能改寫 |
| `src/framework/base_spider.py` | BaseSpider 基底類 | 提供 SpiderResponse、collect_only 模式 |
| `src/framework/base_item.py` | BrokerBreakdownItem | 最終輸出的 Item 格式 (目前 BsrClient 回傳 dict，Stage 3 才轉 Item) |
| `tests/test_bsr_captcha.py` | Stage 1 產出的獨立測試 | 驗證 BSR Session/Captcha 流程正確 |
| `src/spiders/` | 爬蟲目錄 | 新模組放置於此 |

### 2.2 外部依賴

| 依賴 | 版本 | 用途 |
|------|------|------|
| `ddddocr` | 1.6.1 | OCR 辨識 (已安裝) |
| `onnxruntime` | 1.26.0 | ONNX 推論引擎 (已安裝) |
| `requests` | - | HTTP 請求 (已安裝) |
| `beautifulsoup4` | - | HTML 解析 (已安裝) |
| `lxml` | - | BeautifulSoup 解析器 (已安裝) |

### 2.3 設計模式

- **Facade 模式**: `BsrClient` 對外提供簡單的 `fetch_broker_data(symbol)` 介面，內部封裝 Session、Captcha、OCR、Submit、Parse 等複雜流程
- **Adapter 模式**: `OcrSolver` 封裝 ddddocr，提供統一的 `solve(image_bytes)` 介面
- **Circuit Breaker**: 保護 BSR 服務不被過度請求

---

## 3. 階段規劃

### 3.1 階段 2.1 — OcrSolver 封裝模組 (1h)

**檔案**: `src/spiders/ocr_solver.py`

**實作內容:**
```python
class OcrSolver:
    """ddddocr 封裝，提供統一的 captcha 解碼介面"""
    
    def __init__(self, gpu: bool = False):
        self._ocr = ddddocr.DdddOcr()
    
    def solve(self, image_bytes: bytes) -> str:
        return self._ocr.classification(image_bytes)
    
    def solve_with_preprocess(self, image_bytes: bytes, threshold: int = 128) -> str:
        # 灰階 → 二值化 → OCR
```

**測試策略:**
- Mock ddddocr 的 `classification()` 方法
- 測試正常回傳 5 碼字串
- 測試預處理路徑

### 3.2 階段 2.2 — BSR Session 管理 (2h)

**檔案**: `src/spiders/bsr_client.py` (部分)

**實作內容:**
```python
class BsrClient:
    BASE_URL = "https://bsr.twse.com.tw/bshtm/"
    
    def __init__(self, max_retries: int = 3):
        self.session = requests.Session()
        self.ocr = OcrSolver()
        self.max_retries = max_retries
        # ASP.NET state
        self.viewstate = None
        self.eventvalidation = None
        self.viewstategenerator = None
        self.captcha_guid = None
        # Circuit breaker
        self._failure_count = 0
        self._circuit_open_until = 0
    
    def _refresh_session(self) -> bool:
        """GET bsMenu.aspx → 解析 ASP.NET state + captcha GUID"""
    
    def _parse_aspnet_state(self, html: str) -> dict:
        """從 HTML 解析 __VIEWSTATE, __EVENTVALIDATION, __VIEWSTATEGENERATOR"""
    
    def _extract_captcha_guid(self, html: str) -> str:
        """從 HTML 提取 CaptchaImage.aspx?guid=XXX"""
```

**測試策略:**
- Mock `requests.Session.get()` 回傳 BSR 頁面 HTML
- 驗證正確解析 __VIEWSTATE / __EVENTVALIDATION / GUID
- 測試 Session 過期後自動刷新

### 3.3 階段 2.3 — Captcha 下載 + OCR 流程 (1h)

**檔案**: `src/spiders/bsr_client.py` (續)

**實作內容:**
```python
    def _get_captcha_image(self) -> Optional[bytes]:
        """下載 Captcha 圖片 (PNG bytes)"""
    
    def _solve_captcha(self) -> Optional[str]:
        """完整 captcha 流程: refresh → download → OCR"""
```

**測試策略:**
- Mock `_get_captcha_image()` 回傳假 PNG
- Mock OcrSolver 回傳假 captcha code
- 端到端 mock 驗證完整流程

### 3.4 階段 2.4 — 表單提交 + 結果解析 (1.5h)

**檔案**: `src/spiders/bsr_client.py` (續)

**實作內容:**
```python
    def _submit_query(self, symbol: str, captcha_code: str) -> Optional[str]:
        """POST bsMenu.aspx → 回傳結果 HTML"""
    
    def _parse_result(self, html: str) -> List[Dict]:
        """解析 BSR 回傳的 HTML table → dict list
    
    BrokerBreakdown格式:
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
    """
    
    def fetch_broker_data(self, symbol: str) -> List[Dict]:
        """完整流程: refresh → captcha → submit → parse (含重試)"""
```

**測試策略:**
- 準備 BSR 回傳的 HTML fixture (從真實 BSR 頁面擷取)
- 測試 `_parse_result()` 正確解析表格
- Mock `_submit_query()` 驗證 POST 資料結構

### 3.5 階段 2.5 — 重試與錯誤處理 (1h)

**檔案**: `src/spiders/bsr_client.py` (錯誤處理)

**實作內容:**
```python
    class BsrError(Exception): pass
    class BsrConnectionError(BsrError): pass
    class BsrCaptchaError(BsrError): pass
    class BsrParseError(BsrError): pass
    class BsrCircuitBreakerOpen(BsrError): pass
    
    def _check_captcha_error(self, html: str) -> bool:
        """檢查回傳 HTML 是否包含驗證碼錯誤訊息"""
    
    def fetch_broker_data(self, symbol: str) -> List[Dict]:
        """含重試 + circuit breaker 的完整流程"""
```

**測試策略:**
- Mock `_submit_query()` 先回傳驗證碼錯誤，再回傳成功
- 驗證重試次數 = max_retries
- 測試 Circuit Breaker 開啟/關閉邏輯
- 測試指數退避 (使用 `freezegun` 或 time mock)

---

## 4. 完成標準

### 4.1 測試指標

| 測試 | 類型 | 案例數 | 說明 |
|------|------|--------|------|
| `test_ocr_solver.py` | 單元測試 | ≥ 5 | OcrSolver 封裝正確 |
| `test_bsr_client_session.py` | 單元測試 | ≥ 8 | Session/ASP.NET state 管理 |
| `test_bsr_client_captcha.py` | 單元測試 | ≥ 5 | Captcha 下載 + OCR 流程 |
| `test_bsr_client_submit.py` | 單元測試 | ≥ 6 | 表單提交 + 結果解析 |
| `test_bsr_client_retry.py` | 單元測試 | ≥ 6 | 重試 + Circuit Breaker |
| **合計** | | **≥ 30** | |

### 4.2 驗收清單

- [ ] `src/spiders/ocr_solver.py` 實作完成，所有方法有 docstring
- [ ] `src/spiders/bsr_client.py` 實作完成，所有方法有 docstring
- [ ] 所有測試通過 (`pytest tests/test_bsr_client.py -v`)
- [ ] BsrClient 的 `fetch_broker_data("2330")` 正確回傳 List[Dict]
- [ ] 重試機制在 captcha 錯誤時正確觸發
- [ ] Circuit Breaker 在連續失敗時正確開啟
- [ ] 文件已更新 (此 task_plan 中的完成項目打勾)

---

## 5. 開發過程記錄

### 5.1 注意事項

1. **BSR ASP.NET Web Forms**: 需要處理 `__VIEWSTATE`、`__EVENTVALIDATION`、`__VIEWSTATEGENERATOR` 三個隱藏欄位
2. **Session 管理**: 使用 `requests.Session()` 自動維持 Cookie
3. **User-Agent**: 必須設定，否則 BSR 可能拒絕請求
4. **請求間隔**: 測試時建議 2-3 秒間隔避免被 BAN
5. **Captcha GUID**: 每次 `GET bsMenu.aspx` 產生新的 GUID，需每次重新解析

### 5.2 禁止事項

- ❌ 不要在 `bsr_client.py` 中引入 `BrokerBreakdownSpider` 或 `BaseSpider` (BsrClient 是獨立模組)
- ❌ 不要在 `bsr_client.py` 中使用 feapder 相關程式碼
- ❌ 不要建立 `BrokerBreakdownItem` — BsrClient 回傳 dict，由 spider 轉為 Item
- ❌ 不要直接寫入資料庫

### 5.3 相關文件

| 文件 | 位置 |
|------|------|
| Phase 5 開發目標 | `docs/agent_context/phase5/01_dev_goal_context.md` |
| 工作分解 | `docs/agent_context/phase5/02_work_breakdown.md` |
| 架構設計 | `docs/agent_context/phase5/arch_design.md` |
| OCR 測試計畫 | `docs/agent_context/phase5/03_ocr_test_plan.md` |
| 風險評估 | `docs/agent_context/phase5/05_risk_assessment.md` |
| Stage 1 測試 | `tests/test_bsr_captcha.py` |
