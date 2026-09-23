"""Application settings. Secrets come only from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

BotMode = Literal["polling", "webhook"]
#: Who classifies complaints (DECISIONS Q-18): the CatBoost service in `ml/`,
#: the hosted LLM, or keyword rules. All three sit behind one port.
ClassifierKind = Literal["catboost", "llm", "rules"]
CLASSIFIER_KINDS: tuple[str, ...] = ("catboost", "llm", "rules")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    try:
        return float(raw) if raw else default
    except ValueError:
        return default


def _env_str(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


@dataclass(frozen=True)
class Config:
    bot_token: str
    log_level: str

    database_url: str

    # Updates delivery. Production is webhook-only (MAX Q&A); polling is for
    # local development without a public HTTPS endpoint.
    bot_mode: BotMode
    webhook_url: str | None
    webhook_secret: str | None
    http_host: str
    http_port: int
    # Polling removes an active webhook subscription only when explicitly asked:
    # the bot token is shared, a teammate's local polling must not silently
    # break the deployed webhook.
    polling_takeover: bool

    # Hackathon demo: synthetic data and a "become a dispatcher" button so
    # checkers can walk both sides with one MAX account.
    demo_mode: bool
    # Accept `Authorization: dev <max_user_id>` in the REST API (frontend work
    # outside MAX). Never in production.
    dev_auth_enabled: bool

    # Hosted LLM behind an OpenAI-compatible API (DECISIONS D-007). When off,
    # the bot works on the rule-based StubAIService.
    llm_enabled: bool
    llm_base_url: str
    llm_model: str
    llm_api_key: str | None
    llm_timeout_sec: float
    llm_temperature: float

    # Complaint classification (DECISIONS D-005, D-006, Q-18).
    classifier: ClassifierKind
    ml_service_url: str
    ml_service_timeout_sec: float
    ml_confidence_threshold: float


def load_config() -> Config:
    token = _env_str("MAX_TOKEN") or _env_str("MAX_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "MAX_TOKEN is not set. Copy .env.example to .env and put the bot "
            "token issued by the hackathon organisers there."
        )

    database_url = _env_str("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set (see .env.example).")

    bot_mode = _env_str("BOT_MODE", "polling")
    if bot_mode not in ("polling", "webhook"):
        raise RuntimeError("BOT_MODE must be 'polling' or 'webhook'.")

    webhook_url = _env_str("WEBHOOK_URL") or None
    webhook_secret = _env_str("WEBHOOK_SECRET") or None
    if bot_mode == "webhook" and not (webhook_url and webhook_secret):
        raise RuntimeError("BOT_MODE=webhook requires WEBHOOK_URL and WEBHOOK_SECRET.")

    classifier = _env_str("CLASSIFIER", "catboost").lower()
    if classifier not in CLASSIFIER_KINDS:
        raise RuntimeError("CLASSIFIER must be 'catboost', 'llm' or 'rules'.")
    if classifier == "llm" and not _env_str("LLM_MODEL"):
        raise RuntimeError("CLASSIFIER=llm requires LLM_MODEL (and LLM_API_KEY).")

    return Config(
        bot_token=token,
        log_level=_env_str("LOG_LEVEL", "INFO").upper(),
        database_url=database_url,
        bot_mode=bot_mode,  # type: ignore[arg-type]
        webhook_url=webhook_url,
        webhook_secret=webhook_secret,
        http_host=_env_str("HTTP_HOST", "0.0.0.0"),
        http_port=int(_env_str("HTTP_PORT", "8080")),
        polling_takeover=_env_bool("POLLING_TAKEOVER", False),
        demo_mode=_env_bool("DEMO_MODE", True),
        dev_auth_enabled=_env_bool("DEV_AUTH_ENABLED", False),
        llm_enabled=_env_bool("LLM_ENABLED", False),
        llm_base_url=_env_str("LLM_BASE_URL", "https://ai.api.cloud.yandex.net/v1"),
        llm_model=_env_str("LLM_MODEL"),
        llm_api_key=_env_str("LLM_API_KEY") or None,
        llm_timeout_sec=_env_float("LLM_TIMEOUT_SEC", 20.0),
        llm_temperature=_env_float("LLM_TEMPERATURE", 0.2),
        classifier=classifier,  # type: ignore[arg-type]
        ml_service_url=_env_str("ML_SERVICE_URL", "http://localhost:8100"),
        ml_service_timeout_sec=_env_float("ML_SERVICE_TIMEOUT_SEC", 3.0),
        ml_confidence_threshold=_env_float("ML_CONFIDENCE_THRESHOLD", 0.6),
    )
