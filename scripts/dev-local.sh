#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

export QDRANT_URL="http://127.0.0.1:56333"
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@127.0.0.1:55432/ai_research"
export REDIS_URL="redis://127.0.0.1:56379/0"
export MINIO_URL="127.0.0.1:59000"
export MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-admin}"
export MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-password}"
export API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"

case "${1:-}" in
  infra)
    exec docker compose -f docker/docker-compose.yml up -d
    ;;
  migrate)
    exec .venv/bin/alembic upgrade head
    ;;
  api)
    exec .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    ;;
  worker)
    exec .venv/bin/arq src.worker.WorkerSettings
    ;;
  ui)
    cd frontend
    exec npm run dev
    ;;
  *)
    echo "Usage: $0 {infra|migrate|api|worker|ui}" >&2
    exit 2
    ;;
esac
