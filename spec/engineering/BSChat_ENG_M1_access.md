# BSChat ENG — M1 進場（Email＋密碼＋Google）

> **版本**：v1.0  
> **日期**：2026-07-14  
> **依據**：`BSChat_SA-SD_M1_access.md`、`BSChat_UIUX_M1_access.md`、TECH_STACK LOCKED  
> **估算**：~1–1.5 工程日  
> **範圍**：密碼註冊／登入／重設、產品 Auth UI、去 Dev 進場；不改試用扣次

---

## Delta check（M1 · ENG 進場）

已檢查 PRD §6.5、SA-SD_M1_access、UIUX_M1_access、TECH_STACK、既有 `auth.py`／`identity.py`／`LoginForm`  
→ ✅ 開工 ENG

---

## 1. 技術選型（增量）

| 項 | 選擇 |
|----|------|
| 密碼雜湊 | `argon2-cffi`（Argon2id） |
| 寄信 | 既有 Resend／`send_magic_email` 可复用改主旨／文案為重設密碼 |
| 其餘 | FastAPI、Alembic、既有 JWT |

`uv add argon2-cffi`

---

## 2. 後端改動清單

| 檔案 | 動作 |
|------|------|
| `alembic/versions/021_password_auth.py` | `users.password_hash`、`password_changed_at`；`magic_login_tokens.purpose` |
| `app/models/user.py` / `magic_login.py` | 欄位 |
| `app/core/passwords.py`（新） | `hash_password` / `verify_password` |
| `app/modules/team_invite/identity.py` | upsert 不清 password；可抽 `ensure_free_entitlement` |
| `app/api/v1/auth.py` | `register` / `login` / `password/forgot` / `password/reset`；`auth-mode` 欄位；magic 登入可不刪但產品不用 |
| `app/api/v1/me.py` | `POST /plan` 開頭：`if not allow_dev_login: 403` |
| `app/schemas/auth.py` | Register／Login／Forgot／Reset body |
| `tests/test_m1_password_auth.py` | 註冊、重複 email、登入錯、重設、Google 合併不清密、dev-login 關時 403、plan 關時 403 |

### 註冊偽碼

```python
email = normalize(body.email)
if await get_user_by_email(email): raise 409 EMAIL_ALREADY_REGISTERED
user = User(email=email, display_name=..., password_hash=hash_password(body.password))
# workspace + entitlement free（含 public_recommend 預設）
if body.invite_token: await accept_invite(...)
return TokenResponse(create_access_token(user.id))
```

---

## 3. 前端改動清單

| 檔案 | 動作 |
|------|------|
| `app/(auth)/register/page.tsx` | 新頁 |
| `app/(auth)/forgot-password/page.tsx` | 新頁 |
| `app/(auth)/reset-password/page.tsx` | 新頁 |
| `features/auth/components/LoginForm.tsx` | **重寫**：密碼表單＋Google；刪 Dev／plan／seed |
| `features/auth/components/RegisterForm.tsx` | 新 |
| `features/auth/api.ts` | register／login／forgot／reset；可留 `devLogin` 但不掛 UI |
| `features/auth/hooks.ts` | 對應 hooks |
| `features/settings/…` | 移除一鍵切方案；升級 CTA |
| `features/org/OrgAdminPage.tsx` | 文案拿掉「用 dev 登入選 enterprise」 |
| `shared/types/auth.ts` | AuthMode 新欄位 |

`auth-mode`：`password_auth_enabled`／`google_enabled`；**永不**依 `allow_dev_login` 顯示 Dev UI。

---

## 4. 實作序

1. Migration + passwords helper + register／login API + tests  
2. Forgot／reset + 寄信文案  
3. 前端四頁＋拆 LoginForm  
4. `/me/plan` gate＋設定／Admin 文案清理  
5. 手動：註冊→登出→登入→忘記密碼；Google（若有憑證）

---

## 5. 測試要點

| ID | Expect |
|----|--------|
| T1 | 註冊 201＋JWT；DB 有 hash 非明文 |
| T2 | 同 email 再註冊 409 |
| T3 | 錯密碼 401 INVALID_CREDENTIALS |
| T4 | forgot 對不存在 email 仍 200 |
| T5 | reset 後可用新密碼；舊密失敗 |
| T6 | `ALLOW_DEV_LOGIN=false` → dev-login 與 /me/plan 403 |

---

## 6. 完成標準
- [x] 檔案清單與序清楚  
- [ ] Code → QA  
