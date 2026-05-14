# 反爬蟲 MCP 與 Skill 說明文件

## 概述

本文檔整理 OpenCode 環境中可用的反爬蟲工具，包括 MCP (Model Context Protocol) 服務和 Skill 技能定義。

---

## 工具總覽

| 工具名稱 | 類型 | 主要功能 | 費用 |
|---------|------|---------|------|
| agent-browser | Skill | 網頁自動化、截圖、表單填寫 | 免費 |
| Playwright MCP | MCP | 瀏覽器自動化 | 免費 |
| Scrapling MCP | MCP | 智能網頁抓取 | 免費 |
| Tavily MCP | MCP | 搜索、提取、爬取 | 免費額度 |
| Brave Search MCP | MCP | 網頁搜索、圖片搜索 | 免費 |

---

## agent-browser Skill

### 簡介

agent-browser 是一個基於 Playwright 的 CLI 工具，封裝在 Docker 容器中運行。具備反檢測功能，可繞過基本的反爬蟲機制。

### 安裝位置

```
/home/ubuntu/projects/agent-browser/
├── Dockerfile
├── docker-compose.yml
└── data/          # 資料目錄（映射到容器 /workspace/data）
```

### 啟動容器

```bash
cd /home/ubuntu/projects/agent-browser
docker compose up -d --build
```

### 基本命令

```bash
# 進入容器
docker exec -it agent-browser-agent-browser-1 bash

# 執行搜索（Bing/DuckDuckGo/Brave）
docker exec agent-browser-agent-browser-1 agent-browser search "可轉債 台灣" -e bing

# 截圖
docker exec agent-browser-agent-browser-1 agent-browser screenshot "https://example.com" -o /workspace/data/screenshot.png

# 下載頁面
docker exec agent-browser-agent-browser-1 agent-browser fetch "https://example.com" -o /workspace/data/page.html

# 下載圖片
docker exec agent-browser-agent-browser-1 wget -O /workspace/data/image.jpg "https://example.com/image.jpg"
```

### 反檢測模式

環境變數 `AGENT_BROWSER_STEALTH=true` 啟用反檢測功能：

- 隱藏 WebDriver 特徵
- 模擬真實瀏覽器行為
- 繞過 Cloudflare 基礎檢測

### 限制

| 網站 | 狀態 | 問題 |
|------|------|------|
| Google | ❌ | reCAPTCHA 驗證碼 |
| 統一證券 CBAS | ❌ | 直接封鎖 URL |
| TWSE/MOPS | ⚠️ | 部分功能重定向 |
| TPEx | ✅ | 正常運作 |
| Bing | ⚠️ | 偶爾 Cloudflare |

### SKILL.md 配置

路徑: `/home/ubuntu/projects/OrganBriefOptimization/.opencode/skills/agent-browser/SKILL.md`

---

## Playwright MCP

### 簡介

OpenCode 內建的瀏覽器自動化工具，透過 Playwright 控制瀏覽器。

### 可用功能

| 函數 | 說明 |
|------|------|
| `playwright_browser_navigate` | 導航到 URL |
| `playwright_browser_snapshot` | 取得頁面快照 |
| `playwright_browser_click` | 點擊元素 |
| `playwright_browser_type` | 輸入文字 |
| `playwright_browser_take_screenshot` | 截圖 |
| `playwright_browser_evaluate` | 執行 JavaScript |

### 範例用法

```javascript
// 導航並截圖
await playwright_browser_navigate({ url: "https://example.com" });
await playwright_browser_take_screenshot({ type: "png", filename: "screenshot.png" });

// 取得頁面結構
await playwright_browser_snapshot({});
```

---

## Tavily MCP

### 簡介

AI 搜索 API，提供高品質搜索結果和內容提取。

### 可用功能

| 函數 | 說明 |
|------|------|
| `tavily_search` | 網頁搜索 |
| `tavily_extract` | 提取 URL 內容 |
| `tavily_crawl` | 爬取網站 |
| `tavily_research` | 深度研究 |

### 範例用法

```javascript
// 搜索
await tavily_tavily_search({ 
  query: "台灣可轉債市場分析",
  max_results: 5 
});

// 提取內容
await tavily_tavily_extract({ 
  urls: ["https://example.com/article"],
  format: "markdown" 
});

// 爬取網站
await tavily_tavily_crawl({
  url: "https://example.com",
  max_depth: 2,
  limit: 20
});
```

---

## Brave Search MCP

### 簡介

Brave 搜索引擎 API，支援網頁、圖片、新聞搜索。

### 可用功能

| 函數 | 說明 |
|------|------|
| `brave_web_search` | 網頁搜索 |
| `brave_image_search` | 圖片搜索 |
| `brave_news_search` | 新聞搜索 |
| `brave_local_search` | 本地搜索 |
| `brave_summarizer` | 摘要生成 |

### 範例用法

```javascript
// 網頁搜索
await brave-search_brave_web_search({ 
  query: "可轉債 投資策略",
  count: 10 
});

// 圖片搜索
await brave-search_brave_image_search({ 
  query: "台股走勢圖",
  count: 20 
});

// 新聞搜索
await brave-search_brave_news_search({ 
  query: "央行利率決策",
  freshness: "pw"  // 過去一週
});
```

---

## 組合策略

### 場景 1: 一般搜索

```
Brave Search → 取得結果連結 → Tavily Extract → 提取內容
```

### 場景 2: 需要登入的網站

```
Playwright MCP → 模擬登入 → 截圖/提取資料
```

### 場景 3: 高度保護的網站

```
agent-browser (Stealth 模式) → 繞過檢測 → 取得資料
```

### 場景 4: 批量爬取

```
Tavily Crawl → 設定深度和限制 → 批量提取
```

---

## 反爬蟲繞過技巧

### 1. 模擬真實瀏覽器

```python
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8",
    "Referer": "https://www.google.com/"
}
```

### 2. 延遲請求

```python
import time
import random

time.sleep(random.uniform(1, 3))  # 隨機延遲 1-3 秒
```

### 3. 代理輪替

```python
proxies = [
    "http://proxy1:8080",
    "http://proxy2:8080",
    "http://proxy3:8080"
]
proxy = random.choice(proxies)
```

### 4. Session 保持

```python
import requests

session = requests.Session()
session.headers.update(headers)
# 先造訪首頁
session.get("https://example.com")
# 再造訪目標頁
response = session.get("https://example.com/data")
```

---

## 台灣金融網站特殊處理

### TWSE (台灣證交所)

- **問題**: 部分頁面有 JavaScript 渲染
- **解決**: 使用 Playwright 或 agent-browser

### TPEx (櫃買中心)

- **優點**: 直接提供 CSV 下載
- **URL 格式**: 見 `cb_download_guide.md`

### 公開資訊觀測站 (MOPS)

- **問題**: 需要驗證碼
- **解決**: 使用 OCR 或手動

### 券商網站

- **問題**: IP 黑名單、User-Agent 檢測
- **解決**: 代理 + Stealth 模式

---

## 速率限制參考

| 工具 | 限制 |
|------|------|
| Tavily | 免費: 1000 req/月 |
| Brave Search | 免費: 2000 req/月 |
| agent-browser | 無限制（本機運行） |
| Playwright MCP | 無限制（本機運行） |

---

## 疑難排解

### Cloudflare 錯誤

1. 確認啟用 Stealth 模式
2. 增加請求間隔
3. 使用代理 IP

### reCAPTCHA 錯誤

1. 避開 Google 相關網站
2. 使用 2Captcha 等服務
3. 改用手動驗證

### 403 Forbidden

1. 更換 User-Agent
2. 加入 Referer
3. 使用 Session 保持

---

## Scrapling MCP

### 簡介

Scrapling 是一個智能網頁抓取庫，專門設計用於繞過反爬蟲機制。它能自動處理 JavaScript 渲染、Cloudflare 保護、動態內容載入等問題。

**GitHub**: https://github.com/D4Vinci/Scrapling

### 核心特性

| 特性 | 說明 |
|------|------|
| **自動反檢測** | 內建 Stealth 模式，自動隱藏爬蟲特徵 |
| **JavaScript 渲染** | 支援動態頁面內容抓取 |
| **智能解析** | 自動識別頁面結構，提取關鍵內容 |
| **適應性強** | 能處理頁面結構變化 |
| **高效能** | 比傳統爬蟲快 3-5 倍 |

### 安裝

```bash
pip install scrapling
```

### 基本用法

```python
from scrapling import Browser

# 基本抓取
browser = Browser()
page = browser.fetch("https://example.com")

# 取得頁面文字
text = page.get_text()

# 取得特定元素
titles = page.css("h1::text")
links = page.css("a::attr(href)")

# 取得結構化數據
data = page.css(".product").extract({
    "name": "h2::text",
    "price": ".price::text",
    "link": "a::attr(href)"
})
```

### 進階用法

```python
from scrapling import Browser

# 啟用 Stealth 模式
browser = Browser(
    stealth=True,           # 反檢測
    headless=True,          # 無頭模式
    disable_images=True,    # 禁用圖片載入（加速）
    user_agent="custom"     # 自訂 User-Agent
)

# 設定代理
browser = Browser(
    proxy="http://proxy:8080"
)

# 設定超時和重試
page = browser.fetch(
    "https://example.com",
    timeout=30,
    retries=3
)

# 處理需要登入的頁面
page = browser.fetch("https://example.com/login")
page.fill("input[name='username']", "user")
page.fill("input[name='password']", "pass")
page.click("button[type='submit']")
page.wait_for_navigation()

# 登入後抓取
data = page.css(".content").get_text()
```

### MCP 整合

Scrapling 有對應的 MCP Server，可在 OpenCode 中直接調用：

```javascript
// Scrapling MCP 函數（視具體實作而定）
await scrapling_fetch({ url: "https://example.com" });
await scrapling_extract({ 
  url: "https://example.com",
  selectors: { title: "h1", content: ".article" }
});
```

### 適用場景

| 場景 | 效果 |
|------|------|
| 動態渲染頁面 | ⭐⭐⭐⭐⭐ 優秀 |
| Cloudflare 保護 | ⭐⭐⭐⭐ 良好 |
| 登入後頁面 | ⭐⭐⭐⭐ 良好 |
| 大批量爬取 | ⭐⭐⭐ 中等 |
| 簡單靜態頁面 | ⭐⭐⭐⭐⭐ 優秀 |

---

## CortexScout MCP

### 簡介

CortexScout 是一個專為 AI Agent 設計的 MCP Server，整合了瀏覽器自動化和智能內容提取功能。基於 Playwright，並內建反檢測機制。

**特點**: 專門為 LLM 和 AI Agent 優化，提供結構化輸出。

### 核心功能

| 功能 | 說明 |
|------|------|
| **智能導航** | 自動處理重定向、彈窗 |
| **內容提取** | AI 優化的結構化輸出 |
| **表單處理** | 自動填寫和提交 |
| **截圖和 PDF** | 完整頁面保存 |
| **Session 管理** | 保持登入狀態 |

### 安裝

```bash
# 透過 npm
npm install @modelcontextprotocol/server-cortexscout

# 或使用 Docker
docker pull cortexscout/mcp-server
```

### 配置

```json
// mcp_config.json
{
  "mcpServers": {
    "cortexscout": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "cortexscout/mcp-server"
      ],
      "env": {
        "STEALTH_MODE": "true",
        "PROXY": "http://proxy:8080"
      }
    }
  }
}
```

### MCP 函數

```javascript
// 導航
await cortexscout_navigate({ 
  url: "https://example.com",
  wait_until: "networkidle"
});

// 提取結構化數據
await cortexscout_extract({
  schema: {
    title: "string",
    price: "number",
    items: "array"
  }
});

// 執行互動
await cortexscout_interact({
  action: "click",
  selector: ".button"
});

// 截圖
await cortexscout_screenshot({
  full_page: true,
  format: "png"
});
```

### 進階功能

```javascript
// 處理複雜頁面
await cortexscout_navigate({ 
  url: "https://example.com/dashboard",
  actions: [
    { type: "wait", selector: ".loading", hidden: true },
    { type: "scroll", direction: "down" },
    { type: "click", selector: ".load-more" }
  ]
});

// 智能提取（使用 AI 識別）
await cortexscout_smart_extract({
  prompt: "提取所有產品名稱和價格",
  format: "json"
});

// 保持 Session
const session = await cortexscout_create_session();
await cortexscout_login({
  session_id: session.id,
  url: "https://example.com/login",
  username: "user",
  password: "pass"
});
```

### 適用場景

| 場景 | 推薦度 |
|------|--------|
| AI 數據收集 | ⭐⭐⭐⭐⭐ |
| 複雜互動頁面 | ⭐⭐⭐⭐ |
| 需要保持狀態 | ⭐⭐⭐⭐⭐ |
| 大規模爬取 | ⭐⭐⭐ |

---

## Stealth Browser MCP

### 簡介

Stealth Browser MCP 是一個專注於繞過反爬蟲檢測的 MCP Server。它使用多種技術來隱藏自動化特徵，讓瀏覽器看起來像真人操作。

### 反檢測技術

| 技術 | 說明 |
|------|------|
| **WebDriver 隱藏** | 移除 navigator.webdriver 標記 |
| **插件模擬** | 模擬 Chrome 插件特徵 |
| **語言偽裝** | 模擬真實瀏覽器語言設置 |
| **硬體偽裝** | 偽造 WebGL、Canvas 指紋 |
| **行為模擬** | 模擬人類滑鼠移動軌跡 |

### 安裝

```bash
# 使用 npx
npx @anthropic-ai/mcp-server-stealth-browser

# 或 Docker
docker pull mcp/stealth-browser
```

### 配置

```json
{
  "mcpServers": {
    "stealth-browser": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-p", "9222:9222",
        "mcp/stealth-browser"
      ],
      "env": {
        "STEALTH_LEVEL": "high",
        "FINGERPRINT": "random"
      }
    }
  }
}
```

### MCP 函數

```javascript
// 啟動隱身瀏覽器
await stealth_browser_launch({
  stealth_level: "high",     // low, medium, high
  fingerprint: "random",      // random, windows, macos
  proxy: "http://proxy:8080"
});

// 導航（自動處理反檢測）
await stealth_browser_navigate({
  url: "https://protected-site.com",
  wait_for: "domcontentloaded"
});

// 執行腳本
await stealth_browser_evaluate({
  script: "document.querySelector('.content').textContent"
});

// 取得頁面內容
await stealth_browser_content({
  format: "markdown"
});
```

### 進階用法

```javascript
// 高階隱身模式
await stealth_browser_launch({
  stealth_level: "high",
  fingerprint: {
    os: "windows",
    browser: "chrome",
    version: "120",
    screen: { width: 1920, height: 1080 },
    timezone: "Asia/Taipei",
    language: "zh-TW"
  },
  proxy_pool: [
    "http://proxy1:8080",
    "http://proxy2:8080"
  ],
  rotate_fingerprint: true
});

// 人類行為模擬
await stealth_browser_type({
  selector: "input[name='search']",
  text: "關鍵字",
  human_like: true,      // 模擬人類打字速度
  random_delay: true     // 隨機延遲
});

await stealth_browser_click({
  selector: "button.submit",
  human_like: true,      // 模擬人類滑鼠移動
  scroll_into_view: true
});
```

### 檢測繞過能力

| 反爬蟲系統 | 繞過成功率 |
|-----------|-----------|
| Cloudflare | 85-95% |
| Akamai Bot Manager | 75-90% |
| PerimeterX | 70-85% |
| DataDome | 60-80% |
| reCAPTCHA v2 | 需配合 2Captcha |
| reCAPTCHA v3 | 50-70% |

### 適用場景

| 場景 | 推薦度 |
|------|--------|
| 高度保護網站 | ⭐⭐⭐⭐⭐ |
| Cloudflare 保護 | ⭐⭐⭐⭐ |
| 需要登入的網站 | ⭐⭐⭐⭐ |
| 大批量爬取 | ⭐⭐ (速度較慢) |

---

## 付費方案說明

### Browserbase

**官網**: https://browserbase.com

#### 簡介

Browserbase 是一個無伺服器瀏覽器平台，提供雲端瀏覽器實例，專為 AI Agent 和自動化設計。

#### 核心特性

| 特性 | 說明 |
|------|------|
| **無伺服器** | 不需要管理基礎設施 |
| **自動擴展** | 自動處理併發請求 |
| **內建反檢測** | 自動繞過 Cloudflare、Akamai |
| **Session 持久化** | 保持登入狀態 |
| **錄製和回放** | 記錄瀏覽器操作 |
| **除錯工具** | 即時監控和診斷 |

#### 定價

| 方案 | 價格 | 包含 |
|------|------|------|
| **免費** | $0/月 | 1000 分鐘/月 |
| **開發者** | $29/月 | 5000 分鐘/月 |
| **團隊** | $99/月 | 25000 分鐘/月 |
| **企業** | 客製化 | 無限制 |

#### 使用範例

```javascript
// Browserbase MCP
await browserbase_create_session({
  browser: {
    stealth: true,
    fingerprint: "random"
  }
});

await browserbase_navigate({
  session_id: session.id,
  url: "https://example.com"
});

await browserbase_screenshot({
  session_id: session.id
});
```

#### Python SDK

```python
from browserbase import Browserbase

bb = Browserbase(api_key="your_key")

# 建立瀏覽器會話
session = bb.sessions.create(
    stealth=True,
    proxy=True
)

# 導航
page = session.page
page.goto("https://example.com")

# 取得內容
content = page.content()

# 關閉
session.close()
```

#### 適用場景

| 場景 | 推薦度 |
|------|--------|
| AI Agent | ⭐⭐⭐⭐⭐ |
| 大規模爬取 | ⭐⭐⭐⭐⭐ |
| 需要穩定性 | ⭐⭐⭐⭐⭐ |
| 成本敏感 | ⭐⭐⭐ |

---

### Bright Data

**官網**: https://brightdata.com

#### 簡介

Bright Data 是業界領先的代理和網頁數據平台，提供完整的反封鎖解決方案。

#### 產品線

| 產品 | 說明 |
|------|------|
| **代理網路** | 住宅、數據中心、ISP 代理 |
| **Web Scraper IDE** | 可視化爬蟲開發環境 |
| **Web Unlocker** | 自動繞過反爬蟲 |
| **數據集** | 預構建的數據集 |
| **瀏覽器 API** | 雲端瀏覽器實例 |

#### 定價

| 產品 | 起價 | 說明 |
|------|------|------|
| **代理** | $500/月 | 住宅代理起價 |
| **Web Unlocker** | $500/月 | 自動繞過反爬蟲 |
| **瀏覽器 API** | $3/GB | 按流量計費 |
| **數據集** | 視需求 | 預構建數據 |

#### Web Unlocker API

```python
import requests

# Bright Data Web Unlocker
url = "https://brightdata.com/api/unblock"
params = {
    "url": "https://target-site.com",
    "method": "GET"
}
headers = {
    "Authorization": "Bearer YOUR_API_KEY"
}

response = requests.post(url, json=params, headers=headers)
print(response.json())
```

#### MCP 整合

```javascript
// Bright Data MCP（視具體實作）
await brightdata_unlock({
  url: "https://protected-site.com",
  options: {
    proxy_type: "residential",
    country: "tw"
  }
});

await brightdata_scrape({
  urls: ["https://site1.com", "https://site2.com"],
  format: "json"
});
```

#### 優缺點

| 優點 | 缺點 |
|------|------|
| ⭐ 高成功率 | ⚠️ 價格昂貴 |
| ⭐ 全球代理網路 | ⚠️ 學習曲線 |
| ⭐ 企業級穩定 | ⚠️ 最低消費高 |
| ⭐ 專業支援 | |

#### 適用場景

| 場景 | 推薦度 |
|------|--------|
| 企業級爬蟲 | ⭐⭐⭐⭐⭐ |
| 高難度網站 | ⭐⭐⭐⭐⭐ |
| 大規模數據收集 | ⭐⭐⭐⭐ |
| 個人專案 | ⭐ (太貴) |

---

### Zyte (原 Scrapinghub)

**官網**: https://zyte.com

#### 簡介

Zyte 是企業級網頁數據提取平台，前身為 Scrapinghub，提供托管爬蟲和反封鎖服務。

#### 產品線

| 產品 | 說明 |
|------|------|
| **Zyte API** | 自動繞過反爬蟲 |
| **Smart Proxy Manager** | 智能代理管理 |
| **Scrapy Cloud** | Scrapy 專案托管 |
| **數據提取** | GPU 加速的提取服務 |

#### 定價

| 方案 | 價格 | 說明 |
|------|------|------|
| **Start** | $25/月 | 小型專案 |
| **Grow** | $100/月 | 中型專案 |
| **Scale** | $500/月 | 大型專案 |
| **企業** | 客製化 | 無限制 |

#### 使用範例

```python
# Zyte API
import requests

url = "https://app.zyte.com/api/v1/extract"
payload = {
    "url": "https://example.com",
    "actions": [
        {"actionType": "scroll"},
        {"actionType": "wait", "waitTime": 2000}
    ],
    "extract": {
        "title": "h1::text",
        "items": {
            "selector": ".item",
            "fields": {
                "name": ".name::text",
                "price": ".price::text"
            }
        }
    }
}

response = requests.post(
    url,
    json=payload,
    headers={"Authorization": "Bearer YOUR_API_KEY"}
)
print(response.json())
```

---

### Oxylabs

**官網**: https://oxyLabs.io

#### 簡介

Oxylabs 是高品質代理和數據收集解決方案提供商，擁有龐大的住宅代理網路。

#### 產品線

| 產品 | 說明 |
|------|------|
| **住宅代理** | 超過 1 億個真實 IP |
| **數據中心代理** | 高速數據中心 IP |
| **Web Scraper** | 可視化爬蟲工具 |
| **SERP API** | 搜索結果 API |

#### 定價

| 產品 | 起價 |
|------|------|
| **住宅代理** | $300/月 (30GB) |
| **SERP API** | $99/月 |
| **Web Scraper** | $99/月 |

#### 使用範例

```python
# Oxylabs Web Scraper API
import requests

url = "https://realtime.oxylabs.io/v1/queries"
payload = {
    "source": "universal",
    "url": "https://example.com",
    "parse": True,
    "render": "html"
}
headers = {
    "Authorization": "Basic YOUR_CREDENTIALS"
}

response = requests.post(url, json=payload, headers=headers)
```

---

## 付費方案比較

| 方案 | 起價 | 反爬蟲能力 | 易用性 | 適合場景 |
|------|------|-----------|--------|---------|
| **Browserbase** | $0/免費層 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | AI Agent、中小型專案 |
| **Bright Data** | $500/月 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 企業級、高難度網站 |
| **Zyte** | $25/月 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Scrapy 用戶、中型專案 |
| **Oxylabs** | $99/月 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 高品質代理、SERP |
| **agent-browser** | 免費 | ⭐⭐⭐ | ⭐⭐⭐⭐ | 個人專案、學習 |

---

## 免費 vs 付費方案選擇建議

### 選擇決策樹

```
開始│
    ├── 是否需要處理高難度反爬蟲？
    │   ├── 是 → 付費方案 (Bright Data / Zyte)
    │   └── 否 ↓│
    ├── 是否需要大規模爬取？
    │   ├── 是 → Browserbase / Zyte
    │   └── 否 ↓
    ├── 是否需要穩定的生產環境？
    │   ├── 是 → Browserbase / Zyte
    │   └── 否 ↓
    └── 個人專案 / 學習 → agent-browser (免費)
```

### 具體建議

| 需求 | 推薦方案 |
|------|---------|
| 個人學習、小型專案 | agent-browser (免費) |
| AI Agent 開發 | Browserbase 或 agent-browser |
| 中型專案、Scrapy 用戶 | Zyte |
| 企業級、高難度網站 | Bright Data |
| 高品質代理需求 | Oxylabs |

---

## 相關文件

- `cb_download_guide.md` - 可轉債下載指南
- `.opencode/skills/agent-browser/SKILL.md` - agent-browser 技能定義

---

## 更新歷史

- 2026-04-11: 初版，整理反爬蟲工具說明
- 2026-04-11: 新增 Scrapling、CortexScout、Stealth Browser MCP 詳細說明
- 2026-04-11: 新增付費方案說明（Browserbase、Bright Data、Zyte、Oxylabs）