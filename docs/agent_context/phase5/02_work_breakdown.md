# Phase 5 — 工作分解結構 (WBS)

---

## 階段總覽

```
Phase 5: BSR Captcha OCR 解決方案
├── 階段 1: OCR 環境與辨識率測試 (3h)
│   ├── 1.1 安裝 ddddocr + 相依套件
│   ├── 1.2 撰寫 Captcha 下載腳本
│   ├── 1.3 執行批量辨識測試 (100+ 次)
│   └── 1.4 分析結果與決策
├── 階段 2: BSR 客戶端實作 (6h)
│   ├── 2.1 實作 OCR Solver 封裝模組
│   ├── 2.2 實作 BSR Session 管理
│   ├── 2.3 實作 Captcha 下載 + OCR 流程
│   ├── 2.4 實作表單提交 + 結果解析
│   └── 2.5 實作重試與錯誤處理
├── 階段 3: BrokerBreakdownSpider 改寫 (4h)
│   ├── 3.1 重構 BSR 查詢方法
│   ├── 3.2 維持 collect_only + pipeline 模式
│   ├── 3.3 更新 CLI 支援
│   └── 3.4 單元測試
├── 階段 4: RiskAssessor 恢復 (3h)
│   ├── 4.1 驗證現有 S/A/B/C 評級邏輯
│   ├── 4.2 確保 broker_risk_pct 正確傳遞
│   └── 4.3 整合測試
└── 階段 5: E2E 整合與驗證 (2h)
    ├── 5.1 run_daily.py 相容性測試
    ├── 5.2 E2E 流程測試
    └── 5.3 開發日誌撰寫
```

---

## 階段 1: OCR 環境與辨識率測試

### 1.1 安裝 ddddocr + 相依套件

**動作**:
```bash
pip install ddddocr Pillow requests
```

**驗證**:
```python
import ddddocr
ocr = ddddocr.DdddOcr()
print(ocr.classification(b"test"))  # 確認無錯誤
```

**產出**: 可正常 import 並執行推論

**耗時**: 30min

---

### 1.2 撰寫 Captcha 下載腳本

**檔案**: `research/backtests/ocr_test/test_bsr_captcha.py`

**功能**:
1. 發送 GET 到 `bsMenu.aspx`
2. 解析 `__VIEWSTATE`, `__EVENTVALIDATION`, Captcha GUID
3. 下載 Captcha 圖片 `CaptchaImage.aspx?guid=XXX`
4. 用 ddddocr 辨識
5. 儲存圖片 + 辨識結果到 `research/backtests/ocr_test/samples/`

**關鍵實作注意事項**:
- 使用 `requests.Session()` 維持 Cookie
- `__VIEWSTATE` 在 HTML 的 `<input type="hidden" name="__VIEWSTATE">`
- Captcha URL 從 `<img src='CaptchaImage.aspx?guid=XXX'>` 提取
- GUID 格式: UUID v4 (36 chars)

**耗時**: 1h

---

### 1.3 執行批量辨識測試

**方法**:
1. 每 3 秒請求一次 (避免被封)
2. 總共下載 100+ 張 captcha
3. 自動 OCR 並記錄結果
4. 人工抽樣驗證正確性 (因 BSR 不提供 ground truth)

**人工驗證策略**:
- 抽取 20% 樣本 (至少 20 張) 人工比對
- 若人工樣本中 ddddocr 結果與肉眼判斷一致，則視為正確
- 基於此推估整體準確率

**產出**:
- `research/backtests/ocr_test/samples/` — captcha 圖片集
- `research/backtests/ocr_test/results.csv` — 辨識結果統計
- 人工驗證記錄

**耗時**: 1h (下載) + 30min (人工驗證) = 1.5h

---

### 1.4 分析結果與決策

**決策樹**:

```
辨識率 ≥ 80%?
  ├── ✅ YES → 繼續階段 2
  │              (重試 3 次後理論成功率 > 99%)
  │
  └── ❌ NO (辨識率 < 80%)
       ├── 檢查是否為 ddddocr 預設模型問題
       │    └── 嘗試 onnx 模型參數調整
       ├── 若仍 < 80%:
       │    └── 實作降級方案 (見風險評估文件)
       │
       └── 無論辨識率如何都 >= 60% 時可繼續
            (搭配 3 次重試可達 > 95%)
```

**門檻條件**:
| 條件 | 動作 |
|------|------|
| 1st-attempt ≥ 80% | 繼續原計畫 |
| 1st-attempt ≥ 60% 但 < 80% | 增加重試次數至 5 次 |
| 1st-attempt < 60% | 需額外 training 或另尋方案 |

**耗時**: 30min

---

## 階段 2: BSR 客戶端實作

### 2.1 實作 OCR Solver 封裝模組

**檔案**: `src/spiders/ocr_solver.py`

**設計**:
```python
class OcrSolver:
    """ddddocr 封裝，提供統一的 captcha 解碼介面"""
    
    def __init__(self):
        self._ocr = ddddocr.DdddOcr()
    
    def solve(self, image_bytes: bytes) -> str:
        """辨識 captcha 圖片，回傳 5 碼字串"""
        return self._ocr.classification(image_bytes)
    
    def solve_with_retry(self, image_bytes: bytes, max_attempts: int = 3) -> Optional[str]:
        """帶重試的辨識（同張圖片多次 OCR）"""
```

**注意**: ddddocr 具有確定性 (同張圖片同結果)，所以 retry 主要是重新下載 captcha 而非重試 OCR。

**耗時**: 1h

---

### 2.2 實作 BSR Session 管理

**檔案**: `src/spiders/bsr_client.py`

**類別**: `BsrClient`

**核心方法**:

```python
class BsrClient:
    BASE_URL = "https://bsr.twse.com.tw/bshtm/"
    
    def __init__(self):
        self.session = requests.Session()
        self.viewstate = None
        self.eventvalidation = None
        self.viewstategenerator = None
    
    def _parse_aspnet_state(self, html: str) -> dict:
        """從 HTML 解析 __VIEWSTATE, __EVENTVALIDATION, __VIEWSTATEGENERATOR"""
    
    def _refresh_session(self) -> bool:
        """GET bsMenu.aspx 取得最新 ASP.NET state"""
    
    def _get_captcha_image(self) -> Optional[bytes]:
        """下載 Captcha 圖片，回傳 PNG bytes"""
    
    def submit_query(self, symbol: str, captcha_code: str) -> Optional[str]:
        """提交查詢表單，回傳結果 HTML"""
    
    def fetch_broker_data(self, symbol: str) -> Optional[List[dict]]:
        """完整流程：refresh → captcha → OCR → submit → parse"""
    
    def close(self):
        """關閉 session"""
```

**耗時**: 2h

---

### 2.3 實作 Captcha 下載 + OCR 流程

**設計**:

```
fetch_broker_data(symbol)
  │
  ├─ 1. _refresh_session() → GET bsMenu.aspx
  │     ├─ 解析 __VIEWSTATE, __EVENTVALIDATION
  │     └─ 提取 Captcha GUID → CaptchaImage.aspx?guid=XXX
  │
  ├─ 2. _get_captcha_image() → captcha PNG bytes
  │
  ├─ 3. ocr_solver.solve(image_bytes) → "5碼字串"
  │
  ├─ 4. submit_query(symbol, captcha_code) → POST bsMenu.aspx
  │     ├─ 若成功 → 回傳結果 HTML
  │     └─ 若失敗 (驗證碼錯誤) → retry (max 3)
  │
  └─ 5. _parse_result(html) → List[BrokerBreakdown dicts]
```

**重試邏輯**:
```
max_attempts = 3
for attempt in 1..max_attempts:
    if attempt > 1:
        # 重新獲取 session + captcha
        _refresh_session()
    captcha = _get_captcha_image()
    code = ocr_solver.solve(captcha)
    html = submit_query(symbol, code)
    if "查詢結果" in html (或特定成功訊號):
        return parse(html)
    # 檢查是否驗證碼錯誤
    if "驗證碼" in html and "錯誤" in html:
        continue  # 重試
    # 其他錯誤 (網路、server error)
    wait(2^attempt)  # exponential backoff
raise MaxRetryExceeded
```

**耗時**: 1.5h

---

### 2.4 實作表單提交 + 結果解析

**POST 資料結構**:
```
POST bsMenu.aspx
Content-Type: application/x-www-form-urlencoded

__VIEWSTATE=...&
__EVENTVALIDATION=...&
__VIEWSTATEGENERATOR=...&
RadioButton_Normal=RadioButton_Normal&
TextBox_Stkno=2330&
CaptchaControl1=ABCDE&
btnOK=查詢
```

**結果 HTML 解析**:
- BSR 回傳的 HTML 包含 `<table>` 格式的買賣超資料
- 需要使用 BeautifulSoup 解析表格
- 表格欄位預計包含: 券商名稱、買進股數、賣出股數、淨買超股數
- 需要對應到 `BrokerBreakdownItem` 的欄位

**注意**: 需要實際測試確認 BSR 回傳的 HTML 結構，所以此部分可能需要在階段 1 完成後調整。

**耗時**: 1.5h

---

### 2.5 實作重試與錯誤處理

**錯誤類型**:
| 錯誤 | 處理方式 |
|------|---------|
| 驗證碼錯誤 | 重新獲取 Captcha + 重試 (max 3) |
| Network Timeout | 指數退避重試 (1s, 2s, 4s) |
| HTTP 500 | 等待 5s 後重試 |
| __VIEWSTATE 過期 | 重新 GET bsMenu.aspx |
| Session 過期 | 建立新 Session |

**Circuit Breaker**:
- 連續 5 次失敗 → 暫停 60s
- 之後恢復正常請求

**耗時**: 1h

---

## 階段 3: BrokerBreakdownSpider 改寫

### 3.1 重構 BSR 查詢方法

**修改目標**: `src/spiders/broker_breakdown_spider.py`

```python
class BrokerBreakdownSpider(BaseSpider):
    # 移除舊的 API_BASE
    # 新增 BSR 支援
    
    def __init__(self, pipeline=None, ...):
        super().__init__(...)
        self.pipeline = pipeline
        self.items = []
        self.collect_only = True
        self.bsr_client = None  # lazy init
    
    def fetch_broker_breakdown(self, date: str, symbol: str) -> SpiderResponse:
        """使用 BSR + OCR 取得分點資料"""
        try:
            if not self.bsr_client:
                from src.spiders.bsr_client import BsrClient
                self.bsr_client = BsrClient()
            
            records = self.bsr_client.fetch_broker_data(symbol)
            # 轉換為 BrokerBreakdownItem
            # ... (與現有邏輯類似)
            
            self.items.clear()
            for rank, record in enumerate(records, 1):
                item = BrokerBreakdownItem(
                    date=date,
                    symbol=symbol,
                    broker_id=record["broker_id"],
                    broker_name=record["broker_name"],
                    buy_volume=record["buy_volume"],
                    sell_volume=record["sell_volume"],
                    net_volume=record["net_volume"],
                    rank=rank,
                    source_type="bsr",
                    source_url=self.bsr_client.BASE_URL,
                )
                self.items.append(item)
                self.add_item(item)
            
            return SpiderResponse(
                success=True,
                data={"count": len(self.items)},
            )
        except Exception as e:
            return SpiderResponse(
                success=False,
                error=f"BSR 查詢失敗: {e}",
            )
    
    def close(self):
        """清理 BSR session"""
        if self.bsr_client:
            self.bsr_client.close()
```

**耗時**: 2h

---

### 3.2 維持 collect_only + pipeline 模式

**無需修改**: 現有 `BaseSpider.add_item()` + `flush_items()` 模式完全相容。
- `collect_only = True` 時 items 暫存在 `_pending_items`
- 驗證通過後呼叫 `spider.flush_items(pipeline)`
- 與 run_daily.py 的 `step_spiders()` → `flush_pipelines()` 流程一致

**耗時**: 0h (相容性確認)

---

### 3.3 更新 CLI 支援

保持現有 CLI 介面不變，確保：
```bash
python3 -m src.spiders.broker_breakdown_spider --date 20260509 --symbol 2330
```
正常執行 BSR 查詢流程。

**耗時**: 0.5h

---

### 3.4 單元測試

**檔案**: `tests/test_bsr_client.py`

| 測試案例 | 說明 |
|---------|------|
| test_session_refresh | 確認可成功 GET bsMenu.aspx |
| test_captcha_download | 確認可下載 captcha 圖片 (200x60 PNG) |
| test_ocr_solve | 確認 ddddocr 可輸出 5 碼字串 |
| test_full_query | 完整流程測試 (需要手動確認) |
| test_retry_logic | 驗證碼錯誤時自動重試 |
| test_parse_result | 解析 mock HTML 表格 |
| test_spider_bsr_mode | BrokerBreakdownSpider 使用 BSR |

**耗時**: 1.5h

---

## 階段 4: RiskAssessor 恢復

### 4.1 驗證現有 S/A/B/C 評級邏輯

**現狀**: 檢查 `src/analytics/risk_assessor.py` 和 `src/analytics/rules/risk_rules.py`

```
RATING_THRESHOLDS = {
    "S": {"max_premium": 0.02, "max_risk": 0.10},
    "A": {"max_premium": 0.03, "max_risk": 0.20},
    "B": {"max_premium": 0.05, "max_risk": 0.30},
}

assess(premium_ratio, risk_ratio):
    for rating in ["S", "A", "B"]:
        if premium_ratio < threshold["max_premium"] and risk_ratio < threshold["max_risk"]:
            return rating
    return "C"
```

**結論**: 評級邏輯已經完整存在。只需要確保 `run_analysis()` 中的 `broker_risk_pct` 從 BSR 資料正確填入 `daily_analysis_results` 表。

**耗時**: 0.5h

---

### 4.2 確保 broker_risk_pct 正確傳遞

**檢查點**:
1. `ChipProfiler.analyze(date)` → 從 `broker_breakdown` 表讀取資料
2. Broker breakdown 表由 BSR spider 寫入
3. `RiskAssessor.run_analysis()` → 從 `ChipProfiler.analyze()` 取得 `risk_ratio`
4. → 寫入 `daily_analysis_results.broker_risk_pct`

**如果 BSR 查詢失敗的處理**:
- 保留前一日 broker_risk_pct 資料
- 或者使用 0 (不加權風險)
- 記錄警報

**耗時**: 1h

---

### 4.3 整合測試

```bash
# 1. 測試 BSR 查詢 + DB 寫入
python3 -c "
from src.spiders.broker_breakdown_spider import BrokerBreakdownSpider
s = BrokerBreakdownSpider()
r = s.fetch_broker_breakdown('20260509', '2330')
print(r.success, len(s.items))
"

# 2. 測試 ChipProfiler 讀取
python3 -m src.analytics.chip_profiler --date 2026-05-09

# 3. 測試 RiskAssessor 評級
python3 -m src.analytics.risk_assessor --date 2026-05-09
```

**耗時**: 1.5h

---

## 階段 5: E2E 整合與驗證

### 5.1 run_daily.py 相容性測試

**測試**: `python3 src/run_daily.py --validate-only`

確認:
- `step_spiders()` 中 BrokerBreakdownSpider 正常執行
- 資料通過 collect_only → validate → flush 流程
- `--validate-only` 模式下暫存資料正確

**耗時**: 1h

---

### 5.2 E2E 流程測試

**測試**: `python3 src/run_daily.py`

完整流程:
1. 爬蟲 (含 BSR captcha)
2. 驗證
3. 寫入 DB
4. 清洗

**耗時**: 0.5h

---

### 5.3 開發日誌撰寫

**檔案**: `docs/agent_context/phase5/development_log.md`

記錄:
- 各階段實作情況
- OCR 測試結果
- 遇到的問題與解決方案
- 最終驗收結果

**耗時**: 0.5h

---

## 總結: 時間分配

| 階段 | 工時 | 佔比 |
|------|------|------|
| 階段 1: OCR 測試 | 3h | 17% |
| 階段 2: BSR Client | 6h | 33% |
| 階段 3: Spider 改寫 | 4h | 22% |
| 階段 4: RiskAssessor | 3h | 17% |
| 階段 5: E2E 測試 | 2h | 11% |
| **合計** | **18h** | **100%** |

## 關鍵路徑 (Critical Path)

```
1.2 下載腳本 → 1.3 批量測試 → 1.4 分析決策
    ↓
2.1 OCR Solver → 2.2 BSR Session → 2.3 Captcha+OCR → 2.4 表單+解析
                                             ↓
                                    3.1 Spider 改寫
                                             ↓
                                    4.2 broker_risk_pct 傳遞
                                             ↓
                                    5.1 run_daily 整合
```

**注意**: 階段 1 是 Gate — 若 ddddocr 辨識率不足，後續所有階段需調整策略。
