# BSChat SA/SD — Module 11：企業公開商務目錄（Publisher → Pool B）

> **版本**：v1.0  
> **日期**：2026-06-16  
> **依據**：kickoff `spec/kickoffs/m11-20260616.md`、PRD §11.3 E/F、§11.5 Stage 2、§13.1~13.2、DDR-58~62、DDR-75~80、DDR-K11-01~03  
> **架構模式**：Modular Monolith（FastAPI + PostgreSQL + Celery/in-process workers，對齊 TECH_STACK LOCKED）

---

## 1. 架構概覽

```
┌─────────────────────────────────────────────────────────────────┐
│  Enterprise Admin UI  (frontend/(admin)/org/*)                   │
│  · stub 列表 / 新增 / 編輯 / 發布 / 下架 / CSV 匯入              │
└────────────────────────────┬────────────────────────────────────┘
                             │ Bearer JWT + org_admin
┌────────────────────────────▼────────────────────────────────────┐
│  M11 Admin API  /api/v1/orgs/{org_id}/…                          │
│  · CRUD public_business_stubs                                    │
│  · publish / unpublish → index worker                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐   ┌─────────────────┐   ┌──────────────────┐
│ organizations │   │ public_business │   │ org_members      │
│ org_members   │   │ _stubs          │   │ (M1 gate)        │
└───────────────┘   └────────┬────────┘   └──────────────────┘
                             │ publish
                             ▼
                  ┌──────────────────────────┐
                  │ public_directory_        │
                  │ documents (Pool B index) │
                  │ tsvector + pg_trgm       │
                  └────────────┬─────────────┘
                               │ read (Pro+)
                               ▼
                  ┌──────────────────────────┐
                  │ M5b 跨池搜尋（Stage 2b）  │
                  │ source_pool=public_      │
                  │ directory                  │
                  └──────────────────────────┘

Pool A (M3 contacts + contact_search_documents) ──×── 永不寫入 Pool B
```

**M11 MVP 邊界**：只負責 **寫 Pool B**；**不**實作 M5b 跨池检索（下游模組）。

---

## 2. L4 Depth Gate

### 2.1 Data Flow

```
[Enterprise Admin 登入 · plan_tier=enterprise · org_role=admin]
        │
        ▼
[POST /orgs/{id}/stubs]  draft stub（external_card_url 必填）
        │
        ▼
[POST …/publish]
        ├─ status → published
        ├─ Enqueue PublicDirectoryIndexJob(stub_id)
        └─ (optional) emit PublicStubPublished
                │
                ▼
[Index Worker — 對稱 M3 index_contact]
        build search_text = name | company | title | keywords
        UPSERT public_directory_documents
        SET search_vector = to_tsvector('simple', search_text)
                │
                ▼
[M5b 讀取]  Pro/Enterprise user · search_scope=network|all

[POST …/unpublish]
        ├─ status → unpublished
        ├─ Enqueue PublicDirectoryUnindexJob(stub_id)
        └─ DELETE or tombstone index row（24h SLA · R-P3-3）
```

### 2.2 與 M3 Contact 隔離（DDR-59 · R-P3-1）

| | Pool A (`contacts`) | Pool B (`public_business_stubs`) |
|--|---------------------|----------------------------------|
| 建立者 | 個人 user 收錄 | 企業 Admin |
| 可被他人搜尋 | ❌ 永不 | ✅ 發布後 Pro+ 可搜 |
| 表 | `contacts` | `public_business_stubs` |
| 索引 | `contact_search_documents` | `public_directory_documents` |
| 電話/Email | 有（私人） | **MVP 無**（DDR-80） |

**禁止**：從 `contacts` 複製列到 stub；從 M2 匯入他人名片進 Pool B。

### 2.3 M1 職責切分（DDR-90）

| 層 | Owner | 內容 |
|----|-------|------|
| `plan_tier` / quota preset | **M1** | `enterprise` preset 已存在 |
| `organizations` / `org_members` / stub | **M11** | 本模組 schema |
| Admin 授權 | **M1 + M11** | JWT + `org_members.role=admin` + `plan_tier=enterprise` |

`GET /me` 擴充（M1 實作、M11 消費）：

```json
{
  "plan_tier": "enterprise",
  "org_memberships": [
    { "org_id": "uuid", "org_name": "Acme Corp", "role": "admin" }
  ]
}
```

---

## 3. 資料模型

### 3.1 `organizations`

```sql
CREATE TABLE organizations (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            VARCHAR(255) NOT NULL,
  slug            VARCHAR(100) NOT NULL UNIQUE,  -- URL / dev seed
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.2 `org_members`

```sql
CREATE TABLE org_members (
  org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role            VARCHAR(20) NOT NULL DEFAULT 'admin',  -- MVP: admin only
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (org_id, user_id)
);
CREATE INDEX idx_org_members_user ON org_members(user_id);
```

### 3.3 `public_business_stubs`

```sql
CREATE TABLE public_business_stubs (
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id                  UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  display_name            VARCHAR(255) NOT NULL,
  company_name            VARCHAR(255) NOT NULL,
  title                   VARCHAR(255),
  responsibility_keywords JSONB NOT NULL DEFAULT '[]',   -- 職責關鍵字
  product_keywords        JSONB NOT NULL DEFAULT '[]',   -- 產品/服務關鍵字（可手填）
  external_card_url       TEXT NOT NULL,                 -- 必填 · HiBox/LinkedIn/官網
  status                  VARCHAR(20) NOT NULL DEFAULT 'draft',
    -- draft | published | unpublished
  published_at            TIMESTAMPTZ,
  unpublished_at          TIMESTAMPTZ,
  created_by_user_id      UUID NOT NULL REFERENCES users(id),
  created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_stub_status CHECK (status IN ('draft','published','unpublished'))
);
CREATE INDEX idx_stubs_org ON public_business_stubs(org_id);
CREATE INDEX idx_stubs_status ON public_business_stubs(org_id, status);
```

**MVP 刻意不含**：phone、email、avatar_host、template_id、employee_consent_at（US-11.2 簡化為 Admin 發布即 org 同意 · DDR-77 seat 預設公開）。

### 3.4 `public_directory_documents`（Pool B 索引 · 對稱 M3）

```sql
CREATE TABLE public_directory_documents (
  stub_id         UUID PRIMARY KEY REFERENCES public_business_stubs(id) ON DELETE CASCADE,
  org_id          UUID NOT NULL REFERENCES organizations(id),
  search_text     TEXT NOT NULL,
  search_vector   TSVECTOR,
  content_hash    VARCHAR(64),
  indexed_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_pdd_org ON public_directory_documents(org_id);
CREATE INDEX idx_pdd_search_vector ON public_directory_documents USING GIN (search_vector);
CREATE INDEX idx_pdd_search_text_trgm ON public_directory_documents USING GIN (search_text gin_trgm_ops);
```

**search_text 組裝**（對稱 M3 `build_search_text`）：

```
{display_name} | {company_name} | {title} | {responsibility_keywords joined} | {product_keywords joined}
```

---

## 4. API 契約

**Base**：`/api/v1` · Bearer JWT  
**授權**：`plan_tier ∈ {enterprise}` 且 `org_members.role=admin` 且 path `org_id` 匹配 membership。

### 4.1 Org（MVP 最小）

| Method | Path | 說明 |
|--------|------|------|
| GET | `/orgs/mine` | 當前 user 的 org 列表（Admin UI 選 org） |
| GET | `/orgs/{org_id}` | org 詳情 + published stub 計數 |

> MVP 可不開 `POST /orgs`（dev seed + migration）；正式環境 Phase 2 由 billing/onboarding 建立。

### 4.2 Stub CRUD

| Method | Path | 說明 |
|--------|------|------|
| GET | `/orgs/{org_id}/stubs` | 列表；query `status=draft\|published\|unpublished` |
| POST | `/orgs/{org_id}/stubs` | 建立 draft |
| GET | `/orgs/{org_id}/stubs/{stub_id}` | 詳情 |
| PATCH | `/orgs/{org_id}/stubs/{stub_id}` | 更新（published 時改 keywords 需 re-index） |
| DELETE | `/orgs/{org_id}/stubs/{stub_id}` | 僅 draft；published 走 unpublish |

**POST body**：

```json
{
  "display_name": "王小明",
  "company_name": "Acme Taiwan",
  "title": "業務經理",
  "responsibility_keywords": ["OEM", "通路"],
  "product_keywords": ["工業電腦", "嵌入式"],
  "external_card_url": "https://hibox.example/card/abc"
}
```

**Errors**：

| Code | HTTP | 條件 |
|------|------|------|
| `ORG_ACCESS_DENIED` | 403 | 非 org admin |
| `ENTERPRISE_REQUIRED` | 403 | plan_tier ≠ enterprise |
| `INVALID_EXTERNAL_URL` | 400 | URL 非 http(s) |
| `STUB_NOT_DRAFT` | 409 | 對 published 做 delete |

### 4.3 發布 / 下架

| Method | Path | Response |
|--------|------|----------|
| POST | `/orgs/{org_id}/stubs/{stub_id}/publish` | 202 `{ "status": "published", "index_status": "indexing" }` |
| POST | `/orgs/{org_id}/stubs/{stub_id}/unpublish` | 200 `{ "status": "unpublished" }` |

發布後觸發 index worker；下架後 **24h 內** index 不可被 M5b 命中（R-P3-3）。

### 4.4 CSV 匯入（DDR-79 最小）

| Method | Path | Body |
|--------|------|------|
| POST | `/orgs/{org_id}/stubs/import-csv` | `multipart/form-data` file |

**CSV 欄位**（header 必填）：

```csv
display_name,company_name,title,responsibility_keywords,product_keywords,external_card_url
```

- `responsibility_keywords` / `product_keywords`：分號分隔 `OEM;通路`
- 匯入預設 **draft**；可 query `?auto_publish=true`（Admin 確認後）

**Response 202**：

```json
{
  "imported": 12,
  "skipped": 1,
  "errors": [{ "row": 3, "reason": "INVALID_EXTERNAL_URL" }]
}
```

---

## 5. M5b 介面契約（M11 寫 · M5b 讀）

> M5b 實作時引用本節；M11 MVP 只需保證 index 正確。

### 5.1 检索

- **表**：`public_directory_documents` JOIN `public_business_stubs` WHERE `status='published'`
- **检索 SQL**：复用 M5 `retrieve_candidates` 模式（tsvector + pg_trgm fallback）
- **不** JOIN `contacts` / `users`（私人）

### 5.2 Search API 擴充（M5b owner）

```json
// POST /search/queries
{ "query_text": "…", "search_scope": "private" | "network" | "all" }
```

| plan_tier | 允許 scope |
|-----------|------------|
| free | `private` only |
| pro / enterprise | `private` \| `network` \| `all` |

**DDR-91**：以 `plan_tier`（pro / enterprise）開放 `search_scope=network|all`；**Pro+ 內建**（對齊 §11.5 · kickoff DDR-K11-02）。

### 5.3 結果 DTO（M5b · DDR-80）

```json
{
  "stub_id": "uuid",
  "rank": 1,
  "match_reason": "…；公開商務 · Acme Taiwan",
  "source_pool": "public_directory",
  "publisher_org_id": "uuid",
  "publisher_org_name": "Acme Corp",
  "external_card_url": "https://…",
  "stub_preview": {
    "display_name": "王小明",
    "company_name": "Acme Taiwan",
    "title": "業務經理",
    "product_keywords": ["工業電腦"]
  }
}
```

**禁止**出現在 Pro 結果：`phones`、`emails`（stub 表無此欄）。

---

## 6. Worker / 排程

| Task | 觸發 | 行為 |
|------|------|------|
| `public_directory.index` | publish / stub 更新 | UPSERT `public_directory_documents` |
| `public_directory.unindex` | unpublish | DELETE index row（或 `tombstone_until`） |
| `public_directory.reconcile` | daily cron（optional MVP） | 清 orphaned index |

Dev：`use_celery_workers=false` 時 in-process async（對齊 M3 index）。

---

## 7. 前端（Admin UI · TECH_STACK 預留）

| 路由 | 畫面 |
|------|------|
| `/admin/org` | org 選擇 / 概覽 |
| `/admin/org/stubs` | stub 列表（狀態 filter） |
| `/admin/org/stubs/new` | 新增 draft |
| `/admin/org/stubs/[id]` | 編輯 + 發布/下架 |
| `/admin/org/import` | CSV 上傳 |

**Gate**：非 enterprise → 403 頁 + CTA；非 org admin → 403。

---

## 8. Dev / Seed

```bash
# dev-login 擴充（M1）
POST /api/v1/auth/dev-login
{ "email": "admin@acme.com", "plan_tier": "enterprise", "seed_org": "acme-demo" }

# 種子：1 org + 3 published stubs → 供 M5b 联测
```

---

## 9. 🔗 Coupling Map 更新

### Shared Entities（M11 新增）

| Entity | Owner | Consumers | Contract |
|--------|-------|-----------|----------|
| `organizations` | M11 | M1 `/me` | id, name |
| `org_members` | M11 | M1 auth | user_id, role |
| `public_business_stubs` | M11 | M5b | status, keywords, external_card_url |
| `public_directory_documents` | M11 | **M5b** | search_vector, stub_id |

### Cross-module Contracts

| From | To | Trigger | Sync/Async |
|------|-----|---------|------------|
| M11 | M5b | index ready | Pull DB |
| M1 | M11 | enterprise + org_membership | Sync auth |
| M11 | M7 | stub 無 PII 電話/email | Schema |
| M6 | M11 | （P2）可選 enrich product_keywords | Async optional |

**M11 不消費** M3 ContactUpsert / M2 handoff。

---

## 10. DDR 新增（SA/SD M11）

| ID | 決策 | 理由 |
|----|------|------|
| DDR-90 | Org/stub schema **M11 owner**；M1 只擴 `GET /me` memberships + enterprise gate | 避免 M1 膨脹 |
| DDR-91 | M5b 用 `plan_tier pro\|enterprise` 開 `search_scope` | 對齊 §11.5 · kickoff |
| DDR-92 | Unpublish → index 24h 內移除（worker + reconcile） | R-P3-3 |
| DDR-93 | Stub **無** phone/email 欄；Pro 只顯示摘要 + 外链 | DDR-80 |
| DDR-94 | CSV 匯入 MVP 最小 6 欄；預設 draft | DDR-79 |
| DDR-95 | Pool B index 复用 tsvector+trgm（同 M5/M3），不另建 ES | TECH_STACK LOCKED |

---

## 11. Open Items（非阻塞 MVP）

| 🚧 | 議題 | 建議 |
|----|------|------|
| B-M11-1 | 員工個人同意 flow（US-11.2 完整版） | Stage 2+；MVP Admin 發布即代表 org 授權 |
| B-M11-2 | M6 自動 enrich stub product_keywords | P2；MVP 手填 |
| B-M11-3 | 用量報表（被搜尋次數） | Enterprise Phase 2 |

---

## 12. M11 MVP 驗收（對接 QA）

- [ ] Enterprise Admin 建立 ≥3 stub 並 publish → `public_directory_documents` 有列
- [ ] Unpublish 後 24h 內 M5b 检索不到（可先 unit + integration）
- [ ] Free user 的 M5 `search_scope=network` → 403
- [ ] Pool A contact_id **從未**出現在 `public_directory_documents`
- [ ] Pro 結果 DTO **無** phone/email；有 `external_card_url`
- [ ] CSV 匯入 10 行 ≥9 成功

---

**Coupling Map updates**：`organizations`, `org_members`, `public_business_stubs`, `public_directory_documents`  
**下一棒**：`BSChat_PM_M11.md`（US 驗收）→ `BSChat_ENG_M11.md` → 實作 migration `011_m11_public_directory`
