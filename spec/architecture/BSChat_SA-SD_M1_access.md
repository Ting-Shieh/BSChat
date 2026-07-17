# BSChat SA/SD — Module 1：進場切片（Email＋密碼＋Google）

> **版本**：v1.1（進場）  
> **日期**：2026-07-14  
> **依據**：kickoff `m1-access-20260714.md`、`BSChat_PM_M1.md`、PRD v4 §6.5／DDR-v4-8  
> **與 v1.0 關係**：v1.0＝公開推薦終身試用（仍有效）；**本文＝身分進場**，不改試用扣次契約  
> **架構**：Modular Monolith；Auth＝傳統確定性 code（⚠️ 禁止 AI 化）  
> **🟡 已採預設並鎖定**（用戶「繼續」）：見 §7 DDR-M1-A10～A14

試用契約全文見同目錄歷史段落／原 `BSChat_SA-SD_M1.md` v1.0 正文（檔案後半保留或分檔；實作以 entitlement helpers 為準）。

---

## 1. 模組內部架構（進場）

```
┌─────────────────────────────────────────────────────────────┐
│  Client                                                      │
│  /register  /login  /forgot-password  /reset-password        │
│  Google 按鈕 → API /auth/google/start                        │
│  （無 Dev 登入、無方案下拉、無 seed_org）                       │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  M1 Access                                                   │
│  · register / login（password verify）                       │
│  · password reset request / confirm                          │
│  · upsert_user_from_identity（Google 既有）                  │
│  · 建立 Workspace + UserEntitlement(free)                    │
│  · 可選 accept_invite(invite_token)                          │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  既有                                                          │
│  JWT · Resend 寄信 · Org invite · entitlement 試用（v1.0）   │
└─────────────────────────────────────────────────────────────┘
```

| 擁有（本切片） | 不擁有 |
|----------------|--------|
| password_hash、註冊／登入／重設 API、產品 Auth UI 契約、`auth-mode` 產品欄位 | 金流、SSO、細 RBAC |
| 拿掉產品 Dev 進場面 | 自動化測試用 `ALLOW_DEV_LOGIN`（後端可留） |
| Google 與密碼帳號合併規則 | 強制 Email 驗證擋進 App（Should／Next） |

**⚠️ 不建議 AI 化**：密碼雜湊／比對、token 核發、登入失敗訊息、權限閘門。  
**MCP**：不 expose。

---

## 2. 資料庫設計（增量）

### 2.1 `users`（增量）

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `password_hash` | VARCHAR(255) | NULL | Argon2id 編碼字串；僅 Google 註冊可為 NULL |
| `password_changed_at` | TIMESTAMPTZ | NULL | 重設／首次設密時更新（稽核；可選） |

既有：`email` UNIQUE、`google_sub` UNIQUE NULL、`display_name`。

### 2.2 `magic_login_tokens` → 擴充用途（DDR-M1-A10＝A）

| Column | Type | Description |
|--------|------|-------------|
| `purpose` | VARCHAR(32) NOT NULL DEFAULT `'magic_login'` | `magic_login`｜`password_reset` |

- **產品一般登入不再走** `magic_login` purpose。  
- `password_reset`：單次消費、短 TTL（建議 **1 小時**）、消費後更新 `password_hash`。  
- 舊列 migration 設 `purpose='magic_login'`。

### 2.3 不新增
- 不另建 `password_reset_tokens` 表（減少重複）。  
- 不加 `email_verified_at` 於本 Must（Should：可另開）。

**Migration**：Alembic 下一版（建議 `021_password_auth`）。

---

## 3. 密碼與安全規則

| 規則 | 值 |
|------|-----|
| 雜湊 | **Argon2id**（Python：`argon2-cffi`／pwdlib） |
| 長度 | min **8**、max **128**（UTF-8 碼元） |
| 登入失敗 | 一律 `401` + `INVALID_CREDENTIALS`（不區分 email 是否存在） |
| 註冊 email 重複 | `409` + `EMAIL_ALREADY_REGISTERED` |
| 無密碼帳號（純 Google）用密碼登入 | 同 `INVALID_CREDENTIALS`；可另 `hint` 於 UI「請用 Google」但不經 API 洩漏 |
| 重設請求 | 一律 `200` + `{ sent: true }`（防枚舉）；無 Resend 且非測試 → `503 EMAIL_NOT_CONFIGURED` |
| Rate limit（ENG 實作） | 登入／註冊／重設：依 IP＋email 節流（可先粗：每分鐘 N 次） |

---

## 4. API 規格

**Base**：`/api/v1/auth` · 成功登入類回 `TokenResponse { access_token }`（與現況一致）

### 4.1 `POST /auth/register`

```json
// req
{ "email": "a@b.com", "password": "********", "display_name": "Ada", "invite_token": null }
// 201 res
{ "access_token": "…" }
```

行為：
1. 正規化 email lower；驗證密碼長度  
2. 若 email 已存在 → 409  
3. 建立 User（hash 密碼）+ Workspace + Entitlement(`free` + 試用欄位預設)  
4. 若有 `invite_token` → `accept_invite`  
5. 回 JWT（註冊即登入）

### 4.2 `POST /auth/login`

```json
{ "email": "a@b.com", "password": "********" }
// 200 → TokenResponse
```

### 4.3 `POST /auth/password/forgot`

```json
{ "email": "a@b.com" }
// 200 { "sent": true }
```

建立 `purpose=password_reset` token；寄信連結  
`{FRONTEND}/reset-password?token=…`（或 API verify 頁再轉前端——建議 **前端頁** 帶 token 呼叫 confirm）。

### 4.4 `POST /auth/password/reset`

```json
{ "token": "raw", "new_password": "********" }
// 200 → TokenResponse（重設後直接登入）
```

無效／過期／已消費 → `400` `RESET_TOKEN_INVALID`

### 4.5 Google（既有，契約微調）

- `GET /auth/google/start?invite_token=&next=`  
- callback → `upsert_user_from_identity`：  
  - 同 email 已存在：綁 `google_sub`（若空）、**不清除**既有 `password_hash`  
  - 新用戶：`password_hash=NULL` + free entitlement  
  - 有 invite → accept  

### 4.6 產品下架／降級

| Endpoint | 產品 | 測試 |
|----------|------|------|
| `POST /auth/dev-login` | UI 不呼叫；`ALLOW_DEV_LOGIN=false` 時 403 | 可開 flag |
| `POST /me/plan` | **UI 移除**；API 僅當 `ALLOW_DEV_LOGIN=true` 否則 403 | 測試切方案 |
| `POST /auth/magic-link`（登入用） | **產品 UI 不提供**；可保留後端供內部／相容 | — |
| `GET /auth/auth-mode` | 見下 | |

### 4.7 `GET /auth/auth-mode`（產品欄位）

```json
{
  "password_auth_enabled": true,
  "google_enabled": true,
  "password_reset_email_enabled": true,
  "allow_dev_login": false,
  "server_time": "…"
}
```

前端：**忽略** `allow_dev_login` 渲染（即使 true 也不顯示 Dev UI）。  
可移除對產品有意義的 `email_magic_link_enabled`（改 `password_reset_email_enabled`）。

---

## 5. 內部資料流程

**Flow R — Email 註冊**  
validate → create user+hash → workspace → entitlement free → optional invite → JWT → `/contacts` 或 `/welcome`

**Flow L — 密碼登入**  
lookup by email → verify hash → JWT（失敗統一 INVALID_CREDENTIALS）

**Flow F — 忘記密碼**  
always 200 →（若 user 存在且可寄信）寫 reset token → email link → 用戶設新密 → consume token → 更新 hash → JWT

**Flow G — Google**  
OAuth → upsert（合併規則 §4.5）→ optional invite → JWT

**Flow D — 產品無 Dev**  
登入頁不讀方案／seed；設定頁升級＝CTA 文案，不呼叫 `/me/plan`

---

## 6. 前端路由契約（給 UI/UX）

| 路由 | 必要 |
|------|------|
| `/register` | email、password、確認密碼（或單欄+強度提示）、可選顯示名、連到登入、Google |
| `/login` | email、password、忘記密碼連結、註冊連結、Google |
| `/forgot-password` | email → 「若帳號存在將收到信件」 |
| `/reset-password` | token（query）+ 新密碼 |
| `/join/[token]` | 預覽後導向 register／login 並帶 `invite_token` |
| 設定 | 移除一鍵切方案；顯示目前方案＋申請／聯絡 CTA |

---

## 7. 決策紀錄（進場）

| ID | 決策 | Tier | 狀態 |
|----|------|------|------|
| DDR-M1-A10 | 重設 token 擴充 `magic_login_tokens.purpose`，不另開表 | 🟡 | **鎖定＝A** |
| DDR-M1-A11 | 雜湊＝Argon2id；密碼長度 8–128 | 🟢 | 鎖定 |
| DDR-M1-A12 | 註冊成功直接發 JWT；驗證信＝Should 不擋進 App | 🟢 | 鎖定（對齊 PM） |
| DDR-M1-A13 | `/me/plan` 與 `dev-login` 僅 `ALLOW_DEV_LOGIN` | 🟢 | 鎖定 |
| DDR-M1-A14 | 產品登入主路徑＝密碼＋Google；magic 不作一般登入 | 🟢 | 鎖定（PM／用戶） |
| DDR-M1-A3 等 | 見 `BSChat_PM_M1.md` | — | 已鎖定 |

---

## 8. 正向追溯

| 產出 | 來源 |
|------|------|
| Email＋密碼＋Google、忘記密碼 | PM F-1.1／1.1b、US-M1-01／02／02b、DDR-v4-8 |
| 去 Dev 進場 | PM F-1.7、US-M1-06、DDR-M1-A4 |
| 邀請可選 | US-M1-03／04 |
| Free 預設＋試用欄 | v1.0 試用切片 |

---

## 9. 完成標準（本階段）

- [x] Schema／API／合併規則／Dev 邊界寫清  
- [x] DDR-M1-A10～A14 鎖定  
- [x] → 進 UI/UX（進場畫面）→ UIUX／ENG 已產出；待 Code

---

# 附錄：v1.0 公開推薦終身試用（仍有效）

> 原文自 2026-07-14 試用切片；扣次／`/me` quotas／DDR-M1-01／02 不變。實作已落地 migration 019。細節以 git 歷史中 v1.0 全文與 `app/core/entitlements.py` 為準。若需完整重貼可從上一版還原；**進場實作不得改動扣次語意**。
