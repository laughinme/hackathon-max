from types import SimpleNamespace

from maxapi.enums.chat_type import ChatType
from maxapi.types.updates.bot_added import BotAdded
from maxapi.types.users import User

from bot.scopes import DialogScope, GroupScope


def _event(chat_type: ChatType | None) -> SimpleNamespace:
    recipient = SimpleNamespace(chat_type=chat_type)
    return SimpleNamespace(message=SimpleNamespace(recipient=recipient))


def _added(is_channel: bool) -> BotAdded:
    user = User(user_id=1, first_name="A", is_bot=False, last_activity_time=0)
    return BotAdded(timestamp=0, chat_id=-5, user=user, is_channel=is_channel)


async def test_dialog_updates_go_to_dialog_routers_only():
    event = _event(ChatType.DIALOG)
    assert await DialogScope()(event)
    assert not await GroupScope()(event)


async def test_house_chat_updates_go_to_group_router_only():
    event = _event(ChatType.CHAT)
    assert not await DialogScope()(event)
    assert await GroupScope()(event)


async def test_bot_started_has_no_message_and_belongs_to_the_dialog():
    assert await DialogScope()(SimpleNamespace(user=1))


async def test_bot_added_to_a_group_but_not_to_a_channel():
    assert await GroupScope()(_added(is_channel=False))
    assert not await GroupScope()(_added(is_channel=True))
    assert not await DialogScope()(_added(is_channel=False))
