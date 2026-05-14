# Phase 4.2 - 實作計畫 (依評估結果決定路徑)

## 路徑 A: 找到替代資料源

```python
# BrokerBreakdownSpider 改寫範例 (使用 FinMind 為例)
class BrokerBreakdownSpider(BaseSpider):
    API_BASE = "https://finmindtrade.com/api/v4/data"
    
    def __init__(self, pipeline=None, ...):
        super().__init__(...)
        self.pipeline = pipeline
        self.items = []
        self.collect_only = True
        self.api_token = os.getenv("FINMIND_TOKEN", "")
    
    def fetch_broker_breakdown(self, date: str, symbol: str) -> SpiderResponse:
        """從 FinMind 取得分點資料"""
        import requests
        
        url = f"{self.API_BASE}"
        params = {
            "dataset": "TaiwanStockBrokerBuysell",
            "data_id": symbol,
            "start_date": date,
            "end_date": date,
            "token": self.api_token,
        }
        ...
```

### 修改範圍
| 檔案 | 變更 |
|------|------|
| `src/spiders/broker_breakdown_spider.py` | 改用新 API |
| `src/run_daily.py` | 調整呼叫 (若有 API 格式差異) |
| `requirements.txt` | 新增 twstock / shioaji 等 |

## 路徑 B: 無替代資料源 → 調整 RiskAssessor

```python
# 簡化版 RiskAssessor (不使用風險佔比)
class RiskAssessor:
    @staticmethod
    def assess(premium_ratio: float, risk_ratio: float = 0.0) -> str:
        # 只用溢價率評級
        if premium_ratio < 0.02:
            return "S"
        elif premium_ratio < 0.03:
            return "A"
        elif premium_ratio < 0.05:
            return "B"
        else:
            return "C"
```

### 修改範圍
| 檔案 | 變更 |
|------|------|
| `src/analytics/risk_assessor.py` | 簡化 assess()，忽略 risk_ratio |
| `src/spiders/broker_breakdown_spider.py` | 保留但標記為 deprecated |
| `src/db/init_eod_tables.sql` | broker_breakdown 表可保留 |

## 執行步驟

### Step 1: 安裝與測試 twstock (@CODER/ANALYST)
- `pip install twstock`
- 測試基本功能: 股價抓取、fetcher 類型
- 檢查原始碼是否包含分點資料端點
- 時限: 2 小時

### Step 2: 測試 FinMind (@CODER)
- 註冊帳號取得 Token
- 測試 TaiwanStockBrokerBuysell 端點
- 確認回傳資料格式是否合規
- 時限: 3 小時

### Step 3: 測試 Goodinfo 爬蟲 (@CODER)
- 檢查 HTML 結構是否有分點表格
- 評估反爬蟲難度
- 時限: 3 小時

### Step 4: 決策與實作 (@ARCH/CODER)
- 根據測試結果選擇最佳方案
- 修改 BrokerBreakdownSpider 或 RiskAssessor
- 更新對應測試
- 時限: 4-8 小時
