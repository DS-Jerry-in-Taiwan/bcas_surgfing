# BCAS Quant 爬蟲架構高階規劃

## 1. 架構設計原則
- **模組化**：每一工具、flow以MCP/Skill模組封裝，便於橫向擴充
- **高容錯**：針對目標網頁不同反爬蟲方案選擇適當引擎與繞過策略
- **混合式自動化**：本地（Playwright、agent-browser、Scrapling）、API雲端（Tavily、Brave、Browserbase等）
- **流程組合**：可疊加多個步驟（導航、互動、下載、解析、批量自動化等）

## 2. 技術棧/模組
- **Browser Skill/agent-browser**：基於 Playwright 的本地容器瀏覽器自動化，支援反檢測 stealth 模式，遮蔽自動化特徵、可做人機互動仿真。
- **Playwright MCP**：對主流程有較高自控權，能實現複雜互動（如登入、動態資料載入、全頁快照等）。
- **Scrapling MCP**：聚焦於智能解構HTML、解決動態渲染與Cloudflare等障礙，效率高、支援steam抓取。若需批量內容提取，適用。
- **Tavily MCP/Brave Search MCP**：API 型搜尋＋抓取/摘要，適合不需登入的公開頁面、新聞、快照。對關鍵詞自動發想（查找可轉債最新動態、新公告等）特別有用。
- **CortexScout MCP**：為AI/LLM Agent設計，兼具互動、智慧節點導航與結構化資料輸出。
- **Browserbase, BrightData, Zyte, Oxylabs, Web Unlocker（付費）**：企業/大規模場景下可導入。提供全球代理，輕鬆突破多數反爬蟲保護。

## 3. 流程/能力組合
- 依照目標網站保護程度，自動選用組合：
  1. 快速公開頁面：Brave Search → Tavily Extract/Tavily Crawl → (可用) Playwright Snapshot
  2. 需登入互動頁面：Playwright MCP／Stealth MCP → 互動→ 頁面解析
  3. 高度Cloudflare/DDOS保護頁：agent-browser Stealth／Scrapling Stealth／Stealth Browser MCP → 分段抓取
  4. 巨量資料頁面：Tavily Crawl → Scrapling／Playwright 批次下載/解析
  5. 企業級（如遭遇全面封鎖）：Bright Data/Zyte/Oxylabs 付費 API 配合。

## 4. 決策指引（Decision Tree）
- 目標站點是否有高安全檢測？
  - 是：優先 Stealth Browser MCP、Bright Data、Scrapling Stealth
  - 否 → 下步
- 是否需大量批次爬取？
  - 是：Browserbase、Tavily Crawl、Zyte、Scrapling（stream設計）
  - 否 → 普通方案
- 是否需複雜互動？
  - 是：Playwright MCP、CortexScout、agent-browser
  - 否：Tavily/Brave Search + Extract
- 成本考量、穩定性？
  - Free 方案優先（除大企業或主管明示）

## 5. 通用高階流程
1. 任務分級與分類——根據目標快篩最適方案
2. 流量控管與防黑機制——設限速、輪替代理、人機仿真延遲
3. 資料清理、驗證、統一格式轉換（如Big5→UTF8等）
4. 串接MCP/Skill自動管理任務隊列與錯誤重試
5. 結合AI智能探索——利用 LLM 做動態封鎖時的規則意圖分析（ex:自動尋找繞過新策略、驗證碼識別等）

## 6. 擴展/未來發展
- 自動化決策機制強化（ex: 站點回應自動分類/適應路徑切換）
- 多語系爬蟲及通用化數據Schemas（便於資料庫/資產池匯總）
- 結合用戶端AI Agent協同（ex: 用戶自助式資料收集事前/事後自動校驗）
- 企業級API Key及流量/監控儀表板整合

---

本文件將持續根據實際專案經驗、現場需求更新，用於團隊溝通架構全圖，及新進/合作人員快速上手，並規劃擴展方向。