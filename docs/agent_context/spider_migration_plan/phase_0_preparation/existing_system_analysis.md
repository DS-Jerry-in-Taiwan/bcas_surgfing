# 現有爬蟲系統分析報告

## 1. 系統概覽

現有爬蟲系統位於 `src/crawlers/` 目錄，共包含 17 個 Python 腳本，分為三大類：

| 類別 | 檔案數 | 說明 |
|------|--------|------|
| 主檔案 | 8 | 主要爬蟲邏輯 |
| 日報模組 | 5 | 日報資料抓取 |
| Master 模組 | 4 | 主檔資料抓取 |

---

## 2. 現有爬蟲架構

### 2.1 基礎類別 (`base.py`)

```python
class RateLimiter:
    - 基於執行緒鎖的速率限制器
    - 支援 calls_per_sec 參數設定

class BaseCrawler(ABC):
    - 抽象基類，定義 fetch/parse/save 三個介面
```

### 2.2 爬蟲類型分析

| 爬蟲名稱 | 類型 | 技術棧 | 目標網站 |
|----------|------|--------|----------|
| `tpex_master.py` | 可轉債主檔 | requests + BeautifulSoup | TPEx |
| `tpex_master_playwright.py` | 可轉債主檔 | Playwright (async) | TPEx |
| `twse.py` | 股票/日成交 | requests | TWSE |
| `twse_daily.py` | 日成交資料 | requests + JSON | TWSE |
| `tpex_cb.py` | 可轉債日報 | requests + RateLimiter | TPEx |
| `tpex_cb_daily.py` | 可轉債日報 | - | TPEx |
| `stock_crawler.py` | 上市股票主檔 | requests + pandas | TWSE/TPEx |
| `cb_crawler.py` | 可轉債主檔 | requests + pandas | TPEx |

---

## 3. 遷移至 Feapder 風險分析

### 3.1 高風險項目 🔴

| 項目 | 說明 | 影響 |
|------|------|------|
| **非同步 Playwright 整合** | `tpex_master_playwright.py` 使用 async Playwright | Feapder 原生支援需評估 |
| **自訂速率限制器** | `base.py` 中的 `RateLimiter` 類 | Feapder 有內建，需重寫 |
| **自訂 BaseCrawler** | 抽象類別需對應 Feapder 架構 | 需重構繼承關係 |

### 3.2 中風險項目 🟡

| 項目 | 說明 | 影響 |
|------|------|------|
| **編碼處理** | Big5 (TWSE) / UTF-8 (TPEx) 混用 | 需確保 Feapder 正確處理 |
| **pandas DataFrame 整合** | 多處使用 pandas 解析 HTML 表格 | Feapder 需額外處理 |
| **反爬機制** | 僅依賴 User-Agent  Header | 需補充 Cookie/Session |

### 3.3 低風險項目 🟢

| 項目 | 說明 | 影響 |
|------|------|------|
| **CSV/JSON 輸出** | 標準格式，Feapder 完全支援 | 直接遷移 |
| **簡易 HTTP 請求** | 純 requests 調用 | 易於重構 |
| **錯誤處理** | 基本 try-except 模式 | Feapder 有完善機制 |

---

## 4. 詳細技術分析

### 4.1 RateLimiter 類 (`base.py:6-23`)

```python
class RateLimiter:
    - 使用 threading.Lock 實現執行緒安全
    - 基於時間間隔的速率控制
```

**遷移建議**：Feapder AirSpider 已有 `@loop_interval()` 裝飾器，可直接替換。

### 4.2 表格解析 (`stock_crawler.py:11-12`)

```python
df = pd.read_html(resp.text, encoding="big5")[0]
```

**風險**：Feapder 的 item 機制不直接支援 pandas，需額外轉換層。

### 4.3 非同步爬蟲 (`tpex_master_playwright.py`)

```python
async def fetch_tpex_cb_master():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
```

**風險**：Feapder 主要基於同步架構，async Playwright 需特別處理。

---

## 5. 遷移策略建議

### Phase 1: 簡易爬蟲遷移 (優先)
- `tpex_csv_fetcher.py` → Feapder AirSpider
- `tpex_master.py` → Feapder AirSpider

### Phase 2: 中等複雜度遷移
- `twse_daily.py` → Feapder AirSpider + 自訂 Item
- `tpex_cb.py` → Feapder AirSpider (替換 RateLimiter)

### Phase 3: 高風險遷移
- `tpex_master_playwright.py` → Feapder + Playwright 整合
- `stock_crawler.py` → Feapder Spider (批次處理)

---

## 6. 總結

| 指標 | 數值 |
|------|------|
| 總爬蟲檔案數 | 17 |
| 高風險遷移項目 | 3 |
| 中風險遷移項目 | 3 |
| 低風險遷移項目 | 3 |
| 建議遷移順序 | Phase 1 → 2 → 3 |

---

*報告生成時間：2026-04-15*
