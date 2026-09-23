"""Process entry point: one FastAPI app for MAX updates, REST and health.

`webhook` mode: updates arrive at `POST /webhooks/max` (HTTPS 443 in front).
`polling` mode (local development): a background task pulls updates. A
background relay delivers outbox notifications in both modes.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from maxapi import Bot, Dispatcher, ExceptionTypeFilter
from maxapi.enums.parse_mode import ParseMode
from maxapi.enums.update import UpdateType
from maxapi.exceptions.max import MaxApiError
from maxapi.types.command import BotCommand

from api.http.app import mount_api
from api.http.miniapp import mount_miniapp
from api.webhooks.max import WebhookReceiver
from app.config import Config, load_config
from app.relay import run_housekeeping, run_overdue_watch, run_relay
from app.services import Services, build_services
from application.notifications.deliver import DeliverNotifications
from bot.errors import on_error
from bot.handlers import (
    create,
    dispatcher,
    fallback,
    group,
    my_requests,
    privacy,
    start,
)
from bot.middleware import ServicesMiddleware
from bot.notifications import MaxNotificationSender
from infrastructure.clock import SystemClock
from infrastructure.db.dialog_context import PostgresDialogContext
from infrastructure.db.engine import make_engine, make_session_factory, ping
from infrastructure.db.inbox import SqlInbox
from infrastructure.db.outbox import SqlOutboxReader
from infrastructure.db.ticket_queries import SqlTicketQueries
from infrastructure.db.uow import SqlUnitOfWork

logger = logging.getLogger(__name__)

WEBHOOK_PATH = "/webhooks/max"
UPDATE_TYPES = [
    UpdateType.MESSAGE_CREATED,
    UpdateType.MESSAGE_CALLBACK,
    UpdateType.BOT_STARTED,
    UpdateType.BOT_ADDED,
    UpdateType.BOT_REMOVED,
]
BOT_COMMANDS = (
    BotCommand(name="start", description="Начать работу с ботом"),
    BotCommand(name="menu", description="Главное меню"),
    BotCommand(name="privacy", description="Мои данные и их удаление"),
)


def build_dispatcher(
    services: Services,
    storage: type | None = None,
    storage_kwargs: dict[str, Any] | None = None,
) -> Dispatcher:
    """Routers order matters: `fallback` catches any free text, so it goes last.

    `storage` is the maxapi conversation-state class (in-memory by default).
    """

    dp = (
        Dispatcher(storage=storage, **(storage_kwargs or {}))
        if storage
        else Dispatcher()
    )
    dp.errors(ExceptionTypeFilter(Exception))(on_error)
    dp.register_outer_middleware(ServicesMiddleware(services))
    dp.include_routers(
        start.router,
        create.router,
        my_requests.router,
        dispatcher.router,
        privacy.router,
        group.router,
        fallback.router,
    )
    return dp


async def set_commands(bot: Bot) -> None:
    """Best effort: a missing command hint must not stop the bot."""

    try:
        await bot.set_commands(*BOT_COMMANDS)
    except MaxApiError:
        logger.warning("Could not set bot commands", exc_info=True)


async def ensure_webhook(bot: Bot, config: Config) -> None:
    """Subscribe on every start: MAX drops a subscription after 8 h of failures."""

    assert config.webhook_url is not None
    current = await bot.get_subscriptions()
    if any(sub.url == config.webhook_url for sub in current.subscriptions):
        logger.info("Webhook subscription is already active")
        return
    await bot.subscribe_webhook(
        url=config.webhook_url, update_types=UPDATE_TYPES, secret=config.webhook_secret
    )
    logger.info("Subscribed webhook %s", config.webhook_url)


async def prepare_polling(bot: Bot, config: Config) -> None:
    """Polling gets nothing while a webhook is active; never break it silently."""

    current = await bot.get_subscriptions()
    urls = [sub.url for sub in current.subscriptions]
    if not urls:
        return
    if config.polling_takeover:
        logger.warning("POLLING_TAKEOVER: removing webhook subscriptions %s", urls)
        await bot.delete_webhook()
        return
    logger.error(
        "Webhook is active (%s): polling will receive no updates. The deployed "
        "bot keeps working. Set POLLING_TAKEOVER=true to take the bot over.",
        urls,
    )


def create_app(config: Config) -> FastAPI:
    engine = make_engine(config.database_url)
    session_factory = make_session_factory(engine)
    clock = SystemClock()
    queries = SqlTicketQueries(session_factory)
    services = build_services(
        config,
        uow_factory=lambda: SqlUnitOfWork(session_factory),
        queries=queries,
        clock=clock,
    )
    bot = Bot(token=config.bot_token, format=ParseMode.HTML)
    dp = build_dispatcher(
        services,
        storage=PostgresDialogContext,
        storage_kwargs={"session_factory": session_factory},
    )
    inbox = SqlInbox(session_factory)
    receiver = WebhookReceiver(
        dp, bot, config.webhook_secret or "", inbox=inbox, clock=clock
    )
    deliver = DeliverNotifications(
        SqlOutboxReader(session_factory),
        MaxNotificationSender(
            bot,
            services.escalation_document,
            queries,
            clock,
            config.bot_link,
        ),
        clock,
    )

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        await set_commands(bot)
        relay = asyncio.create_task(run_relay(deliver))
        overdue = asyncio.create_task(run_overdue_watch(services.detect_overdue))
        housekeeping = asyncio.create_task(run_housekeeping(inbox, clock))
        polling: asyncio.Task[None] | None = None
        try:
            if config.bot_mode == "webhook":
                await dp.startup(bot)
                await ensure_webhook(bot, config)
                yield
                await receiver.drain()
            else:
                await prepare_polling(bot, config)
                polling = asyncio.create_task(dp.start_polling(bot))
                yield
        finally:
            relay.cancel()
            overdue.cancel()
            housekeeping.cancel()
            if polling is not None:
                await dp.stop_polling()
            await services.close()
            await bot.close_session()
            await engine.dispose()

    app = FastAPI(
        title="Domovoy API",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    mount_api(app, services)
    if config.bot_mode == "webhook":
        receiver.mount(app, WEBHOOK_PATH)

    @app.get("/health", tags=["ops"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "bot_mode": config.bot_mode}

    @app.get("/ready", tags=["ops"])
    async def ready() -> JSONResponse:
        try:
            await ping(engine)
        except Exception:  # noqa: BLE001 - any DB failure means "not ready"
            logger.exception("Database is not reachable")
            return JSONResponse({"database": "unavailable"}, status_code=503)
        return JSONResponse({"database": "ok"})

    if config.dev_auth_enabled:
        logger.warning("DEV_AUTH_ENABLED: REST accepts 'Authorization: dev <id>'")
    if config.miniapp_dir and (Path(config.miniapp_dir) / "index.html").is_file():
        mount_miniapp(app, Path(config.miniapp_dir))
        logger.info("Mini-app served at / from %s", config.miniapp_dir)
    return app


class _SkipProbes(logging.Filter):
    """Platform health checks every 15 s drown the useful access log lines."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return not ('"GET /ready' in message or '"GET /health' in message)


def main() -> None:
    config = load_config()
    logging.basicConfig(
        level=getattr(logging, config.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    logging.getLogger("uvicorn.access").addFilter(_SkipProbes())
    uvicorn.run(
        create_app(config),
        host=config.http_host,
        port=config.http_port,
        proxy_headers=True,
        log_config=None,
    )


if __name__ == "__main__":
    main()
