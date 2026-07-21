# BSChat SA/SD — 子團隊共享池（M7b）

> **版本**：v1.0 · 2026-07-20  
> **依據**：kickoff `subteam-pool-20260720.md` ✅、UIUX `BSChat_UIUX_subteam.md`、PRD §2.5／§4／DDR-v4-10～12  
> **階段**：SA/SD（UI 已確認）→ 下一棒 ENG  
> **明確不做**：單張名片共享、職稱系統、SaaS Platform 後台（DDR-v4-12 Next）、Free／Pro 子團隊

---

## Delta check（SA）

已檢查 PRD DDR-v4-10～12、UIUX subteam、enterprise B SA、`get_team_user_ids`（現 org-wide）、`team_invites.invite_kind`  
→ ✅ 開工 SA

---

## 1. 模組內部架構

```
┌──────────────────────────────────────────────────────────────┐
│ Client                                                        │
│ 「我的」Tab 子團隊 · /teams/[id] · /join/team/[token]         │
│ 名片庫／搜尋（可見範圍）· Admin「子團隊」Tab                     │
└────────────────────────────┬─────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────┐
│ Sub-team pool（本切片）                                         │
│ · sub_teams / sub_team_members                                  │
│ · 邀請（team_invites kind=sub_team）                            │
│ · get_visible_capturer_ids（取代 org-wide 池）                  │
└───────┬──────────────────────────────┬────────────────────────┘
        │                              │
┌───────▼────────┐            ┌────────▼─────────┐
│ Org（enterprise）│            │ contacts.user_id  │
│ OrgMember        │            │ （收錄人＝擁有者）  │
└────────────────┘            └──────────────────┘
```

| 擁有 | 不擁有 |
|------|--------|
| 子團隊 CRUD、成員、邀請、解散 | 單張 share 欄位 |
| 可見範圍解析（列表／搜尋） | 平台 SaaS 後台 |
| Admin 全公司隊列表／強制解散 | Free／Pro 組織共享 |

⚠️ **不建議 AI 化**：成員／邀請／解散。  
**MCP**：不 expose。

---

## 2. 可見性規則（核心契約）

名片**不**標記所屬子團隊（避免收錄時選隊）。

使用者 **V** 可見收錄人 **C** 的名片，當且僅當：

1. `C == V`，或  
2. 存在子團隊 `T`，使得 V∈T 且 C∈T（**共同隊籍**）

多隊主管：可見範圍＝各隊成員之**聯集**（UI chip 可再篩單隊）。

| 使用者狀態 | 可見範圍 |
|------------|----------|
| Free／Pro（非 enterprise 租戶） | 僅自己 |
| 企業成員、**未加入任何子團隊** | 僅自己 |
| 企業成員、加入 ≥1 子團隊 | 自己 ∪ 同隊成員的收錄 |

**破壞性變更**：現行 `get_team_user_ids`＝整 org 成員 → 改為上表。企業 dogfood 需先建隊並邀人，否則彼此看不到（符合產品）。

函式更名建議：`get_visible_capturer_ids(db, user_id) -> list[UUID]`（舊名可暫時包一層）。

---

## 3. 資料庫設計（增量 · migration `023_sub_teams`）

### 3.1 `sub_teams`（新）

| Column | Type | 說明 |
|--------|------|------|
| `id` | UUID PK | |
| `org_id` | UUID FK organizations ON DELETE CASCADE | 必須 `is_enterprise` |
| `name` | VARCHAR(120) NOT NULL | |
| `description` | VARCHAR(500) NULL | |
| `created_by_user_id` | UUID FK users | 建立者（初始負責人） |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

Index：`(org_id)`；可選 unique `(org_id, lower(name))` 防同名（🟢 建議加）。

### 3.2 `sub_team_members`（新）

| Column | Type | 說明 |
|--------|------|------|
| `sub_team_id` | UUID FK sub_teams CASCADE | PK 複合 |
| `user_id` | UUID FK users CASCADE | PK 複合 |
| `role` | VARCHAR(20) NOT NULL | `owner`｜`member` |
| `joined_at` | TIMESTAMPTZ | |

規則：
- 建隊時插入建立者 `role=owner`
- 一隊可有多 owner（本輪：僅建立者；轉移 owner＝Later）
- 同一 user 可屬於同 org 多個子團隊
- 加入前必須已是該 `org_id` 的 `OrgMember`（企業席次）

### 3.3 `team_invites` 增量

| Column | Type | 說明 |
|--------|------|------|
| `sub_team_id` | UUID NULL FK sub_teams ON DELETE CASCADE | `invite_kind=sub_team` 時必填 |

既有 `invite_kind`：`team`｜`enterprise_seat`｜**`sub_team`**。

---

## 4. API（REST `/api/v1`）

權限：除非註明，皆需登入且 `org.is_enterprise` + 呼叫者為該 org 成員。

| Method | Path | 說明 |
|--------|------|------|
| `GET` | `/sub-teams` | 我加入的子團隊列表 |
| `POST` | `/sub-teams` | body: `{ name, description? }` → 建隊＋自己 owner |
| `GET` | `/sub-teams/{id}` | 詳情＋成員（須為隊員或主 Admin） |
| `POST` | `/sub-teams/{id}/invites` | 建邀請連結（隊員即可；owner／Admin 可） |
| `POST` | `/join/sub-team/{token}` | 接受邀請（須已是企業成員） |
| `DELETE` | `/sub-teams/{id}/members/{user_id}` | owner 或主 Admin 移除；不可移最後一位 owner（本輪僅一 owner 則解散另走） |
| `POST` | `/sub-teams/{id}/leave` | 自己離開；owner 離開前須先解散或 Later 轉移 |
| `DELETE` | `/sub-teams/{id}` | 解散：owner **或** 主 Admin；刪 members＋invites；名片保留 |
| `GET` | `/orgs/{org_id}/sub-teams` | **主 Admin**：全公司隊列表 |

錯誤：`403` 非企業／非成員；`404`；邀請過期／撤銷同既有 invite。

`GET /me` 可擴：`sub_teams: [{ id, name, role }]`（方便前端 Tab）。

---

## 5. 與既有模組接點

| 模組 | 改動 |
|------|------|
| `app/core/team.py` | 實作 `get_visible_capturer_ids`；列表／搜尋改呼叫 |
| M3 contacts list/detail | 回傳可選 `sub_team_names`（收錄人與自己的共同隊，或收錄人所屬隊∩我的隊） |
| M5 retrieval | `_private_*` 的 user_ids 改新 helper |
| PrivacyStrip／搜尋文案 | 「子團隊庫」 |
| Settings UI | 三分頁；子團隊僅 enterprise |
| Admin `/admin/org` | Tab 子團隊 |
| 舊 `invite_kind=team` | 非企業路徑可保留但不擴可見池（Free／Pro 仍個人庫） |

---

## 6. 決策紀錄（本模組）

| ID | 決策 | Tier |
|----|------|------|
| DDR-ST-1 | 可見性＝**共同隊籍**，名片不寫 `sub_team_id` | 🟢 |
| DDR-ST-2 | 子團隊表獨立；邀請沿用 `team_invites` + `sub_team_id` | 🟢 |
| DDR-ST-3 | 企業成員皆可建；主 Admin 可解散任何隊 | 已拍板 DDR-v4-10 |
| DDR-ST-4 | 非企業＝個人庫（不再 org-wide） | 已拍板 DDR-v4-11 |
| DDR-ST-5 | owner 離開須先解散（本輪不轉移 owner） | 🟢 可 Later 放寬 |

**🟡 曾考慮**：收錄時指定「進哪一隊」——否決（摩擦高；共同隊籍已夠）。

---

## 7. 測試要點（給 ENG／QA）

1. 同隊互見；跨隊不可見  
2. 雙隊主管見聯集  
3. 未入隊企業成員＝僅自己  
4. Free／Pro＝僅自己（即使有舊 org_members）  
5. 解散後原隊員互不可見；名片仍在收錄人名下  
6. 非 org 成員無法靠邀請進子團隊（先企業席次）  
7. 主 Admin 可解散自己不是隊員的隊  

---

## 8. 完成標準

- [x] SA/SD 本文  
- [ ] ENG：migration 023 + API + `get_visible_capturer_ids` + FE 分頁／隊 UI  
- [ ] QA：上列用例  

下一棒：**ENG**（可先後端契約＋migration，再前端）。
