from types import SimpleNamespace

from maxapi.enums.chat_type import ChatType

from bot.middleware import DialogOnlyMiddleware


def _event(chat_type: ChatType | None) -> SimpleNamespace:
    recipient = SimpleNamespace(chat_type=chat_type)
    return SimpleNamespace(message=SimpleNamespace(recipient=recipient))


async def _handled(event: object) -> bool:
    calls: list[object] = []

    async def handler(event_object: object, data: dict) -> None:
        calls.append(event_object)

    await DialogOnlyMiddleware()(handler, event, {})
    return bool(calls)


async def test_dialog_updates_reach_handlers() -> None:
    assert await _handled(_event(ChatType.DIALOG))


async def test_group_updates_are_skipped() -> None:
    assert not await _handled(_event(ChatType.CHAT))


async def test_updates_without_message_reach_handlers() -> None:
    assert await _handled(SimpleNamespace(user=1))
