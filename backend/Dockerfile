# Build context is the repository root: the image also carries the mini-app
# (frontend/dist), which the backend serves at `/` next to /api and the webhook.
#   docker build -f backend/Dockerfile .

FROM node:24-alpine AS miniapp
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/
WORKDIR /app

# Dependencies first: cached until pyproject/lock change.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/alembic.ini backend/entrypoint.sh ./
COPY backend/src ./src
COPY backend/scripts ./scripts
COPY --from=miniapp /frontend/dist ./miniapp

ENV PATH="/app/.venv/bin:$PATH" PYTHONPATH=/app/src MINIAPP_DIR=/app/miniapp
RUN useradd --create-home --uid 1000 botuser && chown -R botuser:botuser /app
USER botuser

EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/ready', timeout=2)"

ENTRYPOINT ["./entrypoint.sh"]
