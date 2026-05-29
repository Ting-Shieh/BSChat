# BSChat 技术栈与仓库结构（Implementation Authority）

> **版本**：v1.1  
> **日期**：2026-05-20  
> **性质**：**实作层权威文档**。与 `BSChat_ENG_M*.md` 业务逻辑一致，但 **工具链以本文为准**（ENG 早期按 Node/Monorepo 撰写，见 §6 对照表）。  
> **状态**：✅ **LOCKED**（2026-05-20 确认）

---

## 1. TL;DR

| 层 | 选型 |
|----|------|
| **仓库** | 单 Git repo：`spec/` + `frontend/` + `backend/`（**非 Monorepo**） |
| **前端** | Next.js 15 **PWA** · TypeScript · Tailwind · shadcn/ui · TanStack Query · Zustand |
| **后端** | **FastAPI** · **uv** · Python 3.12+ · Pydantic v2 |
| **数据** | PostgreSQL · SQLAlchemy 2 (async) · Alembic · asyncpg |
| **队列** | Redis · **Celery**（worker 独立进程） |
| **AI** | Anthropic Claude（`app/ai/`，预留扩展） |
| **存储** | Cloudflare R2（S3 兼容 · boto3） |
| **API 文档** | **Swagger UI** `/docs` · ReDoc `/redoc` · OpenAPI 3 |
| **Auth MVP** | JWT + dev login（M1-minimal）；Phase 2 可换 Clerk |

---

## 2. 架构原则

### 2.1 与规格文档分离

```
BSChat/
├── spec/          # SDLC 规格（PM/SA/ENG/QA/UIUX）— 不参与 build、不被 import
├── frontend/      # Next.js 纯 UI
└── backend/       # API + Worker + DB + Docker + OpenAPI + 运维脚本
```

- **`spec/`** 仅作设计与验收依据。
- **实作代码** 不得写入 `spec/`。

### 2.2 前后端分离（非 Monorepo）

- **两个独立 `package.json` / `pyproject.toml`**，无 pnpm workspace、无共用 npm package。
- 前后端通过 **REST `/api/v1/*` + OpenAPI** 协作。
- 类型同步：`frontend` 使用 `openapi-typescript` 从 backend OpenAPI 生成 TS 类型。

### 2.3 为何不用 Monorepo

- 2 人 MVP；避免 `packages/shared` 耦合。
- 未来拆 repo / 拆 deploy：搬 `frontend/` 或 `backend/` 目录即可。
- 企业 API、Phase 3 公开池：backend 为唯一业务真相。

### 2.4 契约与运维归属 backend

| 内容 | 位置 |
|------|------|
| OpenAPI / Swagger | `backend/app/` → 运行时 `/openapi.json`；快照 `backend/contracts/` |
| Docker Compose（Postgres + Redis） | `backend/docker/` |
| DB migration | `backend/alembic/` |
| Seed 脚本 | `backend/scripts/` |

**不在 repo 根** 另设 `contracts/`、`infra/`。

---

## 3. 仓库目录结构（目标）

```
BSChat/
├── spec/                              # 不变
│   ├── BSChat_PRD_v2.md
│   ├── modules/                       # PM L3
│   ├── architecture/                  # SA/SD
│   ├── design/                        # UI/UX
│   ├── engineering/                   # ENG + 本文
│   └── qa/
│
├── frontend/
│   ├── app/                           # 路由薄层（只 compose features）
│   │   ├── (auth)/login/
│   │   ├── (app)/                     # Tab：search / contacts / capture / review / settings
│   │   ├── manifest.ts                # PWA manifest（Next Metadata API）
│   │   └── sw.ts                      # Serwist service worker 入口
│   ├── features/                      # 按产品模块划分（可复用单元）
│   │   ├── auth/                      # M1
│   │   ├── capture/                   # M2 连拍 · 相机 · 待确认
│   │   ├── contacts/                  # M3 列表 · 详情
│   │   ├── search/                    # M5 对话搜尋
│   │   ├── enrichment/                # M6 展示块（读 API）
│   │   └── actions/                   # M8 复制/联络
│   ├── shared/                        # 跨模块复用（禁止写业务规则）
│   │   ├── ui/                        # shadcn 原语 + 主题
│   │   ├── components/                # PrivacyStrip, EmptyState, ContactAvatar...
│   │   ├── hooks/
│   │   ├── lib/                       # api-client, cn, design-tokens.css
│   │   └── types/                     # openapi 生成 + UI 辅助类型
│   ├── public/
│   │   ├── icons/                     # PWA 192/512 maskable
│   │   └── splash/                    # optional
│   ├── package.json
│   ├── next.config.ts                 # Serwist 插件
│   └── .env.local
│
└── backend/
    ├── pyproject.toml                 # uv 项目
    ├── uv.lock
    ├── app/
    │   ├── main.py                    # FastAPI 入口 · Swagger
    │   ├── api/v1/                    # 路由：auth, me, cards, contacts, companies, search
    │   ├── modules/                   # m1_auth, m2_capture, m3_contacts, m5_search, m6_enrichment
    │   ├── ai/                        # prompts, pipelines, clients（AI 扩展中心）
    │   ├── worker/                    # Celery app + tasks/
    │   └── core/                      # config, db, auth, storage, entitlements
    ├── alembic/
    ├── contracts/
    │   └── openapi.json               # CI 从 /openapi.json 导出（可选快照）
    ├── docker/
    │   └── docker-compose.yml
    ├── scripts/
    │   └── seed_dev_user.py
    ├── .env.example
    └── README.md
```

根目录可选：`README.md`、`.gitignore`（**无** `pnpm-workspace.yaml`）。

---

## 4. 前端技术栈

| 项目 | 选型 | 说明 |
|------|------|------|
| 框架 | **Next.js 15** App Router | Tab 路由、SSR 首屏、后期 admin 路由组 |
| **PWA** | **@serwist/next** | 展场 **Add to Home Screen**、全屏连拍；见 §4.3 |
| 语言 | TypeScript | |
| 样式 | **Tailwind CSS 4** | 对齐 `BSChat_Design_Foundation.md` tokens |
| 组件 | **shadcn/ui** | 放在 `shared/ui/` |
| Server state | **TanStack Query v5** | 列表、详情、搜尋、M6 polling |
| Client UI state | **Zustand** | M2 连拍 thumbnail / upload progress |
| 图片压缩 | **browser-image-compression** | 上传前 max 2048px（M2 ENG） |
| API | `fetch` + 生成类型 | `openapi-typescript` ← backend OpenAPI |
| 部署 | **Vercel**（建议） | PWA + Next；**HTTPS 必须**（相机 API） |

### 4.1 前端不做的事

- ❌ 业务 REST API（全部在 backend）
- ❌ 直接连 PostgreSQL / Redis
- ❌ OCR / enrich / search rerank 逻辑

### 4.2 PWA（Mobile-first 收名片 · 必选项）

Design Foundation 已定：**Web PWA 优先**；M2 展场连拍依赖「像 App 一样打开相机」。

| 项目 | 选型 / 做法 |
|------|-------------|
| Service Worker | **[@serwist/next](https://serwist.pages.dev/docs/next)**（Next App Router 适用；取代旧 `next-pwa`） |
| Manifest | `display: standalone` · `orientation: portrait` · theme/background 对齐 Design tokens |
| 图标 | `public/icons/` — 192、512、**maskable**（Android 主屏幕） |
| 安装 | 首次 onboarding 可选提示「加入主画面」；iOS Safari **手动**「加入主画面」 |
| HTTPS | 生产 **必须**；`getUserMedia` 本地 dev 可用 localhost |

**相机策略（M2 连拍）**：

```
优先：getUserMedia({ video: { facingMode: 'environment' } })  ← 连拍不离开取景
降级：input[type=file][accept=image/*][capture=environment]   ← iOS 权限拒否时
相册：input[type=file][accept=image/*][multiple]               ← 展后补扫
```

| 能力 | MVP | 说明 |
|------|-----|------|
| 安装到主画面 | ✅ P0 | 展场单手打开 |
| 全屏连拍 UI | ✅ P0 | `(app)/capture/burst` client component |
| 离线拍照队列 | ❌ | **DDR-17** 不做；无网时提示 retry |
| 离线读缓存 | P2 | Serwist 仅 cache 静态 shell；**不 cache API** |
| Push 通知 | ❌ Phase 2 | |

**iOS Safari 限制（QA 须测）**：PWA 相机、存储配额较紧；M2 ENG 已列风险——**file capture fallback 必做**。

### 4.3 前端模块复用架构（Feature-Sliced）

**原则**：`app/` 只负责路由与拼装；**业务 UI 按 BSChat 模块放在 `features/`**；**跨模块组件放 `shared/`**。

```
依赖方向（禁止反向）：

  app/pages  →  features/*  →  shared/*
                  ↓
              不可 features/A 直接 import features/B
              共用部分抽到 shared/ 或通过 props 注入
```

#### 4.3.1 目录约定

| 路径 | 职责 |
|------|------|
| `features/<module>/components/` | 该模块专属 UI |
| `features/<module>/hooks/` | 该模块 TanStack Query / Zustand |
| `features/<module>/api.ts` | 薄封装 backend 端点（可选） |
| `shared/components/` | 2+ 模块共用 |
| `shared/ui/` | shadcn Button、Dialog… |
| `shared/lib/api-client.ts` | JWT、base URL、错误处理 |

#### 4.3.2 跨模块复用清单（写 code 时对照）

| 共用组件 / Hook | 位置 | 使用者 |
|-----------------|------|--------|
| `PrivacyStrip` | `shared/components/` | 全 Tab（Design Foundation §6.4） |
| `EmptyState` | `shared/components/` | M2/M3/M5 空状态模板 |
| `ConfidenceDot` | `shared/components/` | M2 待确认、M3 |
| `ContactAvatar` / 缩图 | `shared/components/` | M3 列表、M5 结果卡 |
| **`ContactPreviewCard`** | `shared/components/` | **M3 列表 + M5 SearchResultCard**（同一视觉） |
| `CompanyProductsLine` | `shared/components/` | M3 列表 AI 行、M6 preview |
| `ResponsibilityLine` | `shared/components/` | M3 列表、详情 ai_inferred |
| `SearchInput` | `features/search/` 或 `shared/` | M5 Tab；中性 placeholder（MVP） |
| `CopyContactButton` | `features/actions/` | M5 结果、M3 详情（M8） |
| `SearchContextBanner` | `features/search/` | M3 详情（from_search） |
| `CompanyEnrichmentBlock` | `features/enrichment/` | M3 详情（M6 数据） |
| `useAuth` / `useApiClient` | `shared/hooks/` | 全局 |

**例：M5 结果卡不复制 M3 列表 markup** — 共用 `ContactPreviewCard` + slot `matchReason`。

#### 4.3.3 与后端模块对齐

| Frontend `features/` | 规格模块 | Backend `app/modules/` |
|----------------------|----------|-------------------------|
| `auth/` | M1 | `m1_auth/` |
| `capture/` | M2 | `m2_capture/` |
| `contacts/` | M3 | `m3_contacts/` |
| `search/` | M5 | `m5_search/` |
| `enrichment/` | M6（UI） | `m6_enrichment/` |
| `actions/` | M8 | （纯前端 MVP） |

命名一致，便于 2 人团队对照 spec 找代码。

#### 4.3.4 路由薄层示例

```tsx
// app/(app)/search/page.tsx — 只 compose，不含业务逻辑
import { SearchPage } from '@/features/search/components/SearchPage';

export default function Page() {
  return <SearchPage />;
}
```

### 4.4 后期扩展（同一 Next + PWA 应用）

| 能力 | 路由建议 |
|------|----------|
| 个人设定 / Pro | `(app)/settings/*` |
| 企业后台（M11 · Phase 3） | `(admin)/org/*` 路由组 |
| 更复杂运营后台 | 未来可拆独立 `frontend-admin/` repo，共用 backend API |

---

## 5. 后端技术栈

| 项目 | 选型 | 说明 |
|------|------|------|
| 语言 | **Python 3.12+** | AI 生态、后续 AI 功能扩展 |
| 包管理 | **[uv](https://github.com/astral-sh/uv)** | `pyproject.toml` + `uv.lock` |
| Web 框架 | **FastAPI** | 异步、自动 OpenAPI |
| 校验 | **Pydantic v2** | 对齐 SA/SD JSON schema；AI structured output |
| ORM | **SQLAlchemy 2.0 (async)** | 替代 ENG 文档中的 Prisma |
| Migration | **Alembic** | |
| DB 驱动 | **asyncpg** | |
| 任务队列 | **Celery** + **Redis** | 替代 ENG 文档中的 BullMQ |
| HTTP 客户端 | **httpx** | M6 网页抓取 |
| HTML 解析 | **selectolax** 或 **beautifulsoup4** | enrich pipeline |
| AI SDK | **anthropic** | OCR Vision、inference、enrich、search rerank |
| 对象存储 | **boto3** | Cloudflare R2 |
| Auth | **python-jose** / **PyJWT** + passlib（MVP dev login） | Phase 2 可接 Clerk |

### 5.1 API 规范

- Base path：**`/api/v1`**
- 与 `BSChat_SA-SD_M*.md` 路径保持一致。
- 错误格式：JSON `{ "code": "...", "message": "..." }`（与 SA/SD 对齐）。

### 5.2 Swagger / OpenAPI

| 项目 | 配置 |
|------|------|
| Swagger UI | **`GET /docs`** |
| ReDoc | **`GET /redoc`** |
| OpenAPI JSON | **`GET /openapi.json`** |
| JWT 测试 | FastAPI `HTTPBearer`；Swagger **Authorize** 填 `Bearer <token>` |
| 生产环境 | `ENABLE_SWAGGER=false` 时关闭 `/docs`（或 Basic Auth） |
| 契约快照 | CI 可选：`curl /openapi.json > contracts/openapi.json` |

所有 v1 路由须声明 **Pydantic request/response model**，保证 Swagger 完整可试。

### 5.3 Worker（Celery）

独立进程，与 API 同 `backend/` repo：

```bash
uv run celery -A app.worker.celery_app worker -l info
```

| 任务（对应模块） | 队列/job |
|------------------|----------|
| M2 OCR | `ocr.process_card` |
| M2 → M3 handoff | `contacts.upsert_from_handoff` |
| M3 inference | `contacts.inference` |
| M3 index | `contacts.index` |
| M6 enrich | `companies.enrich` |
| M5 live augment（P1） | `search.live_augment` |

**API 进程不跑长任务**（OCR/enrich 5–30s），避免阻塞。

### 5.4 AI 扩展目录（`app/ai/`）

```
app/ai/
├── clients/           # anthropic；预留其他 provider
├── prompts/           # OCR, inference, enrich, search_rerank
├── pipelines/         # 可组合步骤（fetch → extract → validate）
└── schemas/           # Pydantic 输出（M5 match_reason 校验等）
```

MVP **不引入** LangChain；需要 orchestration 时再评估 LangGraph 或自研 pipeline。

---

## 6. 与 ENG 规格对照（实现映射）

| ENG / SA/SD 写法 | 本栈实作 |
|------------------|----------|
| Prisma schema | SQLAlchemy models + Alembic |
| BullMQ | Celery + Redis |
| Zod | Pydantic v2 |
| Next.js Route Handlers | FastAPI routes |
| `packages/shared` | `app/modules/` + `app/core/` |
| Monorepo `apps/web` | `frontend/` |
| Monorepo `apps/worker` | `backend/app/worker/` |
| Clerk（M2 ENG 提及） | MVP JWT；Clerk 为 Phase 2 可选项 |

**业务规则、API 路径、状态机、DDR** 仍以各模块 PM/SA/SD/ENG 为准；仅 **运行时技术绑定** 以本文为准。

---

## 7. 数据与基础设施

| 服务 | 选型 | 用途 |
|------|------|------|
| PostgreSQL | **Neon** 或 Docker 本地 | contacts, search tsvector, pg_trgm；预留 pgvector |
| Redis | **Upstash** 或 Docker 本地 | Celery broker |
| Object storage | **Cloudflare R2** | 名片原图 |
| AI | **Anthropic API** | Claude Sonnet / Haiku |

### 7.1 本地开发

```bash
cd backend/docker && docker compose up -d    # postgres:5432, redis:6379
cd backend && uv sync && uv run alembic upgrade head
cd backend && uv run uvicorn app.main:app --reload --port 8001
cd backend && uv run celery -A app.worker.celery_app worker -l info
cd frontend && pnpm dev                         # :3000
# Swagger: http://localhost:8001/docs
```

### 7.2 环境变量（摘要）

**backend/.env**

```bash
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
JWT_SECRET=...
ANTHROPIC_API_KEY=...
R2_*=...
ENABLE_SWAGGER=true
CORS_ORIGINS=http://localhost:3000
```

**frontend/.env.local**

```bash
NEXT_PUBLIC_API_URL=http://localhost:8001
```

---

## 8. 部署建议

| 组件 | 建议平台 | 备注 |
|------|----------|------|
| frontend | Vercel | Next.js |
| backend API | Railway / Fly.io / Render | 常驻进程 |
| Celery worker | 同上（第二 service） | 同镜像、不同 start command |
| PostgreSQL | Neon / Railway | 需 pg_trgm 扩展 |
| Redis | Upstash / Railway | |
| R2 | Cloudflare | |

⚠️ **勿** 在 Vercel Serverless 跑 OCR/enrich worker。

---

## 9. 安全与合规（MVP）

| 项目 | 做法 |
|------|------|
| CORS | 仅允许 frontend origin |
| Auth | JWT；所有 `/api/v1/*`（除 login）需 Bearer |
| Tenant | `user_id` 强制过滤（M7 私密） |
| Swagger 生产 | 默认关闭或保护 |
| Query 日志 | 不 log 完整用户 query 到第三方（B-15） |

---

## 10. 实施顺序（确认后）

1. Scaffold `backend/`（uv + FastAPI + Swagger + docker + Alembic 空壳）
2. **M1-minimal**：users / workspaces / entitlements + dev login + `/docs` 可试
3. Scaffold `frontend/`（Next 15 **PWA Serwist** + `features/`/`shared/` + login）
4. 垂直切片：**M2 → M3 → M6 → M5**（规格已 LOCKED）

---

## 11. 待确认项（请勾选或留言）

| # | 项目 | 建议值 | 确认 |
|---|------|--------|------|
| 1 | 前端 | Next.js 15 | ☐ |
| 2 | **PWA** | **Serwist + manifest + 相机连拍** | ☐ |
| 3 | **前端结构** | **`features/` + `shared/` 模块复用** | ☐ |
| 4 | 后端 | FastAPI + uv | ☐ |
| 5 | ORM | SQLAlchemy 2 + Alembic | ☐ |
| 6 | 队列 | Celery + Redis | ☐ |
| 7 | Swagger | `/docs` + `/openapi.json` | ☐ |
| 8 | Auth MVP | JWT dev login | ☐ |
| 9 | 目录 | `spec/` + `frontend/` + `backend/` | ☐ |
| 10 | Python | 3.12+ | ☐ |
| 11 | Celery vs ARQ | **Celery**（可改 ARQ） | ☐ |
| 12 | Auth Phase 2 | Clerk 可选 | ☐ |

---

## 12. 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.1 草案 | 2026-05-20 | 补充 PWA（Serwist、相机）、`features/`/`shared/` 模块复用架构 |
| v1.0 草案 | 2026-05-20 | 前后端分离、FastAPI+uv、Swagger、非 Monorepo |

---

*✅ LOCKED v1.1 — scaffold 依本文执行。*

---

## 13. 确认记录

| 日期 | 确认项 |
|------|--------|
| 2026-05-20 | Next 15 PWA · FastAPI+uv · Swagger · features/shared · 前后端分离 |
