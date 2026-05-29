# BSChat ENG — Module 2：名片收錄（含 OCR）

> **依據**：M2 PM L3、M2 SA/SD L4、M2 UI/UX、`BSChat_Design_Foundation.md`  
> **團隊**：2 人（1 full-stack + 1 product/design）  
> **M2 估算**：~5–7 工程日（1 人 full-stack）

---

## 1. 技術選型 / Technology Stack

### 1.1 總覽

| 層級 | 選型 | 理由 |
|------|------|------|
| **Frontend** | Next.js 15 (App Router) + TypeScript | SSR/PWA、API Routes 同 repo、mobile-first、2 人團隊效率最高 |
| **UI** | Tailwind CSS 4 + shadcn/ui | 對齊 Design Token；元件可快速組裝 |
| **State** | TanStack Query + Zustand | Query 管 server state；Zustand 管 capture session UI state |
| **Backend** | Next.js Route Handlers (`/app/api/v1/*`) | Modular Monolith（SA/SD 決策） |
| **ORM** | Prisma | 型別安全、migration 內建 |
| **DB** | PostgreSQL (Neon) | SA/SD schema；serverless 友好 |
| **Cache/Queue** | Redis (Upstash) + BullMQ | OCR/Handoff 背景 job |
| **Worker** | 獨立 Node process（同 monorepo） | BullMQ consumer；不阻塞 Vercel serverless 10s 限制 |
| **Object Storage** | Cloudflare R2 | 圖片儲存；S3-compatible、成本低 |
| **OCR** | Claude Sonnet Vision API | DDR-19 LLM-first |
| **Auth** | Clerk | MVP 快速整合；M1 最小 workspace 可後接 |
| **Deploy** | Vercel (web+API) + Railway (worker) | Web 與 worker 分離部署 |
| **CI/CD** | GitHub Actions | lint + typecheck + test on PR |
| **Monitoring** | Sentry + Vercel Analytics | 錯誤追蹤 + 基本效能 |

### 1.2 未選方案

| 方案 | 不選原因 |
|------|---------|
| React Native 原生 App | 2 人團隊 + 2–4 週 MVP；PWA 足夠展覽連拍 |
| NestJS 獨立後端 | 多 repo、多部署；Next.js 全端夠用 |
| Supabase Storage only | R2 成本更低；已有 SA/SD S3 path 設計 |
| Google Document AI | MVP 先驗證 LLM-first；pilot 後再評估降本 |
| tRPC | REST 已 SA/SD 定義；OpenAPI 合約清晰 |

### 1.3 環境變數（M2 相關）

```bash
# Database
DATABASE_URL=
# Redis
REDIS_URL=
# Storage
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
R2_PUBLIC_URL=
# AI
ANTHROPIC_API_KEY=
OCR_MODEL=claude-sonnet-4-20250514
OCR_DAILY_QUOTA_PER_USER=50
# Auth
CLERK_SECRET_KEY=
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
# App
NEXT_PUBLIC_APP_URL=
WORKER_CONCURRENCY=5
```

---

## 2. Monorepo 結構

```
bschat/
├── apps/
│   ├── web/                    # Next.js 15
│   │   ├── app/
│   │   │   ├── (tabs)/         # 搜尋/名片庫/收錄/待確認/我的
│   │   │   ├── api/v1/         # REST API
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── capture/        # M2 元件
│   │   │   ├── ui/             # shadcn
│   │   │   └── design-system/  # Token wrappers
│   │   ├── lib/
│   │   │   ├── api-client.ts
│   │   │   └── design-tokens.css
│   │   └── hooks/
│   └── worker/                 # BullMQ consumers
│       ├── jobs/
│       │   ├── ocr.job.ts
│       │   ├── url-import.job.ts
│       │   └── handoff-m3.job.ts
│       └── index.ts
├── packages/
│   ├── db/                     # Prisma schema + client
│   ├── shared/                 # types, constants, validators
│   └── queue/                  # BullMQ queue definitions
├── prisma/
│   └── schema.prisma
└── .github/workflows/ci.yml
```

---

## 3. 前端架構（M2 相關）

### 3.1 路由

| Path | 畫面 | 優先 |
|------|------|------|
| `/capture` | 收錄 Tab（空狀態 / 入口） | P0 |
| `/capture/burst` | 連拍全屏 | P0 |
| `/capture/session/[id]` | Session 摘要 | P0 |
| `/capture/import-url` | 貼連結 | P1 |
| `/capture/scan-qr` | QR 掃描 | P1 |
| `/review` | 待確認列表 | P0 |
| `/review/[cardId]` | 單張核对 | P0 |

### 3.2 元件階層

```
CapturePage
├── PrivacyStrip
├── CaptureEmptyState
└── CaptureActions
    ├── BurstCaptureButton → /capture/burst
    ├── ImportUrlButton    → /capture/import-url (P1)
    └── ScanQrButton       → /capture/scan-qr (P1)

BurstCapturePage
├── CaptureSessionHeader
├── CameraViewfinder       # getUserMedia / input capture
├── ShutterButton          # Accent 72px
├── ThumbnailStrip
│   └── ThumbnailItem      # status: uploading/ocr/failed
└── UploadProgressBar

ReviewPage
├── ReviewHintBar
└── ReviewCardList
    └── ReviewCard           # swipeable
        ├── CardImagePreview
        ├── ReviewField x3   # name, company, title
        └── ConfidenceDot

ReviewDetailPage
├── CardImageFull
├── ReviewForm (3 fields)
└── ReadonlyOcrFields      # phone/email grey
```

### 3.3 State 策略

| State | 工具 | 說明 |
|-------|------|------|
| cards list, session | TanStack Query | `useCards()`, `useCaptureSession()` |
| burst thumbnails, upload progress | Zustand `captureStore` | 本地 optimistic UI |
| camera stream | React ref + hook | 不持久化 |

### 3.4 API Client

```typescript
// lib/api/capture.ts
export const captureApi = {
  createSession: (body) => POST('/api/v1/capture-sessions', body),
  uploadCard: (sessionId, file, idempotencyKey) =>
    POST(`/api/v1/capture-sessions/${sessionId}/cards`, formData, {
      headers: { 'Idempotency-Key': idempotencyKey },
    }),
  listCards: (params) => GET('/api/v1/cards', { params }),
  reviewCard: (id, body) => PATCH(`/api/v1/cards/${id}/review`, body),
  importUrl: (url) => POST('/api/v1/cards/import-url', { url }),
};
```

Polling：OCR 完成前 `refetchInterval: 2000` on session/card queries；P1 可改 SSE。

### 3.5 PWA / 相機

- `next-pwa` 或 `@vite-pwa` equivalent for Next
- Mobile：`input[type=file][capture=environment]` fallback if getUserMedia denied
- 連拍：連續 trigger capture without leaving camera view
- Image client-side compress：`browser-image-compression` → max 2048px before upload

### 3.6 Design Token 落地

`apps/web/lib/design-tokens.css` — 直接對應 `BSChat_Design_Foundation.md` §3 CSS variables。

shadcn 主題 override：
- `--primary` → `#0F4C5C`
- `--accent` → `#D97706`（快门用 custom class）

### 3.7 前端測試

| 類型 | 工具 | 範圍 |
|------|------|------|
| Unit | Vitest | validators, idempotency key gen |
| Component | Testing Library | ReviewCard, ThumbnailStrip |
| E2E | Playwright | 連拍 mock camera → upload → review flow |

---

## 4. 後端架構（M2 相關）

### 4.1 分層

```
Route Handler (app/api/v1/...)
    → Middleware (auth, rateLimit, validate)
    → Service (capture.service.ts, review.service.ts)
    → Repository (prisma)
    → Queue (enqueue OCR / import / handoff)
```

### 4.2 核心 Service

```typescript
// capture.service.ts
class CaptureService {
  async createSession(userId, workspaceId, dto): Promise<CaptureSession>
  async uploadCard(sessionId, userId, file, idempotencyKey): Promise<RawCard>
  async closeSession(sessionId, userId): Promise<CaptureSession>
  async checkDuplicate(userId, imageHash): Promise<DuplicateWarning | null>
}

// review.service.ts
class ReviewService {
  async reviewCard(cardId, userId, { name, company, title, version }): Promise<RawCard>
  // optimistic lock → 409 on version mismatch
}

// ocr.service.ts (used by worker)
class OcrService {
  async extractFields(imageUrl: string): Promise<OcrResult>
  // Claude Vision structured output
}
```

### 4.3 Middleware 順序

```
1. clerkAuth()           → req.userId, workspaceId
2. rateLimiter(endpoint) → per SA/SD limits
3. validate(zodSchema)
4. handler
5. errorHandler          → unified { error: { code, message, details } }
```

### 4.4 Background Jobs

| Queue | Job | Concurrency | Retry |
|-------|-----|-------------|-------|
| `ocr` | processOcr(rawCardId) | 5 | 2x exponential |
| `import` | resolveUrl(rawCardId) | 3 | 1x |
| `handoff` | contactUpsert(payload) | 5 | 3x + DLQ |

Outbox pattern：`domain_events` table 或 BullMQ job id 作為 at-least-once handoff。

### 4.5 Claude OCR Prompt 契約

```typescript
// Worker output schema (Zod)
const OcrOutputSchema = z.object({
  name: z.string().nullable(),
  company: z.string().nullable(),
  title: z.string().nullable(),
  phones: z.array(z.string()),
  emails: z.array(z.string()),
  address: z.string().nullable(),
  website: z.string().nullable(),
  raw_text: z.string(),
  field_confidences: z.record(z.number().min(0).max(1)),
});
```

Review status logic:
```typescript
const reviewFields = ['name', 'company', 'title'];
const autoAccept = reviewFields.every(f => confidences[f] >= 0.8);
```

### 4.6 安全

- Upload：magic bytes 驗證（非僅 extension）
- URL import：SSRF blocklist（private IP, localhost, metadata IP）
- Signed URL：R2 presigned PUT for upload；GET 1h expiry
- Rate limit：Upstash Ratelimit per SA/SD table

---

## 5. 模組拆分 — M2 Ticket 清單

### Sprint M2-A（P0 核心，3–4 天）

| ID | Ticket | FE | BE | DB | 估時 |
|----|--------|----|----|-----|------|
| M2-001 | Monorepo scaffold + Prisma schema (M2 tables) | ✓ | ✓ | ✓ | 0.5d |
| M2-002 | Design tokens + Bottom Tab shell | ✓ | — | — | 0.5d |
| M2-003 | POST /capture-sessions + GET/PATCH | — | ✓ | ✓ | 0.5d |
| M2-004 | POST /cards upload + R2 presigned + idempotency | — | ✓ | ✓ | 1d |
| M2-005 | OCR worker (Claude Vision) + status update | — | ✓ | ✓ | 1d |
| M2-006 | Burst capture UI (camera + thumbnail strip) | ✓ | — | — | 1d |
| M2-007 | GET /cards list + status filters | — | ✓ | — | 0.5d |
| M2-008 | Review API PATCH + optimistic lock | — | ✓ | — | 0.5d |
| M2-009 | Review UI (list + 3-field form + swipe) | ✓ | — | — | 1d |
| M2-010 | Session summary + Aha modal (≥3 OCR done) | ✓ | — | — | 0.5d |
| M2-011 | Error states (upload retry, OCR failed) | ✓ | ✓ | — | 0.5d |
| M2-012 | Handoff M3 job stub (event emit) | — | ✓ | — | 0.5d |

### Sprint M2-B（P1 擴展，2–3 天）

| ID | Ticket | FE | BE | 估時 |
|----|--------|----|----|------|
| M2-013 | POST /import-url + URL resolver worker | ✓ | ✓ | 1d |
| M2-014 | QR scan UI + POST /import-qr | ✓ | ✓ | 0.5d |
| M2-015 | Duplicate hash warning (non-blocking) | ✓ | ✓ | 0.5d |
| M2-016 | POST /cards/manual (無圖) | ✓ | ✓ | 0.5d |
| M2-017 | OCR daily quota + delayed queue | — | ✓ | 0.5d |
| M2-018 | Playwright E2E: burst → review flow | ✓ | — | 0.5d |

### 依賴圖

```
M2-001 → M2-003 → M2-004 → M2-005 → M2-012
              ↓
M2-002 → M2-006 → M2-010
              ↓
M2-007 → M2-008 → M2-009
M2-001 (M1 stub: Clerk auth + workspace_id in JWT)
```

**M1 最小依賴（M2 阻塞項）**：
- Clerk 登入
- `users` + `workspaces` 表；註冊時 auto-create personal workspace
- 估時：1d（可與 M2-001 並行）

---

## 6. Prisma Schema 片段（M2）

```prisma
model CaptureSession {
  id              String   @id @default(uuid())
  userId          String   @map("user_id")
  workspaceId     String   @map("workspace_id")
  sourceType      String?  @map("source_type")
  sourceLabel     String?  @map("source_label")
  status          String   @default("active")
  cardCount       Int      @default(0) @map("card_count")
  confirmedCount  Int      @default(0) @map("confirmed_count")
  pendingCount    Int      @default(0) @map("pending_count")
  startedAt       DateTime @default(now()) @map("started_at")
  closedAt        DateTime? @map("closed_at")
  deletedAt       DateTime? @map("deleted_at")
  rawCards        RawCard[]

  @@index([userId, status])
  @@map("capture_sessions")
}

model RawCard {
  id                String   @id @default(uuid())
  captureSessionId  String?  @map("capture_session_id")
  userId            String   @map("user_id")
  workspaceId       String   @map("workspace_id")
  captureMethod     String   @map("capture_method")
  imageUrl          String?  @map("image_url")
  imageHash         String?  @map("image_hash")
  sourceType        String?  @map("source_type")
  sourceLabel       String?  @map("source_label")
  status            String   @default("uploading")
  reviewStatus      String   @default("pending_review") @map("review_status")
  idempotencyKey    String?  @map("idempotency_key")
  version           Int      @default(1)
  deletedAt         DateTime? @map("deleted_at")
  createdAt         DateTime @default(now()) @map("created_at")
  updatedAt         DateTime @updatedAt @map("updated_at")
  ocrResult         OcrResult?
  importJob         ImportJob?

  @@unique([userId, idempotencyKey])
  @@index([userId, status])
  @@index([userId, imageHash])
  @@map("raw_cards")
}

model OcrResult {
  id                String   @id @default(uuid())
  rawCardId         String   @unique @map("raw_card_id")
  engine            String
  engineVersion     String   @map("engine_version")
  rawText           String?  @map("raw_text")
  extractedFields   Json     @map("extracted_fields")
  fieldConfidences  Json     @map("field_confidences")
  overallConfidence Float?   @map("overall_confidence")
  processedAt       DateTime @map("processed_at")
  durationMs        Int?     @map("duration_ms")
  rawCard           RawCard  @relation(fields: [rawCardId], references: [id])

  @@map("ocr_results")
}
```

---

## 7. Definition of Done — M2

### P0 Done Checklist

- [ ] 用户可連拍 ≥10 張，每張 <3s 完成 upload 觸發
- [ ] OCR 背景完成，卡片狀態正確流轉
- [ ] 待確認僅 3 欄可編輯（姓名/公司/抬頭）
- [ ] `auto_accepted` 卡片可被 M5 搜尋（handoff stub 已 emit）
- [ ] ≥3 張 OCR 完成觸發 Aha modal
- [ ] 9 種錯誤態至少 5 種已實作（upload retry, OCR failed, duplicate, session 0, 409）
- [ ] 所有 API 有 auth + rate limit
- [ ] E2E smoke test 通過

### P1 Done Checklist

- [ ] 貼連結 + QR 匯入可用
- [ ] vCard + HTML fallback parser
- [ ] OCR daily quota 生效

---

## 8. 風險與緩解

| 風險 | 影響 | 緩解 |
|------|------|------|
| Vercel serverless 10s 限制 | OCR 不能在 API route 做 | Worker on Railway（已規劃） |
| 相機權限被拒 | 無法連拍 | fallback file input capture |
| Claude API 延遲/限流 | OCR 慢 | queue + delayed + UI 狀態 |
| R2 CORS | 前端直传失败 | presigned POST via API |
| iOS Safari PWA 限制 | 相機/通知受限 | 先保 file capture；原生 App Phase 2 |

---

## 9. 與其他模組接口（ENG 視角）

| 模組 | 接口 | M2 實作 |
|------|------|---------|
| M1 | JWT `{ userId, workspaceId }` | Clerk middleware |
| M3 | `ContactUpsertRequested` event | M2-012 stub → Sprint M3 接 consumer |
| M6 | `CompanyEnrichRequested` | M3 handoff 後觸發；M2 不直接 call |
| M5 | 搜尋 index | 依賴 M3 contact；M2 確保 handoff payload 完整 |
| M9 | Analytics events | `card_uploaded`, `ocr_completed`, `card_reviewed` |

---

*ENG M2 v1.0 — SDLC Phase 1*
