# BSChat ENG — Module 3：聯絡人結構化與審核

> **依據**：M3 PM L3、M3 SA/SD L4、M3 UI/UX、`BSChat_ENG_M2.md`  
> **團隊**：2 人（1 full-stack + 1 product/design）  
> **M3 估算**：~4–6 工程日（1 人 full-stack）  
> **前置**：M2 handoff stub（M2-012）· M1-Minimal stub

---

## 1. 技術選型（M3 增量）

延續 M2 栈，M3 新增：

| 層級 | 選型 | 用途 |
|------|------|------|
| **Inference** | Claude Sonnet（text） | `responsibility_scope` 推估 |
| **Search Index** | PostgreSQL `tsvector` + GIN | MVP 全文索引（DDR-25） |
| **pgvector** | `vector(1536)` 欄位预留 | M5 接入 embedding |
| **Phone norm** | `libphonenumber-js` | E.164 normalization |
| **Event** | BullMQ + outbox table | ContactUpsert / Index / Inference |

### 環境變數（M3 新增）

```bash
INFERENCE_MODEL=claude-sonnet-4-20250514
INFERENCE_CONFIDENCE_THRESHOLD=0.6
INFERENCE_PROMPT_VERSION=v1
CONTACT_INDEX_WORKER_CONCURRENCY=5
```

---

## 2. Monorepo 增量結構

```
apps/web/
├── app/
│   ├── (tabs)/contacts/
│   │   ├── page.tsx                 # 名片庫列表
│   │   └── [id]/page.tsx            # 詳情
│   └── api/v1/contacts/
│       ├── route.ts                 # GET list
│       └── [id]/
│           ├── route.ts             # GET/PATCH/DELETE
│           ├── provenance/route.ts
│           └── reject-inference/route.ts
├── components/contacts/
│   ├── ContactListCard.tsx
│   ├── ContactDetailSection.tsx
│   ├── ProvenanceBadge.tsx
│   ├── ResponsibilityBlock.tsx
│   ├── CompanyEnrichmentBlock.tsx   # M6 占位
│   ├── ContactEmptyState.tsx
│   └── ContactEditSheet.tsx         # P1
└── hooks/
    ├── useContacts.ts
    └── useContactDetail.ts

apps/worker/jobs/
├── contact-upsert.job.ts            # consume M2 handoff
├── responsibility-inference.job.ts
├── contact-index.job.ts
└── company-enriched-handler.job.ts  # M6 event → pass 2

packages/shared/
├── schemas/contact.ts               # Zod
├── events/contact-upsert.ts
└── inference/prompts.ts
```

---

## 3. 前端架構

### 3.1 路由

| Path | 畫面 | 優先 |
|------|------|------|
| `/contacts` | 名片庫列表 | P0 |
| `/contacts/[id]` | 詳情三區塊 | P0 |

Tab 導航「📇 名片庫」→ `/contacts`

### 3.2 元件階層

```
ContactsPage
├── PrivacyStrip
├── ContactListHeader（count + 篩選 P1）
├── ContactList
│   └── ContactListCard × n
└── ContactEmptyState

ContactDetailPage
├── ContactDetailHeader（name + menu）
├── CardImageViewer（pinch zoom P1）
├── ContactDetailSection variant="original"
│   └── CopyableField（phone/email）
├── ResponsibilityBlock              # conf≥0.6 only
│   ├── ProvenanceBadge
│   └── RejectInferenceLink
├── CompanyEnrichmentBlock           # M6 stub / pending
├── SourceMeta（source_label, privacy）
└── ContactActionBar（致電/Email → M8）
```

### 3.3 TanStack Query Keys

```typescript
['contacts', { page, reviewStatus, sourceLabel, q }]
['contacts', contactId]
['contacts', contactId, 'provenance']
```

- 列表：`staleTime 30s`，pull-to-refresh
- 詳情：handoff 后 M2 可 invalidate `['contacts']`

### 3.4 詳情三區塊渲染邏輯

```typescript
function ContactDetail({ data }: { data: ContactDetailResponse }) {
  const showInference =
    data.sections.ai_inferred?.responsibility_scope &&
    data.sections.ai_inferred.responsibility_scope.confidence >= 0.6 &&
    data.sections.ai_inferred.responsibility_scope.status !== 'rejected';

  return (
    <>
      <ContactDetailSection variant="original" fields={data.sections.card_original.fields} />
      {showInference && (
        <ResponsibilityBlock scope={data.sections.ai_inferred.responsibility_scope} />
      )}
      <CompanyEnrichmentBlock enrichment={data.sections.company_enrichment} />
    </>
  );
}
```

### 3.5 API Client

```typescript
export const contactsApi = {
  list: (params) => GET('/api/v1/contacts', { params }),
  get: (id) => GET(`/api/v1/contacts/${id}`),
  update: (id, body) => PATCH(`/api/v1/contacts/${id}`, body),
  delete: (id) => DELETE(`/api/v1/contacts/${id}`),
  rejectInference: (id) => POST(`/api/v1/contacts/${id}/reject-inference`),
};
```

---

## 4. 後端架構

### 4.1 Service 層

```typescript
// contact.service.ts
class ContactService {
  async upsertFromHandoff(payload: ContactUpsertRequested): Promise<Contact>
  async getById(id: string, userId: string): Promise<ContactDetailDTO>
  async list(userId: string, filters: ContactListFilters): Promise<Paginated<ContactSummary>>
  async updateFields(id: string, userId: string, dto: UpdateContactDTO): Promise<Contact>
  async softDelete(id: string, userId: string): Promise<void>
  async rejectInference(id: string, userId: string): Promise<void>
}

// provenance.service.ts
class ProvenanceService {
  async upsertFromHandoff(contactId: string, fields: HandoffFields): Promise<void>
  async applyManualOverride(contactId: string, field: string, value: string, userId: string): Promise<void>
  resolveDisplayValue(contactId: string, fieldName: string): Promise<ResolvedField>
}

// inference.service.ts
class InferenceService {
  async runPass(contactId: string, pass: 1 | 2, inputs: InferenceInputs): Promise<InferenceResult | null>
  // returns null if confidence < threshold
}

// index.service.ts
class ContactIndexService {
  async buildDocument(contact: Contact): Promise<ContactSearchDocument>
  async upsertIndex(contactId: string): Promise<void>
}
```

### 4.2 Contact Upsert Worker

```typescript
// contact-upsert.job.ts
async function processContactUpsert(job: Job<ContactUpsertRequested>) {
  const contact = await contactService.upsertFromHandoff(job.data);
  await provenanceService.upsertFromHandoff(contact.id, job.data.fields);

  if (contact.company_name) {
    await queue.add('company-enrich', { contactId: contact.id, companyName: contact.company_name });
  }

  await queue.add('responsibility-inference', { contactId: contact.id, pass: 1 });
  await queue.add('contact-index', { contactId: contact.id });

  await analytics.track('contact_created', { contactId: contact.id, userId: contact.user_id });
}
```

**Idempotency**：`raw_card_id` UNIQUE → 重复 handoff 做 UPDATE + version++

### 4.3 Responsibility Inference Worker

```typescript
async function processInference(job: Job<{ contactId: string; pass: 1 | 2 }>) {
  const contact = await db.contact.findUnique({ where: { id: job.data.contactId } });
  const inputs = await buildInferenceInputs(contact, job.data.pass);

  const result = await inferenceService.runPass(contact.id, job.data.pass, inputs);

  if (!result || result.confidence < THRESHOLD) return; // 宁缺勿滥

  await db.$transaction(async (tx) => {
    // supersede previous active
    await tx.responsibilityInference.updateMany({
      where: { contactId: contact.id, status: 'active' },
      data: { status: 'superseded' },
    });
    await tx.responsibilityInference.create({ data: { ...result, status: 'active', passNumber: job.data.pass } });
    await tx.contact.update({
      where: { id: contact.id },
      data: {
        responsibility_scope: result.inferred_scope,
        responsibility_confidence: result.confidence,
      },
    });
  });

  await queue.add('contact-index', { contactId: contact.id }); // re-index
}
```

### 4.4 Contact Index Worker

```typescript
async function processContactIndex(job: Job<{ contactId: string }>) {
  const doc = await indexService.buildDocument(contactId);
  const contentHash = sha256(doc.search_text);

  await db.contactSearchDocument.upsert({
    where: { contactId },
    create: { ...doc, search_vector: toTsVector(doc.search_text), content_hash: contentHash },
    update: { ...doc, search_vector: toTsVector(doc.search_text), content_hash: contentHash, indexed_at: new Date() },
  });

  await db.contact.update({ where: { id: contactId }, data: { search_status: 'indexed' } });
}
```

**search_text 拼接**：
```
display_name | company_name | title | responsibility_scope | source_label | phones | emails | company_products(M6)
```

### 4.5 M6 Event Handler（stub → 正式接 M6）

```typescript
// company-enriched-handler.job.ts
async function onCompanyEnriched(event: CompanyEnriched) {
  await db.contact.update({
    where: { id: event.contactId },
    data: { company_id: event.companyId },
  });
  if (event.products?.length) {
    await queue.add('responsibility-inference', { contactId: event.contactId, pass: 2 });
  }
  await queue.add('contact-index', { contactId: event.contactId });
}
```

MVP 无 M6 时：`CompanyEnrichmentBlock` 显示 pending；inference pass 1 仍运行。

### 4.6 Delete Cascade

```typescript
async function deleteContact(id: string, userId: string) {
  const contact = await contactService.getOwned(id, userId);
  await db.contact.update({ where: { id }, data: { deleted_at: new Date() } });
  await queue.add('delete-card-cascade', { raw_card_id: contact.raw_card_id });
  await db.contactSearchDocument.delete({ where: { contactId: id } }).catch(() => {});
}
```

---

## 5. Prisma Schema 增量

追加至 `schema.prisma`（完整 DDL 见 SA/SD M3）：

```prisma
model Contact {
  id                        String    @id @default(uuid())
  userId                    String    @map("user_id")
  workspaceId               String    @map("workspace_id")
  rawCardId                 String    @unique @map("raw_card_id")
  displayName               String?   @map("display_name")
  companyName               String?   @map("company_name")
  title                     String?
  responsibilityScope       String?   @map("responsibility_scope")
  responsibilityConfidence  Float?    @map("responsibility_confidence")
  phones                    Json      @default("[]")
  emails                    Json      @default("[]")
  address                   String?
  website                   String?
  sourceType                String?   @map("source_type")
  sourceLabel               String?   @map("source_label")
  captureMethod             String?   @map("capture_method")
  reviewStatus              String    @default("unconfirmed") @map("review_status")
  searchStatus              String    @default("pending_index") @map("search_status")
  companyId                 String?   @map("company_id")
  imageUrl                  String?   @map("image_url")
  version                   Int       @default(1)
  deletedAt                 DateTime? @map("deleted_at")
  createdAt                 DateTime  @default(now()) @map("created_at")
  updatedAt                 DateTime  @updatedAt @map("updated_at")

  fieldProvenance           ContactFieldProvenance[]
  overrides                 ManualOverride[]
  inferences                ResponsibilityInference[]
  searchDocument            ContactSearchDocument?

  @@index([userId, updatedAt(sort: Desc)])
  @@map("contacts")
}

// ... ContactFieldProvenance, ManualOverride, ResponsibilityInference, ContactSearchDocument
```

---

## 6. API 實作要点

### GET `/contacts/:id` Response Builder

```typescript
function buildContactDetail(contact: Contact, provenance: Provenance[], activeInference: Inference | null, enrichment: Enrichment | null) {
  return {
    id: contact.id,
    sections: {
      card_original: {
        fields: provenance.filter(p => p.source !== 'ai_inferred').map(toFieldDTO),
        image_url: contact.imageUrl,
      },
      ai_inferred: activeInference ? {
        responsibility_scope: {
          value: activeInference.inferredScope,
          confidence: activeInference.confidence,
          source: 'ai_inferred',
          pass: activeInference.passNumber,
          status: activeInference.status,
        },
      } : null,
      company_enrichment: enrichment ? toEnrichmentDTO(enrichment) : { status: 'pending' },
    },
    source_type: contact.sourceType,
    source_label: contact.sourceLabel,
    review_status: contact.reviewStatus,
    version: contact.version,
  };
}
```

### PATCH `/contacts/:id`

- Validate `version` → 409 on mismatch
- Each changed field → `manual_overrides` + provenance update
- `company_name` change → re-enqueue enrich + inference pass 1

### POST `/contacts/:id/reject-inference`

- Set active inference `status=rejected`
- Clear `contacts.responsibility_scope` + `responsibility_confidence`
- Re-index

---

## 7. Sprint Ticket 清單

### M3-A P0 核心（3–4 天）

| ID | Ticket | FE | BE/Worker | 估時 |
|----|--------|----|-----------| ---- |
| M3-001 | Prisma models + migration（M3 tables） | — | ✓ | 0.5d |
| M3-002 | contact-upsert.worker（consume M2 handoff） | — | ✓ | 1d |
| M3-003 | provenance upsert logic | — | ✓ | 0.5d |
| M3-004 | GET /contacts list + pagination | ✓ | ✓ | 0.5d |
| M3-005 | GET /contacts/:id detail builder | ✓ | ✓ | 1d |
| M3-006 | ContactListCard + ContactsPage | ✓ | — | 0.5d |
| M3-007 | ContactDetailPage 三區塊 | ✓ | — | 1d |
| M3-008 | responsibility-inference.worker pass 1 | — | ✓ | 0.5d |
| M3-009 | contact-index.worker + tsvector | — | ✓ | 0.5d |
| M3-010 | DELETE /contacts + cascade event | ✓ | ✓ | 0.5d |
| M3-011 | ContactEmptyState | ✓ | — | 0.25d |
| M3-012 | Wire M2 handoff-m3.job → contact-upsert queue | — | ✓ | 0.25d |

### M3-B P1 擴展（1–2 天）

| ID | Ticket | 估時 |
|----|--------|------|
| M3-013 | PATCH /contacts 编辑 + override | 0.5d |
| M3-014 | POST reject-inference + UI | 0.5d |
| M3-015 | company-enriched handler（M6 stub event） | 0.5d |
| M3-016 | inference pass 2 | 0.5d |
| M3-017 | 列表筛选 + 排序 | 0.5d |
| M3-018 | CopyableField + ContactActionBar（M8 stub） | 0.5d |
| M3-019 | Vitest integration: upsert + inference gate | 0.5d |
| M3-020 | Playwright: 列表→详情 smoke | 0.5d |

### 依賴圖

```
M3-001 → M3-002 → M3-003
              ↓
M3-004 → M3-006 ─┐
M3-005 → M3-007 ─┤
M3-008 → M3-009 ─┘
M3-012（依赖 M2-012 handoff emit）
M1-Minimal stub（userId in all queries）
```

---

## 8. Definition of Done — M3

### P0

- [ ] M2 handoff 后 30s 内 Contact 出现在 `/contacts`
- [ ] 詳情三區塊正确渲染（original always; inference only if conf≥0.6）
- [ ] conf < 0.6 不写入 DB、UI 不显示推估区
- [ ] `contact_search_documents` 写入 + search_status=indexed
- [ ] DELETE cascade emit to M2
- [ ] 跨用户访问 404
- [ ] CompanyEnrichmentBlock 显示 pending（M6 未接时）

### P1

- [ ] reject-inference 流程
- [ ] PATCH 编辑 + 409 handling
- [ ] pass 2 inference on M6 stub event

---

## 9. 測試要点（供 QA）

| 区域 | 关键断言 |
|------|---------|
| Upsert | 同 raw_card_id 重复 → UPDATE not duplicate |
| Inference | mock conf 0.55 → no scope in response |
| Inference | mock conf 0.72 → ResponsibilityBlock visible |
| Index | contact created → search_document row exists |
| Delete | contact gone + DeleteCardCascade job queued |
| UI | empty state when 0 contacts |

---

## 10. 風險

| 風險 | 緩解 |
|------|------|
| M6 未完成时详情缺公司区 | pending UI；不阻塞 M3 launch |
| inference 延迟 | 详情先显示 OCR；AI 区 skeleton → populate |
| tsvector 中文分词 | MVP 用 simple + pg_trgm；M5 升级 |
| M2 handoff 未就绪 | M3-012 可用 fixture job 本地测 |

---

## 11. 模組接口

| 模块 | 接口 | M3 角色 |
|------|------|---------|
| M2 | ContactUpsertRequested | consumer |
| M2 | DeleteCardCascade | producer（on delete） |
| M6 | CompanyEnrichRequested | producer |
| M6 | CompanyEnriched | consumer（pass 2） |
| M5 | contact_search_documents | producer |
| M8 | Contact display fields | provider |
| M1 | userId/workspaceId | consumer（auth stub） |

---

*ENG M3 v1.0 — SDLC Phase 1*
