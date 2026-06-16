# BSChat SA/SD — Module 5：AI 搜尋（對話式找商機）

> **依據**：M5 PM L3 v1.1、M3/M6 SA/SD 契約、PRD v2.2 §11/§13、DDR-51~59  
> **架構模式**：Modular Monolith + Sync API（Layer A/B）+ Async Worker（Layer C P1）  
> **版本**：v1.0

---

## 1. 架構概覽

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Client（搜尋 Tab）                            │
│  POST /search/queries  ·  GET /search/queries/:id  ·  P1: live-augment│
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                    Search API (M5) — Sync Path (P0)                  │
│  1. Entitlement check (cache quota)                                  │
│  2. Intent parse (Claude lite / 合併进 rerank)                       │
│  3. Retrieval — tsvector top-50 (Pool A only)                      │
│  4. Rerank + Explain — Claude structured JSON                        │
│  5. Persist search_queries + search_results                          │
│  6. Emit SearchCompleted / AhaMoment (M9 stub)                       │
└───────────────┬───────────────────────────────┬─────────────────────┘
                │ read                          │ P1 async
┌───────────────▼──────────────┐    ┌───────────▼─────────────────────┐
│  PostgreSQL                   │    │  Search Live Augment Worker (P1) │
│  contact_search_documents ←M3│    │  · reuse M6 fetch+LLM pipeline   │
│  contacts (JOIN rerank)       │    │  · write query_augmentations     │
│  company_enrichments (JOIN)   │    │  · merge into search response    │
│  search_sessions/queries/     │    └───────────▲─────────────────────┘
│    results                    │                │ adopt
│  query_augmentations (M5 own) │    ┌───────────┴─────────────────────┐
│  user_entitlements ←M1        │    │  M6 POST /companies/:id/enrich   │
└───────────────────────────────┘    │  trigger=query_adopt             │
                                     └───────────────────────────────────┘
```

**為何 Sync + 可選 Async**：
- Layer A+B（tsvector + LLM rerank）目標 P95 < 3s → **MVP 同步 API** 足夠
- Layer C live 查 5–30s → **P1 异步 worker** + polling / SSE；不阻塞 P0 Aha

**Pool 边界（MVP）**：
- `search_scope` 固定 `private`（Pool A）；`user_id = JWT.sub` 强制过滤（DDR-59）
- Phase 3 Pool B → `public_directory_documents`（M11）；本文 §12 预留

---

## 2. L4 Depth Gate

### 2.1 Data Flow

```
[User POST /search/queries { query_text }]
        │
        ├─ EntitlementService.check('search_cache') → 429 if daily exceeded
        ├─ INSERT search_queries status=SUBMITTED
        │
        ▼ PARSING_INTENT
[IntentService.parse(query_text)]
        · parsed_intent JSON: { products[], roles[], events[], regions[], keywords[] }
        · 不写入 user profile（DDR-5）
        │
        ▼ RETRIEVING
[RetrievalService.search(userId, parsed_intent)]
        · tsvector @@ websearch_to_tsquery('simple', built_query)
        · pg_trgm fallback if ts hits < 5（B-14）
        · JOIN contacts + latest company_enrichment
        · top 50 candidates + retrieval_score
        │
        ▼ RERANKING
[RerankService.rerank(query, candidates)]  — Claude structured output
        · top 5–10 + match_reason + match_sources[]
        · validate sources ⊆ candidate fields（DDR-53）
        · apply confirmed +10% boost post-rerank（DDR-56）
        │
        ▼ COMPLETED | EMPTY
        · INSERT search_results (append-only)
        · UPDATE search_queries status, result_count, latency_ms
        · IF first_search AND result_count≥1 → emit AhaMomentDetected
        │
        ▼ Response 200

[P1 — User POST .../live-augment]
        ├─ EntitlementService.check('search_live') → 403 quota
        ├─ Enqueue search-live-augment job (top 3 companies by rank)
        ├─ Worker: M6-compatible fetch+LLM → INSERT query_augmentations
        └─ PATCH search_results.live_products merge; status LIVE_AUGMENTING→COMPLETED

[P1 — User POST .../adopt]
        └─ POST M6 /companies/:id/enrich { trigger: "query_adopt", queryAugmentationId }
```

**Index 更新路径（M3 owner，M5 consumer）**：
```
Contact upsert / CompanyEnriched / inference pass 2
    → M3 contact-index worker
    → contact_search_documents.search_text + search_vector
    → M5 下次检索可见（eventual consistency，通常 < 30s）
```

### 2.2 State Boundaries

| 狀態 / 資料 | 存儲 | Owner |
|-------------|------|-------|
| `search_queries.status` | `search_queries` | **M5** |
| `search_results` | `search_results` | **M5** |
| `query_augmentations` | `query_augmentations` | **M5** write；M6 read adopt |
| `contact_search_documents` | PostgreSQL | **M3** write / **M5** read |
| Contact 业务字段 | `contacts` | **M3** |
| Company products cache | `company_enrichments` | **M6** |
| Quota counters | `user_entitlements` | **M1** owner；M5 read + increment（DDR-44 模式） |

**Transaction 邊界**：
- Search sync path：`search_queries` INSERT → retrieval（read-only）→ `search_results` bulk INSERT → `search_queries` UPDATE **同一 DB transaction**（失败则 FAILED，无 orphan results）
- Live augment：`query_augmentations` INSERT 独立 transaction；不更新 M6 cache（DDR-36）

### 2.3 Concurrency

| 場景 | 策略 |
|------|------|
| 用户快速连发 2 次 search | 独立 `query_id`；UI 显示最新；无 lock |
| 检索时 index 正在更新 | 读 committed index；可能缺最新 Contact；UX「資料同步中」optional banner |
| 同一 query 重复 POST | `Idempotency-Key` header（可选）；默认每次新 query |
| LLM rerank 并发 | API worker pool；单 query 内串行 |
| Live augment 同一 company | job dedupe key `live:{query_id}:{company_id}` |
| Delete contact 后搜索 | M3 删 index doc；M5 JOIN 过滤 `deleted_at IS NULL` |

### 2.4 Failure Modes

| 失敗 | 處理 | HTTP / UX |
|------|------|-----------|
| 0 indexed contacts | status=EMPTY；suggestions | 200 + `empty_state` payload |
| tsvector 0 hits | pg_trgm fallback → 仍 0 → EMPTY | 200 |
| Claude intent/rerank timeout | fallback：tsvector order top 10；`match_reason` 简化模板 | 200 + `degraded: true` |
| Claude 429 | retry 1x → fallback retrieval order | 200 degraded |
| DB down | 503 | SERVICE_UNAVAILABLE |
| cache search quota 用尽 | 429 | `SEARCH_QUOTA_EXCEEDED` + 明日重置 |
| live quota 用尽（P1） | 403 | `LIVE_QUOTA_EXCEEDED` + Pro CTA |
| M6 adopt 失败（P1） | 502；augmentation 仍 `adopted=false` | Toast retry |
| index 延迟 > 60s | 不阻塞；结果可能缺新卡 | optional `index_stale_hint` |

### 2.5 Empty State / Cold Start

| 時刻 | API 行為 | UI payload |
|------|----------|------------|
| 0 indexed | 200 EMPTY | `reason: NO_INDEXED_CONTACTS`；CTA 收錄 |
| 1–2 indexed | 200 COMPLETED 或 EMPTY | hint「再多收幾張更準」 |
| indexed ≥3，0 匹配 | 200 EMPTY | `reason: NO_MATCH`；换问法 + 範例 query |
| 首次 ≥1 结果 | 200 + `aha_moment: true` | Aha 动画（DDR-10） |

**Bootstrap**：`GET /search/status` 返回 `{ indexed_count, can_search, sample_queries[] }`。**MVP**：`sample_queries` 恒為 `[]`（DDR-71）；Pro P1 依索引名片填充，供個人化靈感 UI。

---

## 3. Blocker 決策

### B-7 — MVP 检索：**tsvector-only** ✅

| 方案 | MVP | P1 |
|------|-----|-----|
| tsvector + GIN | ✅ P0 | ✅ |
| pgvector cosine | ❌ | ✅ F-5.14 |
| 外部引擎（Elasticsearch） | ❌ | 不规划 |

**理由**：M3 已建 `search_vector`；Aha 路径不依赖 embedding；pgvector 需 embedding worker + 成本。P1 在 `ContactIndexed` 后异步写 `embedding`。

### B-13 — Rerank + match_reason Schema ✅

**Claude 输出 JSON Schema（strict）**：

```typescript
interface SearchRerankResponse {
  results: Array<{
    contact_id: string;       // UUID，必须 ∈ candidate set
    match_score: number;      // 0.0–1.0
    match_reason: string;     // ≤ 200 字，繁中
    match_sources: MatchSource[];
  }>;
  refinement_suggestions?: string[];  // P1，≤ 3 条
}

interface MatchSource {
  field:
    | 'company_products'
    | 'responsibility_scope'
    | 'title'
    | 'company_name'
    | 'source_label';
  value: string;
  confidence?: number;        // 0.0–1.0，推估字段必填
}
```

**服务端校验（DDR-53）**：
```typescript
function validateResult(item: RerankItem, candidate: CandidateDoc): boolean {
  for (const src of item.match_sources) {
    if (src.field === 'company_products' && (candidate.products_confidence ?? 0) < 0.5) return false;
    if (src.field === 'responsibility_scope' && (candidate.responsibility_confidence ?? 0) < 0.6) return false;
    if (!candidateHasField(candidate, src.field, src.value)) return false;
  }
  return item.match_sources.length >= 1;
}
```
校验失败 → 剔除该条或降级为 `title`/`company_name` 弱匹配理由。

**Prompt 要点**：
- System：B2B 商機匹配助手；禁止编造 index 中不存在的 products
- User：`query` + `candidates[]` 结构化 JSON（≤ 20 条）
- 低信心推估用「可能負責…（AI 推估 · n%）」措辞

### B-11 — Layer C 触发 ✅

| 触发 | MVP | P1 |
|------|-----|-----|
| 用户点「深入查詢」 | — | ✅ 强制 live |
| top1 match_score < **0.45** | — | response 带 `suggest_live: true` |
| query 含「最新\|最近\|現在」 | — | auto-suggest only，不 auto-run |
| cache products conf ≥ 0.7 | 不 live | 不 live |

**成本上限**：单次 query live augment ≤ **3 家公司**；Free 5 次/月（PM R-10）。

### B-14 — 中文检索 ✅

MVP 策略（延续 M3 ENG 风险登记）：
```sql
-- Primary
search_vector @@ websearch_to_tsquery('simple', :q)

-- Fallback when hits < 5
similarity(company_name, :keyword) > 0.3   -- pg_trgm
OR search_text ILIKE '%' || :keyword || '%'
```

`search_text` 已含中文公司名、产品、职称（M3 index worker）。Pilot 后评估 `zhparser` 或外部分词；**不阻塞 MVP**。

### B-12 — 多轮 Session ✅

MVP：**单轮**；DB 预留 `search_sessions` 表，API 不暴露。  
P1：`POST /search/sessions` + `POST /search/sessions/:id/turns`；rerank prompt 含前 2 turn 摘要（≤ 500 tokens）。

---

## 4. 資料模型

### 4.1 `search_sessions`（P1 启用；MVP migration 建空表）

```sql
CREATE TABLE search_sessions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL,
  workspace_id    UUID NOT NULL,
  status          VARCHAR(20) DEFAULT 'active',  -- active|closed
  turn_count      INT DEFAULT 0,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_search_sessions_user ON search_sessions(user_id, updated_at DESC);
```

### 4.2 `search_queries`

```sql
CREATE TABLE search_queries (
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id              UUID REFERENCES search_sessions(id),
  user_id                 UUID NOT NULL,
  workspace_id            UUID NOT NULL,
  query_text              TEXT NOT NULL,
  parsed_intent           JSONB,
  search_scope            VARCHAR(20) DEFAULT 'private',  -- MVP: private only
  retrieval_mode          VARCHAR(20) DEFAULT 'cache',   -- cache|cache+live
  live_augmentation_used  BOOLEAN DEFAULT FALSE,
  status                  VARCHAR(30) NOT NULL,
  -- SUBMITTED|PARSING_INTENT|RETRIEVING|RERANKING|LIVE_AUGMENTING|COMPLETED|EMPTY|FAILED
  result_count            INT DEFAULT 0,
  latency_ms              INT,
  degraded                BOOLEAN DEFAULT FALSE,         -- LLM fallback
  suggest_live            BOOLEAN DEFAULT FALSE,         -- P1
  error_code              VARCHAR(50),
  created_at              TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_search_queries_user_created ON search_queries(user_id, created_at DESC);
```

### 4.3 `search_results`

```sql
CREATE TABLE search_results (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  query_id        UUID NOT NULL REFERENCES search_queries(id) ON DELETE CASCADE,
  contact_id      UUID NOT NULL REFERENCES contacts(id),
  rank            INT NOT NULL,
  match_score     FLOAT NOT NULL,
  match_reason    TEXT NOT NULL,
  match_sources   JSONB NOT NULL DEFAULT '[]',
  live_products   JSONB,                    -- P1 Layer C merge
  source_pool     VARCHAR(30) DEFAULT 'private_rolodex',  -- Phase 3: public_directory
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (query_id, contact_id)
);
CREATE INDEX idx_search_results_query ON search_results(query_id, rank);
```

### 4.4 `query_augmentations`（M6 migration 已建；M5 写）

见 M6 SA/SD §3.6。M5 补充 index：

```sql
CREATE INDEX idx_query_augmentations_query ON query_augmentations(query_id);
```

### 4.5 `user_entitlements` 扩展（M5 quota）

```sql
ALTER TABLE user_entitlements ADD COLUMN IF NOT EXISTS
  search_cache_daily_quota      INT DEFAULT 30,
  search_cache_used_today       INT DEFAULT 0,
  search_cache_reset_at         TIMESTAMPTZ,
  live_augment_monthly_quota    INT DEFAULT 5,      -- Free; Pro: 50 Pilot
  live_augment_used_this_month  INT DEFAULT 0,
  live_augment_reset_at         TIMESTAMPTZ;
```

---

## 5. 检索实现（Layer A）

### 5.1 Candidate Query（核心 SQL）

```sql
WITH q AS (
  SELECT websearch_to_tsquery('simple', :search_string) AS tsq
)
SELECT
  csd.contact_id,
  c.display_name,
  c.company_name,
  c.title,
  c.responsibility_scope,
  c.responsibility_confidence,
  c.review_status,
  c.source_label,
  c.company_id,
  ts_rank_cd(csd.search_vector, q.tsq) AS retrieval_score,
  ce.main_products,
  ce.overall_confidence AS products_confidence,
  comp.last_enriched_at AS company_enriched_at
FROM contact_search_documents csd
CROSS JOIN q
JOIN contacts c ON c.id = csd.contact_id
  AND c.user_id = :user_id
  AND c.deleted_at IS NULL
LEFT JOIN companies comp ON comp.id = c.company_id
LEFT JOIN LATERAL (
  SELECT main_products, overall_confidence
  FROM company_enrichments
  WHERE company_id = comp.id
  ORDER BY enrich_version DESC
  LIMIT 1
) ce ON TRUE
WHERE csd.user_id = :user_id
  AND (
    csd.search_vector @@ q.tsq
    OR (:fallback_trgm AND similarity(c.company_name, :keyword) > 0.3)
  )
ORDER BY
  retrieval_score DESC,
  CASE WHEN c.review_status = 'confirmed' THEN 1.06 ELSE 1.0 END  -- DDR-56 approx
LIMIT 50;
```

### 5.2 Intent → search_string

```typescript
function buildSearchString(intent: ParsedIntent, rawQuery: string): string {
  const parts = [
    ...intent.products,
    ...intent.roles,
    ...intent.events,
    ...intent.keywords,
  ];
  return parts.length ? parts.join(' ') : rawQuery;
}
```

Intent parse：Claude Haiku 单 call（≤ 300ms target）或 P0 直接用 `rawQuery` 作 search_string（降级开关 `SEARCH_SKIP_INTENT_PARSE=true`）。

---

## 6. API 規格

**Base**：`/api/v1` · Bearer JWT（M1 stub：`X-User-Id`）

| Method | Path | 说明 | P | Idempotent |
|--------|------|------|---|------------|
| GET | `/search/status` | indexed_count + can_search | P0 | ✅ |
| POST | `/search/queries` | 执行搜尋（sync） | P0 | Optional Key |
| GET | `/search/queries/:id` | 查询结果 / 状态 | P0 | ✅ |
| POST | `/search/queries/:id/live-augment` | 触发 Layer C | P1 | ✅ |
| POST | `/search/queries/:id/adopt` | adopt live → M6 | P1 | ✅ |
| GET | `/search/queries` | 历史（分页） | P2 | ✅ |

### GET `/search/status`

```json
{
  "indexed_count": 12,
  "can_search": true,
  "min_recommended": 3,
  "sample_queries": [],
  "quotas": {
    "search_cache_remaining_today": 28,
    "live_augment_remaining_month": 5
  }
}
```

### POST `/search/queries`

**Request**：
```json
{
  "query_text": "我手上有誰做 IPC 的？",
  "search_scope": "private",
  "session_id": null
}
```

**Response 200 — COMPLETED**：
```json
{
  "query_id": "uuid",
  "status": "COMPLETED",
  "result_count": 3,
  "latency_ms": 1840,
  "degraded": false,
  "aha_moment": false,
  "suggest_live": false,
  "results": [{
    "contact_id": "uuid",
    "rank": 1,
    "match_score": 0.87,
    "match_reason": "公司主要產品包含工業電腦主機；職稱為 OEM 業務經理",
    "match_sources": [
      { "field": "company_products", "value": "工業電腦主機", "confidence": 0.82 },
      { "field": "title", "value": "OEM 業務經理" }
    ],
    "source_pool": "private_rolodex",
    "contact_preview": {
      "display_name": "王小明",
      "company_name": "ABC Tech",
      "title": "OEM 業務經理",
      "review_status": "unconfirmed",
      "phones": ["0912..."],
      "emails": ["ming@abc.com"]
    }
  }]
}
```

**Response 200 — EMPTY**：
```json
{
  "query_id": "uuid",
  "status": "EMPTY",
  "empty_state": {
    "reason": "NO_MATCH",
    "suggestions": ["試試『工業電腦』而非縮寫", "或先收錄更多名片"],
    "sample_queries": [],
    "cta": { "action": "capture", "label": "去收錄名片" }
  }
}
```

**Errors**：
| Code | HTTP | 条件 |
|------|------|------|
| `SEARCH_QUOTA_EXCEEDED` | 429 | cache daily quota |
| `SEARCH_SCOPE_NOT_ALLOWED` | 403 | scope ≠ private in MVP |
| `QUERY_TOO_LONG` | 400 | > 2000 chars |
| `SERVICE_UNAVAILABLE` | 503 | DB/LLM total failure |

### POST `/search/queries/:id/live-augment`（P1）

**Request**：
```json
{ "company_ids": ["uuid1", "uuid2"] }
```

**Response 202**：
```json
{
  "status": "LIVE_AUGMENTING",
  "job_ids": ["..."],
  "poll_url": "/search/queries/:id"
}
```

Worker 完成后 `GET /search/queries/:id` 的 results 含：
```json
"live_products": ["嵌入式系統", "Edge AI 盒"],
"match_reason": "...；本次查詢：公司產品包含嵌入式系統（即時查詢）"
```

### POST `/search/queries/:id/adopt`（P1）

**Request**：
```json
{
  "contact_id": "uuid",
  "query_augmentation_id": "uuid"
}
```

**Flow**：M5 标记 `adopted=true` → 调用 M6 `POST /companies/:id/enrich { trigger: "query_adopt", queryAugmentationId }` → 202。

### 跳转 M3 详情

`GET /contacts/:id?from_search=:query_id&rank=:n`  
M3 读 `search_results` 显示 Context Banner（M3 UIUX 已预留）。

---

## 7. Event 契約

### 7.1 `SearchCompleted`（M5 → M9）

```typescript
interface SearchCompleted {
  eventId: string;
  userId: string;
  queryId: string;
  resultCount: number;
  latencyMs: number;
  degraded: boolean;
  occurredAt: string;
}
```

### 7.2 `AhaMomentDetected`（M5 → M9）

```typescript
interface AhaMomentDetected {
  eventId: string;
  userId: string;
  queryId: string;
  firstResultContactId: string;
  occurredAt: string;
}
```

**Emit 条件**：
```typescript
const isFirstSearchWithResults =
  !(await searchRepo.hasPriorCompletedQuery(userId)) && resultCount >= 1;
```

### 7.3 Consumer（M5 不消费 M3 index event）

M5 **不**订阅 `ContactIndexed`；依赖 DB 读最新 index（pull model）。P1 可选 cache invalidation 无必要。

---

## 8. Layer C — Live Augment Worker（P1）

```typescript
async function processSearchLiveAugment(job: {
  queryId: string;
  userId: string;
  companyId: string;
}) {
  // Reuse M6 EnrichmentPipeline.fetchAndExtract(companyId)
  const extracted = await enrichmentPipeline.queryTimeExtract(job.companyId);

  await db.queryAugmentation.create({
    data: {
      user_id: job.userId,
      company_id: job.companyId,
      query_id: job.queryId,
      live_products: extracted.main_products,
      source_urls: extracted.source_urls,
      confidence: extracted.overall_confidence,
    },
  });

  await entitlementService.increment(job.userId, 'live_augment');
  // Merge into search_results for matching contact_ids under that company
}
```

**DDR-36**：不写 `company_enrichments`；仅 `query_augmentations`。

---

## 9. M3 / M6 整合契約

### 9.1 M3 Index Read Contract

M5 只读 `contact_search_documents` + JOIN `contacts`：

```typescript
// M3 IndexService.buildDocument 产出 → search_text 必含：
interface IndexDocumentFields {
  display_name: string;
  company_name: string;
  title?: string;
  responsibility_scope?: string;
  source_label?: string;
  company_products?: string[];   // M6 enrich 后
  review_status: 'unconfirmed' | 'confirmed';
}
```

**M3 责任**：Contact 变更 / CompanyEnriched / inference 后 **30s 内** index 更新（M3 SLA）。

### 9.2 M6 Products in Search

| 字段 | 来源 | 检索权重 |
|------|------|----------|
| `company_products` | latest enrichment | 高（search_text + rerank） |
| `products_confidence` | enrichment | ≥0.5 才可作 match_source |
| `company_enriched_at` | companies | P1 stale hint |

### 9.3 M6 query_adopt

```
M5 POST /search/queries/:id/adopt
  → M6 POST /companies/:id/enrich
       { "trigger": "query_adopt", "queryAugmentationId": "..." }
  → M6 append enrichment trigger_type=query_adopt
  → CompanyEnriched → M3 re-index
```

---

## 10. Phase 3 预留（Pool B · 不阻塞 MVP）

| 项目 | MVP | Phase 3 |
|------|-----|---------|
| `search_scope` | `private` only | `network` \| `all` |
| Index 表 | `contact_search_documents` | + `public_directory_documents`（M11） |
| `source_pool` | `private_rolodex` | + `public_directory` |
| Auth | `user_id` filter | + `plan_tier` pro/enterprise 可 `search_scope=network|all` |

API 若收到 `search_scope=network` → **403 `SEARCH_SCOPE_NOT_ALLOWED`**（MVP）。

---

## 11. 🔗 Coupling Map 更新

### Shared Entities（M5 新增）

| Entity | Owner | Consumers | Contract |
|--------|-------|-----------|----------|
| `search_sessions` | M5 | M5 | id, user_id, status |
| `search_queries` | M5 | M9 | query_text, status, parsed_intent |
| `search_results` | M5 | M3 UI, M8 | match_reason, match_sources, contact_id |
| `query_augmentations` | M5 | M6 adopt | live_products, adopted, query_id |
| `contact_search_documents` | M3 | **M5** | search_vector, search_text |

### Cross-module Contracts（M5 新增）

| From | To | Event/API | Trigger | Sync/Async |
|------|-----|-----------|---------|------------|
| M3 | M5 | index read | contact-index done | Pull DB |
| M5 | M3 | GET contact + search context | user click result | Sync |
| M5 | M6 | query_adopt enrich | user adopt | Async |
| M6 | M5 | products in index | CompanyEnriched → re-index | Async |
| M5 | M8 | contact_preview phones/emails | result card | Sync DTO |
| M5 | M9 | SearchCompleted, AhaMoment | search done | Async |
| M1 | M5 | entitlements | every search / live | Sync |

### Cross-cutting Concerns

| Concern | M5 实现 |
|---------|---------|
| Auth | 所有 API `user_id = JWT.sub`；结果 contact 必须 owned |
| Tenant | `workspace_id` on queries（MVP 单 workspace） |
| Quota | EntitlementService；cache 429 / live 403 |
| Audit | `search_queries` + `search_results` 保留 90 天 |
| Privacy | Pool A only；不 log 完整 query 到第三方（Claude 企业 API） |
| Feature flags | `SEARCH_DEGRADED_MODE`, `SEARCH_LIVE_ENABLED` |

---

## 12. DDR 新增（SA/SD）

| ID | 决策 | 理由 |
|----|------|------|
| DDR-63 | MVP 检索 = tsvector + pg_trgm fallback；pgvector P1 | 解 B-7；复用 M3 index |
| DDR-64 | Layer A+B 同步 API；Layer C 异步 worker | P95 < 3s vs live 30s |
| DDR-65 | Rerank 输出 strict JSON + 服务端 field 校验 | 解 B-13；防幻觉 |
| DDR-66 | Intent parse 可跳过（feature flag）；rawQuery 直搜 | 降级保可用 |
| DDR-67 | confirmed boost ×1.06 在 SQL ORDER BY | DDR-56 实现 |
| DDR-68 | search_results 保留 90 天；session P1 | 分析 + 多轮 |
| DDR-69 | MVP reject `search_scope != private` | Phase 3 Pool B |
| DDR-70 | Live augment ≤3 companies/query | 解 B-11 成本 |
| DDR-71 | MVP 不顯示通用靈感 chips；Pro 個人化建議依索引名片推導 | 見 PRD v2 §4 / §11.2 |
| DDR-72 | `indexed_count` = Pool A 可搜尋且未刪除；UI「X 位可搜尋」；Pool B 另列不共用「已索引」 | 見 PRD v2 |
| DDR-73 | Intent 解析多維度條件（非僅職稱）；hard constraint 跨欄位；rerank 後過濾；NO_MATCH 優於部分符合 | 見 PRD v2 §4 |

### Intent 維度（DDR-73）

| 使用者可能問法 | 解析維度 | 索引/欄位來源 |
|----------------|----------|----------------|
| AWS 人脈 / 亞馬遜 | 公司/生態 | `company_name`、必要時 products |
| 做雲端 / 工控 | 產業/產品 | M6 `company_products`、`responsibility_scope` |
| Computex 認識的 | 場合 | `source_label` |
| 架構師 / 窗口 / PM | 職能 | `title`、`responsibility_scope` |

**Hard constraint 範例**：「AWS 人脈中找架構師就好」→ 須同時滿足 AWS 相關 **且** 職能含架構師證據；僅 AWS 但職稱 PM → **排除**。

---

## 13. Open Blockers（残留 🚧）

| 🚧 | 议题 | 状态 | 备注 |
|----|------|------|------|
| B-7 | tsvector vs pgvector | **✅ MVP tsvector-only** | pgvector P1 |
| B-11 | Layer C 阈值 | **✅ 设计完成** | suggest 0.45；manual trigger |
| B-12 | 多轮 session | **✅ MVP 单轮** | 表预留 P1 |
| B-13 | rerank schema | **✅ JSON schema 锁定** | §3 Blocker |
| B-14 | 中文分词 | **✅ MVP pg_trgm fallback** | Pilot 评估 zhparser |
| B-15 | Claude query 日志留存策略 | 🚧 | ENG + 法务；不阻塞 MVP |
| B-16 | Pro live/search quota 具体数字 | 🚧 | Pilot 定 |

---

## 14. L4 Depth Gate 自检

| Gate | 状态 |
|------|------|
| Data flow | ✅ |
| State boundaries | ✅ |
| Concurrency | ✅ |
| Failure modes | ✅ |
| Empty state | ✅ |
| Coupling Map | ✅ |

**M5 SA/SD L4：✅ 可锁定**

---

### 🤝 Handoff: SA/SD → UI/UX — Module 5：AI 搜尋

**State Tracker snapshot**：
| 模組 | PM | SA/SD | UI/UX | ENG | QA |
|------|:--:|:-----:|:-----:|:---:|:--:|
| M5 | ✅ v1.1 | ✅ v1.0 | ⏳ | ⏳ | ⏳ |

**Per-Module Depth Spec**：见本文 §2 L4 Depth Gate

**Coupling Map updates**：`search_queries`, `search_results`, `query_augmentations`；读 `contact_search_documents`

**API contracts UI must wire**：
- `GET /search/status` — Tab 空状态 / 範例 query
- `POST /search/queries` — 对话输入 + typing indicator
- `GET /search/queries/:id` — 结果列表 + match_reason 区块
- P1：`live-augment` suggest banner、`adopt` flow

**Error scenarios UI/UX must cover**：
- EMPTY：`NO_INDEXED_CONTACTS` vs `NO_MATCH` 不同 CTA
- `degraded: true` — 小字「简化排序模式」
- 429 cache quota / 403 live quota + Pro CTA
- `index_stale_hint` — 「部分新名片同步中」
- pending_review badge on result card
- Privacy Strip 常显（Design Foundation §6.5）

**Empty states UI/UX must design**：
- 0 indexed → 收錄引导
- 1–2 indexed → 「再多收幾張」
- 0 match → 换问法 + 範例
- Aha modal（`aha_moment: true`）

**Result card 必含**：
- display_name, company_name, title
- match_reason（主视觉）
- M8 copy phone/email CTA
- → 详情带 context banner

**Open blockers（🚧）**：B-15 日志策略、B-16 Pro 配额数字（不阻塞 UI/UX）

---

*SA/SD M5 v1.0 — SDLC Phase 1*
