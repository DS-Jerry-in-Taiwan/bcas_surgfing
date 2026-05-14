# 可轉債 (CB) 每日交易資料下載指南

## 概述

本文檔記錄如何從證券櫃檯買賣中心 (TPEx) 下載可轉換公司債每日交易資料。

---

## 資料來源

- **網站**: 證券櫃檯買賣中心 (TPEx)
- **頁面**: https://www.tpex.org.tw/zh-tw/bond/info/statistics-cb/day.html
- **直接下載**: CSV 檔案

---

## 下載 URL 格式

### 基本格式

```
https://www.tpex.org.tw/storage/bond_zone/tradeinfo/cb/{西元年}/{西元年月}/RSta0113.{西元年月日}-C.csv
```

### 日期轉換規則

| 民國年 | 西元年 | 計算方式 |
|--------|--------|----------|
| 115 | 2026 | 115 + 1911 = 2026 |
| 114 | 2025 | 114 + 1911 = 2025 |

### URL 範例

| 民國日期 | 西元日期 | URL |
|---------|---------|-----|
| 115/04/10 | 2026/04/10 | `https://www.tpex.org.tw/storage/bond_zone/tradeinfo/cb/2026/202604/RSta0113.20260410-C.csv` |
| 115/04/09 | 2026/04/09 | `https://www.tpex.org.tw/storage/bond_zone/tradeinfo/cb/2026/202604/RSta0113.20260409-C.csv` |

---

## CSV 檔案格式

### 編碼

- **原始編碼**: Big5（繁體中文）
- **建議轉換**: UTF-8

### 欄位說明

| 欄位 | 說明 |
|------|------|
| 代號 | 可轉債代號（如 11011） |
| 名稱 | 可轉債名稱（如 台泥一永） |
| 交易 | 交易類型（等價/議價） |
| 收市 | 收盤價 |
| 漲跌 | 漲跌幅度 |
| 開市 | 開盤價 |
| 最高 | 最高價 |
| 最低 | 最低價 |
| 筆數 | 成交筆數 |
| 單位 | 成交單位（張） |
| 金額 | 成交金額（元） |
| 均價 | 平均价 |
| 明日參價 | 明日參考價 |
| 明日漲停 | 明日漲停價 |
| 明日跌停 | 明日跌停價 |

### CSV 結構範例

```
TITLE,櫃檯買賣轉(交)換公司債買賣斷交易行情表-含議價及鉅額交易
DATADATE,日期:115年04月10日
ALIGN,C,L,C,R,R,R,R,R,R,R,R,R,R,R
HEADER,代號,名稱,交易,收市,漲跌,開市,最高,最低,筆數,單位,金額,均價,明日參價,明日漲停,明日跌停
BODY,"11011","台泥一永  ","等價","100.05 ","+0.45  ","99.90  ","101.00 ","99.90  ","83      ","754     ","75,580,700    ","100.23 ","100.05 ","110.05 ","90.05  "
```

---

## Python 爬蟲程式碼

### 完整範例

```python
import requests
import pandas as pd
from io import BytesIO

class TpexCbCrawler:
    """櫃買中心可轉債每日交易資料爬蟲"""
    
    def __init__(self):
        self.csv_base = "https://www.tpex.org.tw/storage/bond_zone/tradeinfo/cb"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    def roc_to_ad(self, roc_date):
        """
        民國日期轉西元日期
        roc_date: "115/04/10" 或 "1150410"
        return: (year, month, day) 如 (2026, "04", "10")
        """
        if "/" in roc_date:
            parts = roc_date.split("/")
            roc_year = int(parts[0])
            month = parts[1]
            day = parts[2]
        else:
            roc_year = int(roc_date[:3])
            month = roc_date[3:5]
            day = roc_date[5:7]
        
        ad_year = roc_year + 1911
        return ad_year, month, day
    
    def get_csv_url(self, roc_date):
        """
        取得 CSV 下載 URL
        roc_date: 民國日期，如 "115/04/10"
        """
        year, month, day = self.roc_to_ad(roc_date)
        year_month = f"{year}{month}"
        year_month_day = f"{year}{month}{day}"
        
        return f"{self.csv_base}/{year}/{year_month}/RSta0113.{year_month_day}-C.csv"
    
    def download(self, roc_date):
        """
        下載指定日期的 CSV
        roc_date: 民國日期，如 "115/04/10"
        return: CSV 內容（bytes）
        """
        url = self.get_csv_url(roc_date)
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        return response.content
    
    def parse(self, content):
        """
        解析 CSV 內容
        content: CSV bytes
        return: pandas DataFrame
        """
        # 原始編碼為 Big5
        df = pd.read_csv(BytesIO(content), encoding='big5')
        return df
    
    def fetch(self, roc_date):
        """
        下載並解析（一站式）
        roc_date: 民國日期，如 "115/04/10"
        return: pandas DataFrame
        """
        content = self.download(roc_date)
        return self.parse(content)


# 使用範例
if __name__ == "__main__":
    crawler = TpexCbCrawler()
    
    # 下載單日資料
    df = crawler.fetch("115/04/10")
    print(df.head())
    
    # 批次下載多日
    dates = ["115/04/10", "115/04/09", "115/04/08"]
    for date in dates:
        try:
            df = crawler.fetch(date)
            df.to_csv(f"cb_{date.replace('/', '')}.csv", index=False, encoding='utf-8')
            print(f"已下載: {date}")
        except Exception as e:
            print(f"下載失敗 {date}: {e}")
```

---

## 批次下載範例

### 下載一個月份的資料

```python
import datetime

def download_month(roc_year, roc_month):
    """下載指定月份的所有交易日資料"""
    crawler = TpexCbCrawler()
    
    # 民國轉西元
    ad_year = roc_year + 1911
    
    # 遍歷該月份每一天
    for day in range(1, 32):
        try:
            roc_date = f"{roc_year:03d}/{roc_month:02d}/{day:02d}"
            content = crawler.download(roc_date)
            
            # 儲存檔案
            filename = f"cb_{ad_year}{roc_month:02d}{day:02d}.csv"
            with open(filename, 'wb') as f:
                f.write(content)
            
            print(f"已下載: {roc_date}")
        except Exception as e:
            # 可能是週末或非交易日
            pass

# 下載民國 115 年 4 月的資料
download_month(115, 4)
```

---

## 報表類型

TPEx 提供多種可轉債報表：

| 報表名稱 | 說明 |
|---------|------|
| 每日轉(交)換公司債買賣斷交易行情表 | 每日交易行情（本文檔所用） |
| 每日轉(交)換公司債買賣斷券商買賣日報表 | 券商買賣日報 |
| 每日轉(交)換公司債附條件交易行情表 | 附條件交易行情 |
| 每日交易概況 | 交易概況 |
| 每日附認股權公司債行情表 | 附認股權公司債 |

---

## 注意事項

1. **日期格式**: URL 使用西元年，需從民國年轉換（+1911）
2. **編碼**: 原始 CSV 為 Big5 編碼，需轉換為 UTF-8
3. **非交易日**: 週末及國定假日無資料
4. **檔案命名**: 格式為 `RSta0113.{日期}-C.csv`

---

## 測試記錄

| 日期 | URL | 狀態 | 檔案大小 |
|------|-----|------|---------|
| 115/04/10 | [連結](https://www.tpex.org.tw/storage/bond_zone/tradeinfo/cb/2026/202604/RSta0113.20260410-C.csv) | ✅ 成功 | 70KB |
| 115/04/09 | [連結](https://www.tpex.org.tw/storage/bond_zone/tradeinfo/cb/2026/202604/RSta0113.20260409-C.csv) | ✅ 成功 | 71KB |

---

## 相關連結

- TPEx 可轉債統計頁面: https://www.tpex.org.tw/zh-tw/bond/info/statistics-cb/day.html
- TPEx 首頁: https://www.tpex.org.tw/

---

## 更新歷史

- 2026-04-10: 初版，記錄下載機制與程式碼範例