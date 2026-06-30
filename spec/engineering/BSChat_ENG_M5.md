# BSChat ENG — Module 5：AI 搜尋（對話式找商機）

> **依據**：M5 PM L3 v1.1、M5 SA/SD v1.0、M5 UI/UX v1.0、`BSChat_ENG_M3.md`、`BSChat_ENG_M6.md`  
> **團隊**：2 人（1 full-stack + 1 product/design）  
> **M5 估算**：~4–6 工程日（1 人 full-stack）  
> **前置**：M3-009 contact-index worker · M3 contact_search_documents · M6 company_products in index · M1-Minimal entitlement

---

## 1. 技術選型（M5 增量）

延續 M2/M3/M6 栈，M5 新增：

| 層級 | 選型 | 用途 |
|------|------|------|
| **Retrieval** | PostgreSQL `tsvector` + GIN + `pg_trgm` | Layer A 召回（DDR-63） |
| **Intent / Rerank** | Claude Haiku（intent）+ Sonnet（rerank） | 结构化 JSON 输出 |
| **JSON 校验** | Zod `SearchRerankResponseSchema` | DDR-65 服务端校验 |
| **ORM Raw SQL** | Prisma `$queryRaw` | ts_rank + trgm fallback |
| **State** | TanStack Query v5 | status / search mutation |
| **Clipboard** | `navigator.clipboard` + fallback | M8 copy on ResultCard |
| **Async Live（P1）** | BullMQ `search-live-augment` | Layer C worker |

### 環境變數（M5 新增）

```bash
SEARCH_INTENT_MODEL=claude-haiku-4-20250514
SEARCH_RERANK_MODEL=claude-sonnet-4-20250514
SEARCH_PROMPT_VERSION=v1
SEARCH_SKIP_INTENT_PARSE=false          # DDR-66 降级开关
SEARCH_RETRIEVAL_LIMIT=50
SEARCH_RESULT_LIMIT=10
SEARCH_CONFIRMED_BOOST=1.06             # DDR-67
SEARCH_SUGGEST_LIVE_THRESHOLD=0.45      # P1
SEARCH_CACHE_DAILY_QUOTA_FREE=30
SEARCH_LIVE_MONTHLY_QUOTA_FREE=5
SEARCH_LIVE_MAX_COMPANIES_PER_QUERY=3   # DDR-70
SEARCH_QUERY_MAX_LENGTH=2000
SEARCH_RESULTS_RETENTION_DAYS=90
# P1
SEARCH_LIVE_ENABLED=false
# DDR-101 统一漏斗（全用户同一常数）
SEARCH_RETRIEVAL_TOP_K=50
SEARCH_RERANK_INPUT_MAX=60
```

### 1.1 检索契约与两种分数（DDR-101 · 对齐 SA/SD M5 §2.6）

**Pipeline（禁止按 `indexed_count` 分支）**：

1. `parse_intent` → `ParsedIntent`（含 P1 `semantic_query` 供 embedding）
2. `hybrid_retrieve(pool, intent, K=SEARCH_RETRIEVAL_TOP_K)` → `CandidateDoc[]` + `retrieval_score`
3. 跨池合并 cap `SEARCH_RERANK_INPUT_MAX`
4. `rerank(query, candidates, search_precision)` → `RerankItem[]` + `match_score`
5. `filter_rerank_results`：**仅** hard constraint + id 校验；**删除** `match_score < min` 分支
6. `validate_rerank_item` → persist `search_results.match_score`

| 分数 | Python 字段 | 持久化 | 允许 | 禁止 |
|------|-------------|--------|------|------|
| `retrieval_score` | `CandidateDoc.retrieval_score` | 否（可选 query debug） | 召回 ORDER BY；RRF 合并 | EMPTY gate；`effective_min_match_score` |
| `match_score` | `RerankItem.match_score` → DB | `search_results.match_score` | 排序；API 响应；UI；`suggest_live` 阈值 | `filter_rerank_results` 硬过滤 |

**废止模块逻辑**（实作迁移时删除）：`semantic_rescue` 整池 bypass、`is_weak_literal_recall`、`PRECISION_THRESHOLDS` / `effective_min_match_score`。

**`search_precision`**：传入 `RERANK_PROMPT` 模板变量，不传 `min_match_score` 参数。

---

## 2. Monorepo 增量結構

```
apps/web/
├── app/
│   ├── (tabs)/search/
│   │   └── page.tsx                         # SearchPage
│   └── api/v1/search/
│       ├── status/route.ts                  # GET
│       ├── queries/
│       │   ├── route.ts                     # POST, GET list P2
│       │   └── [id]/
│       │       ├── route.ts                 # GET
│       │       ├── live-augment/route.ts    # POST P1
│       │       └── adopt/route.ts           # POST P1
├── components/search/
│   ├── SearchInput.tsx
│   ├── QueryBubble.tsx
│   ├── AssistantBubble.tsx
│   ├── SearchResultCard.tsx
│   ├── SearchEmptyState.tsx
│   ├── AhaMomentModal.tsx
│   ├── SearchQuotaBanner.tsx
│   └── LiveAugmentBanner.tsx                # P1
├── components/contacts/
│   └── SearchContextBanner.tsx              # M3 详情顶
└── hooks/
    ├── useSearchStatus.ts
    ├── useSearch.ts
    └── useCopyContact.ts                    # M8 stub

apps/worker/jobs/
├── search-live-augment.job.ts               # P1 Layer C

packages/shared/
├── schemas/search.ts                        # Zod request/response
├── search/
│   ├── intent-parse.prompt.ts
│   ├── rerank-explain.prompt.ts
│   ├── build-search-string.ts
│   └── validate-rerank-result.ts
└── services/
    ├── search.service.ts                    # orchestrator
    ├── search-retrieval.service.ts
    ├── search-rerank.service.ts
    ├── search-intent.service.ts
    └── search-status.service.ts
```

**Queue 命名（P1）**：

| Queue | Producer | Consumer |
|-------|----------|----------|
| `search-live-augment` | POST live-augment | `search-live-augment.job` |

---

## 3. 前端架構

### 3.1 路由

| Path | 畫面 | 優先 |
|------|------|------|
| `/search` | 搜尋 Tab 主頁 | P0 |
| `/contacts/[id]?from_search=&rank=` | 詳情 + Context Banner | P0 |

### 3.2 SearchPage 状态机

```typescript
type SearchUiState =
  | { phase: 'idle'; status: SearchStatusResponse }
  | { phase: 'loading'; queryText: string }
  | { phase: 'results'; data: SearchQueryResponse }
  | { phase: 'empty'; data: SearchQueryResponse }
  | { phase: 'error'; code: string; queryText: string };
```

```typescript
// app/(tabs)/search/page.tsx
export default function SearchPage() {
  const { data: status } = useSearchStatus();
  const search = useSearch();
  const [lastQuery, setLastQuery] = useState('');

  const handleSubmit = async (queryText: string) => {
    setLastQuery(queryText);
    const result = await search.mutateAsync({ query_text: queryText });
    if (result.aha_moment) showAhaOnce();
  };

  return (
    <>
      <PrivacyStrip />
      <SearchInput
        disabled={search.isPending || status?.quotas.search_cache_remaining_today === 0}
        onSubmit={handleSubmit}
      />
      {search.isPending && <SearchLoading queryText={lastQuery} />}
      {search.data?.status === 'COMPLETED' && (
        <SearchResultsList results={search.data.results} queryId={search.data.query_id} />
      )}
      {search.data?.status === 'EMPTY' && (
        <SearchEmptyState {...search.data.empty_state} onRetry={handleSubmit} />
      )}
      <AhaMomentModal />
    </>
  );
}
```

### 3.3 Tab 默认逻辑（Design Foundation §2.2）

```typescript
// apps/web/lib/default-tab.ts — 扩展
export function resolveDefaultTab(ctx: {
  indexedCount: number;
  hasSearched: boolean;
  pendingReview: number;
}): TabId {
  if (ctx.indexedCount === 0) return 'capture';
  if (ctx.indexedCount >= 3 && !ctx.hasSearched) return 'search';
  if (ctx.pendingReview > 0) return 'review'; // 不阻挡 search
  return 'search';
}
```

`hasSearched`：`localStorage` 或 GET `/search/queries?limit=1`。

### 3.4 SearchResultCard → M3 详情

```typescript
router.push(
  `/contacts/${contactId}?from_search=${queryId}&rank=${rank}`
);
```

### 3.5 M8 Copy（P0 stub）

```typescript
// hooks/useCopyContact.ts
export function useCopyContact() {
  return useMutation({
    mutationFn: async (text: string) => {
      await navigator.clipboard.writeText(text);
    },
    onSuccess: () => toast.success('已複製'),
  });
}
```

### 3.6 Aha Moment 一次性

```typescript
const AHA_KEY = 'bschat_aha_dismissed';
export function showAhaOnce() {
  if (localStorage.getItem(AHA_KEY)) return;
  setAhaOpen(true);
}
```

### 3.7 桌面 Split（P0 基础 / P2 polish）

```tsx
<div className="lg:grid lg:grid-cols-[1fr_420px] lg:gap-6">
  <SearchConversationPanel />
  <SearchResultsPanel className="lg:sticky lg:top-4 lg:max-h-[calc(100vh-8rem)] lg:overflow-y-auto" />
</div>
```

---

## 4. 資料模型（Prisma）

```prisma
model SearchSession {
  id           String   @id @default(uuid())
  userId       String   @map("user_id")
  workspaceId  String   @map("workspace_id")
  status       String   @default("active")
  turnCount    Int      @default(0) @map("turn_count")
  createdAt    DateTime @default(now()) @map("created_at")
  updatedAt    DateTime @updatedAt @map("updated_at")
  queries      SearchQuery[]

  @@index([userId, updatedAt(sort: Desc)])
  @@map("search_sessions")
}

model SearchQuery {
  id                    String   @id @default(uuid())
  sessionId             String?  @map("session_id")
  session               SearchSession? @relation(fields: [sessionId], references: [id])
  userId                String   @map("user_id")
  workspaceId           String   @map("workspace_id")
  queryText             String   @map("query_text")
  parsedIntent          Json?    @map("parsed_intent")
  searchScope           String   @default("private") @map("search_scope")
  retrievalMode         String   @default("cache") @map("retrieval_mode")
  liveAugmentationUsed  Boolean  @default(false) @map("live_augmentation_used")
  status                String
  resultCount           Int      @default(0) @map("result_count")
  latencyMs             Int?     @map("latency_ms")
  degraded              Boolean  @default(false)
  suggestLive           Boolean  @default(false) @map("suggest_live")
  errorCode             String?  @map("error_code")
  createdAt             DateTime @default(now()) @map("created_at")
  results               SearchResult[]

  @@index([userId, createdAt(sort: Desc)])
  @@map("search_queries")
}

model SearchResult {
  id            String   @id @default(uuid())
  queryId       String   @map("query_id")
  query         SearchQuery @relation(fields: [queryId], references: [id], onDelete: Cascade)
  contactId     String   @map("contact_id")
  rank          Int
  matchScore    Float    @map("match_score")
  matchReason   String   @map("match_reason")
  matchSources  Json     @default("[]") @map("match_sources")
  liveProducts  Json?    @map("live_products")
  sourcePool    String   @default("private_rolodex") @map("source_pool")
  createdAt     DateTime @default(now()) @map("created_at")

  @@unique([queryId, contactId])
  @@index([queryId, rank])
  @@map("search_results")
}
```

**user_entitlements 扩展**（migration）：

```sql
ALTER TABLE user_entitlements ADD COLUMN IF NOT EXISTS
  search_cache_daily_quota INT DEFAULT 30,
  search_cache_used_today INT DEFAULT 0,
  search_cache_reset_at TIMESTAMPTZ,
  live_augment_monthly_quota INT DEFAULT 5,
  live_augment_used_this_month INT DEFAULT 0,
  live_augment_reset_at TIMESTAMPTZ;
```

`query_augmentations` 已由 M6 migration 建立；M5 补 index `idx_query_augmentations_query`。

---

## 5. API 實作

### 5.1 GET `/api/v1/search/status`

```typescript
export async function GET(req: Request) {
  const userId = requireUserId(req);
  const indexedCount = await db.contactSearchDocument.count({ where: { userId } });
  await entitlementService.resetDailyIfNeeded(userId, 'search_cache');

  return json({
    indexed_count: indexedCount,
    can_search: indexedCount > 0,
    min_recommended: 3,
    sample_queries: pickSampleQueries(userId), // MVP: always []; Pro P1: personalized from index (DDR-71)
    quotas: await entitlementService.getSearchQuotas(userId),
  });
}
```

### 5.2 POST `/api/v1/search/queries`

```typescript
const CreateSearchQuerySchema = z.object({
  query_text: z.string().min(1).max(2000),
  search_scope: z.enum(['private']).default('private'), // MVP DDR-69
  session_id: z.string().uuid().optional(),
});

export async function POST(req: Request) {
  const userId = requireUserId(req);
  const body = CreateSearchQuerySchema.parse(await req.json());

  if (body.search_scope !== 'private') {
    throw apiError(403, 'SEARCH_SCOPE_NOT_ALLOWED');
  }

  await entitlementService.checkAndIncrement(userId, 'search_cache');

  const started = Date.now();
  const query = await db.searchQuery.create({
    data: { userId, workspaceId, queryText: body.query_text, status: 'SUBMITTED', ... },
  });

  try {
    const intent = await searchIntentService.parse(body.query_text);
    const candidates = await searchRetrievalService.retrieve(userId, intent, body.query_text);

    if (candidates.length === 0) {
      return finalizeEmpty(query, userId, indexedCount, started);
    }

    const { results, degraded, refinementSuggestions } =
      await searchRerankService.rerank(body.query_text, intent, candidates);

    const ahaMoment = await searchService.detectAha(userId, results.length);
    const suggestLive = results[0]?.match_score < SUGGEST_LIVE_THRESHOLD;

    await searchService.persistResults(query.id, results);
    // ... update query COMPLETED, return response
  } catch (e) {
    await db.searchQuery.update({ where: { id: query.id }, data: { status: 'FAILED', ... } });
    throw e;
  }
}
```

### 5.3 GET `/api/v1/search/queries/:id`

Ownership check + join contact preview for each result.

### 5.4 POST live-augment / adopt（P1）

见 M5 SA/SD §6、§5.4；`SEARCH_LIVE_ENABLED=true` feature flag。

---

## 6. Search Pipeline（BE 核心）

### 6.1 Intent Parse

```typescript
// packages/shared/search/intent-parse.prompt.ts
export const ParsedIntentSchema = z.object({
  products: z.array(z.string()).default([]),
  roles: z.array(z.string()).default([]),
  events: z.array(z.string()).default([]),
  regions: z.array(z.string()).default([]),
  keywords: z.array(z.string()).default([]),
});

export async function parseIntent(queryText: string): Promise<ParsedIntent> {
  if (process.env.SEARCH_SKIP_INTENT_PARSE === 'true') {
    return { products: [], roles: [], events: [], regions: [], keywords: [] };
  }
  const raw = await claude.messages.create({
    model: process.env.SEARCH_INTENT_MODEL!,
    max_tokens: 256,
    messages: [{ role: 'user', content: buildIntentPrompt(queryText) }],
  });
  return ParsedIntentSchema.parse(JSON.parse(extractJson(raw)));
}
```

### 6.2 Retrieval（tsvector + trgm）

```typescript
// packages/shared/services/search-retrieval.service.ts
export async function retrieve(userId: string, intent: ParsedIntent, rawQuery: string) {
  const searchString = buildSearchString(intent, rawQuery);

  let rows = await prisma.$queryRaw<CandidateRow[]>`
    SELECT ... ts_rank_cd(...) AS retrieval_score
    FROM contact_search_documents csd
    ...
    WHERE csd.user_id = ${userId}::uuid
      AND csd.search_vector @@ websearch_to_tsquery('simple', ${searchString})
    ORDER BY retrieval_score DESC
    LIMIT ${RETRIEVAL_LIMIT}
  `;

  if (rows.length < 5) {
    const keyword = intent.products[0] ?? rawQuery.slice(0, 32);
    rows = await prisma.$queryRaw`... pg_trgm similarity fallback ...`;
  }

  return rows.map(applyConfirmedBoost);
}
```

### 6.3 Rerank + Validate

```typescript
// packages/shared/search/validate-rerank-result.ts
export function validateRerankItem(item: RerankItem, candidate: CandidateDoc): boolean {
  if (!candidates.has(item.contact_id)) return false;
  for (const src of item.match_sources) {
    if (src.field === 'company_products' && (candidate.products_confidence ?? 0) < 0.5) return false;
    if (src.field === 'responsibility_scope' && (candidate.responsibility_confidence ?? 0) < 0.6) return false;
    if (!fieldMatches(candidate, src)) return false;
  }
  return item.match_sources.length >= 1;
}
```

**LLM 失败降级**：

```typescript
catch (err) {
  return {
    results: candidates.slice(0, 10).map((c, i) => ({
      contact_id: c.contact_id,
      rank: i + 1,
      match_score: c.retrieval_score,
      match_reason: buildFallbackReason(c),
      match_sources: [{ field: 'company_name', value: c.company_name }],
    })),
    degraded: true,
  };
}
```

### 6.4 Empty State Builder

```typescript
function buildEmptyState(userId: string, indexedCount: number): EmptyState {
  if (indexedCount === 0) {
    return { reason: 'NO_INDEXED_CONTACTS', cta: { action: 'capture', label: '開始收錄' }, ... };
  }
  if (indexedCount < 3) {
    return { reason: 'LOW_INDEX_COUNT', ... };
  }
  return { reason: 'NO_MATCH', sample_queries: [], ... }; // MVP DDR-71
}
```

### 6.5 Aha Detection

```typescript
async function detectAha(userId: string, resultCount: number): Promise<boolean> {
  if (resultCount < 1) return false;
  const prior = await db.searchQuery.count({
    where: { userId, status: 'COMPLETED', resultCount: { gt: 0 } },
  });
  return prior === 0;
}
```

### 6.6 P1 Live Augment Worker

```typescript
// apps/worker/jobs/search-live-augment.job.ts
export async function processSearchLiveAugment(job: Job<LiveAugmentPayload>) {
  const extracted = await enrichmentPipeline.queryTimeExtract(job.data.companyId);
  await db.queryAugmentation.create({ data: { ... } });
  await searchService.mergeLiveProducts(job.data.queryId, job.data.companyId, extracted);
  await entitlementService.increment(job.data.userId, 'live_augment');
}
```

复用 M6 `page-fetcher` + `extract-products.prompt`；**不写** `company_enrichments`（DDR-36）。

---

## 7. EntitlementService 扩展

```typescript
type SearchQuotaAction = 'search_cache' | 'live_augment';

async checkAndIncrement(userId: string, action: SearchQuotaAction) {
  const ent = await this.getOrCreate(userId);
  if (action === 'search_cache') {
    await this.resetDailyIfNeeded(userId, action);
    if (ent.searchCacheUsedToday >= ent.searchCacheDailyQuota) {
      throw apiError(429, 'SEARCH_QUOTA_EXCEEDED');
    }
    await db.userEntitlements.update({
      where: { userId },
      data: { searchCacheUsedToday: { increment: 1 } },
    });
  }
  // live_augment: monthly reset, 403 LIVE_QUOTA_EXCEEDED
}
```

MVP Pro 数字与 Free 相同（B-16 Pilot）；字段预留。

---

## 8. M3 整合 — SearchContextBanner

```typescript
// app/contacts/[id]/page.tsx
const fromSearch = searchParams.get('from_search');
const { data: searchContext } = useSearchResultContext(fromSearch, contactId);

{fromSearch && searchContext && (
  <SearchContextBanner
    matchReason={searchContext.match_reason}
    matchSources={searchContext.match_sources}
    onBack={() => router.push('/search')}
  />
)}
```

```typescript
// GET handler 或 client fetch：search_results by query_id + contact_id
```

---

## 9. Zod Schemas（packages/shared/schemas/search.ts）

```typescript
export const MatchSourceSchema = z.object({
  field: z.enum(['company_products', 'responsibility_scope', 'title', 'company_name', 'source_label']),
  value: z.string(),
  confidence: z.number().min(0).max(1).optional(),
});

export const SearchResultItemSchema = z.object({
  contact_id: z.string().uuid(),
  rank: z.number().int().positive(),
  match_score: z.number().min(0).max(1),
  match_reason: z.string().max(200),
  match_sources: z.array(MatchSourceSchema).min(1),
  source_pool: z.literal('private_rolodex').default('private_rolodex'),
  contact_preview: z.object({
    display_name: z.string(),
    company_name: z.string(),
    title: z.string().nullable(),
    review_status: z.enum(['unconfirmed', 'confirmed']),
    phones: z.array(z.string()),
    emails: z.array(z.string()),
    image_url: z.string().nullable().optional(),
  }),
});
```

---

## 10. Sprint Ticket 清單

### M5-A P0 核心（3–4 天）

| ID | Ticket | FE | BE | 估時 |
|----|--------|----|-----|------|
| M5-001 | Prisma search models + entitlement columns migration | — | ✓ | 0.5d |
| M5-002 | Zod schemas + prompt templates | — | ✓ | 0.25d |
| M5-003 | search-retrieval.service（tsvector + trgm） | — | ✓ | 0.75d |
| M5-004 | search-intent.service | — | ✓ | 0.25d |
| M5-005 | search-rerank.service + validate + fallback | — | ✓ | 0.75d |
| M5-006 | search.service orchestrator + persist + aha | — | ✓ | 0.5d |
| M5-007 | GET /search/status | — | ✓ | 0.25d |
| M5-008 | POST /search/queries + GET /:id | — | ✓ | 0.5d |
| M5-009 | entitlement search quota | — | ✓ | 0.25d |
| M5-010 | SearchPage + SearchInput + loading | ✓ | — | 0.75d |
| M5-011 | SearchResultCard + results list | ✓ | — | 0.75d |
| M5-012 | SearchEmptyState（3 reason） | ✓ | — | 0.5d |
| M5-013 | AhaMomentModal | ✓ | — | 0.25d |
| M5-014 | SearchContextBanner + contact route params | ✓ | ✓ | 0.5d |
| M5-015 | useCopyContact on ResultCard（M8） | ✓ | — | 0.25d |
| M5-016 | default-tab 逻辑 + invalidate on capture | ✓ | — | 0.25d |

### M5-B P1 扩展（1–2 天）

| ID | Ticket | 估時 |
|----|--------|------|
| M5-017 | search-live-augment worker + API | 0.75d |
| M5-018 | LiveAugmentBanner + adopt flow UI | 0.5d |
| M5-019 | POST adopt → M6 query_adopt | 0.5d |
| M5-020 | refinement_suggestions chips | 0.25d |
| M5-021 | search_sessions + multi-turn API | 0.75d |
| M5-022 | SearchQuotaBanner 429/403 | 0.25d |
| M5-023 | Vitest: retrieval mock + validate-rerank | 0.5d |
| M5-024 | Playwright: search happy path + empty | 0.5d |

### 依赖图

```
M5-001 → M5-003 → M5-005 → M5-006 → M5-008
M5-002 ────────────────┘
M5-004 ─────────────────┘
M5-009 → M5-007, M5-008
M5-010 → M5-011 → M5-012, M5-013
M5-014（依赖 M3 详情页）
M5-015
M3-009 contact-index（前置：indexed docs 存在）
M6-013 company_products in index（前置： enrich 后 search_text 含 products）
```

**建议垂直切片顺序**：
1. M5-001~009 → API E2E（curl / Vitest）
2. M5-010~013 → 搜尋 Tab 可见
3. M5-014~016 → 详情 context + Tab 逻辑
4. M5-017~022 → P1 live + quota UI

---

## 11. Definition of Done — M5

### P0

- [ ] `GET /search/status` 返回 indexed_count；MVP `sample_queries=[]`（DDR-71）
- [ ] `POST /search/queries` 同步返回 COMPLETED + match_reason
- [ ] 0 indexed → EMPTY `NO_INDEXED_CONTACTS`
- [ ] 有 index 无匹配 → EMPTY `NO_MATCH`
- [ ] pending_review 联系人可出现在结果
- [ ] match_sources 校验：低 confidence 不引用 products/inference
- [ ] LLM 失败 → degraded + tsvector fallback 仍有结果
- [ ] 首次有结果 → `aha_moment: true`
- [ ] ResultCard 复制 phone/email Toast
- [ ] 详情 from_search 显示 SearchContextBanner
- [ ] `search_scope != private` → 403
- [ ] cache daily quota 429
- [ ] 跨用户 query/result → 404
- [ ] P95 cache search < 3s（本地 20 contacts seed）

### P1

- [ ] live-augment worker + quota 403
- [ ] adopt → M6 query_adopt 接通
- [ ] suggest_live when top1 < 0.45
- [ ] refinement_suggestions UI
- [ ] SEARCH_LIVE_ENABLED flag

---

## 12. 測試要点（供 QA）

| 区域 | 关键断言 |
|------|---------|
| Status | 0 indexed → can_search false |
| Retrieve | company_products in search_text → query「工業電腦」命中 |
| Rerank | mock LLM 返回 hallucinated field → 条目被剔除 |
| Confidence | products conf 0.4 → match_sources 无 company_products |
| Inference | resp conf 0.55 → 理由不含 responsibility_scope |
| Empty | NO_MATCH vs NO_INDEXED 不同 payload |
| Aha | 第二次 search 不返回 aha_moment |
| Quota | 第 31 次 search → 429 |
| Scope | search_scope=network → 403 |
| Banner | from_search param → ContextBanner visible |
| Delete | contact deleted → 不再出现在 search |
| Degraded | LLM throw → degraded true + results.length > 0 |

---

## 13. 風險

| 風險 | 緩解 |
|------|------|
| M3 index 延迟 | status caption；不 promise 即时 |
| 中文 tsvector 弱 | pg_trgm fallback（B-14） |
| LLM 延迟 > 3s | Haiku intent + Sonnet top-20 only；超时降级 |
| 0 enrich 时 match 弱 | title/company_name 弱匹配 + empty 引导 |
| Claude query 隐私（B-15） | 企业 API；不 log full query 到第三方 analytics |
| M6 未 enrich | 仍可用 title/company 搜；理由简化 |

---

## 14. 模組接口

| 模块 | 接口 | M5 角色 |
|------|------|---------|
| M3 | contact_search_documents | consumer（read） |
| M3 | GET /contacts/:id | consumer（preview + banner） |
| M6 | company_products via index | consumer（read） |
| M6 | POST enrich query_adopt | producer（P1 adopt） |
| M8 | copy actions | FE stub P0 |
| M1 | user_entitlements | consumer |
| M9 | SearchCompleted, AhaMoment | producer（event stub） |
| M2 | capture complete | invalidate search/status |

---

## 15. Observability（MVP 最小）

```typescript
logger.info('search.completed', {
  queryId,
  userId,
  resultCount,
  latencyMs,
  degraded,
  retrievalCandidates: candidates.length,
});
```

- **不** log 完整 `query_text` 到 stdout（B-15）；仅 hash 或 length
- Metric counters：`search_completed_total`, `search_empty_total`, `search_degraded_total`

---

**M5 ENG v1.0：✅ 可锁定**

---

### 🤝 Handoff: ENG → QA — Module 5：AI 搜尋

**State Tracker snapshot**：
| 模組 | PM | SA/SD | UI/UX | ENG | QA |
|------|:--:|:-----:|:-----:|:---:|:--:|
| M5 | ✅ v1.1 | ✅ v1.0 | ✅ v1.0 | ✅ v1.0 | ⏳ |

**QA 测试依据**：
- `BSChat_PM_M5.md` User Stories US-5.1~5.6
- `BSChat_SA-SD_M5.md` API + empty/degraded/quota
- `BSChat_UIUX_M5.md` 空状态 / Aha / Context Banner
- 本文 §12 测试要点

**Seed 数据建议**：
- User A：≥5 contacts，2 家「工業電腦」相关 enrich
- User B：0 indexed（empty path）
- User C：3 contacts 无匹配 query

**Open blockers（不阻塞 QA P0）**：B-15 日志策略、B-16 Pro 配额数字、P1 live flow

---

*ENG M5 v1.0 — SDLC Phase 1*
