"""Точка входа MAX-бота «Умный город: обращения в УК»."""

from __future__ import annotations

import asyncio
import logging

from maxapi import Bot, Dispatcher
from maxapi.enums.parse_mode import ParseMode
from maxapi.types.command import BotCommand

from app import notifier
from app.config import Config, load_config
from app.handlers import create, fallback, my_requests, start
from app.services import setup_services, shutdown_services

logger = logging.getLogger(__name__)

BOT_COMMANDS = (
    BotCommand(name="start", description="Начать работу с ботом"),
    BotCommand(name="menu", description="Главное меню"),
)


def build_dispatcher() -> Dispatcher:
    """Собирает диспетчер.

    Порядок роутеров важен: `fallback` идёт последним, потому что
    ловит любой свободный текст вне сценария.
    """

    dispatcher = Dispatcher()
    dispatcher.include_routers(
        start.router,
        create.router,
        my_requests.router,
        fallback.router,
    )
    return dispatcher


def build_bot(config: Config) -> Bot:
    """Создаёт бота с общими настройками форматирования."""

    return Bot(token=config.bot_token, format=ParseMode.HTML)


def setup_logging(level: str) -> None:
    """Настраивает логирование приложения."""

    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )


async def run() -> None:
    """Запускает long polling до остановки."""

    config = load_config()
    setup_logging(config.log_level)
    setup_services(config)

    bot = build_bot(config)
    dispatcher = build_dispatcher()

    logger.info(
        "Запуск бота. Интеграция с УК: %s. AI-слой: %s",
        "реальная" if config.uk_enabled else "модельная (mock)",
        "дообученная модель" if config.llm_enabled else "заглушка",
    )

    try:
        await bot.set_my_commands(*BOT_COMMANDS)
        await dispatcher.start_polling(bot)
    finally:
        await notifier.shutdown()
        await shutdown_services()
        await bot.close_session()
        logger.info("Бот остановлен")


def main() -> None:
    """CLI-обёртка: корректно гасит бота по Ctrl+C."""

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Остановка по запросу пользователя")


if __name__ == "__main__":
    main()
