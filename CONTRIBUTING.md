# 貢獻指南

歡迎對 BCAS Quant Data Pipeline 專案做出貢獻！本指南將幫助你了解如何參與專案開發。

## 開發流程

1. **Fork 專案**：點擊 GitHub 頁面上的 "Fork" 按鈕，建立你的副本。
2. **建立分支**：為你的功能或修復建立一個新分支：
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **進行修改**：編寫程式碼、測試或文件。
4. **提交更改**：使用清晰的提交訊息：
   ```bash
   git commit -m "feat: 新增某某功能"
   ```
5. **推送分支**：將分支推送到你的 Fork：
   ```bash
   git push origin feature/your-feature-name
   ```
6. **建立 Pull Request**：在原始專案頁面建立 Pull Request。

## 提交訊息規範

請遵循以下格式：
- `feat:` 新增功能
- `fix:` 修復錯誤
- `docs:` 文件更新
- `style:` 程式碼格式調整（不影響功能）
- `refactor:` 重構程式碼
- `test:` 新增或修改測試
- `chore:` 雜項任務（構建、工具等）

## 程式碼風格

- 使用 Python 3.x
- 遵循 PEP 8 風格指南
- 使用有意義的變數和函數名稱
- 為複雜邏輯添加註解

## 測試要求

- 新增功能時請包含對應的測試
- 確保現有測試通過
- 測試檔案應放在 `tests/` 目錄下

## 文件要求

- 更新相關的 README 或文件
- 新增功能時請更新 `docs/` 目錄下的相關文件
- 保持文件與程式碼同步

## 問題回報

發現問題時，請在 Issue 中提供：
1. 問題描述
2. 重現步驟
3. 預期行為與實際行為
4. 環境資訊（Python 版本、作業系統等）

## 聯絡

如有疑問，請透過專案 Issue 或團隊內部管道聯絡。

---

感謝你的貢獻！