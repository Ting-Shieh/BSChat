# BSChat UI/UX — M11 電子名片 opt-in（v4 切片）

> **版本**：v1.0 · 2026-07-14  
> **依據**：`BSChat_SA-SD_M11_v1.1.md`、Design Foundation、既有 `OrgAdminPage`

## Delta check（M11 · UI/UX）
已檢查 SA-SD v1.1、PRD §2.3、既有 Admin UI  
→ ✅ 開工

## 1. Admin（改文案＋欄位）
- 頁標題：`公開目錄` → **`電子名片`**
- 列表狀態：已發布 → **`AI 可推薦`**；草稿／已下架照舊語意
- 主按鈕：發布 → **`允許 AI 推薦`**；下架 → **`關閉 AI 推薦`**
- 表單加：一句話介紹、頭像 URL（選填）
- 已允許推薦的列：顯示可複製 **`分享連結`**（`/card/{id}`）

## 2. 公開分享頁 `/card/[id]`
- 一頁一職：品牌弱化、名片為主（對齊現有 surface tokens）
- 顯示：頭像（可無）、姓名、職稱、公司、一句話、關鍵字 chips、外鏈 CTA
- 無電話／Email；未公開 → 簡單「找不到或未開放推薦」
- 可複製本頁連結（QR Later；本切片可省略或用外鏈文字）

## 3. 完成 → ENG／Code
