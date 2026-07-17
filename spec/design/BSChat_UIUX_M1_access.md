# BSChat UI/UX — M1 進場（註冊／登入／忘記密碼）

> **版本**：v1.0  
> **日期**：2026-07-14  
> **依據**：`BSChat_SA-SD_M1_access.md`、`BSChat_PM_M1.md`、Design Foundation、既有 `(auth)/login`  
> **UI 庫**：沿用 shadcn/ui（不新選庫）  
> **範圍**：產品 Auth 畫面；**移除** Dev／方案／seed_org 進場  
> **靜態原型**：  
> - 登入／註冊：[`screen-5-auth-account.html`](../screens/screen-5-auth-account.html)  
> - **我的改版**：[`screen-6-my-account.html`](../screens/screen-6-my-account.html)

---

## Delta check（M1 · UI/UX 進場）

已檢查 PRD §6.5、SA-SD_M1_access（剛鎖定）、PM_M1、register、既有 LoginForm（Dev 向）  
→ ✅ 開工 UI/UX

---

## 1. 使用者流程

### 註冊
1. `/register` → 填 Email、密碼、（可選）顯示名 → 提交  
2. 成功 → 進 App（預設聯絡人／歡迎）  
3. 可點「使用 Google 註冊」  
4. 底：「已有帳號？登入」

### 登入
1. `/login` → Email＋密碼 → 進 App  
2. 或 Google  
3. 「忘記密碼？」→ `/forgot-password`  
4. 「沒有帳號？註冊」

### 忘記／重設密碼
1. 輸入 Email → 提示「若帳號存在，我們已寄重設信」  
2. 信內連結 → `/reset-password?token=` → 設新密碼 → 自動登入

### 邀請
1. `/join/[token]` → 顯示團隊名 → CTA「註冊並加入」／「登入並加入」  
2. 帶 `invite_token` 進 register／login／Google

### 設定／「我的」（權限後必改）
| 要 | 不要 |
|----|------|
| 只讀方案徽章、公開推薦剩餘／無限 | 一鍵切 Free／Pro／企業、改回 Free |
| 升級 Pro＝「聯絡我們」CTA | 「試用 Pro」假切換 |
| 申請企業版（與 Pro 分開） | 暗示 Pro 可曝光電子名片 |
| 團隊建立／邀請（既有） | Dev／seed 文案 |
| 企業 Admin → 電子名片管理入口 | — |

靜態對照：`screen-5-auth-account.html` 畫面 D／E／F。

---

## 2. 畫面規格

### `/login` · `/register`
| 區塊 | 內容 |
|------|------|
| 標題 | 登入／建立 Free 帳號 |
| 主表單 | Email、Password（register 可加「確認密碼」前端校驗） |
| 次要 | Google 按鈕（`google_enabled` 時） |
| 連結 | 互跳、忘記密碼（僅 login） |
| **禁止** | 方案選單、公司代號／seed_org、Dev 一鍵登入、debug_link 展示 |

錯誤：`INVALID_CREDENTIALS` → 「Email 或密碼不正確」  
`EMAIL_ALREADY_REGISTERED` → 「此 Email 已註冊，請登入」

### `/forgot-password` · `/reset-password`
極簡單欄；成功態清楚；token 無效 → 「連結已失效，請重新申請」

### 密碼欄
- `type=password`；可選顯示／隱藏切換  
- 註冊：下方小字「至少 8 個字元」

---

## 3. 元件對照（shadcn）

| UI | 元件 |
|----|------|
| 表單 | Input、Label、Button |
| 錯誤 | 表單下 inline text / Alert |
| Google | Button variant outline + 文案 |
| 互跳 | Link（Next） |

沿用現有 auth layout／品牌區，不另開設計系統。

---

## 4. 文案（微拷貝）

| 位置 | 文案 |
|------|------|
| Register CTA | 建立帳號 |
| Login CTA | 登入 |
| Google | 使用 Google 繼續 |
| Forgot success | 若此 Email 已註冊，重設信件將寄出 |
| Settings upgrade | 需要更多公開推薦？升級 Pro（聯絡我們） |
| Enterprise | 要發布可被 AI 推薦的電子名片？申請企業版 |

---

## 5. 無障礙
- 標籤與 input 關聯；錯誤 `aria-live`  
- 密碼顯示切換有 accessible name  
- 鍵盤可完成全流程  

---

## 6. 完成標準
- [x] 四路由流程與禁止項寫清  
- [x] 與 SA API 錯誤碼對齊  
- [ ] → ENG  
