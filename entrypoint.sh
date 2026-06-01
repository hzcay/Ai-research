#!/bin/sh
set -e

echo "Waiting for database migration..."
until alembic upgrade head; do
  echo "Database not ready, retrying in 2 seconds..."
  sleep 2
done

echo "Starting FastAPI..."
exec uvicorn main:app --host 0.0.0.0 --port 8000