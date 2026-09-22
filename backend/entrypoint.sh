#!/bin/sh
# Apply database migrations, then start the bot and HTTP server.
set -eu
alembic upgrade head
exec python -m app.main
