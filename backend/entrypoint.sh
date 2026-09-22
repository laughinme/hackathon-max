#!/bin/sh
# Apply database migrations, load demo data if asked, then start the app.
set -eu
alembic upgrade head
if [ "${SEED_DEMO:-false}" = "true" ]; then
    python -m scripts.seed_demo
fi
exec python -m app.main
