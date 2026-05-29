# BSChat SA/SD — Module 3：聯絡人結構化與審核

> **依據**：M3 PM L3、M2 Handoff 契約、DDR-21~24  
> **架構模式**：Modular Monolith + Event-driven workers（延續 M2）

---

## 1. 架構概覽

```
┌─────────────────────────────────────────────────────────────┐
│                     Event Bus (Redis Pub/Sub / BullMQ)       │
│  ContactUpsertRequested ← M2                                 │
│  CompanyEnriched        ← M6                                 │
│  ContactIndexRequested  ← M3                                 │
│  DeleteCardCascade      → M2                                 │
└───────────────┬─────────────────────────────┬───────────────┘
                │                             │
┌───────────────▼──────────────┐   ┌──────────▼───────────────┐
│  Contact Upsert Worker (M3)  │   │  Inference Worker (M3)   │
│  - consume handoff           │   │  - Claude prompt           │
│  - upsert contact            │   │  - confidence gate 0.6     │
│  - write provenance          │   │  - supersede on re-run     │
│  - emit enrich + index       │   └──────────────────────────┘
└───────────────┬──────────────┘
                │
┌───────────────▼──────────────────────────────────────────────┐
│  PostgreSQL                                                   │
│  contacts | contact_field_provenance | manual_overrides       │
│  responsibility_inferences | contact_raw_card_map             │
└───────────────┬──────────────────────────────────────────────┘
                │ index document
┌───────────────▼──────────────┐
│  Search Index (M5 占位)       │
│  MVP: PostgreSQL tsvector +   │
│        pgvector embedding     │
└──────────────────────────────┘
```

**MVP 搜索索引策略（DDR-25）**：不等待 M5 完整方案，M3 先写 `contact_search_documents` 表 + tsvector；M5 接入时升级 pgvector/外部引擎。

---

## 2. L4 Depth Gate

### 2.1 Data Flow

```
[M2 OCR/Review Complete]
        │
        ▼ ContactUpsertRequested (async)
[M3 Upsert Worker]
        ├─ INSERT/UPDATE contacts
        ├─ UPSERT contact_field_provenance (per field)
        ├─ IF company_name present → CompanyEnrichRequested → M6
        ├─ Enqueue ResponsibilityInferenceJob (pass 1)
        └─ Enqueue ContactIndexJob
                │
                ▼
[M3 Inference Worker - pass 1]
        Input: title + company_name
        Output: responsibility_inferences (if conf ≥ 0.6)
                │
                ▼ (async, when M6 ready)
[M6 CompanyEnriched event]
        │
        ▼
[M3 Inference Worker - pass 2]
        Input: title + company_name + company_products
        Supersede pass 1 if new confidence higher
                │
                ▼
[M3 Index Worker]
        Write contact_search_documents
        search_status → indexed
                │
                ▼
[M5 Search] (future consumer)
```

### 2.2 State Boundaries

| 状态 | 存储 | Owner |
|------|------|-------|
| Contact 业务字段 | `contacts` 表 | M3 |
| 字段 provenance | `contact_field_provenance` | M3 |
| 用户修正 | `manual_overrides` | M3 |
| OCR 原始 | `ocr_results` | M2（只读） |
| AI 职责推估 | `responsibility_inferences` | M3 |
| 公司补全 | `companies` / enrichments | M6 |
| 搜索文档 | `contact_search_documents` | M3 写 / M5 读 |
| Job 状态 | Redis BullMQ | infra |

**Transaction 边界**：
- Upsert：`contacts` + `provenance` + `raw_card_map` 同一 DB transaction
- Event emit：Outbox pattern（`outbox_events` 表）与 transaction 同事务提交
- Inference：独立 transaction；失败不影响 Contact ACTIVE 状态

### 2.3 Concurrency

| 场景 | 策略 |
|------|------|
| 同一 raw_card 重复 handoff | Upsert idempotent by `raw_card_id` UNIQUE |
| M2 review + M3 详情编辑冲突 | `contacts.version` optimistic lock；409 |
| 两次 inference（pass1/pass2） | pass2 `supersede` pass1；UI 读 `status=active` 最新 |
| 并发 index | index job idempotent by `contact_id + content_hash` |
| 删除 vs 编辑 | 软删除后 reject 所有 mutation 410 |

### 2.4 Failure Modes

| 失败 | 处理 | UX |
|------|------|-----|
| handoff 格式错误 | DLQ + alert | 后台；卡片在 M2 仍可见 |
| 缺 name+company | 仍 CREATE；display_name=未命名 | 列表 badge |
| inference API 失败 | retry 2x → 留空 scope | 不显示推估区 |
| M6 enrich 失败/超时 | Contact 仍 active | 详情「公司资料补充中」 |
| index 失败 | search_status=pending_index；retry | 搜索可能暂缺 |
| cascade delete 失败 | DLQ retry | 「删除中」 |
| DB down | API 503 | 全局错误页 |

### 2.5 Empty State / Cold Start

| 时刻 | 行为 |
|------|------|
| t=0 无 Contact | 名片库空状态 → 引导收录 Tab |
| 首笔 handoff | Contact 自动出现；无需用户操作 |
| 0 responsibility（低信心） | 详情页隐藏推估区；不显示空白占位 |
| 0 company enrich | 详情仅 OCR 字段；M6 区显示 pending |

---

## 3. 資料庫設計

### 3.1 `contacts`

```sql
CREATE TABLE contacts (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               UUID NOT NULL,
  workspace_id          UUID NOT NULL,
  raw_card_id           UUID UNIQUE NOT NULL,  -- 1:1 MVP
  display_name          VARCHAR(255),
  company_name          VARCHAR(255),
  title                 VARCHAR(255),
  responsibility_scope    TEXT,                   -- nullable, conf≥0.6 only
  responsibility_confidence FLOAT,
  phones                JSONB DEFAULT '[]',       -- [{value, normalized, primary}]
  emails                JSONB DEFAULT '[]',
  address               TEXT,
  website               VARCHAR(512),
  source_type           VARCHAR(20),
  source_label          VARCHAR(255),
  capture_method        VARCHAR(20),
  review_status         VARCHAR(20) DEFAULT 'unconfirmed',  -- unconfirmed|confirmed
  search_status         VARCHAR(20) DEFAULT 'pending_index', -- pending_index|indexed
  company_id            UUID,                     -- FK M6, nullable
  image_url             TEXT,
  version               INT DEFAULT 1,
  deleted_at            TIMESTAMPTZ,
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  updated_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_contacts_user_updated ON contacts(user_id, updated_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_contacts_user_company ON contacts(user_id, company_name) WHERE deleted_at IS NULL;
CREATE INDEX idx_contacts_search_status ON contacts(search_status) WHERE deleted_at IS NULL;
```

**Soft-delete**：`deleted_at`；hard-delete 由 M7 cascade job。

### 3.2 `contact_field_provenance`

```sql
CREATE TABLE contact_field_provenance (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id    UUID NOT NULL REFERENCES contacts(id),
  field_name    VARCHAR(50) NOT NULL,
  current_value TEXT,
  source        VARCHAR(20) NOT NULL,  -- ocr|manual|ai_inferred|import
  source_ref    UUID,
  confidence    FLOAT,
  updated_at    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(contact_id, field_name)
);
```

### 3.3 `manual_overrides`

```sql
CREATE TABLE manual_overrides (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id      UUID NOT NULL REFERENCES contacts(id),
  field_name      VARCHAR(50) NOT NULL,
  original_value  TEXT,
  override_value  TEXT NOT NULL,
  overridden_by   UUID NOT NULL,
  overridden_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_overrides_contact ON manual_overrides(contact_id);
```

### 3.4 `responsibility_inferences`

```sql
CREATE TABLE responsibility_inferences (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id      UUID NOT NULL REFERENCES contacts(id),
  inferred_scope  TEXT NOT NULL,
  confidence      FLOAT NOT NULL,
  inputs_used     JSONB,
  model           VARCHAR(50),
  prompt_version  VARCHAR(20),
  pass_number     INT DEFAULT 1,         -- 1=post-create, 2=post-enrich
  status          VARCHAR(20) DEFAULT 'active',  -- active|superseded|rejected
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_inference_contact_active ON responsibility_inferences(contact_id) WHERE status = 'active';
```

### 3.5 `contact_search_documents`（M5 前置）

```sql
CREATE TABLE contact_search_documents (
  contact_id      UUID PRIMARY KEY REFERENCES contacts(id),
  user_id         UUID NOT NULL,
  workspace_id    UUID NOT NULL,
  search_text     TEXT NOT NULL,          -- 拼接所有可搜字段
  search_vector   TSVECTOR,               -- tsvector index
  embedding       VECTOR(1536),           -- nullable, M5 启用
  content_hash    VARCHAR(64),
  indexed_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_search_vector ON contact_search_documents USING GIN(search_vector);
```

---

## 4. API 規格

**Base**：`/api/v1` · Bearer JWT（M1 stub：dev header）

| Method | Path | 说明 | Idempotent |
|--------|------|------|------------|
| GET | `/contacts` | 列表 paginated | ✅ |
| GET | `/contacts/:id` | 详情 + provenance + active inference | ✅ |
| PATCH | `/contacts/:id` | 编辑字段 + version | ❌ |
| DELETE | `/contacts/:id` | soft-delete + cascade event | ✅ |
| POST | `/contacts/:id/reject-inference` | 用户 reject AI 推估 | ✅ |
| GET | `/contacts/:id/provenance` | 字段来源详情 | ✅ |

### GET `/contacts`

**Query**：`page`, `limit`, `review_status`, `source_label`, `q`（简单前缀搜索 MVP）

**Response 200**：
```json
{
  "data": [{
    "id": "uuid",
    "display_name": "王小明",
    "company_name": "ABC Tech",
    "title": "OEM 業務經理",
    "responsibility_scope": "可能負責 OEM 通路",
    "responsibility_confidence": 0.67,
    "source_label": "Computex 2026",
    "review_status": "unconfirmed",
    "image_url": "...",
    "company_products_preview": null
  }],
  "pagination": { "page": 1, "limit": 20, "total": 45 }
}
```

### GET `/contacts/:id`

**Response** 含分区：
```json
{
  "id": "uuid",
  "sections": {
    "card_original": {
      "fields": [
        { "name": "name", "value": "王小明", "source": "ocr", "confidence": 0.95 }
      ],
      "image_url": "..."
    },
    "ai_inferred": {
      "responsibility_scope": { "value": "...", "confidence": 0.67, "source": "ai_inferred", "pass": 2 }
    },
    "company_enrichment": null
  },
  "source_type": "event",
  "source_label": "Computex 2026",
  "version": 3
}
```

### PATCH `/contacts/:id`

```json
{
  "fields": {
    "company_name": "ABC Technology Co."
  },
  "version": 3
}
```

- 写 `manual_overrides` + 更新 provenance source=manual
- 若 company_name 变更 → emit `CompanyEnrichRequested`

### DELETE `/contacts/:id`

- soft-delete contact
- emit `DeleteCardCascade { raw_card_id }`

**Rate limits**：GET 60/min · PATCH/DELETE 30/min

---

## 5. Responsibility Inference 设计

### 5.1 Prompt 策略（Claude）

**Pass 1**（Contact 创建后）：
```
Input: title="{title}", company="{company_name}"
Task: 推测此人在该公司的可能负责业务范围（1-2句）
Output JSON: { "scope": "...", "confidence": 0.0-1.0 }
Rule: 若 title 过于泛化（如"经理"）且缺公司信息，confidence 应 < 0.6
```

**Pass 2**（M6 enrich 后）：
```
Input: title, company, products="{company.main_products}"
Task: 同上，但结合公司产品推断更精确
Supersede pass 1 if new confidence > old
```

### 5.2 Confidence Gate（DDR-9 / PM R-2）

```typescript
if (result.confidence < 0.6) {
  // 不写入 contacts.responsibility_scope
  // 不显示 UI 区块
  return;
}
contacts.responsibility_scope = result.scope;
contacts.responsibility_confidence = result.confidence;
```

---

## 6. M5 Index Document 契约（提前定义）

```typescript
interface ContactSearchDocument {
  contact_id: string;
  user_id: string;
  workspace_id: string;
  display_name: string;
  company_name: string;
  title: string;
  responsibility_scope?: string;
  company_products?: string[];      // from M6
  source_label?: string;
  phones: string[];
  emails: string[];
  raw_text?: string;                // from M2 ocr
  review_status: 'unconfirmed' | 'confirmed';
  updated_at: string;
}
```

**Index 权重建议**（M5 参考）：
- company_products: 高
- responsibility_scope: 高
- company_name / title: 中
- source_label: 中
- confirmed > unconfirmed: +10% boost

---

## 7. 🔗 Coupling Map 更新

### Shared Entities（新增）

| Entity | Owner | Consumers | Contract |
|--------|-------|-----------|----------|
| `contacts` | M3 | M5,M6,M8,M4,M7 | id, user_id, display_name, company_name, title, responsibility_scope, company_id |
| `contact_search_documents` | M3 write | M5 read | search_text, search_vector, embedding |
| `responsibility_inferences` | M3 | M5 UI explain | inferred_scope, confidence, status |

### Cross-module Contracts（新增）

| From | To | Event | Trigger |
|------|-----|-------|---------|
| M2 | M3 | ContactUpsertRequested | OCR done / review |
| M3 | M6 | CompanyEnrichRequested | company_name present/changed |
| M6 | M3 | CompanyEnriched | enrich complete |
| M3 | M5 | ContactIndexed | index job done |
| M3 | M2 | DeleteCardCascade | contact deleted |
| M4 | M3 | DuplicateSuspected | P1 dedup match |

---

## 8. DDR 新增

| ID | 决策 |
|----|------|
| DDR-25 | MVP 搜索索引用 PostgreSQL tsvector；pgvector 字段预留，M5 启用 |
| DDR-26 | Inference pass-2 仅在 M6 enrich 成功且 products 非空时运行 |
| DDR-27 | GET /contacts/:id 响应分区：card_original / ai_inferred / company_enrichment |

---

## 9. L4 Depth Gate 自检

| Gate | 状态 |
|------|------|
| Data flow | ✅ |
| State boundaries | ✅ |
| Concurrency | ✅ |
| Failure modes | ✅ |
| Empty state | ✅ |
| Coupling Map | ✅ |

**M3 SA/SD L4：✅ 可锁定**

---

*SA/SD M3 v1.0 — SDLC Phase 1*
