# BSChat SA/SD — Module 6：公司資訊補全（Enrichment）

> **依據**：M6 PM L3 v1.1、M3 SA/SD 契約、PRD v2.1 §11–12、DDR-28~39  
> **架構模式**：Modular Monolith + Event-driven workers（延續 M2/M3）  
> **版本**：v1.0

---

## 1. 架構概覽

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Event Bus (Redis / BullMQ)                       │
│  CompanyEnrichRequested  ← M3（ingest / company_name_changed）       │
│  CompanyEnriched         → M3（pass 2 inference + re-index）       │
└───────────────┬──────────────────────────────┬──────────────────────┘
                │                              │
┌───────────────▼──────────────┐    ┌──────────▼──────────────────────┐
│  Company Enrich Worker (M6)  │    │  Stale Refresh Scheduler (M6)   │
│  - resolve Company           │    │  - daily cron scan              │
│  - web fetch + LLM extract   │    │  - read M1 entitlement          │
│  - append enrichment         │    │  - enqueue stale_auto jobs      │
│  - link contacts.company_id  │    └─────────────────────────────────┘
│  - emit CompanyEnriched      │
└───────────────┬──────────────┘
                │
┌───────────────▼──────────────────────────────────────────────────────┐
│  PostgreSQL                                                           │
│  companies | company_enrichments | company_field_reviews             │
│  enrich_jobs | user_entitlements (M1 owner, M6 read)                   │
└───────────────┬──────────────────────────────────────────────────────┘
                │ read cache
┌───────────────▼──────────────┐    ┌──────────────────────────────────┐
│  M3 Contact Detail API       │    │  M5 Search (future)               │
│  company_enrichment section  │    │  Layer 3 query-time augmentation  │
└──────────────────────────────┘    │  (separate store, DDR-36)         │
                                    └──────────────────────────────────┘
```

**為何 Modular Monolith + Worker**：
- Enrich 為 I/O 密集（網頁抓取 5–15s + LLM 3–10s），必須非同步，不可阻塞 M2/M3 API
- 同一 Company 多 Contact 共享 enrich 結果 → 需要 job dedupe + DB 層去重
- Pro stale refresh 為定時批次 → BullMQ repeatable job 足夠，無需獨立 microservice

**外部整合（MVP）**：
| 服務 | 用途 | 備註 |
|------|------|------|
| Claude API | 從網頁文字抽取 `main_products`、summary | 同 M2/M3 模型家族 |
| HTTP Fetch | 抓取官網首頁 + `/about`/`/products` 候選路徑 | 8s timeout；robots 尊重 |
| M1 Entitlement | `plan_tier`、quota、auto_refresh 開關 | MVP hardcode free（DDR-39） |

**B-3 決策（網頁抓取 + LLM pipeline）**：

```
1. Website Discovery
   a. contact.website（OCR）若有效 → 優先
   b. 域名啟發式：{slug}.com.tw / .com / .tw（最多 3 次 HEAD 探測）
   c. P1：Tavily Search API 作為 fallback（🚧 成本待 Pilot 驗證）

2. Page Fetch（最多 3 頁，各 8s timeout）
   - homepage
   - /about, /about-us, /company
   - /products, /services, /solution

3. LLM Extraction（Claude）
   Input: 合併文字 ≤ 12,000 chars + company_name
   Output JSON:
   {
     "main_products": ["...", "..."],   // 1–5 項，各 ≤ 80 字
     "summary": "...",                  // P1，nullable
     "industry_tags": ["..."],          // P1
     "overall_confidence": 0.0-1.0,
     "fields_provenance": {
       "main_products": { "source_urls": ["..."], "confidence": 0.72 }
     }
   }

4. Gate
   - 無官網可達 → status=failed，不腦補（R-6）
   - 有官網但 products conf < 0.3 → partial
   - products conf ≥ 0.5 → completed + emit CompanyEnriched（DDR-31）
```

---

## 2. L4 Depth Gate

### 2.1 Data Flow

```
[M3 Contact Upsert — company_name 有值]
        │
        ▼ CompanyEnrichRequested (async, outbox)
[M6 Enrich Worker]
        ├─ Resolve: find/create Company by (user_id, normalized_name)
        ├─ Dedupe: 24h 内 skip unless manual|stale_auto|name_changed
        ├─ Check entitlement: daily quota / manual monthly quota
        ├─ Discover website → fetch pages → LLM extract
        ├─ INSERT company_enrichments (append-only, enrich_version++)
        ├─ UPDATE companies.enrich_status, last_enriched_at
        ├─ UPDATE contacts.company_id for matching contacts
        └─ IF DDR-31 satisfied AND user未 reject → CompanyEnriched
                │
                ▼
[M3] inference pass 2 + contact-index job

[Pro Stale Scheduler — daily 03:00 UTC]
        ├─ SELECT companies WHERE last_enriched_at < now - interval_days
        ├─ JOIN user_entitlements WHERE plan=pro AND auto_refresh_enabled
        └─ Enqueue stale_auto enrich (respect daily quota)

[User Manual Refresh]
        POST /companies/:id/enrich
        ├─ M6 读 M1 quota → decrement if allowed
        └─ trigger_type=manual → bypass 24h dedupe

[M5 Query-time Live — DDR-36，M5 拥有]
        搜尋时 live 查 → 写入 query_augmentations（非 M6 cache）
        用户「采用」→ POST /companies/:id/enrich?source=query_adopt
```

### 2.2 State Boundaries

| 状态 | 存储 | Owner | 说明 |
|------|------|-------|------|
| Company 实体 | `companies` | M6 | user-scoped 去重（DDR-30） |
| Enrich 历史 | `company_enrichments` | M6 | append-only；UI 读最新 version |
| 用户审核 | `company_field_reviews` | M6 | accept/reject/override（DDR-32） |
| Job 追踪 | `enrich_jobs` | M6 | 可观测 + dedupe |
| Entitlement | `user_entitlements` | **M1 write** / M6 read | MVP default free |
| Contact.company_id | `contacts` | M3 write / M6 update | FK |
| Query-time 结果 | `query_augmentations` | **M5** | 不自动覆写 cache |
| Queue 状态 | Redis BullMQ | infra | |

**Transaction 边界**：
- Enrich 完成：`company_enrichments` INSERT + `companies` UPDATE + `contacts.company_id` UPDATE → **同一 DB transaction**
- `CompanyEnriched` emit：**Outbox pattern**，与 transaction 同事务提交
- LLM / HTTP 在 transaction **外**执行；失败只写 job status，不 half-update company

**Cache 策略**：
- 无 Redis 业务 cache；`companies` + 最新 `company_enrichments` 即为 cache-at-ingest
- 24h dedupe 查 `companies.last_enriched_at` + `enrich_jobs.idempotency_key`

### 2.3 Concurrency

| 场景 | 策略 |
|------|------|
| 同公司多 Contact 同时 ingest | Job dedupe：`idempotency_key = enrich:{company_id}:ingest:{hour_bucket}`；BullMQ jobId 唯一 |
| enrich 进行中用户 reject | `company_field_reviews` 写入优先；完成时不 emit CompanyEnriched |
| enrich 完成 vs 用户 override | override 叠加；provenance 保留；显示 user_override 值 |
| manual refresh 并发双击 | POST idempotent by `company_id + minute_bucket`；第二次 409 `ALREADY_IN_PROGRESS` |
| stale batch + manual 冲突 | manual 优先；stale job 见 `enrich_status=pending` 则 skip |
| M3 PATCH company_name | 新 `CompanyEnrichRequested`；可创建新 Company 或 re-match |

**Optimistic locking**：`companies.enrich_version` 递增；enrichment INSERT 带 `enrich_version = companies.enrich_version + 1`

### 2.4 Failure Modes

| 失败 | 处理 | UX（M3/M6 UI 需覆盖） |
|------|------|------------------------|
| 找不到官網 | `enrich_status=failed`；不写入 products | 「無法取得公開資訊」 |
| HTTP timeout / 403 | retry 1x → partial or failed | 同上或「資訊不足」 |
| LLM API 失败 | retry 2x exponential → job failed | 「正在補充…」→ 失败态 |
| LLM 低信心 (<0.3) | partial；不 emit CompanyEnriched | 「資訊不足，建議確認公司名稱」 |
| daily quota 超出 | job delayed +24h queue | Toast「今日補全額度已用完」 |
| manual quota 超出 (Free) | 403 `QUOTA_EXCEEDED` | 升级 CTA（M1 P1） |
| Pro 降级 Free | 停止 stale scheduler；保留 cache | 设置页开关 disabled |
| DB down | worker retry；API 503 | 全局错误 |
| 多候选公司 (B-6) | MVP：选最高 conf + `needs_review` flag | 低信心显示 + P1 消歧 UI |
| user rejected (DDR-32) | 隐藏 products；re-enrich 不复活 | 除非用户点「重新補全」 |

### 2.5 Empty State / Cold Start

| 时刻 | 行为 |
|------|------|
| t=0 无 Company | 首笔 Contact 带 company_name → 自动 create Company + enqueue enrich |
| enrich pending | M3 详情显示「⏳ 正在補充公司資訊...」 |
| enrich failed | 显示失败态；Contact 仍可用（OCR 字段不受影响） |
| 0 products 可显示 | 列表 `company_products_preview=null`；不显示空白 AI 区 |
| MVP plan=free | `user_entitlements` seed default；stale scheduler no-op |
| 首笔 manual refresh | Free 扣 1/3 月度配额 |

---

## 3. 資料庫設計

### 3.1 `companies`

```sql
CREATE TABLE companies (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               UUID NOT NULL,              -- scope: user（DDR-30）
  workspace_id          UUID NOT NULL,
  normalized_name       VARCHAR(255) NOT NULL,      -- 去重键
  display_name          VARCHAR(255) NOT NULL,      -- 最新 company_name 原文
  website_url           VARCHAR(512),
  enrich_status         VARCHAR(20) DEFAULT 'never',
    -- never|pending|completed|partial|failed|needs_review
  last_enriched_at      TIMESTAMPTZ,                -- enriched_at（DDR-35）
  enrich_version        INT DEFAULT 0,
  needs_review          BOOLEAN DEFAULT FALSE,      -- B-6 多候选
  deleted_at            TIMESTAMPTZ,
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  updated_at            TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, normalized_name)
);

CREATE INDEX idx_companies_user_status ON companies(user_id, enrich_status)
  WHERE deleted_at IS NULL;
CREATE INDEX idx_companies_stale_scan ON companies(last_enriched_at)
  WHERE deleted_at IS NULL AND enrich_status IN ('completed', 'partial');
```

**Soft-delete**：`deleted_at`；Contact 仍保留 `company_name` 文字，FK nullable。

**Shared contract**：`id`, `display_name`, `website_url`, `enrich_status`, `last_enriched_at` → M3 detail, M5 index

### 3.2 `company_enrichments`（append-only）

```sql
CREATE TABLE company_enrichments (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id            UUID NOT NULL REFERENCES companies(id),
  enrich_version        INT NOT NULL,
  main_products         JSONB DEFAULT '[]',         -- string[]
  summary               TEXT,                       -- P1
  industry_tags         JSONB DEFAULT '[]',         -- P1
  fields_provenance     JSONB NOT NULL DEFAULT '{}',
  overall_confidence    FLOAT NOT NULL DEFAULT 0,
  trigger_type          VARCHAR(30) NOT NULL,
    -- ingest|manual|stale_auto|company_name_changed|query_adopt
  source_urls           JSONB DEFAULT '[]',
  model                 VARCHAR(50),
  prompt_version        VARCHAR(20),
  status                VARCHAR(20) NOT NULL,
    -- completed|partial|failed
  candidate_companies   JSONB,                        -- P1 消歧候選
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(company_id, enrich_version)
);

CREATE INDEX idx_enrichments_company_latest
  ON company_enrichments(company_id, enrich_version DESC);
```

**读取规则**：UI/API 读 `MAX(enrich_version)`；M5 index 读 active enrichment 的 `main_products`。

### 3.3 `company_field_reviews`

```sql
CREATE TABLE company_field_reviews (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id      UUID NOT NULL REFERENCES companies(id),
  user_id         UUID NOT NULL,
  field_name      VARCHAR(50) NOT NULL,   -- main_products|summary|website_url
  review_status   VARCHAR(20) NOT NULL,   -- auto|accepted|rejected|user_override
  override_value  JSONB,                    -- user_override 时
  reviewed_at     TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(company_id, user_id, field_name)
);
```

**DDR-32**：`review_status=rejected` 时，即使新 enrichment 完成，UI 仍隐藏该字段，直到用户 POST `re-enrich` 或改 review_status。

### 3.4 `enrich_jobs`

```sql
CREATE TABLE enrich_jobs (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id        UUID NOT NULL REFERENCES companies(id),
  user_id           UUID NOT NULL,
  contact_id        UUID,                 -- nullable for stale_auto
  trigger_type      VARCHAR(30) NOT NULL,
  status            VARCHAR(20) NOT NULL DEFAULT 'requested',
    -- requested|resolving|enriching|completed|partial|failed|skipped
  idempotency_key   VARCHAR(128) UNIQUE,
  error_code        VARCHAR(50),
  latency_ms        INT,
  started_at        TIMESTAMPTZ,
  completed_at      TIMESTAMPTZ,
  created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_enrich_jobs_company_created ON enrich_jobs(company_id, created_at DESC);
```

### 3.5 `user_entitlements`（M1 owner，M6 read-only）

```sql
CREATE TABLE user_entitlements (
  user_id                       UUID PRIMARY KEY,
  plan_tier                     VARCHAR(10) DEFAULT 'free',  -- free|pro
  auto_refresh_enabled          BOOLEAN DEFAULT FALSE,
  auto_refresh_interval_days    INT DEFAULT 90
    CHECK (auto_refresh_interval_days IN (30, 60, 90)),
  manual_refresh_quota_monthly  INT DEFAULT 3,               -- Pro: -1 = unlimited
  manual_refresh_used_this_month INT DEFAULT 0,
  manual_refresh_reset_at       TIMESTAMPTZ,
  daily_enrich_quota            INT DEFAULT 50,
  daily_enrich_used             INT DEFAULT 0,
  daily_enrich_reset_at         TIMESTAMPTZ,
  updated_at                    TIMESTAMPTZ DEFAULT NOW()
);
```

**MVP（DDR-39）**：Contact 创建时 upsert default row（plan=free）。M6 通过 `EntitlementService.check(action)` 读取。

### 3.6 `query_augmentations`（M5 owner，M6 只读 adopt 来源）

```sql
CREATE TABLE query_augmentations (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL,
  company_id      UUID REFERENCES companies(id),
  query_id        UUID NOT NULL,          -- M5 search session
  live_products   JSONB,
  source_urls     JSONB,
  confidence      FLOAT,
  adopted         BOOLEAN DEFAULT FALSE,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

**DDR-36**：M5 写入；用户 adopt → M6 `trigger_type=query_adopt` 写入新 enrichment。

---

## 4. Event 契約

### 4.1 `CompanyEnrichRequested`（M3 → M6）

```typescript
interface CompanyEnrichRequested {
  eventId: string;           // UUID, outbox idempotency
  userId: string;
  workspaceId: string;
  contactId: string;
  companyName: string;
  contactWebsite?: string;   // OCR website 辅助 discovery
  triggerType: 'ingest' | 'company_name_changed';
  occurredAt: string;        // ISO8601
}
```

**Queue**：`company-enrich` · priority：ingest=5, name_changed=7

### 4.2 `CompanyEnriched`（M6 → M3）

```typescript
interface CompanyEnriched {
  eventId: string;
  userId: string;
  workspaceId: string;
  contactId: string;         // 触发 enrich 的 contact
  companyId: string;
  status: 'completed' | 'partial';
  mainProducts: string[];
  productsConfidence: number;
  websiteUrl?: string;
  enrichedAt: string;
  enrichVersion: number;
}
```

**Emit 条件（DDR-31）**：
```typescript
const shouldEmit =
  ['completed', 'partial'].includes(enrichment.status) &&
  enrichment.main_products.length > 0 &&
  enrichment.overall_confidence >= 0.5 &&
  !(await reviewRepo.isRejected(companyId, 'main_products'));
```

**Consumer（M3 已有 stub）**：pass 2 inference + contact-index

---

## 5. API 規格

**Base**：`/api/v1` · Bearer JWT（M1 stub：dev header `X-User-Id`）

| Method | Path | 说明 | Idempotent | Rate limit |
|--------|------|------|------------|------------|
| GET | `/companies/:id` | 公司 + 最新 enrichment + reviews | ✅ | 60/min |
| POST | `/companies/:id/enrich` | 手动 refresh | ✅（minute bucket） | 10/min |
| PATCH | `/companies/:id/review` | accept/reject/override | ❌ | 30/min |
| POST | `/companies/:id/re-enrich` | reject 后重新补全 | ✅ | 10/min |
| GET | `/companies/:id/enrich-status` | 轻量 polling（optional） | ✅ | 120/min |

M3 `GET /contacts/:id` 仍为主要入口；内部调用 `CompanyEnrichmentService.buildSection(companyId)`.

### POST `/companies/:id/enrich`

**Request**：
```json
{
  "trigger": "manual",
  "queryAugmentationId": null
}
```

**Success 202**：
```json
{
  "job_id": "uuid",
  "status": "requested",
  "quota_remaining": 2
}
```

**Errors**：
| Code | HTTP | 说明 |
|------|------|------|
| `QUOTA_EXCEEDED` | 403 | Free manual 月度用尽 |
| `DAILY_LIMIT` | 429 | 每日 enrich 上限 |
| `ALREADY_IN_PROGRESS` | 409 | 同公司 job 进行中 |
| `COMPANY_NOT_FOUND` | 404 | |
| `PLAN_REQUIRED` | 403 | P2 功能 |

### PATCH `/companies/:id/review`

```json
{
  "field_name": "main_products",
  "review_status": "rejected"
}
```

或 override：
```json
{
  "field_name": "main_products",
  "review_status": "user_override",
  "override_value": ["工業電腦", "嵌入式系統"]
}
```

### GET `/companies/:id` — Response（供 M3 section builder）

```json
{
  "id": "uuid",
  "display_name": "ABC Technology",
  "website_url": "https://abc-tech.com.tw",
  "enrich_status": "completed",
  "last_enriched_at": "2026-05-18T10:30:00Z",
  "enrichment": {
    "main_products": ["工業電腦主機", "嵌入式板卡"],
    "overall_confidence": 0.78,
    "fields_provenance": {
      "main_products": {
        "source_urls": ["https://abc-tech.com.tw/products"],
        "confidence": 0.78
      }
    },
    "trigger_type": "ingest",
    "enrich_version": 2
  },
  "reviews": {
    "main_products": { "review_status": "auto" }
  },
  "display": {
    "show_products": true,
    "label": "✦ AI 補全 · abc-tech.com.tw · 78%",
    "updated_label": "更新於 2026-05-18"
  }
}
```

**Error response 格式**（全模块统一）：
```json
{
  "error": {
    "code": "QUOTA_EXCEEDED",
    "message": "本月手動更新次數已用完（3/3）",
    "details": { "reset_at": "2026-06-01T00:00:00Z" }
  }
}
```

---

## 6. Enrich Worker 實作要點

### 6.1 Company Resolution

```typescript
function normalizeCompanyName(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/\s+(co\.?|ltd\.?|inc\.?|corp\.?|股份有限公司|有限公司|公司)$/i, '')
    .replace(/[^\w\u4e00-\u9fff]+/g, ' ')
    .trim();
}
```

```typescript
async function resolveCompany(input: EnrichInput): Promise<Company> {
  const normalized = normalizeCompanyName(input.companyName);
  return db.companies.upsert({
    where: { user_id_normalized_name: { userId: input.userId, normalizedName: normalized } },
    create: {
      userId: input.userId,
      workspaceId: input.workspaceId,
      normalizedName: normalized,
      displayName: input.companyName,
      enrichStatus: 'pending',
    },
    update: { displayName: input.companyName },  // 保留最新 display
  });
}
```

### 6.2 24h Dedupe（R-2）

```typescript
const BYPASS_TRIGGERS = ['manual', 'stale_auto', 'company_name_changed', 'query_adopt'];

function shouldSkipDedupe(company: Company, trigger: string): boolean {
  if (BYPASS_TRIGGERS.includes(trigger)) return false;
  if (!company.lastEnrichedAt) return false;
  return hoursSince(company.lastEnrichedAt) < 24;
}
```

### 6.3 Entitlement Check（B-8）

```typescript
interface EntitlementService {
  checkDailyEnrich(userId: string): Promise<{ allowed: boolean; remaining: number }>;
  checkManualRefresh(userId: string): Promise<{ allowed: boolean; remaining: number }>;
  consumeManualRefresh(userId: string): Promise<void>;
  isStaleAutoEnabled(userId: string): Promise<{ enabled: boolean; intervalDays: number }>;
}
```

**M1 接口契约（DDR-38）**：
- M6 **只读** `user_entitlements`；不修改 plan_tier / billing
- M6 **可写** `manual_refresh_used_this_month`、`daily_enrich_used`（或通过 M1 RPC；MVP 直接写同一表）
- Stale scheduler：`SELECT c.* FROM companies c JOIN user_entitlements u ON c.user_id = u.user_id WHERE u.plan_tier='pro' AND u.auto_refresh_enabled AND c.last_enriched_at < NOW() - interval`

### 6.4 Stale Scheduler（B-8）

```typescript
// BullMQ repeatable: '0 3 * * *' UTC
async function staleCompanyScan() {
  const batch = await db.query(`
    SELECT c.id, c.user_id, u.auto_refresh_interval_days
    FROM companies c
    JOIN user_entitlements u ON c.user_id = u.user_id
    WHERE u.plan_tier = 'pro'
      AND u.auto_refresh_enabled = true
      AND c.deleted_at IS NULL
      AND c.last_enriched_at < NOW() - (u.auto_refresh_interval_days || ' days')::interval
    LIMIT 200
  `);
  for (const row of batch) {
    await enrichQueue.add('stale-auto', { companyId: row.id, userId: row.user_id }, {
      jobId: `stale:${row.id}:${todayBucket()}`,
    });
  }
}
```

### 6.5 多候选消歧（B-6 MVP）

| 情况 | MVP 行为 | P1 |
|------|---------|-----|
| 2+ 域名 equally valid | 选 Alexa/内容最长页；`needs_review=true`；conf × 0.85 | 用户选择 UI |
| 同名不同产业 | LLM 用 contact.title 辅助；仍低则 needs_review | 候选列表 |
| OCR company_name 歧义 | 不自动 split Company | 编辑公司名 re-trigger |

---

## 7. M3 / M5 整合契約

### 7.1 M3 `company_enrichment` Section DTO

```typescript
interface CompanyEnrichmentSection {
  status: 'pending' | 'completed' | 'partial' | 'failed' | 'rejected' | 'hidden';
  main_products?: string[];
  website_url?: string;
  confidence?: number;
  provenance_label?: string;    // "✦ AI 補全 · source · 78%"
  updated_at?: string;
  can_refresh: boolean;
  refresh_quota_remaining?: number;
  review_status?: 'auto' | 'accepted' | 'rejected' | 'user_override';
}
```

**Display logic（PM L3.6）** 在 `CompanyEnrichmentService.buildSection()` 集中实现。

### 7.2 M5 Index 字段（延续 M3 SA/SD）

```typescript
// contact_search_documents 更新时追加：
company_products: string[];      // from M6 latest enrichment
company_enriched_at: string;
```

Re-index trigger：`CompanyEnriched` event → M3 index worker（已有）。

### 7.3 M5 Query-time（预留给 M5 SA/SD）

- Live 查结果存 `query_augmentations`
- 搜尋响应 merge：`cache_products` + `live_products`（标注来源）
- 用户 adopt → `POST /companies/:id/enrich { trigger: "manual", queryAugmentationId }`

---

## 8. 🔗 Coupling Map 更新

### Shared Entities（M6 新增/扩展）

| Entity | Owner | Consumers | Contract |
|--------|-------|-----------|----------|
| `companies` | M6 | M3, M5 | id, user_id, display_name, website_url, enrich_status, last_enriched_at |
| `company_enrichments` | M6 | M3, M5 | main_products[], overall_confidence, fields_provenance, enrich_version |
| `company_field_reviews` | M6 | M3 UI | field_name, review_status, override_value |
| `user_entitlements` | M1 | M6, M5 | plan_tier, quotas, auto_refresh_* |
| `query_augmentations` | M5 | M6 adopt | live_products, adopted |

### Cross-module Contracts（M6 新增）

| From | To | Event/API | Trigger | Sync/Async |
|------|-----|-----------|---------|------------|
| M3 | M6 | CompanyEnrichRequested | company_name present/changed | Async |
| M6 | M3 | CompanyEnriched | enrich DDR-31 pass | Async |
| M1 | M6 | user_entitlements read | every enrich / stale scan | Sync DB |
| M6 | M5 | company_products in index | CompanyEnriched → re-index | Async |
| M5 | M6 | query_adopt enrich | user adopt live result | Async |
| M3 | M6 | GET enrichment section | contact detail | Sync |

### Cross-cutting Concerns

| Concern | M6 实现 |
|---------|---------|
| Auth | 所有 API 验证 `user_id` 拥有 `company_id` |
| Audit | `enrich_jobs` + `company_enrichments.trigger_type` |
| Tenant | `user_id` + `workspace_id` on companies |
| Quota | EntitlementService；超限 graceful degrade |
| i18n | API message keys；UI 繁中优先 |
| Feature flags | `plan_tier`；MVP hardcode free |

---

## 9. DDR 新增（SA/SD）

| ID | 决策 | 理由 |
|----|------|------|
| DDR-40 | MVP 官网发现 = OCR website + 域名启发式（最多 3 域名 probe） | 零额外 API 成本；Pilot 后加 Tavily |
| DDR-41 | `company_enrichments` append-only；UI 永远读最新 version | 可追溯；reject 不删历史 |
| DDR-42 | Enrich job idempotency_key 含 hour_bucket（ingest） | 防并发 duplicate fetch |
| DDR-43 | Stale scan BullMQ cron 03:00 UTC，batch 200 | 错开高峰；可配置 |
| DDR-44 | M6 可写 quota counter 字段（MVP）；Phase 2 改 M1 RPC | DDR-39 stub 下避免过度工程 |
| DDR-45 | `needs_review` 不阻塞 Contact ACTIVE；低信心仍显示 | 最佳努力优于全隐藏 |

---

## 10. Open Blockers（残留 🚧）

| 🚧 | 议题 | 状态 | 备注 |
|----|------|------|------|
| B-3 | 网页抓取 + LLM pipeline | **✅ MVP 方案锁定** | Tavily fallback 标 P1 |
| B-6 | 多候选消歧 | **✅ MVP 范围锁定** | needs_review + P1 UI |
| B-8 | stale scheduler + entitlement | **✅ 设计完成** | ENG 实现 BullMQ cron |
| B-9 | Tavily/Search API 成本上限 | 🚧 | Pilot 后定；不影响 MVP |
| B-10 | 官网 robots.txt 合规策略 | 🚧 | ENG 实现 respect robots |

---

## 11. L4 Depth Gate 自检

| Gate | 状态 |
|------|------|
| Data flow | ✅ |
| State boundaries | ✅ |
| Concurrency | ✅ |
| Failure modes | ✅ |
| Empty state | ✅ |
| Coupling Map | ✅ |

**M6 SA/SD L4：✅ 可锁定**

---

### 🤝 Handoff: SA/SD → UI/UX — Module 6：公司資訊補全

**State Tracker snapshot**：
| 模組 | PM | SA/SD | UI/UX | ENG | QA |
|------|:--:|:-----:|:-----:|:---:|:--:|
| M6 | ✅ v1.1 | ✅ v1.0 | ⏳ | ⏳ | ⏳ |

**Per-Module Depth Spec**：见本文 §2 L4 Depth Gate

**Coupling Map updates**：`companies`, `company_enrichments`, `company_field_reviews`, `user_entitlements`, `query_augmentations`；Events `CompanyEnrichRequested` / `CompanyEnriched`

**Data entities + state machine**：
- Company：`never → pending → completed|partial|failed|needs_review`
- Enrich Job：`requested → resolving → enriching → completed|partial|failed|skipped`
- User review：`auto → accepted|rejected|user_override`

**Error scenarios UI/UX must cover**：
- enrich pending（⏳）
- conf 0.3–0.49（資訊不足）
- conf < 0.3 / failed（無法取得）
- rejected 隐藏 + 「重新補全」入口
- manual quota 用尽 + Pro 升级 CTA
- override 显示「已修正」
- `last_enriched_at` 更新时间标签（DDR-35）
- Pro 设置：auto_refresh 开关 + interval（M1 设置页，M6 状态反馈）

**Empty states UI/UX must design**：
- 列表 `company_products_preview` 空（不显示 AI 摘要行）
- enrich 进行中列表可选 shimmer / 「補全中」badge
- Free 用户 manual refresh 配额显示（如「本月剩余 2/3」）

**Open blockers（🚧）**：B-9 Tavily 成本、B-10 robots.txt（不阻塞 UI/UX）

---

*SA/SD M6 v1.0 — SDLC Phase 1*
