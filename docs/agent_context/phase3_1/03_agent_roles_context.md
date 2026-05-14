# Phase 3.1 - Agent 角色職責

## 📐 @ARCH
- **職責**: 設計 PremiumCalculator / TechnicalAnalyzer API 介面
- **重點**: 
  - 定義 clear 的輸入/輸出 type hints
  - 確保 AnalysisResult 與 Phase 3.2 RiskAssessor 相容
  - 確認 DB 寫入欄位對應 daily_analysis_results

## 💻 @CODER
- **職責**: 實作計算邏輯與單元測試
- **重點**:
  - **PremiumCalculator**: 純數學函數，浮點精度須達小數 4 位
  - **TechnicalAnalyzer**: numpy 向量化計算，一次批次處理全部標的
  - **單元測試**: 需包含正常值、邊界值、空資料

## 🧪 @ANALYST
- **職責**: 驗證公式正確性 + 歷史資料回測
- **重點**:
  - 使用家登/聚和等已知標的驗證溢價率
  - 確認 TechnicalAnalyzer 在已知突破/盤整行情下判斷正確

## 🏗️ @INFRA
- **職責**: 確保 numpy 依賴已安裝
- **重點**: 更新 requirements.txt、確認 pip install 無衝突
