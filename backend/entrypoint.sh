#!/bin/sh
set -eu

python -m app.db.wait_for_db
alembic upgrade head

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
