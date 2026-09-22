"""Process entry point: FastAPI app that receives MAX updates.

One process serves health checks and bot updates. In `webhook` mode updates
arrive at `POST /webhooks/max` (production: HTTPS 443 behind Caddy). In
`polling` mode, for local development, a background task pulls updates.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from maxapi import Bot, Dispatcher
from maxapi.enums.parse_mode import ParseMode
from maxapi.enums.update import UpdateType
from maxapi.exceptions.max import MaxApiError
from maxapi.types.command import BotCommand
from maxapi.webhook.fastapi import FastAPIMaxWebhook

from app.config import Config, load_config
from app.services import Services, build_services
from bot.handlers import create, fallback, my_requests, start
from bot.middleware import ServicesMiddleware
from infrastructure.clock import SystemClock
from infrastructure.db.engine import make_engine, make_session_factory, ping
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
)


def build_dispatcher(services: Services) -> Dispatcher:
    """Routers order matters: `fallback` catches any free text, so it goes last."""

    dispatcher = Dispatcher()
    dispatcher.register_outer_middleware(ServicesMiddleware(services))
    dispatcher.include_routers(
        start.router, create.router, my_requests.router, fallback.router
    )
    return dispatcher


async def ensure_webhook(bot: Bot, config: Config) -> None:
    """Subscribe on every start: MAX drops a subscription after 8 h of failures."""

    assert config.webhook_url is not None
    current = await bot.get_subscriptions()
    if any(sub.url == config.webhook_url for sub in current.subscriptions):
        logger.info("Webhook subscription is already active")
        return
    await bot.subscribe_webhook(
        url=config.webhook_url,
        update_types=UPDATE_TYPES,
        secret=config.webhook_secret,
    )
    logger.info("Subscribed webhook %s", config.webhook_url)


async def set_commands(bot: Bot) -> None:
    """Best effort: a missing command hint must not stop the bot."""

    try:
        await bot.set_commands(*BOT_COMMANDS)
    except MaxApiError:
        logger.warning("Could not set bot commands", exc_info=True)


def create_app(config: Config) -> FastAPI:
    engine = make_engine(config.database_url)
    session_factory = make_session_factory(engine)
    services = build_services(
        config,
        uow_factory=lambda: SqlUnitOfWork(session_factory),
        clock=SystemClock(),
    )
    bot = Bot(token=config.bot_token, format=ParseMode.HTML)
    dispatcher = build_dispatcher(services)
    webhook = FastAPIMaxWebhook(dp=dispatcher, bot=bot, secret=config.webhook_secret)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        polling: asyncio.Task[None] | None = None
        await set_commands(bot)
        if config.bot_mode == "webhook":
            await ensure_webhook(bot, config)
            async with webhook.lifespan(app):
                yield
        else:
            await bot.delete_webhook()
            polling = asyncio.create_task(dispatcher.start_polling(bot))
            yield
        if polling is not None:
            await dispatcher.stop_polling()
        await services.close()
        await bot.close_session()
        await engine.dispose()

    app = FastAPI(title="Domovoy backend", lifespan=lifespan, docs_url=None)
    if config.bot_mode == "webhook":
        webhook.setup(app, path=WEBHOOK_PATH)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "bot_mode": config.bot_mode}

    @app.get("/ready")
    async def ready() -> JSONResponse:
        try:
            await ping(engine)
        except Exception:  # noqa: BLE001 - any DB failure means "not ready"
            logger.exception("Database is not reachable")
            return JSONResponse({"database": "unavailable"}, status_code=503)
        return JSONResponse({"database": "ok"})

    return app


def main() -> None:
    config = load_config()
    logging.basicConfig(
        level=getattr(logging, config.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    uvicorn.run(
        create_app(config),
        host=config.http_host,
        port=config.http_port,
        proxy_headers=True,
        log_config=None,
    )


if __name__ == "__main__":
    main()
