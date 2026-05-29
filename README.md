# BSChat

AI 驅動名片管理 + B2B 商脈平台。

## 仓库结构

```
BSChat/
├── spec/       # SDLC 规格（不参与 build）
├── backend/    # FastAPI + Celery + PostgreSQL
└── frontend/   # Next.js 15 PWA
```

实作权威文档：[spec/engineering/BSChat_TECH_STACK.md](spec/engineering/BSChat_TECH_STACK.md) ✅ LOCKED

## 本地开发

### 1. 基础设施

```bash
cd backend
docker compose -f docker/docker-compose.yml up -d
```

> 默认端口：**Postgres 5433**、**Redis 6380**（避免与本机已有服务冲突）

### 2. 后端

```bash
cd backend
uv sync
cp .env.example .env
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8001
```

- Swagger：http://localhost:8001/docs

### 3. 前端

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

- App：http://localhost:3000/login

## 实施顺序

1. ✅ Scaffold backend + frontend + M1-minimal
2. ✅ M2 名片收錄（垂直切片 MVP）
3. ✅ M3 聯絡人（垂直切片 MVP）
4. ☐ M6 公司補全
5. ☐ M5 AI 搜尋
