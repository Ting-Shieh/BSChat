# BSChat ENG — M11 電子名片 opt-in（v4 切片）

> **版本**：v1.0 · 2026-07-14  
> **依據**：SA-SD M11 v1.1、UIUX_M11

## Delta check（M11 · ENG）
已檢查 SA-SD v1.1、UIUX、TECH_STACK  
→ ✅ 開工

## 實作清單
1. Alembic `020_ecard_blurb_avatar.py`：`one_line_blurb`、`avatar_url`
2. Model／schemas／service create+update+seed
3. `index_builder.build_search_text` 含 blurb
4. `GET /api/v1/public/cards/{stub_id}`（公開路由）
5. Frontend：`OrgAdminPage` 文案＋欄位＋複製分享連結
6. Frontend：`app/.../card/[id]/page.tsx` 公開頁
7. 單元／API 測：published 200、draft 404（可寫；用戶指示可不跑手動測）

## 完成 → Code
