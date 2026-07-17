# BSChat SA/SD — 企業租戶完整 B（M1 × M11）

> **版本**：v1.0  
> **日期**：2026-07-16  
> **依據**：kickoff `enterprise-tenant-b-20260716.md` ✅、PRD v4 §6.6／DDR-v4-9、`BSChat_enterprise_tenant_model_B.md`  
> **範圍**：申請／核准、唯一主 Admin、企業席次邀請、B1 升降、成員移除／轉移、成員名片草稿＋Admin 發布  
> **暫緩**：次 Admin、SSO、Stripe、網域强制（可留欄位預留）

---

## 1. 模組內部架構

```
┌─────────────────────────────────────────────────────────────┐
│ Client                                                       │
│ /enterprise/apply · /join/enterprise/[token]                 │
│ /admin/org（成員／邀請／名片／轉移）· 「我的」捷徑              │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│ Enterprise Tenant（本切片）                                   │
│ · applications 申請                                           │
│ · provision／approve（營運）                                   │
│ · enterprise_seat invites                                     │
│ · primary admin · transfer · remove member（B1 降級）         │
└───────┬───────────────────────────────┬─────────────────────┘
        │                               │
┌───────▼────────┐              ┌───────▼────────┐
│ Org / OrgMember │              │ M11 電子名片     │
│ + is_enterprise │              │ 成員 draft      │
│ + primary_admin │              │ Admin publish   │
└────────────────┘              └────────────────┘
```

| 擁有 | 不擁有 |
|------|--------|
| 租戶 enterprise 標記、申請、開通、席次邀請、B1 升／降 | 正式金流 |
| 主 Admin 轉移、成員名單 | SSO／次 Admin |
| 邀請 kind 與權限閘 | 一般 Free 註冊（已有） |

⚠️ **不建議 AI 化**：開通、升降方案、邀請核銷、移除下架。  
**MCP**：不 expose。

---

## 2. 資料庫設計（增量）

### 2.1 `organizations`

| Column | Type | 說明 |
|--------|------|------|
| `is_enterprise` | BOOLEAN NOT NULL DEFAULT false | 企業租戶標記 |
| `primary_admin_user_id` | UUID NULL FK users | 唯一主 Admin；enterprise 時 NOT NULL（應用層保證） |
| `seat_limit` | INT NULL | 可空＝不限（dogfood）；Next 座位用 |
| `approved_at` | TIMESTAMPTZ NULL | 開通時間 |

既有 `name`／`slug` 保留。  
**規則**：`is_enterprise=true` 時必須有 `primary_admin_user_id`，且該 user 在 `org_members` 且 `role=admin`。

### 2.2 `enterprise_applications`（新表）

| Column | Type | 說明 |
|--------|------|------|
| `id` | UUID PK | |
| `applicant_user_id` | UUID FK users | 申請人（須已註冊） |
| `company_name` | VARCHAR(255) | |
| `slug_requested` | VARCHAR(100) | 可空；核准時可改 |
| `contact_email` | VARCHAR(255) | |
| `estimated_seats` | INT NULL | |
| `note` | TEXT NULL | |
| `status` | VARCHAR(20) | `pending`｜`approved`｜`rejected` |
| `reviewed_at` | TIMESTAMPTZ NULL | |
| `reviewed_by` | VARCHAR(128) NULL | 營運識別（email／ops id） |
| `resulting_org_id` | UUID NULL FK orgs | 核准後填入 |
| `created_at` | TIMESTAMPTZ | |

### 2.3 `team_invites` 增量

| Column | Type | 說明 |
|--------|------|------|
| `invite_kind` | VARCHAR(32) NOT NULL DEFAULT `team` | `team`｜`enterprise_seat` |
| `invited_email` | VARCHAR(255) NULL | 企業邀請可綁定單一 email（建議必填於 enterprise） |

- `enterprise_seat`：僅 `is_enterprise` org 的 **primary admin** 可建立。  
- 接受 `enterprise_seat` 時執行 B1 升級（§3）。  
- 舊列 migration 預設 `invite_kind=team`（協作／舊行為）。

### 2.4 `org_members` 增量（可選但建議）

| Column | Type | 說明 |
|--------|------|------|
| `plan_before_enterprise` | VARCHAR(10) NULL | 加入企業前方案；移除時還原（無則降 `free`） |

### 2.5 Migration

建議 `022_enterprise_tenant_b.py`。

---

## 3. 運行時規則

### 3.1 B1 升降

| 事件 | 行為 |
|------|------|
| 接受 `enterprise_seat` 邀請 | 記 `plan_before_enterprise`（若空）→ `apply_plan_preset(enterprise)` → `OrgMember(role=member)`（主 Admin 除外） |
| 主 Admin 開通當下 | 申請人／指定人：`role=admin`＋`primary_admin_user_id`＋enterprise preset |
| 移除成員 | 刪 OrgMember → 還原 `plan_before` 或 `free` → 該 user 在此 org 的 stubs **全部 unpublish／離池** |
| 轉移主 Admin | 舊 admin → `member`；新 → `admin`＋更新 `primary_admin_user_id`；兩者皆須已在租戶內 |
| 非 enterprise 的 `POST /teams` | 仍可建 **非企業** org（`is_enterprise=false`）；**不得**因此得到 enterprise 方案 |

### 3.2 誰能做什麼

| 動作 | 條件 |
|------|------|
| 提交申請 | 已登入 |
| 核准／開通 | `ENTERPRISE_OPS_TOKEN` 或 `ALLOW_DEV_LOGIN`（dogfood）；正式可換內部工具 |
| 發 enterprise 邀請 | `org.is_enterprise` 且 `user.id == primary_admin_user_id` |
| 發 team 邀請 | 既有：org member（可收斂為僅非企業 org；企業 org **只允許** enterprise_seat） |
| M11 publish／允許 AI 推薦 | enterprise＋**primary admin**（收緊：僅主 Admin，非任一 role=admin） |
| 建 stub draft | 企業成員可為「自己的」名片建 draft；或 Admin 代建（ENG 定：MVP 允許成員 create draft，publish 僅 Admin） |

### 3.3 Dogfood 開通（無申請也可）

`POST /api/v1/ops/enterprise/provision`：

```json
{
  "company_name": "Acme",
  "slug": "acme",
  "admin_email": "you@company.com",
  "seat_limit": null
}
```

行為：若 admin 用戶不存在 → 404（須先註冊）；建／標記 org enterprise；設 primary admin；升級方案。  
Auth：Header `X-Ops-Token: $ENTERPRISE_OPS_TOKEN`（或 dev 時 ALLOW_DEV_LOGIN）。

---

## 4. API 規格

**Base** `/api/v1`

### 4.1 申請

| Method | Path | Auth | 說明 |
|--------|------|------|------|
| POST | `/enterprise/applications` | User | 建 pending |
| GET | `/enterprise/applications/mine` | User | 自己的申請列表 |

### 4.2 營運

| Method | Path | Auth | 說明 |
|--------|------|------|------|
| POST | `/ops/enterprise/applications/{id}/approve` | Ops | 核准→provision |
| POST | `/ops/enterprise/applications/{id}/reject` | Ops | 拒絕 |
| POST | `/ops/enterprise/provision` | Ops | 直接開通（dogfood） |

### 4.3 企業 Admin

| Method | Path | Auth | 說明 |
|--------|------|------|------|
| GET | `/enterprise/orgs/{org_id}` | Primary admin | 租戶摘要＋座位 |
| GET | `/enterprise/orgs/{org_id}/members` | Primary admin | 名單 |
| DELETE | `/enterprise/orgs/{org_id}/members/{user_id}` | Primary admin | 移除（不可移自己除非已轉移） |
| POST | `/enterprise/orgs/{org_id}/transfer-admin` | Primary admin | `{ "new_admin_user_id" }` |
| POST | `/enterprise/orgs/{org_id}/invites` | Primary admin | body: email, expires_days；kind 固定 enterprise_seat；落庫後以 Resend 寄信，回 `email_sent` |
| POST | `/enterprise/invites/{id}/revoke` | Primary admin | 撤銷 |

### 4.4 接受邀請

| Method | Path | 說明 |
|--------|------|------|
| GET | `/enterprise/invites/{token}` | 預覽（公司名、是否 enterprise） |
| POST | `/enterprise/invites/{token}/accept` | 須登入；B1 入租戶 |

前端路由：`/join/enterprise/[token]`（與 `/join/[token]` 舊團隊邀請並存；舊的僅非企業或標記 team）。

**寄信失敗策略**：邀請先 commit，再寄送 Email；未設定 Resend 或寄送失敗時，
API 仍回可用的 `join_path` 與 `email_sent=false`，Admin 可複製連結，不讓外部郵件服務回滾席次邀請。

### 4.5 `/me` 增量

```json
{
  "enterprise_admin_of": [{ "org_id": "…", "org_name": "…" }],
  "enterprise_member_of": [{ "org_id": "…", "org_name": "…", "role": "member" }]
}
```

（可由既有 `org_memberships` + org.is_enterprise 推導，不一定新欄。）

### 4.6 錯誤碼

| detail | 何時 |
|--------|------|
| `ENTERPRISE_REQUIRED` | 非企業操作企業 API |
| `NOT_PRIMARY_ADMIN` | 非主 Admin |
| `CANNOT_REMOVE_PRIMARY_ADMIN` | 未轉移就移自己 |
| `SEAT_LIMIT_REACHED` | 超座位 |
| `INVITE_EMAIL_MISMATCH` | 邀請綁 email 與登入不符 |
| `OPS_UNAUTHORIZED` | ops token 錯 |

---

## 5. 內部資料流

**Flow P — Dogfood 開本公司**  
Admin 先密碼註冊 → ops provision(slug, admin_email) → 主 Admin 發邀請 → 業務註冊／登入 → accept → enterprise。

**Flow A — 申請**  
登入用戶 submit → pending → ops approve → 同 provision（申請人為 Admin）。

**Flow R — 移除**  
Admin remove → B1 降級 → unpublish 其 stubs。

**Flow T — 轉移**  
Admin transfer → roles 對調 → primary_admin_user_id 更新。

---

## 6. 決策紀錄

| ID | 決策 | 狀態 |
|----|------|------|
| DDR-ENT-01 | `is_enterprise`＋`primary_admin_user_id` 在 organizations | 鎖定 |
| DDR-ENT-02 | 邀請 `invite_kind`；企業僅 primary 可發 `enterprise_seat` | 鎖定 |
| DDR-ENT-03 | B1：接受企業邀請升 enterprise；移除還原／free | 鎖定 |
| DDR-ENT-04 | M11 publish 僅 primary admin | 鎖定（收緊） |
| DDR-ENT-05 | 成員可 draft stub；publish 僅 Admin | 鎖定 |
| DDR-ENT-06 | Ops provision 用 token；無審核自助開企業禁止 | 鎖定 |
| DDR-ENT-07 | 企業 org 不再使用舊「任意 member 發 team 邀請」當席次入口 | 鎖定 |

---

## 7. 正向追溯

| 產出 | PRD／US |
|------|---------|
| 申請／核准／主 Admin／邀請 | §6.6、US-v4-4b |
| B1 | DDR-v4-9、model B |
| 草稿＋Admin AI 推薦 | US-v4-4、model B §10 |
| Dogfood provision | US-v4-4c |

---

## 8. 完成標準（本階段）

- [x] Schema／API／B1／Dogfood 開通寫清  
- [x] DDR-ENT-01～07 鎖定  
- [ ] → UI/UX → ENG → Code  
