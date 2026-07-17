# BSChat PM L3 — M1 帳號／進場／權限／方案

> **確認日期**：2026-07-14（PM 定稿；用戶授權可拿掉開發測試用進場）  
> **模組**：M1  
> **上游**：PRD v4、`BSChat_M1_access_permissions_rethink.md`（重審＝調整 → 本檔落地）  
> **一句話**：一般用戶能自助註冊登入；邀請只負責入團；方案決定能力；**產品路徑不含 Dev／測試登入**。

---

## 1. Overview

### 目標
讓真實用戶（一般業務／團隊／企業 Admin）完成：**進場 → 歸屬 → 方案能力**，支撐 PRD v4 網絡層（消費端 Free／Pro＋供給端企業）。

### 非目標（本模組不做／拿掉）
| 項目 | 處置 |
|------|------|
| Dev 登入、方案下拉、`seed_org` 當進場 | **移出產品 UX**；僅後端 flag／測試保留，預設關 |
| 設定頁「一鍵切 Free／Pro／企業」當正式能力 | **移出產品**（改內部／Later 金流） |
| 自助付款／Stripe | Later |
| SSO、細粒度名片權限 UI | Later |
| 邀請制 only | **廢止** |
| 僅 magic、無密碼當主路徑 | **廢止**（用戶：一般系統要有密碼） |

### 成功樣子
新用戶打開產品 → 註冊或登入 → 立刻是 Free → 能收錄／搜尋；被邀則多一步入團；企業 Admin 另線升等後才能曝光電子名片。

---

## 2. 產品模型（鎖定）

```
Identity（身分）      Email＋密碼 ｜ Google OAuth（可選保留 Email 重設用 magic）→ User + JWT
Membership（歸屬）    無團隊 ｜ OrgMember(member|admin)；進場：自建／邀請
Entitlement（方案）   free｜pro｜enterprise + 額度（含公開推薦終身 2 次）
Capability（能力）    見 §3 矩陣；由方案＋角色共同決定
```

**寫死規則**
1. 邀請 ≠ 進產品門票；無邀請也可註冊。  
2. 建團隊 ≠ 企業版。  
3. Pro＝可**消費**公開推薦；僅企業 Admin＝可**曝光**（允許 AI 推薦）。  
4. 能力看**該用戶** `plan_tier`＋org role，不看「同事是不是企業」。

---

## 3. 能力矩陣（Must 對齊 UI／API）

| 能力 | Free | Pro | 企業成員 | 企業 Admin |
|------|------|-----|----------|------------|
| 自助註冊／登入 | ✅ | ✅ | ✅ | ✅ |
| 庫＋Plan 搜尋 | ✅ | ✅ | ✅ | ✅ |
| 團隊池（有 org） | ✅ | ✅ | ✅ | ✅ |
| 建團隊／邀請同事 | ✅ | ✅ | ✅ | ✅ |
| 公開推薦消費 | 終身 2 次 | ✅ | ✅* | ✅* |
| 電子名片允許 AI 推薦 | ❌ | ❌ | ❌ | ✅ |
| LinkedIn／auto-refresh 等 | 依既有 free preset | ✅ | ✅ | ✅ |

\* 以該帳號 entitlement 為準（企業員工若仍是 free，仍受試用限制——升等是帳號／合約問題，Now 用手動升個人或約定企業帳號）。

---

## 4. Feature Requirements

### Must-have（MVP · 進場切片）
| ID | 需求 |
|----|------|
| F-1.1 | `/register`：Email＋密碼（+ 可選顯示名）；`/login`：Email＋密碼 **或** Google |
| F-1.1b | `/forgot-password`：Email 重設連結（寄信）；設新密碼後可登入 |
| F-1.2 | 新用戶自動 `plan_tier=free`＋公開推薦終身配額 2 |
| F-1.3 | Email 唯一；Google 同 email 合併同一 User（已有密碼則綁定 Google，不覆蓋密碼） |
| F-1.4 | `/join/[token]`：登入或註冊後入團（既有強化文案） |
| F-1.5 | `/me` 回方案、試用剩餘、org_memberships（既有） |
| F-1.6 | 公開推薦閘維持 DDR-M1-01／02（既有） |
| F-1.7 | **產品 UI 移除** Dev 登入、進場用方案選擇、`seed_org` 欄 |
| F-1.8 | 企業曝光閘：非 enterprise Admin → 不可 opt-in（既有硬化文案） |
| F-1.8b | 密碼：伺服端雜湊儲存；最短長度與基本強度；登入失敗不洩漏「帳號是否存在」過度細節 |

### Should-have
| ID | 需求 |
|----|------|
| F-1.9 | 首次登入輕量歡迎（收錄 → 搜尋 → 可選邀請） |
| F-1.10 | 設定頁只**展示**方案與剩餘；升級＝「聯絡我們／申請 Pro」CTA（無假切換） |
| F-1.11 | 註冊後寄驗證信（未驗證仍可進 App；未驗證限制可 Next 再加） |

### Nice-to-have / Next
| ID | 需求 |
|----|------|
| F-1.12 | 強制 Email 驗證後才用公開推薦等敏感能力 |
| F-1.13 | 企業申請表 → 人工開 enterprise |
| F-1.14 | 真實訂閱付款 |

---

## 5. 進場旅程（產品唯一真相）

### A. 一般用戶（主）
註冊／登入 → Free →（歡迎）收錄／搜尋 → 公開試用最多 2 → 升級 CTA

### B. 受邀同事
邀請連結 → 註冊或登入 → 加入 org → 團隊池

### C. 企業 Admin
同 A → 建團隊（admin）→ **後台／人工**升 enterprise → 電子名片／允許 AI 推薦  
（產品內不做「測試用一鍵變企業」）

---

## 6. UX 原則
- 註冊＝Email＋密碼為主；Google 為快捷；登入頁提供「忘記密碼」。  
- 註冊與登入是兩個入口。  
- 任何畫面不出現「開發登入」「任意選方案進場」。  
- 無權限時誠實說明（略過 Plan 步驟 3、企業功能鎖），引導升級／申請。  
- 隱私文案維持：未公開名片不會被外人搜到。

---

## 7. User Stories（MVP）

**US-M1-01** 作為一般業務，我想用 Email＋密碼註冊 Free 帳號。  
AC: Given 新 email＋符合規則的密碼, When 提交註冊, Then 有 User＋free＋可進 App。

**US-M1-02** 作為已註冊用戶，我想用 Email＋密碼或 Google 登入。  
AC: Given 既有帳號, When 憑證正確, Then JWT 有效且庫為本人／團隊可見範圍。

**US-M1-02b** 作為忘記密碼的用戶，我想重設密碼後再登入。  
AC: Given 已註冊 email, When 完成重設連結流程, Then 可用新密碼登入；舊密碼失效。

**US-M1-03** 作為新用戶，沒有邀請也能用。  
AC: Given 無 invite, When 註冊完成, Then 不強制 OrgMember。

**US-M1-04** 作為受邀者，登入後進該團隊。  
AC: Given 有效 token, When 身分就緒, Then OrgMember 存在。

**US-M1-05** 作為 Free，我看到方案與公開推薦剩餘。  
AC: 設定／Plan 與 `/me` 一致；用盡後步驟 3 略過。

**US-M1-06** 作為訪客，我看不到 Dev／測試進場。  
AC: Given 正式前端, When 開 `/login` 或 `/register`, Then 為密碼／Google 表單；無方案下拉、無 seed_org。

**US-M1-07** 作為 Pro，我不能開啟「允許 AI 推薦」。  
AC: Given plan≠enterprise 或非 Admin, When 嘗試 opt-in, Then 拒絕並說明需企業 Admin。

---

## 8. Roadmap

| 階段 | 內容 | 目標 |
|------|------|------|
| **Now** | Email＋密碼註冊／登入／忘記密碼＋Google；拿掉 Dev 進場；歡迎可選 | 一般用戶進得來且像正常帳號系統 |
| **Next** | 強制驗證信、企業申請、升級 CTA | 供給／變現水管 |
| **Later** | 金流、SSO、細權限 | 規模化 |

---

## 9. 技術約束（已知）
- 自幹 Auth：Email＋密碼（hash）＋Google OAuth；重設密碼可用既有寄信（Resend）；本地 User／JWT 為 API 真相。  
- Magic link **可保留作重設密碼／內部**，**不再當一般登入主路徑**。  
- Entitlement 掛 User；公開試用欄位已落地（migration 019）。  
- `ALLOW_DEV_LOGIN`／`POST /auth/dev-login`／測試切方案：**僅自動化測試與本機**，預設 `false`；**不進產品畫面**。  
- 企業升等 Now：DB／內部工具改 `plan_tier`，不經登入表單。

---

## 10. DDR（本模組鎖定）

| ID | 決策 |
|----|------|
| DDR-M1-A1 | 四層模型：Identity／Membership／Entitlement／Capability |
| DDR-M1-A2 | 一般自助註冊／登入＝P0；邀請＝入團 |
| DDR-M1-A3 | Now 認證＝**Email＋密碼＋Google**；忘記密碼＝Must；（覆寫先前「先無密碼」） |
| DDR-M1-A4 | **產品移除** Dev 登入、進場方案選擇、`seed_org` UI；測試用可留後端 |
| DDR-M1-A5 | 設定頁不提供正式「一鍵切方案」；升級走 CTA／人工 |
| DDR-M1-A6 | 企業升等 Now＝人工；不自助變企業 |
| DDR-M1-01/02 | 公開試用扣次規則維持（已鎖定） |

---

## 11. 驗收（模組完成定義）

1. 新 email＋密碼可註冊並進 App（Free）；Google 註冊／登入可用。  
2. Email＋密碼可登出再登入；忘記密碼可完成重設。  
3. 邀請流仍可用。  
4. 登入／註冊頁無 Dev／方案／seed_org。  
5. Free 試用與企業曝光閘與矩陣一致。  
6. 自動化測試可用 API／flag 模擬方案，不依賴產品 Dev UI。

---

## 12. 下一步（工程）

1. module-kickoff：M1 進場切片（對照本 PM）  
2. SA/SD 增量：password_hash、register／login／forgot-password API、拿掉前端 Dev 進場  
3. UIUX → ENG → Code  

*重審文件保留作背景；執行以本 PM L3 為準。*
