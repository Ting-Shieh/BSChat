# Self-hosted auth（產品路徑）

## 產品進場（唯一）
- **註冊**：Email＋密碼（可選顯示名）
- **登入**：Email＋密碼，或 Google OAuth
- **忘記密碼**：Email 重設連結（寄信）
- 新用戶 → 本地 `User` + Free entitlement（含公開推薦終身 2 次）
- **邀請連結** → 加入團隊（`OrgMember`）；**不是**進產品的唯一門
- API 真相：本地 `User` + BSChat JWT

## 明確不是產品進場
- `ALLOW_DEV_LOGIN` / `POST /auth/dev-login` / 登入頁選方案 / `seed_org`  
  → **僅本機與自動化測試**；正式與 dogfood 產品 UI **不提供**
- 企業／Pro 升等：人工或內部工具改 entitlement（Now）；非登入表單
- 純 magic-link 當一般登入主路徑 → **已廢止**（可僅用於重設密碼寄信）

## Google Cloud
1. APIs & Services → Credentials → OAuth 2.0 Client (Web)
2. Authorized redirect URI = `{API}/api/v1/auth/google/callback`
3. Set `GOOGLE_OAUTH_CLIENT_ID` / `SECRET` / `REDIRECT_URI` / `FRONTEND_BASE_URL`

## Email（註冊確認／重設密碼）
- `RESEND_API_KEY`（+ optional `RESEND_FROM_EMAIL`）
- Optional: `AUTH_EMAIL_DOMAIN_ALLOWLIST`（企業限網域時再用；一般用戶註冊**不預設**鎖網域）

## Flow
1. 一般用戶：Email＋密碼註冊／登入（或 Google）→ Free → 收錄／搜尋
2. 需要團隊：設定建立團隊 → 產生邀請 → 同事註冊或登入後加入
3. 企業曝光：人工升 `enterprise` + Admin → 電子名片「允許 AI 推薦」

詳見 `spec/modules/BSChat_PM_M1.md`。
