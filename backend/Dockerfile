# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

# Install project + deps into system site-packages
RUN uv pip install --system -e .

ENV PYTHONUNBUFFERED=1
ENV PORT=8000
EXPOSE 8000

# Dogfood: migrate then serve. Keep USE_CELERY_WORKERS=false so OCR runs in-process.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
