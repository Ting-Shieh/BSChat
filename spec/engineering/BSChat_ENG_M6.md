# BSChat ENG — Module 6：公司資訊補全（Enrichment）

> **依據**：M6 PM L3 v1.1、M6 SA/SD v1.0、M6 UI/UX v1.0、`BSChat_ENG_M3.md`  
> **團隊**：2 人（1 full-stack + 1 product/design）  
> **M6 估算**：~5–7 工程日（1 人 full-stack）  
> **前置**：M3 contact-upsert + company-enriched-handler stub · M1-Minimal entitlement seed

---

## 1. 技術選型（M6 增量）

延續 M2/M3 栈，M6 新增：

| 層級 | 選型 | 用途 |
|------|------|------|
| **Web Fetch** | `undici` / native `fetch` + 8s AbortSignal | 官網抓取 |
| **HTML Parse** | `cheerio` | 去 script/style，抽正文 |
| **Text Extract** | `@mozilla/readability` + cheerio fallback | 主內容區 |
| **Robots** | `robots-parser` | B-10 合規（MVP 尊重 Disallow） |
| **LLM Extract** | Claude Sonnet（text） | `main_products` 結構化抽取 |
| **Scheduler** | BullMQ repeatable job | stale auto-refresh（Pro） |
| **Slug** | 自研 `normalizeCompanyName` + punycode | 域名啟發式 |

### 環境變數（M6 新增）

```bash
ENRICH_MODEL=claude-sonnet-4-20250514
ENRICH_PROMPT_VERSION=v1
ENRICH_CONFIDENCE_DISPLAY_THRESHOLD=0.5
ENRICH_CONFIDENCE_PARTIAL_THRESHOLD=0.3
ENRICH_FETCH_TIMEOUT_MS=8000
ENRICH_MAX_PAGES=3
ENRICH_MAX_TEXT_CHARS=12000
ENRICH_WORKER_CONCURRENCY=3
ENRICH_DAILY_QUOTA_PER_USER=50
ENRICH_MANUAL_QUOTA_FREE=3
STALE_SCAN_CRON=0 3 * * *
STALE_SCAN_BATCH_SIZE=200
# P1
# TAVILY_API_KEY=
```

---

## 2. Monorepo 增量結構

```
apps/web/
├── app/
│   ├── (tabs)/settings/
│   │   └── company-data/page.tsx          # Pro 設定（M1 路由）
│   └── api/v1/companies/
│       └── [id]/
│           ├── route.ts                   # GET
│           ├── enrich/route.ts            # POST
│           ├── re-enrich/route.ts         # POST
│           ├── review/route.ts            # PATCH
│           └── enrich-status/route.ts     # GET（optional polling）
├── components/enrichment/
│   ├── CompanyEnrichmentBlock.tsx
│   ├── CompanyProductsPreview.tsx
│   ├── EnrichmentProvenanceBadge.tsx
│   ├── ManualRefreshButton.tsx
│   ├── EnrichmentProvenanceSheet.tsx
│   ├── EnrichmentRejectDialog.tsx
│   ├── EnrichmentOverrideSheet.tsx
│   ├── EnrichmentQuotaDialog.tsx
│   └── CompanyDataSettings.tsx
└── hooks/
    ├── useCompanyEnrichment.ts
    ├── useManualRefresh.ts
    └── useCompanyDataSettings.ts

apps/worker/jobs/
├── company-enrich.job.ts                  # 主 enrich pipeline
├── stale-company-scan.job.ts            # Pro cron
└── company-enrich-outbox-relay.job.ts     # CompanyEnriched → M3 queue

packages/shared/
├── schemas/company.ts                     # Zod
├── events/company-enrich.ts
├── enrichment/
│   ├── normalize-company-name.ts
│   ├── website-discovery.ts
│   ├── page-fetcher.ts
│   ├── robots.ts
│   └── extract-products.prompt.ts
└── services/
    ├── company.service.ts
    ├── enrichment.service.ts
    ├── entitlement.service.ts
    └── company-enrichment-section.builder.ts
```

**Queue 命名**：

| Queue | Producer | Consumer |
|-------|----------|----------|
| `company-enrich` | M3 upsert / API manual / stale scan | `company-enrich.job` |
| `company-enriched` | M6 outbox relay | M3 `company-enriched-handler.job` |

---

## 3. 前端架構

### 3.1 路由

| Path | 畫面 | 優先 |
|------|------|------|
| `/contacts/[id]` | 詳情含 `CompanyEnrichmentBlock` | P0 |
| `/contacts` | 列表含 `CompanyProductsPreview` | P0 |
| `/settings/company-data` | 公司資料設定 | P1 |

### 3.2 元件整合（替換 M3 stub）

```typescript
// ContactDetailPage — 更新
<CompanyEnrichmentBlock
  companyId={contact.companyId}
  enrichment={data.sections.company_enrichment}
  planTier={entitlement.planTier}
  manualQuotaRemaining={entitlement.manualRefreshRemaining}
  onInvalidate={() => queryClient.invalidateQueries(['contacts', id])}
/>

// ContactListCard — 更新
<CompanyProductsPreview
  products={contact.company_products_preview}
  confidence={contact.company_products_confidence}
  status={contact.company_enrichment_status}  // pending|ready|hidden
/>
```

### 3.3 TanStack Query Keys

```typescript
['companies', companyId]
['companies', companyId, 'enrich-status']   // polling when pending
['settings', 'company-data']
```

**Polling 策略**：詳情 `enrichment.status === 'pending'` 时 `refetchInterval: 5000`，最多 12 次（60s），之后停止。

### 3.4 API Client

```typescript
export const companiesApi = {
  get: (id: string) => GET(`/api/v1/companies/${id}`),
  enrich: (id: string, body?: EnrichRequest) =>
    POST(`/api/v1/companies/${id}/enrich`, body),
  reEnrich: (id: string) => POST(`/api/v1/companies/${id}/re-enrich`),
  review: (id: string, body: ReviewRequest) =>
    PATCH(`/api/v1/companies/${id}/review`, body),
  enrichStatus: (id: string) => GET(`/api/v1/companies/${id}/enrich-status`),
};
```

### 3.5 Hooks

```typescript
// useManualRefresh.ts
export function useManualRefresh(companyId: string) {
  return useMutation({
    mutationFn: () => companiesApi.enrich(companyId, { trigger: 'manual' }),
    onSuccess: () => {
      queryClient.invalidateQueries(['contacts']);
      queryClient.invalidateQueries(['companies', companyId]);
    },
    onError: (err) => {
      if (err.code === 'QUOTA_EXCEEDED') openQuotaDialog();
      if (err.code === 'ALREADY_IN_PROGRESS') toast('已在更新中');
    },
  });
}
```

---

## 4. 後端架構

### 4.1 Service 層

```typescript
// company.service.ts
class CompanyService {
  async resolveFromContact(input: EnrichInput): Promise<Company>
  async linkContacts(companyId: string, userId: string, normalizedName: string): Promise<number>
  async getOwned(id: string, userId: string): Promise<Company>
}

// enrichment.service.ts
class EnrichmentService {
  async runPipeline(job: EnrichJobContext): Promise<EnrichmentResult>
  async appendEnrichment(companyId: string, result: EnrichmentResult, trigger: TriggerType): Promise<CompanyEnrichment>
  async getLatest(companyId: string): Promise<CompanyEnrichment | null>
  shouldEmitCompanyEnriched(enrichment: CompanyEnrichment, companyId: string): Promise<boolean>
}

// entitlement.service.ts
class EntitlementService {
  async ensureDefaults(userId: string): Promise<UserEntitlement>
  async checkDailyEnrich(userId: string): Promise<QuotaCheck>
  async consumeDailyEnrich(userId: string): Promise<void>
  async checkManualRefresh(userId: string): Promise<QuotaCheck>
  async consumeManualRefresh(userId: string): Promise<void>
  async getSettings(userId: string): Promise<CompanyDataSettingsDTO>
  async updateAutoRefresh(userId: string, dto: AutoRefreshDTO): Promise<void>  // Pro only
}

// company-enrichment-section.builder.ts
class CompanyEnrichmentSectionBuilder {
  build(company: Company, enrichment: Enrichment | null, review: Review | null, entitlement: Entitlement): CompanyEnrichmentSection
}
```

### 4.2 Company Enrich Worker（核心）

```typescript
// company-enrich.job.ts
async function processCompanyEnrich(job: Job<CompanyEnrichJobPayload>) {
  const { userId, workspaceId, contactId, companyName, contactWebsite, triggerType } = job.data;

  await entitlementService.ensureDefaults(userId);
  const daily = await entitlementService.checkDailyEnrich(userId);
  if (!daily.allowed) {
    await delayJob(job, 24 * 60 * 60 * 1000);
    return;
  }

  const company = await companyService.resolveFromContact({
    userId, workspaceId, companyName, triggerType,
  });

  if (shouldSkipDedupe(company, triggerType)) {
    await markJobSkipped(job, company.id);
    return;
  }

  const idempotencyKey = buildIdempotencyKey(company.id, triggerType);
  const enrichJob = await enrichJobRepo.create({ companyId: company.id, userId, contactId, triggerType, idempotencyKey });

  await db.company.update({ where: { id: company.id }, data: { enrichStatus: 'pending' } });

  try {
    await enrichJobRepo.updateStatus(enrichJob.id, 'resolving');

    const website = await websiteDiscovery.discover({
      companyName,
      ocrWebsite: contactWebsite,
      contactTitle: job.data.contactTitle,
    });

    if (!website.url) {
      await finalizeFailed(company, enrichJob, 'NO_WEBSITE');
      return;
    }

    await enrichJobRepo.updateStatus(enrichJob.id, 'enriching');
    const pages = await pageFetcher.fetchRelevantPages(website.url, ENRICH_MAX_PAGES);
    const combinedText = truncate(pages.map(p => p.text).join('\n\n'), ENRICH_MAX_TEXT_CHARS);

    const extraction = await enrichmentService.extractWithLlm({
      companyName,
      websiteUrl: website.url,
      pageText: combinedText,
      sourceUrls: pages.map(p => p.url),
      contactTitle: job.data.contactTitle,
    });

    const result = mapExtractionToStatus(extraction);
    await entitlementService.consumeDailyEnrich(userId);

    await db.$transaction(async (tx) => {
      const version = company.enrichVersion + 1;
      const enrichment = await tx.companyEnrichment.create({
        data: {
          companyId: company.id,
          enrichVersion: version,
          mainProducts: result.mainProducts,
          summary: result.summary,
          industryTags: result.industryTags,
          fieldsProvenance: result.fieldsProvenance,
          overallConfidence: result.overallConfidence,
          triggerType,
          sourceUrls: pages.map(p => p.url),
          model: ENRICH_MODEL,
          promptVersion: ENRICH_PROMPT_VERSION,
          status: result.status,
          candidateCompanies: result.candidates,
        },
      });

      await tx.company.update({
        where: { id: company.id },
        data: {
          websiteUrl: website.url,
          enrichStatus: mapEnrichStatus(result),
          lastEnrichedAt: new Date(),
          enrichVersion: version,
          needsReview: result.needsReview,
        },
      });

      await tx.contact.updateMany({
        where: { userId, companyName: { equals: company.displayName, mode: 'insensitive' }, deletedAt: null },
        data: { companyId: company.id },
      });

      if (contactId) {
        await tx.contact.update({ where: { id: contactId }, data: { companyId: company.id } });
      }

      if (await enrichmentService.shouldEmitCompanyEnriched(enrichment, company.id, tx)) {
        await outbox.emit(tx, 'CompanyEnriched', {
          userId, workspaceId, contactId, companyId: company.id,
          status: result.status,
          mainProducts: result.mainProducts,
          productsConfidence: result.overallConfidence,
          websiteUrl: website.url,
          enrichedAt: new Date().toISOString(),
          enrichVersion: version,
        });
      }

      await tx.enrichJob.update({
        where: { id: enrichJob.id },
        data: { status: result.status, completedAt: new Date(), latencyMs: elapsed() },
      });
    });
  } catch (err) {
    await finalizeFailed(company, enrichJob, err.code ?? 'PIPELINE_ERROR');
    throw err; // BullMQ retry policy
  }
}
```

**Retry 策略**：network/LLM 5xx → 2 retries exponential；`NO_WEBSITE` / quota → no retry。

### 4.3 Website Discovery

```typescript
// website-discovery.ts
async function discover(input: DiscoverInput): Promise<{ url: string | null; candidates: Candidate[] }> {
  if (input.ocrWebsite && await isReachable(normalizeUrl(input.ocrWebsite))) {
    return { url: normalizeUrl(input.ocrWebsite), candidates: [] };
  }

  const slug = slugify(input.companyName);
  const probes = [
    `https://${slug}.com.tw`,
    `https://www.${slug}.com.tw`,
    `https://${slug}.com`,
  ].slice(0, 3);

  const reachable = [];
  for (const url of probes) {
    if (await isReachable(url)) reachable.push({ url, score: 0.5 });
  }

  if (reachable.length === 0) return { url: null, candidates: [] };
  if (reachable.length === 1) return { url: reachable[0].url, candidates: [] };

  // B-6 MVP: pick longest HTML content; flag needs_review
  const best = await pickBestByContent(reachable);
  return { url: best.url, candidates: reachable };
}
```

### 4.4 LLM Extraction Prompt

```typescript
// extract-products.prompt.ts
export const EXTRACT_PRODUCTS_PROMPT = `
你是 B2B 公司資訊分析助手。根據以下官網文字，提取公司「主要產品/服務」。

公司名稱：{company_name}
官網：{website_url}
${'{contact_title}' ? '联系人职称（辅助判断）：{contact_title}' : ''}

官網文字：
"""
{page_text}
"""

规则：
1. main_products：1-5 项，每项 ≤80 字，描述具体产品/服务类别
2. 若文字不足以判断，overall_confidence 应 < 0.5
3. 找不到任何产品信息，main_products=[]，confidence=0
4. 不要猜测、不要编造官网没有的内容
5. 输出严格 JSON，无 markdown

格式：
{
  "main_products": ["..."],
  "summary": "1-2句公司简介或null",
  "industry_tags": ["..."],
  "overall_confidence": 0.0,
  "fields_provenance": {
    "main_products": { "source_urls": ["..."], "confidence": 0.0 }
  }
}
`;
```

```typescript
function mapExtractionToStatus(extraction: LlmExtraction): EnrichmentResult {
  const conf = extraction.overall_confidence;
  if (!extraction.main_products?.length || conf < ENRICH_CONFIDENCE_PARTIAL_THRESHOLD) {
    return { ...extraction, status: 'failed' };
  }
  if (conf < ENRICH_CONFIDENCE_DISPLAY_THRESHOLD) {
    return { ...extraction, status: 'partial' };
  }
  return { ...extraction, status: 'completed' };
}
```

### 4.5 Entitlement Service

```typescript
async function checkManualRefresh(userId: string): Promise<QuotaCheck> {
  const e = await ensureDefaults(userId);
  resetMonthlyIfNeeded(e);

  if (e.planTier === 'pro' && e.manualRefreshQuotaMonthly === -1) {
    return { allowed: true, remaining: null };
  }

  const remaining = e.manualRefreshQuotaMonthly - e.manualRefreshUsedThisMonth;
  return { allowed: remaining > 0, remaining: Math.max(0, remaining) };
}

async function consumeManualRefresh(userId: string) {
  const e = await ensureDefaults(userId);
  if (e.planTier === 'pro' && e.manualRefreshQuotaMonthly === -1) return;
  await db.userEntitlement.update({
    where: { userId },
    data: { manualRefreshUsedThisMonth: { increment: 1 } },
  });
}
```

**Seed on first contact**（M3 upsert 或 M6 worker 入口）：

```typescript
await db.userEntitlement.upsert({
  where: { userId },
  create: { userId, planTier: 'free', manualRefreshQuotaMonthly: 3, dailyEnrichQuota: 50 },
  update: {},
});
```

### 4.6 Stale Company Scan

```typescript
// stale-company-scan.job.ts — BullMQ repeatable STALE_SCAN_CRON
async function staleCompanyScan() {
  const rows = await db.$queryRaw`...`; // SA/SD §6.4 SQL
  for (const row of rows) {
    const inProgress = await enrichJobRepo.hasInProgress(row.id);
    if (inProgress) continue;

    await enrichQueue.add(
      'stale-auto',
      { companyId: row.id, userId: row.user_id, triggerType: 'stale_auto' },
      { jobId: `stale:${row.id}:${todayBucket()}` },
    );
  }
}
```

MVP `plan_tier=free` → cron 仍跑但 SQL 0 rows；无需 feature flag。

### 4.7 M3 整合变更

**M3 contact-upsert.job.ts** — 修正 emit：

```typescript
if (contact.companyName) {
  await outbox.emit(tx, 'CompanyEnrichRequested', {
    userId: contact.userId,
    workspaceId: contact.workspaceId,
    contactId: contact.id,
    companyName: contact.companyName,
    contactWebsite: contact.website,
    triggerType: 'ingest',
    occurredAt: new Date().toISOString(),
  });
}
```

**M3 GET /contacts list** — 追加字段：

```typescript
company_products_preview: enrichment?.mainProducts?.slice(0, 3).join('、') ?? null,
company_products_confidence: enrichment?.overallConfidence ?? null,
company_enrichment_status: deriveListEnrichmentStatus(company, enrichment, review),
```

**M3 index.service.ts** — 读 M6：

```typescript
const company = contact.companyId
  ? await enrichmentService.getLatestForContact(contact.companyId)
  : null;

doc.company_products = company?.mainProducts ?? [];
doc.company_enriched_at = company?.lastEnrichedAt?.toISOString();
```

**M3 company-enriched-handler.job.ts** — 已有，无需改逻辑。

### 4.8 Review / Re-enrich API

```typescript
// PATCH /companies/:id/review
async function patchReview(companyId: string, userId: string, dto: ReviewDTO) {
  await companyService.getOwned(companyId, userId);
  await db.companyFieldReview.upsert({
    where: { companyId_userId_fieldName: { companyId, userId, fieldName: dto.field_name } },
    create: { companyId, userId, fieldName: dto.field_name, reviewStatus: dto.review_status, overrideValue: dto.override_value },
    update: { reviewStatus: dto.review_status, overrideValue: dto.override_value, reviewedAt: new Date() },
  });
  // reject → 不触发 re-index products；override → re-index
  if (dto.review_status === 'user_override') {
    await queue.add('contact-index', { contactIds: await contactIdsForCompany(companyId) });
  }
}

// POST /companies/:id/re-enrich
async function reEnrich(companyId: string, userId: string, contactId?: string) {
  await db.companyFieldReview.updateMany({
    where: { companyId, userId, fieldName: 'main_products', reviewStatus: 'rejected' },
    data: { reviewStatus: 'auto' },
  });
  return enqueueManualEnrich(companyId, userId, contactId);
}
```

### 4.9 CompanyEnrichmentSectionBuilder

```typescript
function build(company, enrichment, review, entitlement): CompanyEnrichmentSection {
  if (!company) return { status: 'hidden', can_refresh: false };

  if (company.enrichStatus === 'pending') {
    return { status: 'pending', can_refresh: false };
  }

  if (review?.reviewStatus === 'rejected') {
    return { status: 'rejected', can_refresh: true, refresh_quota_remaining: entitlement.manualRemaining };
  }

  const conf = enrichment?.overallConfidence ?? 0;
  const products = review?.reviewStatus === 'user_override'
    ? review.overrideValue as string[]
    : enrichment?.mainProducts;

  if (company.enrichStatus === 'failed' || conf < 0.3) {
    return { status: 'failed', can_refresh: true, refresh_quota_remaining: entitlement.manualRemaining };
  }

  if (company.enrichStatus === 'partial' || conf < 0.5) {
    return { status: 'partial', can_refresh: true, refresh_quota_remaining: entitlement.manualRemaining };
  }

  return {
    status: company.needsReview ? 'completed' : 'completed', // UI: needsReview → warning badge
    main_products: products,
    website_url: company.websiteUrl,
    confidence: conf,
    provenance_label: buildProvenanceLabel(enrichment),
    updated_at: company.lastEnrichedAt?.toISOString(),
    can_refresh: true,
    refresh_quota_remaining: entitlement.manualRemaining,
    review_status: review?.reviewStatus ?? 'auto',
    needs_review: company.needsReview,
  };
}
```

---

## 5. Prisma Schema 增量

```prisma
model Company {
  id              String    @id @default(uuid())
  userId          String    @map("user_id")
  workspaceId     String    @map("workspace_id")
  normalizedName  String    @map("normalized_name")
  displayName     String    @map("display_name")
  websiteUrl      String?   @map("website_url")
  enrichStatus    String    @default("never") @map("enrich_status")
  lastEnrichedAt  DateTime? @map("last_enriched_at")
  enrichVersion   Int       @default(0) @map("enrich_version")
  needsReview     Boolean   @default(false) @map("needs_review")
  deletedAt       DateTime? @map("deleted_at")
  createdAt       DateTime  @default(now()) @map("created_at")
  updatedAt       DateTime  @updatedAt @map("updated_at")

  enrichments     CompanyEnrichment[]
  reviews         CompanyFieldReview[]
  enrichJobs      EnrichJob[]

  @@unique([userId, normalizedName])
  @@index([userId, enrichStatus])
  @@index([lastEnrichedAt])
  @@map("companies")
}

model CompanyEnrichment {
  id                 String   @id @default(uuid())
  companyId          String   @map("company_id")
  enrichVersion      Int      @map("enrich_version")
  mainProducts       Json     @default("[]") @map("main_products")
  summary            String?
  industryTags       Json     @default("[]") @map("industry_tags")
  fieldsProvenance   Json     @default("{}") @map("fields_provenance")
  overallConfidence  Float    @default(0) @map("overall_confidence")
  triggerType        String   @map("trigger_type")
  sourceUrls         Json     @default("[]") @map("source_urls")
  model              String?
  promptVersion      String?  @map("prompt_version")
  status             String
  candidateCompanies Json?    @map("candidate_companies")
  createdAt          DateTime @default(now()) @map("created_at")

  company            Company  @relation(fields: [companyId], references: [id])

  @@unique([companyId, enrichVersion])
  @@index([companyId, enrichVersion(sort: Desc)])
  @@map("company_enrichments")
}

model CompanyFieldReview {
  id            String   @id @default(uuid())
  companyId     String   @map("company_id")
  userId        String   @map("user_id")
  fieldName     String   @map("field_name")
  reviewStatus  String   @map("review_status")
  overrideValue Json?    @map("override_value")
  reviewedAt    DateTime @default(now()) @map("reviewed_at")

  company       Company  @relation(fields: [companyId], references: [id])

  @@unique([companyId, userId, fieldName])
  @@map("company_field_reviews")
}

model EnrichJob {
  id              String    @id @default(uuid())
  companyId       String    @map("company_id")
  userId          String    @map("user_id")
  contactId       String?   @map("contact_id")
  triggerType     String    @map("trigger_type")
  status          String    @default("requested")
  idempotencyKey  String?   @unique @map("idempotency_key")
  errorCode       String?   @map("error_code")
  latencyMs       Int?      @map("latency_ms")
  startedAt       DateTime? @map("started_at")
  completedAt     DateTime? @map("completed_at")
  createdAt       DateTime  @default(now()) @map("created_at")

  company         Company   @relation(fields: [companyId], references: [id])

  @@index([companyId, createdAt(sort: Desc)])
  @@map("enrich_jobs")
}

model UserEntitlement {
  userId                      String    @id @map("user_id")
  planTier                    String    @default("free") @map("plan_tier")
  autoRefreshEnabled          Boolean   @default(false) @map("auto_refresh_enabled")
  autoRefreshIntervalDays     Int       @default(90) @map("auto_refresh_interval_days")
  manualRefreshQuotaMonthly   Int       @default(3) @map("manual_refresh_quota_monthly")
  manualRefreshUsedThisMonth  Int       @default(0) @map("manual_refresh_used_this_month")
  manualRefreshResetAt        DateTime? @map("manual_refresh_reset_at")
  dailyEnrichQuota            Int       @default(50) @map("daily_enrich_quota")
  dailyEnrichUsed             Int       @default(0) @map("daily_enrich_used")
  dailyEnrichResetAt          DateTime? @map("daily_enrich_reset_at")
  updatedAt                   DateTime  @updatedAt @map("updated_at")

  @@map("user_entitlements")
}

model QueryAugmentation {
  id            String   @id @default(uuid())
  userId        String   @map("user_id")
  companyId     String?  @map("company_id")
  queryId       String   @map("query_id")
  liveProducts  Json?    @map("live_products")
  sourceUrls    Json?    @map("source_urls")
  confidence    Float?
  adopted       Boolean  @default(false)
  createdAt     DateTime @default(now()) @map("created_at")

  @@map("query_augmentations")
}
```

**Contact 模型增量**：

```prisma
model Contact {
  // ...existing
  companyId  String?  @map("company_id")
  company    Company? @relation(fields: [companyId], references: [id])
}
```

---

## 6. API Route Handlers

### POST `/api/v1/companies/[id]/enrich`

```typescript
export async function POST(req: Request, { params }: { params: { id: string } }) {
  const userId = requireUserId(req);
  const company = await companyService.getOwned(params.id, userId);

  if (await enrichJobRepo.hasInProgress(company.id)) {
    return error(409, 'ALREADY_IN_PROGRESS', '已在更新中');
  }

  const body = await parseJson(req);
  if (body.trigger === 'manual' || !body.trigger) {
    const quota = await entitlementService.checkManualRefresh(userId);
    if (!quota.allowed) {
      return error(403, 'QUOTA_EXCEEDED', '本月手動更新次數已用完', {
        reset_at: entitlementService.nextMonthlyReset(userId),
      });
    }
    await entitlementService.consumeManualRefresh(userId);
  }

  const job = await enrichQueue.add('enrich', {
    companyId: company.id,
    userId,
    contactId: body.contactId,
    companyName: company.displayName,
    triggerType: body.trigger ?? 'manual',
    queryAugmentationId: body.queryAugmentationId,
  }, { jobId: `manual:${company.id}:${minuteBucket()}` });

  const remaining = (await entitlementService.checkManualRefresh(userId)).remaining;

  return json(202, { job_id: job.id, status: 'requested', quota_remaining: remaining });
}
```

### GET `/api/v1/contacts` — M3 列表 DTO 扩展

在 M3 list handler 内 join company + latest enrichment（batch query 防 N+1）：

```typescript
const companyIds = contacts.map(c => c.companyId).filter(Boolean);
const enrichments = await enrichmentService.getLatestBatch(companyIds);
```

---

## 7. Sprint Ticket 清單

### M6-A P0 核心（4–5 天）

| ID | Ticket | FE | BE/Worker | 估時 |
|----|--------|----|-----------| ---- |
| M6-001 | Prisma M6 models + migration | — | ✓ | 0.5d |
| M6-002 | `normalizeCompanyName` + company resolve | — | ✓ | 0.25d |
| M6-003 | website-discovery + page-fetcher + robots | — | ✓ | 1d |
| M6-004 | LLM extract prompt + enrichment.service | — | ✓ | 0.5d |
| M6-005 | company-enrich.worker 全流程 | — | ✓ | 1d |
| M6-006 | CompanyEnriched outbox → M3 queue | — | ✓ | 0.25d |
| M6-007 | entitlement.service + seed defaults | — | ✓ | 0.5d |
| M6-008 | CompanyEnrichmentSectionBuilder + M3 detail 接入 | ✓ | ✓ | 0.5d |
| M6-009 | CompanyEnrichmentBlock 全状态 | ✓ | — | 1d |
| M6-010 | CompanyProductsPreview 列表 | ✓ | ✓ | 0.5d |
| M6-011 | GET /companies/:id | — | ✓ | 0.25d |
| M6-012 | M3 upsert emit CompanyEnrichRequested（修正） | — | ✓ | 0.25d |
| M6-013 | M3 index 读 company_products | — | ✓ | 0.25d |

### M6-B P1 扩展（1–2 天）

| ID | Ticket | 估時 |
|----|--------|------|
| M6-014 | POST enrich + manual quota | 0.5d |
| M6-015 | PATCH review + reject/override UI | 0.5d |
| M6-016 | POST re-enrich | 0.25d |
| M6-017 | ManualRefreshButton + QuotaDialog | 0.5d |
| M6-018 | ProvenanceSheet + RejectDialog + OverrideSheet | 0.5d |
| M6-019 | stale-company-scan.job（Pro cron stub） | 0.5d |
| M6-020 | CompanyDataSettings 页 | 0.5d |
| M6-021 | enrich-status polling hook | 0.25d |
| M6-022 | Vitest: pipeline mock + section builder | 0.5d |
| M6-023 | Playwright: 详情 enrich pending→completed | 0.5d |

### 依赖图

```
M6-001 → M6-002 → M6-003 → M6-004 → M6-005 → M6-006
                              ↓
M6-007 → M6-014 ─────────────────┘
M6-008 → M6-009
M6-010 ← M6-008
M6-012（依赖 M3-002 contact-upsert）
M6-013（依赖 M3-009 index worker）
M3-015 company-enriched-handler（已有，M6-006 接通）
```

**建议垂直切片顺序**：
1. M6-001~006 + M6-012 → 背景 enrich E2E
2. M6-008~010 + M6-009 → UI 可见
3. M6-014~018 → 用户交互
4. M6-019~020 → Pro 设定

---

## 8. Definition of Done — M6

### P0

- [ ] Contact 建立后 60s 内 enrich job 入队
- [ ] 有可达官网时 `main_products` 写入 + conf≥0.5 显示
- [ ] 无官网 → failed，不脑补 products
- [ ] conf 0.3–0.49 → partial UI；列表不显示 products
- [ ] `CompanyEnriched` 触发 M3 pass 2 + re-index
- [ ] 同 user 同 normalized_name 共享 Company
- [ ] 24h dedupe 对 ingest 生效
- [ ] 列表 `company_products_preview` 正确
- [ ] 跨用户 company 访问 404

### P1

- [ ] manual refresh + Free 配额 3/月
- [ ] reject 后不显示；re-enrich 可恢复
- [ ] user_override 显示「已修正」
- [ ] stale cron 注册（Pro 0 用户 no-op 可接受）
- [ ] CompanyDataSettings Free preview + Pro toggle stub
- [ ] `enriched_at` 显示于详情

---

## 9. 測試要点（供 QA）

| 区域 | 关键断言 |
|------|---------|
| Resolve | 同公司名两 Contact → 同一 company_id |
| Dedupe | 1h 内 duplicate ingest → 1 fetch job |
| Pipeline mock | 官网 HTML fixture → products JSON |
| Gate | conf 0.45 → partial, no CompanyEnriched |
| Gate | conf 0.72 → completed + CompanyEnriched queued |
| Reject | reject 后 enrich 完成 → UI status rejected |
| Re-enrich | clears reject + new job |
| Quota | Free 第 4 次 manual → 403 |
| Index | enrich 后 search_document 含 company_products |
| UI | pending shimmer → completed products |
| Failed | NO_WEBSITE → failed block, contact still loads |

**Fixture 建议**：`fixtures/websites/abc-tech-home.html` 供 Vitest 不依赖外网。

---

## 10. 風險

| 風險 | 緩解 |
|------|------|
| 官网抓取被 block | retry 1x；failed UI；不阻塞 Contact |
| LLM 幻觉产品 | prompt 强调不猜测；conf gate |
| 中文公司域名启发式 miss | OCR website 优先；P1 Tavily |
| Worker 抓取 SSRF | 仅 allow http(s)；block private IP |
| enrich 慢于 60s | UI polling + 「通常 30 秒内」 |
| M3 stub 未替换 | M6-008 明确替换 CompanyEnrichmentBlock |
| Pro 未上线 | entitlement hardcode free；cron harmless |

---

## 11. 模組接口

| 模块 | 接口 | M6 角色 |
|------|------|---------|
| M3 | CompanyEnrichRequested | consumer |
| M3 | CompanyEnriched | producer |
| M3 | GET contact detail section | provider（builder） |
| M3 | contact-index company_products | provider（data） |
| M1 | user_entitlements | read/write quota（MVP） |
| M5 | query_augmentations adopt | consumer（P1 stub） |
| M5 | search index fields | provider |

---

## 12. ENG 新增 DDR

| ID | 决策 |
|----|------|
| DDR-46 | HTML 解析用 cheerio + Readability；不引入 headless browser MVP |
| DDR-47 | SSRF 防护：fetch 前 DNS resolve + block RFC1918 |
| DDR-48 | Vitest 用 HTML fixture；E2E 用 mock worker 注入 |
| DDR-49 | 列表 enrichment batch query；禁止 N+1 per contact |
| DDR-50 | query_augmentations 表 M6 migration 建空表；M5 再写 |

---

### 🤝 Handoff: ENG → QA — Module 6

**State Tracker**：
| 模組 | PM | SA/SD | UI/UX | ENG | QA |
|------|:--:|:-----:|:-----:|:---:|:--:|
| M6 | ✅ | ✅ | ✅ | ✅ v1.0 | ⏳ |

**P0 测试范围**：背景 enrich、详情/列表显示、pass 2 触发、failed/partial 态  
**P1 测试范围**：manual quota、reject/re-enrich、override、Pro settings stub  
**Mock 策略**：worker HTML fixture；Claude API mock conf 场景

---

*ENG M6 v1.0 — SDLC Phase 1*
