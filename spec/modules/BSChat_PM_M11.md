# BSChat PM L3 — Module 11：企業公開商務目錄（Publisher → Pool B）

> **版本**：v1.0  
> **狀態**：PM L3 ✅ 可鎖定（對齊 kickoff 2026-06-16 + SA-SD M11 v1.0）  
> **依據**：PRD §11.3 E/F、§11.5 Stage 2、§13.1~13.2、DDR-58~62、DDR-75~80、DDR-90~95

---

## 模組定位

> **企業版 = 寫 Pool B；Pro = 讀 Pool B**（DDR-76）。  
> M11 讓 Enterprise Admin 發布「薄商務身份 stub」，使 Pro 使用者能在 AI 搜尋中找到**平台公開商務窗口**（非他人私人名片庫）。

**不做（MVP）**：完整電子名片宿主、真實計費、SSO/HR、品牌模板設計器、個人自願發布 Pool B。

---

## L3.1 — Sub-features（M11 MVP）

| # | Sub-feature | 優先 | 說明 |
|---|-------------|------|------|
| F-11.1 | Organization + Admin 成員 | **P0** | `organizations` / `org_members` |
| F-11.2 | 公開 stub CRUD | **P0** | 姓名、公司、職稱、職責/產品關鍵字、**外部 URL 必填** |
| F-11.3 | 發布 / 下架 | **P0** | draft → published → unpublished |
| F-11.4 | Pool B 索引 | **P0** | `public_directory_documents` |
| F-11.5 | CSV 批量匯入 | **P0** | DDR-79 最小 |
| F-11.6 | Enterprise Admin UI | **P0** | `(admin)/org/*` |
| F-11.7 | Dev seed org + stubs | **P0** | 供 M5b 联测 |
| F-11.8 | 用量報表（被搜次數） | P2 | Enterprise Phase 2 |
| F-11.9 | 員工個人同意 flow | P2 | US-11.2 完整版；MVP Admin 發布即 org 授權 |
| F-11.10 | M6 自動 enrich stub 關鍵字 | P2 | MVP 手填 |

---

## L3.2 — User Stories

### US-11.1 企業 Admin 建立並發布公開 stub

> As a **企業 Admin**, I want to 在 BSChat 建立並發布員工公開商務身份, so that 平台 Pro 用戶能以自然語言找到我們的窗口。

**Acceptance Criteria**

- Given enterprise Admin 已登入且具 org 權限, When 新增 stub 並填寫必填欄位 + 有效 `external_card_url`, Then stub 為 `draft` 且可預覽
- When Admin 按「發布」, Then `status=published` 且 Pool B 索引在合理時間內可搜（integration：index worker 完成）
- When Admin 按「下架」, Then 24h 內 Pro 跨池搜尋**不得**再命中該 stub（R-P3-3）
- Stub **不得**含電話/Email 欄位供 Pro 結果展示（DDR-80 / DDR-93）

### US-11.2 員工曝光範圍（MVP 簡化版）

> As a **企業**, I want to 控制哪些身份出現在公開商務池, so that 離職或不宜曝光者不會被搜到。

**MVP 簡化（DDR-77/78）**

- Seat 預設由 Admin **主動發布**才進 Pool B（非自動從私人 contact 同步）
- 離職/不公開 = Admin **手動下架**（不宣稱 HR 自動同步）

**Stage 2+（完整 US-11.2）**

- 員工本人二次確認同意（opt-in UI）— **非 M11 MVP**

### US-11.3 CSV 批量匯入

> As a **企業 Admin**, I want to 從 CSV 批量建立 stub, so that 不必逐筆 key-in。

- Given 合法 CSV（6 欄 header）, When 上傳, Then 回傳 imported/skipped/errors 逐列
- 非法 URL 列 skipped 且不寫 DB
- 預設匯入為 `draft`；可選 `auto_publish=true`（需二次確認 UI）

---

## L3.3 — 與 Pro / M5b 的產品邊界

| 方案 | Pool A（自己庫） | Pool B（公開 stub） | 管理 stub |
|------|:----------------:|:-------------------:|:---------:|
| Free | ✅ 搜 | ❌ | ❌ |
| Pro | ✅ 搜 | ✅ 搜（**M5b**） | ❌ |
| Enterprise | ✅ 搜 | ✅ 搜 | ✅ **發布/下架** |

**敘事決策（DDR-91 · kickoff DDR-K11-02）**  
**敘事**：Pro 內建「搜公開商務池」；企業版負責發布與管理（DDR-76、DDR-91）。

---

## L3.4 — 規則摘要

| ID | 規則 |
|----|------|
| R-11.1 | 私人 `contacts` **永不**進 Pool B（DDR-59） |
| R-11.2 | Stub 與 Contact **分表**（R-P3-2） |
| R-11.3 | `external_card_url` 必填且 http(s) |
| R-11.4 | Pro 結果：摘要 + 「公開商務 · {公司}」+ **前往外部名片**；無電話/Email（DDR-80） |
| R-11.5 | 下架後 24h 內 index 移除（R-P3-3） |

---

## L3.5 — 模組耦合

| 模組 | 關係 |
|------|------|
| **M1** | `plan_tier=enterprise` gate；`/me` 回 org_memberships |
| **M5b** | 讀 Pool B index；`search_scope` + `source_pool` |
| **M7** | 隱私紅線 QA |
| **M6** | （P2）可選 enrich product_keywords |

---

## L3.6 — MVP 驗收清單

- [ ] Admin 發布 ≥3 stub → index 有資料
- [ ] CSV 匯入 smoke
- [ ] Unpublish → 24h 內不可搜
- [ ] Free 不能 `search_scope=network`（M5b 联测项）
- [ ] Pro 結果無 PII 電話/Email

---

### 🤝 Handoff: PM → ENG — Module 11

**ENG 必須交付**（見 `BSChat_SA-SD_M11.md`）：

1. Migration `011_m11_public_directory`
2. Admin API + auth dependency `require_org_admin`
3. Index/unindex workers
4. Admin UI 最小路由
5. Dev seed + 文件更新 `module-register.md`

**下一棒**：M5b kickoff（M11 index 就緒後）

---

*PM M11 L3 v1.0 — Stage 2a · 2026-06-16*
