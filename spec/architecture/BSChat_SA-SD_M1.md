# BSChat SA/SD — Module 1：帳號／訂閱（公開推薦終身試用切片）

> **版本**：v1.0（**已鎖定 2026-07-14**）· **進場切片見 [`BSChat_SA-SD_M1_access.md`](./BSChat_SA-SD_M1_access.md)（v1.1）**  
> **日期**：2026-07-14  
> **依據**：kickoff `spec/kickoffs/m1-public-trial-20260714.md`、PRD v4 §4／§6 Next／US-v4-5／DDR-v4-3、wedge §10  
> **範圍**：僅 **Free 公開推薦終身 2 次** entitlement；不重做 auth／收款  
> **進場（密碼註冊）**：另檔 SA/SD／UIUX／ENG `*_M1_access` — **不改本檔扣次語意**

---

## 1. 模組內部架構

```
┌──────────────────────────────────────────────────────────────┐
│  Client                                                       │
│  · GET /me → 顯示試用剩餘                                     │
│  · SearchPlanPanel：依 can_use_public_recommend 決定步驟 3    │
└────────────────────────────┬─────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────┐
│  M1 Entitlement（本切片擁有）                                  │
│  · public_recommend_* 欄位                                    │
│  · can_use_public_recommend(ent)                              │
│  · remaining_public_recommend(ent) → int | null(-1=無限)      │
│  · consume_public_recommend(db, ent)  ※僅 Free 且實際查池時   │
└────────────────────────────┬─────────────────────────────────┘
                             │ 被呼叫
┌────────────────────────────▼─────────────────────────────────┐
│  M5 / M5b Search                                              │
│  · 決定 include_public 前問 M1                                │
│  · 空池／無權限 → 略過步驟 3、不扣次（見 DDR-M1-02）           │
│  · 舊 can_use_network_scope(plan_tier) → 改走 M1 API          │
└──────────────────────────────────────────────────────────────┘
```

**邊界契約**

| 擁有（M1） | 不擁有 |
|-----------|--------|
| 終身試用額度欄位、扣次、剩餘計算、`/me` 暴露 | 公開池索引／電子名片（M11） |
| `can_use`／`consume` 純函式給 M5 呼叫 | Plan UI 動畫（M5 前端） |
| 方案切換時**不重置**已用次數 | 真實收款／Stripe（Later） |

**⚠️ 不建議 AI 化**：額度判斷、扣次、方案閘門 — 確定性／可審計／安全。

**MCP**：不 expose（內部 plumbing）。

---

## 2. 資料庫設計（本切片增量）

**Table：`user_entitlements`（既有 · 增量欄位）**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `public_recommend_lifetime_quota` | INT | NOT NULL, DEFAULT **2** | Free 終身上限；Pro／Enterprise 寫入後**忽略**（視為無限） |
| `public_recommend_used_lifetime` | INT | NOT NULL, DEFAULT **0** | 終身已用次數；**永不月重置**；升降級**不清零** |

不加 `reset_at`（對齊 DDR-v4-3「不月重置」）。

**Migration**：Alembic 增量；既有 Free 列 `used=0, quota=2`；Pro／Enterprise 列同樣寫入欄位但 runtime 不扣。

**Indexes**：無額外需求（PK = `user_id`）。

---

## 3. 運行時規則（核心）

### 3.1 `can_use_public_recommend(ent) → bool`

| `plan_tier` | 規則 |
|-------------|------|
| `pro` / `enterprise` | 永遠 `true` |
| `free` | `used_lifetime < lifetime_quota` |
| 其他 | `false` |

取代現有 `can_use_network_scope(plan_tier)`（僅看 tier）。

### 3.2 `remaining_public_recommend(ent) → int`

| tier | 回傳 |
|------|------|
| pro / enterprise | `-1`（無限，與既有 manual_refresh 慣例一致） |
| free | `max(0, quota - used)` |

### 3.3 扣次時機（與 M5 契約）

```
POST /search/queries（欲含公開池）
  1. 若 !can_use → include_public=false；Plan 步驟 3 = skipped；不扣
  2. 若 public_pool_count == 0 → include_public=false；步驟 3 = skipped（誠實「池空」）；不扣  【DDR-M1-02】
  3. 否則（將實際跑公開檢索）→ consume_public_recommend（Free +1）；失敗則 429
  4. 跑 Pool A ± Pool B；結果分區照舊
```

**一「次」定義（DDR-M1-01）**：一次成功進入步驟 3 的搜尋請求（`include_public=true` 且已 consume），**不論**公開結果筆數是否 > 0。  
（空池在步驟 2 已擋下，不會進此定義。）

### 3.4 升降級

| 事件 | 行為 |
|------|------|
| Free → Pro／Enterprise | `used` **保留**（稽核）；之後不扣、`remaining=-1` |
| Pro／Enterprise → Free | `used` **保留**；若已 ≥ quota → 不可再用公開池 |
| `POST /me/plan` 套用 preset | **不得**把 `used` 歸零 |

### 3.5 錯誤碼

| 情境 | HTTP | `detail` |
|------|------|----------|
| Free 試用已用完仍要求 network／all | 403 | `PUBLIC_RECOMMEND_TRIAL_EXHAUSTED` |
| （可選）並發超扣 | 429 | `PUBLIC_RECOMMEND_QUOTA_EXCEEDED` |

前端：403 → Plan 步驟 3 略過 + 升級 CTA（文案屬 UI/UX）。

---

## 4. API 規格（增量）

**Base**：`/api/v1` · Bearer JWT

### 4.1 `GET /me`（擴充 `quotas`）

```json
{
  "quotas": {
    "search_cache_remaining_today": 28,
    "live_augment_remaining_month": 5,
    "manual_refresh_remaining_month": 3,
    "person_linkedin_remaining_month": 0,
    "public_recommend_remaining_lifetime": 2,
    "public_recommend_unlimited": false
  }
}
```

| 欄位 | 語意 |
|------|------|
| `public_recommend_remaining_lifetime` | Free：剩餘整數；Pro／Ent：可回 `0` 或省略，以 `unlimited` 為準 |
| `public_recommend_unlimited` | `plan_tier in {pro,enterprise}` → `true` |

### 4.2 `GET /search/status`（建議擴充 · M5 消費面）

```json
{
  "can_use_public_recommend": true,
  "public_recommend_remaining_lifetime": 2,
  "public_recommend_unlimited": false,
  "public_pool_count": 12
}
```

供 Plan UI 在搜尋前決定步驟 3（不必每次只靠 `plan_tier === pro`）。

### 4.3 Search scope 閘門（M5 呼叫 M1）

| 請求 `search_scope` | Free 有剩餘 | Free 用完 | Pro／Ent |
|---------------------|------------|----------|----------|
| `private` | ✅ | ✅ | ✅ |
| `network` / `all` | ✅ 且扣 1（若池非空） | 403 | ✅ 不扣 |

---

## 5. 內部資料流程

**Flow A — Free 首次含公開搜尋（池有資料）**

1. Client：`search_scope=all`（或前端預設）  
2. M5：`can_use` → true；`public_pool_count>0`  
3. M1：`used += 1`（flush）  
4. M5：檢索私有 + 公開 → 分區結果  
5. `/me` 剩餘變 1；Plan 步驟 3 = done  

**Flow B — Free 試用用完**

1. `can_use` → false  
2. 強制僅私有（或 403 若 client 硬要 network）  
3. Plan 步驟 3 = skipped「試用已用完」  
4. 不扣次  

**Flow C — 公開池空**

1. `can_use` 可為 true  
2. `public_pool_count==0` → 不扣、步驟 3 skipped「目前無公開身份」  
3. 只回庫內結果  

---

## 6. 對下游的契約變更摘要

| 消費者 | 變更 |
|--------|------|
| M5 `public_search.can_use_network_scope` | Deprecated → 改呼叫 M1 `can_use_public_recommend` |
| M5 Plan UI | `includePublicPool` 改依 `/me` 或 `/search/status`，**不是**單純 `isPro` |
| M5b | 同閘門；門檻對齊本文件後再 re-kickoff 實作細節 |
| M11 | 無直接依賴；池空行為見 Flow C |

---

## 7. 決策紀錄（本切片）

| ID | 決策 | Tier | 狀態 |
|----|------|------|------|
| DDR-M1-01 | 一「次」＝實際執行公開池檢索即扣 1（即使 0 命中） | 🟢 | **已鎖定＝A** |
| DDR-M1-02 | 公開池為空時不扣次、步驟 3 略過並誠實說明 | 🟢 | **已鎖定＝A** |
| DDR-M1-03 | 欄位放 `user_entitlements`；無月重置欄 | 🟢 | 鎖定（對齊 PRD） |
| DDR-M1-04 | Pro／Enterprise 無限、不遞增 used；升降級不清 used | 🟢 | 鎖定（對齊 PRD／稽核） |
| DDR-M1-05 | 額度閘門傳統 code，禁止 LLM | 🟢 | 鎖定 |

---

## 8. 正向追溯

| 產出 | PRD |
|------|-----|
| 終身 2 次、不月重置 | §4、DDR-v4-3、US-v4-5 |
| Plan 步驟 3 可略過 | §5 |
| 不暗示搜私人抽屜 | §3 |
| Next P0 計數 | §6 |

---

## 9. 完成標準（本階段）

- [x] Schema／API／扣次時機／升降級寫清  
- [x] 用戶確認 DDR-M1-01、DDR-M1-02（皆 A）  
- [x] SA/SD 鎖定 → 進 UI/UX  

