# Phase 4.1 - 替代資料源分析與測試

## 方案 A: twstock SDK

### 安裝
```bash
pip install twstock
```

### 已知功能 (from 官方文件)
- `stock.Stock`: 歷史股價 (開高低收量) — 我們已有
- `stock.moving_average()`: 均線計算 — 我們已有
- `analytics.BestFourPoint()`: 四大買賣點 — 我們已有
- `realtime.get()`: 即時報價 — EOD 不需
- `codes`: 股票代碼 — 我們已有

### 待確認
- 底層使用 TWSE 哪個 API？
- 是否有 wrapper 能存取 MI_20S 或類似分點資料？
- 原始碼結構能否擴充？

### 測試項目
```python
# test_twstock_basic.py
import twstock

# 1. 測試基本功能
stock = twstock.Stock("2330")
stock.fetch_31()
print(f"Data rows: {len(stock.data)}")
print(f"Raw data: {stock.raw_data[:2] if stock.raw_data else 'Empty'}")

# 2. 檢查 fetcher 內部呼叫哪個 API
fetcher = stock.fetcher
print(f"Fetcher type: {type(fetcher)}")

# 3. 嘗試直接使用底層 TWSE API
from twstock.stock import TWSEFetcher
fetcher = TWSEFetcher()

# 嘗試抓分點 (如果底層有支援)
```

## 方案 B: FinMind API

### API 端點
```
GET https://finmindtrade.com/api/v4/data
參數: dataset=TaiwanStockBrokerBuysell
```

### 文件
- https://finmind.github.io/FinMind/
- 需要註冊取得 Token

### 測試項目
```python
# test_finmind.py
import requests

# 註冊取得 token
API_TOKEN = "your_token_here"
url = "https://finmindtrade.com/api/v4/data"
params = {
    "dataset": "TaiwanStockBrokerBuysell",
    "data_id": "2330",
    "start_date": "2026-05-01",
    "end_date": "2026-05-13",
    "token": API_TOKEN,
}
resp = requests.get(url, params=params)
print(resp.json())
```

## 方案 C: Shioaji (永豐 API)

### 安裝
```bash
pip install shioaji
```

### 文件
- https://sinotrade.github.io/

### 測試項目
```python
# test_shioaji.py
import shioaji as sj

# 需要永豐證券帳戶
api = sj.Shioaji()
api.login(
    person_id="your_id",
    passwd="your_password",
    contracts_cb=lambda security_type: print(f"{security_type} 已更新")
)
```

## 方案 D: Goodinfo 爬蟲

### 爬蟲目標
```
https://goodinfo.tw/StockInfo/StockBuySell.asp?STOCK_ID=2330
```

### 測試項目
```python
# test_goodinfo.py
import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
url = "https://goodinfo.tw/StockInfo/StockBuySell.asp"
params = {"STOCK_ID": "2330"}
resp = requests.get(url, params=params, headers=headers)
soup = BeautifulSoup(resp.text, "html.parser")
# 檢查分點買賣超表格是否存在
```

## 比較矩陣

| 方案 | 資料完整性 | 即時性 | 費用 | 實作難度 | 維護成本 | 風險 |
|------|-----------|--------|------|---------|---------|------|
| **A. twstock** | 低(無分點) | 即時 | 免費 | 低 | 低 | 可能無資料 |
| **B. FinMind** | 高 | T+1 | 部分付費 | 中 | 低 | API 變更 |
| **C. Shioaji** | 高 | 即時 | 需開戶 | 中 | 低 | 需帳戶 |
| **D. Goodinfo** | 中 | T+1 | 免費 | 高 | 高 | 反爬蟲 |
| **E. CMoney** | 中 | T+1 | 免費 | 高 | 高 | 反爬蟲 |
