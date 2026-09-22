FROM python:3.13-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/
WORKDIR /app

# Dependencies first: cached until pyproject/lock change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src

ENV PATH="/app/.venv/bin:$PATH" PYTHONPATH=/app/src
RUN useradd --create-home --uid 1000 mluser && chown -R mluser:mluser /app
USER mluser

EXPOSE 8100
CMD ["uvicorn", "mlsvc.main:app", "--host", "0.0.0.0", "--port", "8100"]
