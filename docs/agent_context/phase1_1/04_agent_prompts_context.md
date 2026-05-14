# Phase 1.1 - Agent 執行 Prompts

## @INFRA Prompt
請建立專案基礎結構：
1. 建立目錄: `data/raw/stock`, `data/raw/cb`, `src/crawlers`, `notebooks`。
2. 建立 `requirements.txt`，包含 pandas, requests, beautifulsoup4, tqdm。
3. 建立 `.env` 樣板。

## @ARCH Prompt
請設計爬蟲模組架構：
1. 定義 `src/crawlers/base.py` 中的 `BaseCrawler` class。
2. 需包含 `fetch(url, params)`, `parse(response)`, `save(data)` 方法。
3. 設計一個 `RateLimiter` decorator 用於控制請求頻率。
4. 輸出架構設計文檔。

## @CODER Prompt
請實作原型爬蟲：
1. `src/crawlers/twse.py`: 針對證交所 API，抓取個股日成交資訊。注意需處理民國年轉西元年。
2. `src/crawlers/tpex_cb.py`: 針對櫃買中心，抓取可轉債日況。
3. 實作 `utils/date_converter.py`。
4. 確保 request header 偽裝成瀏覽器。

## @ANALYST Prompt
請分析抓取到的數據：
1. 執行爬蟲抓取 2330 (台積電) 與幾檔熱門 CB 的近月資料。
2. 使用 Pandas 檢查：
   - 是否有重複資料？
   - High 是否永遠 >= Low？
   - CB 的 Volume 為 0 時，Price 是多少？
3. 產出 Markdown 格式的數據品質報告。

