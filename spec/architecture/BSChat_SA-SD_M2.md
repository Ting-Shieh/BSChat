# BSChat SA/SD — Module 2：名片收錄（含 OCR）

> **依據**：M2 PM L3 v1.0、PRD v2 DDR-10~20、M3 Handoff 契約  
> **架構模式**：Modular Monolith + Event-driven workers  
> **版本**：v1.0（2026-05-20 補寫，對齊 M3/M6 落盤格式）

---

## 1. 架構概覽

```
┌─────────────────────────────────────────────────────────┐
│              Client (Web PWA · Mobile-first)               │
│  連拍 / 選圖 / 貼 URL / 掃 QR / 待確認列表                  │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS REST
┌────────────────────────▼────────────────────────────────┐
│                   API Server (Modular Monolith)            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Capture API  │  │ Review API   │  │ Import API   │   │
│  │ (M2)         │  │ (M2)         │  │ (M2, P1)     │   │
│  └──────┬───────┘  └──────────────┘  └──────┬───────┘   │
│         │ enqueue                            │ enqueue    │
└─────────┼────────────────────────────────────┼───────────┘
          │                                    │
┌─────────▼────────────────────────────────────▼───────────┐
│              Job Queue (Redis + BullMQ)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ OCR Worker  │  │ URL Resolver│  │ Handoff M3  │      │
│  │ (Claude)    │  │ Worker (P1) │  │ Worker      │      │
│  └─────────────┘  └─────────────┘  └──────┬──────┘      │
└─────────────────────────────────────────────┼─────────────┘
          │                    │              │ outbox
┌─────────▼────────────────────▼──────────────▼─────────────┐
│  PostgreSQL          Object Storage (R2)     Event Bus     │
│  capture_sessions    card-images/            ContactUpsert  │
│  raw_cards           {user_id}/{card_id}    Requested → M3│
│  ocr_results                                                │
│  import_jobs (P1)                                           │
└─────────────────────────────────────────────────────────────┘
```

**為何 Modular Monolith + Worker**：
- OCR 為 I/O 密集（Vision API P95 < 15s），不可阻塞 API route（Vercel 10s 限制）
- 连拍需独立 job 粒度；部分失败不影响其他卡片
- 2 人 MVP 团队；单 repo 部署效率最高

**外部整合**：
| 服務 | 用途 |
|------|------|
| Claude Vision API | LLM-first OCR（DDR-19） |
| Cloudflare R2 | 名片原图存储 |
| Clerk | JWT auth（M1） |
| URL fetcher（P1） | vCard / HTML 解析；需 SSRF 防护 |

### 1.1 架構決策（解 🚧 Blockers）

#### B-1 — OCR 引擎選型 → **DDR-19**

| 方案 | MVP |
|------|-----|
| 傳統 OCR + LLM 後處理 | ❌ |
| **Multimodal LLM 一次完成** | **✅** |
| 自建模型 | ❌ |

```
圖片 → Claude Vision（structured JSON）
     → ocr_results.extracted_fields + field_confidences
```

| 項目 | 規格 |
|------|------|
| 模型 | `claude-sonnet-4-20250514`（vision） |
| 輸出 | JSON：`name, company, title, phones[], emails[], address, website, raw_text` |
| 信心度 | per-field 0.0–1.0；review 三栏皆 ≥0.8 → `auto_accepted` |
| SLA | P95 < 15s |
| 成本 | 单 user 每日 OCR quota 50（可配置） |
| Fallback | API 失败 3 次 → `OCR_FAILED`；保留原图 |

#### B-5 — 電子名片 URL/QR → **DDR-20**

| 優先 | 格式 | 解析 |
|------|------|------|
| P1-a | vCard 文字（QR 含 BEGIN:VCARD） | vCard parser |
| P1-b | vCard URL（.vcf） | HTTP GET → parser |
| P1-c | HTTPS 一般 URL | HTML og/meta + contact pattern |
| P2 | CamCard / HiHello 等平台 | 平台 adapter |

失败 → `IMPORT_FAILED` + `UNSUPPORTED_FORMAT`

---

## 2. L4 Depth Gate

### 2.1 Data Flow

| 階段 | 輸入 | 轉換 | 輸出 | 目的地 |
|------|------|------|------|--------|
| Upload | 圖片 binary | 壓縮、hash | R2 URL + raw_card | PostgreSQL |
| OCR | S3/R2 URL | Claude Vision | extracted_fields + confidences | ocr_results |
| Review | 使用者修正 3 欄 | optimistic lock | confirmed | M3 via event |
| Import（P1） | URL/QR | vCard/HTML parser | extracted_fields | raw_card（跳过 OCR 或低优先验证） |
| Handoff | ocr + raw_card meta | 組裝契約 JSON | ContactUpsertRequested | M3 queue |

```
[展覽連拍]
  POST /capture-sessions → POST /cards (×N, Idempotency-Key)
  → R2 upload → raw_cards(status=uploading)
  → OCR worker → ocr_results + review_status
  → Handoff worker → ContactUpsertRequested
  → M3 Contact 自動建立 → M6 enrich

[延後確認]
  GET /cards?status=pending_review
  → PATCH /cards/:id/review (name, company, title)
  → re-emit ContactUpsertRequested（company 变更 → M3 触发 M6）

[貼連結 P1]
  POST /import-url → import_jobs → URL resolver → handoff
```

### 2.2 State Boundaries

| 狀態 | 存儲 | Owner |
|------|------|-------|
| raw_card.status / review_status | `raw_cards` | **M2** |
| ocr_results（不可變） | `ocr_results` | **M2** |
| capture_session 計數 | `capture_sessions` | **M2** |
| contact 業務資料 | `contacts` | **M3** |
| 圖片 binary | R2 | **M2**（M7 cascade 刪除） |
| Job 狀態 | Redis BullMQ | infra |

**Transaction 邊界**：
- Upload：R2 成功 + DB insert 同一 logical unit（DB 失敗 → orphan cleanup job）
- OCR：`ocr_results` INSERT + `raw_cards` status update **同一 DB transaction**
- Review：raw_card update + outbox emit（at-least-once）

### 2.3 Concurrency

| 場景 | 策略 |
|------|------|
| 連拍 10 張同時 upload | 每張独立 raw_card_id；`Idempotency-Key` 防 client retry |
| 雙端 review 衝突 | `raw_cards.version` optimistic lock → 409 |
| OCR worker 並發 | concurrency=5；job 粒度 raw_card_id |
| image_hash 重複 | 非阻擋；`duplicate_warning`；force 用新 Idempotency-Key |
| session 計數 | `UPDATE ... SET card_count = card_count + 1` 原子操作 |

**Idempotent endpoints**：upload（Idempotency-Key）、import-url（url hash per user）、DELETE

### 2.4 Failure Modes

| 失敗 | 處理 | UX |
|------|------|-----|
| Upload timeout | client retry ≤3 | UPLOAD_RETRYING banner |
| S3/R2 不可用 | 503 + retry-after | STORAGE_UNAVAILABLE |
| Claude timeout | worker 30s；retry 2x → OCR_FAILED | 原图 + 手动填 3 栏 |
| Claude 429 quota | delayed queue | OCR_QUEUED_DELAYED |
| 欄位空白/低信心 | 仍存储；pending_review | ConfidenceDot |
| URL SSRF | block private IP | UNSUPPORTED_URL 400 |
| URL 解析失败 | IMPORT_FAILED | Modal 引导手动新增 |
| DB down | API 503 | SERVICE_UNAVAILABLE |
| M3 handoff 失败 | outbox retry + DLQ | 背景；卡片仍可见 |

### 2.5 Empty State / Cold Start

| 時刻 | 行為 |
|------|------|
| t=0 新用戶 | 0 cards → 收錄 Tab 空状态「拍 3 張…」 |
| 首次開 App | 引导「開始連拍」 |
| 0 張可搜尋 | 「處理中 N 張」 |
| session 0 成功 | 摘要页「本次 0 張成功」 |
| 待確認空 | 全部 auto_accepted → badge 0 或「全部已確認 ✓」 |

**Bootstrap**：M1 註冊 → personal workspace → M2 可 POST /capture-sessions

---

## 3. State Machine

### 3.1 `raw_cards.status`

```
uploading → queued → ocr_processing → ocr_done
                  ↘ ocr_failed (OCR_FAILED)
uploading → upload_failed
```

### 3.2 `raw_cards.review_status`

```
pending_review → confirmed（用户 PATCH review）
auto_accepted（name+company+title 皆 conf≥0.8，OCR 后自动）
```

**DDR-18**：待確認**僅可編輯**姓名、公司、抬頭三欄。

---

## 4. 資料庫設計

### 4.1 `capture_sessions`

```sql
CREATE TABLE capture_sessions (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID NOT NULL,
  workspace_id      UUID NOT NULL,
  source_type       VARCHAR(20),          -- event/meeting/referral/import/other
  source_label      VARCHAR(255),         -- e.g. "Computex 2026"
  status            VARCHAR(20) DEFAULT 'active',  -- active|closed
  card_count        INT DEFAULT 0,
  confirmed_count   INT DEFAULT 0,
  pending_count     INT DEFAULT 0,
  started_at        TIMESTAMPTZ DEFAULT NOW(),
  closed_at         TIMESTAMPTZ,
  deleted_at        TIMESTAMPTZ,
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sessions_user_status ON capture_sessions(user_id, status)
  WHERE deleted_at IS NULL;
CREATE INDEX idx_sessions_workspace_started ON capture_sessions(workspace_id, started_at DESC);
```

**Soft-delete**：`deleted_at`

### 4.2 `raw_cards`

```sql
CREATE TABLE raw_cards (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  capture_session_id  UUID REFERENCES capture_sessions(id),
  user_id             UUID NOT NULL,
  workspace_id        UUID NOT NULL,
  capture_method      VARCHAR(20) NOT NULL,  -- camera_burst|upload|manual|url|qr
  image_url           TEXT,
  image_hash          VARCHAR(64),           -- SHA-256
  source_type         VARCHAR(20),
  source_label        VARCHAR(255),
  status              VARCHAR(30) DEFAULT 'uploading',
  review_status       VARCHAR(20) DEFAULT 'pending_review',
  idempotency_key     VARCHAR(64),
  version             INT DEFAULT 1,
  deleted_at          TIMESTAMPTZ,
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, idempotency_key)
);

CREATE INDEX idx_raw_cards_user_status ON raw_cards(user_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_raw_cards_user_hash ON raw_cards(user_id, image_hash) WHERE deleted_at IS NULL;
CREATE INDEX idx_raw_cards_session ON raw_cards(capture_session_id);
```

**Shared contract**：`id`, `user_id`, `workspace_id`, `image_url`, `source_*`, `capture_method`, `review_status` → M3, M7, M9

### 4.3 `ocr_results`

```sql
CREATE TABLE ocr_results (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_card_id         UUID UNIQUE NOT NULL REFERENCES raw_cards(id),
  engine              VARCHAR(50) NOT NULL,   -- claude-sonnet-vision
  engine_version      VARCHAR(20) NOT NULL,
  raw_text            TEXT,
  extracted_fields    JSONB NOT NULL,
  field_confidences   JSONB NOT NULL,
  overall_confidence  FLOAT,
  processed_at        TIMESTAMPTZ NOT NULL,
  duration_ms         INT,
  error_message       TEXT
);

CREATE INDEX idx_ocr_fields ON ocr_results USING GIN(extracted_fields);  -- P2
```

**extracted_fields schema v1**：
```json
{
  "name": "王小明",
  "company": "ABC Tech",
  "title": "OEM 業務經理",
  "phones": ["0912-345-678"],
  "emails": ["wang@abc.com"],
  "address": "台北市...",
  "website": "https://abc-tech.com.tw"
}
```

### 4.4 `import_jobs`（P1）

```sql
CREATE TABLE import_jobs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_card_id     UUID NOT NULL REFERENCES raw_cards(id),
  input_url       TEXT NOT NULL,
  resolver_type   VARCHAR(20),     -- vcard_text|vcard_url|html_scrape
  status          VARCHAR(20) DEFAULT 'pending',
  error_code      VARCHAR(50),
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 5. API 規格

**Base**：`/api/v1` · Bearer JWT（Clerk）· 统一错误格式

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human readable",
    "details": [{ "field": "image", "reason": "..." }]
  }
}
```

| Method | Path | 说明 | Idempotent | Rate limit |
|--------|------|------|------------|------------|
| POST | `/capture-sessions` | 建立 session | ❌ | 10/min/user |
| PATCH | `/capture-sessions/:id` | source_label / close | close ✅ | 30/min |
| POST | `/capture-sessions/:id/cards` | 上传单张 multipart | ✅ Idempotency-Key | 60/min |
| POST | `/capture-sessions/:id/cards/batch` | 批次 ≤20 | ✅ | 10/min |
| GET | `/cards` | 列表 filter status/session | ✅ | 60/min |
| GET | `/cards/:id` | 详情 + ocr_result | ✅ | 60/min |
| PATCH | `/cards/:id/review` | 确认 3 栏 | ❌ version lock | 30/min |
| DELETE | `/cards/:id` | soft-delete | ✅ | 30/min |
| POST | `/cards/import-url` | 贴连结（P1） | ✅ url hash | 20/min |
| POST | `/cards/import-qr` | QR 内容（P1） | ✅ | 20/min |
| POST | `/cards/manual` | 手动新增（P1） | ❌ | 20/min |

### POST `/capture-sessions/:id/cards`

**Request**：
```
Content-Type: multipart/form-data
Idempotency-Key: {client-uuid}
Body: image (file), capture_method (optional)
```

**Response 202**：
```json
{
  "raw_card_id": "uuid",
  "status": "uploading",
  "capture_session_id": "uuid",
  "duplicate_warning": null
}
```

`duplicate_warning` 示例：
```json
{
  "previous_card_id": "uuid",
  "scanned_at": "2026-05-10T14:00:00Z",
  "message": "3 天前可能掃過相同名片"
}
```

### PATCH `/cards/:id/review`

```json
{
  "name": "王小明",
  "company": "ABC Tech",
  "title": "OEM 業務經理",
  "version": 3
}
```

- 成功 → re-emit `ContactUpsertRequested`
- **409** version mismatch

---

## 6. Event 契約 — M3 Handoff

### 6.1 `ContactUpsertRequested`（M2 → M3）

```typescript
interface ContactUpsertRequested {
  eventId: string;
  userId: string;
  workspaceId: string;
  rawCardId: string;
  fields: {
    name: string | null;
    company: string | null;
    title: string | null;
    phones: string[];
    emails: string[];
    address: string | null;
    website: string | null;
  };
  fieldConfidences: Record<string, number>;
  provenance: {
    source: 'ocr' | 'manual' | 'import';
    sourceRef: string;          // raw_card_id
  };
  sourceType: string | null;    // event/meeting/...
  sourceLabel: string | null;   // "Computex 2026"
  captureMethod: string;
  imageUrl: string | null;
  reviewStatus: 'auto_accepted' | 'confirmed' | 'pending_review';
  occurredAt: string;           // ISO8601
}
```

**触发时机**：
- OCR 完成（`auto_accepted` 或 `pending_review` 皆 emit；M3 建立 Contact）
- PATCH review → `confirmed` 或 company 变更 re-emit

**Queue**：`handoff-m3` · retry 3x + DLQ · outbox pattern

**M6 说明**：M2 **不直接** emit `CompanyEnrichRequested`；由 M3 upsert 后触发（SA/SD M3 契約）

### 6.2 `DeleteCardCascade`（M3 → M2，消费）

```typescript
interface DeleteCardCascade {
  rawCardId: string;
  userId: string;
  occurredAt: string;
}
```

M2 worker：soft-delete raw_card + R2 图片（M7 策略）

---

## 7. OCR Worker 要点

```typescript
async function processOcr(rawCardId: string) {
  const card = await getRawCard(rawCardId);
  const imageBytes = await r2.get(card.imageUrl);

  const result = await claudeVision.extract(imageBytes, OCR_PROMPT_V1);

  const reviewFields = ['name', 'company', 'title'];
  const autoAccept = reviewFields.every(f => result.field_confidences[f] >= 0.8);
  const reviewStatus = autoAccept ? 'auto_accepted' : 'pending_review';

  await db.$transaction(async (tx) => {
    await tx.ocrResult.create({ data: { rawCardId, ...result } });
    await tx.rawCard.update({
      where: { id: rawCardId },
      data: { status: 'ocr_done', reviewStatus },
    });
    await outbox.emit(tx, 'ContactUpsertRequested', buildHandoffPayload(card, result, reviewStatus));
  });

  await updateSessionCounts(card.captureSessionId);
}
```

---

## 8. 🔗 Coupling Map

### Shared Entities

| Entity | Owner | Consumers | Contract |
|--------|-------|-----------|----------|
| `raw_cards` | M2 | M3, M7, M9 | id, user_id, image_url, source_*, review_status |
| `ocr_results` | M2 | M3, M5（via M3） | extracted_fields v1, field_confidences, raw_text |
| `capture_sessions` | M2 | M5, M9 | source_type, source_label, card_count |
| `user_id / workspace_id` | M1 | 全部 | JWT claims |

### Cross-module Contracts

| From | To | Event/API | Trigger | Sync/Async |
|------|-----|-----------|---------|------------|
| M2 | M3 | ContactUpsertRequested | OCR done / review confirmed | Async |
| M3 | M2 | DeleteCardCascade | Contact deleted | Async |
| M1 | M2 | JWT | every request | Sync |

### Cross-cutting Concerns

| Concern | M2 实现 |
|---------|---------|
| Auth | 所有 endpoint JWT；raw_card.user_id 必须 match |
| Audit | card_uploaded, ocr_completed, card_reviewed（M9） |
| Privacy | R2 path 含 user_id；signed URL 1h expiry |
| Idempotency | Upload / import 必带 key |
| Rate limit | 见 API 表 |

---

## 9. DDR（M2 模块）

| ID | 决策 | 理由 |
|----|------|------|
| DDR-18 | 待確認欄位 = 姓名 + 公司 + 抬頭 | 訪談「簡單」定義 |
| DDR-19 | MVP OCR = Claude Vision LLM-first | B-1 选型 |
| DDR-20 | URL/QR MVP = vCard + HTML fallback | B-5 选型 |
| DDR-21 | auto_accepted 仍 emit handoff；M3 建立 Contact | 背景建档 |
| DDR-22 | pending_review 仍可被 M5 索引（经 M3） | 不惩罚未确认 |

*DDR-10~17 见 PRD v2 §4（产品层）*

---

## 10. Open Blockers

| 🚧 | 议题 | 状态 |
|----|------|------|
| B-1 | OCR 引擎选型 | ✅ DDR-19 |
| B-5 | URL/QR 格式 | ✅ DDR-20 |
| B-4 | Aha moment 最低名片数 | ✅ ≥3 张 OCR done（UI/ENG） |

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

**M2 SA/SD L4：✅ 可锁定**（文件补写完成）

---

## 12. 下游文件对齐

| 文件 | 引用本文件 |
|------|-----------|
| `spec/design/BSChat_UIUX_M2.md` | 流程、错误态、DDR-18 |
| `spec/engineering/BSChat_ENG_M2.md` | Prisma、API、Worker 实现 |
| `spec/qa/BSChat_QA_M2.md` | TC-M2-* 测试案例 |
| `spec/architecture/BSChat_SA-SD_M3.md` | ContactUpsertRequested consumer |

---

*SA/SD M2 v1.0 — SDLC Phase 1（2026-05-20 補寫）*
