# BSChat Backend

FastAPI + uv + SQLAlchemy async + Celery + PostgreSQL + Redis.

## Quick start

```bash
# 1. Start infra
docker compose -f docker/docker-compose.yml up -d
```

> **端口**：Postgres `5433`、Redis `6380`（避免与本机 5432/6379 冲突）

```bash
# 2. Install deps
uv sync

# 3. Copy env
cp .env.example .env

# 4. Run migrations
uv run alembic upgrade head

# 5. (Optional) seed dev user
uv run python scripts/seed_dev_user.py

# 6. Start API
uv run uvicorn app.main:app --reload --port 8001
```

- Swagger UI: http://localhost:8001/docs
- Health: http://localhost:8001/health

> 預設 **8001**（避免與本機其他服務如 tas-backend 佔用 8000 衝突）

## M1 endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/dev-login` | Dev login → JWT |
| GET | `/api/v1/me` | Current user + quotas |

## Celery worker (M2+)

```bash
uv run celery -A app.workers.celery_app worker --loglevel=info
```

## OCR 測試（Gemini）

在 `.env` 設定：

```bash
OCR_PROVIDER=gemini
OCR_USE_MOCK=false
GEMINI_API_KEY=你的_Gemini_API_Key
GEMINI_OCR_MODEL=gemini-2.5-flash   # 新帳號勿用 gemini-2.0-flash（已停用）   # 或 gemini-1.5-flash
```

API Key 取得：[Google AI Studio](https://aistudio.google.com/apikey)

重啟後端後，在 App **收錄 → 連拍** 上傳名片即可走真實 OCR。

CLI 單張測試：

```bash
uv run python scripts/test_ocr.py /path/to/card.jpg
```
