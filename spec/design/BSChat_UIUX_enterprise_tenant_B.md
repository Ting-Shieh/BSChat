# BSChat UI/UX — 企業租戶完整 B

> **版本**：v1.0 · 2026-07-16  
> **依據**：`BSChat_SA-SD_enterprise_tenant_B.md`、model B、Design Foundation  
> **UI 庫**：shadcn（不新選）

---

## Delta check（UI/UX）

已檢查 PRD §6.6、SA-SD enterprise B、M1 進場靜態 screen-5／6、既有 OrgAdminPage  
→ ✅ 開工

---

## 1. 流程與畫面

| 路由 | 誰 | 內容 |
|------|----|------|
| `/enterprise/apply` | 已登入 | 公司名、聯絡 Email、預估人數、備註；送出後「審核中」 |
| `/join/enterprise/[token]` | 訪客／用戶 | 預覽公司名「企業成員邀請」；CTA 註冊／登入並加入（帶 token） |
| `/admin/org` 擴充 | 主 Admin | Tab：電子名片｜成員｜邀請｜設定（轉移 Admin） |
| `/settings`（我的） | 全角色 | 申請企業 CTA；若為 Admin →「企業後台」；若為成員 → 顯示公司名 |

**禁止**：一般註冊頁出現「註冊企業版」自助成功；Dev 切 enterprise。

---

## 2. Admin 後台（成員／邀請）

**成員表**：姓名、Email、角色（主 Admin／成員）、加入日、操作「移除」（主 Admin 列不可移，提示先轉移）。

**邀請**：Email（必填）＋有效天數 → 建立後由 Resend 寄出邀請信；介面顯示
「邀請信已寄出」。未設定或寄送失敗時顯示 fallback，並永遠保留可複製連結；
列表顯示待接受／已撤銷。信件視覺預覽：`screens/enterprise-invite-email.html`。

**轉移**：下拉選現有成員 → 確認對話「你將失去主 Admin」。

**電子名片**：沿用既有；文案「允許 AI 推薦」；成員若可進後台僅見自己的 draft（MVP：成員不進 Admin，只在「我的」或簡易頁編草稿——ENG 可定成員用 `/admin/org` 只讀名片自己的）。

**MVP 簡化（建議）**：僅主 Admin 使用 `/admin/org`；成員草稿 API 先由 Admin 代建，或成員在「我的」有「我的電子名片草稿」單頁。優先：**Admin 代建＋允許 AI 推薦** 不擋業務測；成員自助草稿列 Should。

---

## 3. 文案

| 位置 | 文案 |
|------|------|
| 企業邀請頁標題 | 加入 {公司}（企業） |
| 與舊 join 差異 | 舊：「加入團隊」；新：「加入企業租戶」 |
| 申請成功 | 已送出，核准後你會成為主 Admin |
| 移除確認 | 對方將失去企業能力，其公開名片會下架 |

---

## 4. 靜態原型

本輪以 SA 為準；可另補 `screen-7-enterprise-admin.html`（成員／邀請）——ENG 前可做。

---

## 5. 完成標準
- [x] 路由與 Admin 資訊架構清楚  
- [ ] → ENG  
