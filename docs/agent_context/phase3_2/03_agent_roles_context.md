# Phase 3.2 - Agent 角色職責

## 📐 @ARCH
- **職責**: 設計評級規則與邊界條件
- **重點**: 
  - 確認 S/A/B/C 門檻值具市場區分度
  - 確保評級邏輯與 Phase 3.1 的溢價率輸出相容

## 💻 @CODER
- **職責**: 實作 ChipProfiler + RiskAssessor + 單元測試
- **重點**:
  - **ChipProfiler**: 
    - 黑名單比對效率 O(1) (使用 Dict/set)
    - match_top_buyers 輸入 broker_breakdown 資料
  - **RiskAssessor**: 
    - 綜合溢價率 (來自 Phase 3.1) + 風險佔比 (來自 ChipProfiler)
    - 評級為 S/A/B/C 字串

## 🧪 @ANALYST
- **職責**: 驗證評級合理性 + 邊界測試
- **重點**: 
  - 使用已知高/低風險案例驗證評級
  - 邊界測試: 9.9%, 10.0%, 10.1% 應得到不同評級
