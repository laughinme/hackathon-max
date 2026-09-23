"""House chat: bind, spot a complaint, file it, "me too", card refresh."""

from dataclasses import replace

import pytest

from application.chats.file_from_chat import FileFromChatCommand
from application.chats.spot_complaint import KnownProblem, NewProblem
from application.tickets.change_status import ChangeStatusCommand
from domain.notifications.entities import NotificationKind
from domain.tickets.enums import ActorRole, TicketStatus
from domain.tickets.exceptions import TicketClosedError
from tests.fakes import StaticClassifier, classification, make_world

CHAT = -700
AUTHOR, NEIGHBOUR, THIRD, DISPATCHER = 11, 12, 13, 7
LIFT_TEXT = "Лифт опять стоит на пятом этаже, двери не открываются"


async def _bound_world(**classifier_overrides):
    world = make_world()
    if classifier_overrides:
        result = replace(classification(), **classifier_overrides)
        object.__setattr__(
            world.services.spot_complaint, "_classifier", StaticClassifier(result)
        )
    world.add_dispatcher(DISPATCHER)
    await world.services.register_chat.execute(CHAT, AUTHOR)
    await world.services.bind_chat.execute(CHAT, "psk001", AUTHOR)
    return world


async def _file(world, user_id=NEIGHBOUR, mid="card.1"):
    spot = world.services.spot_complaint
    spotted = await spot.execute(CHAT, AUTHOR, "m.1", LIFT_TEXT)
    assert isinstance(spotted, NewProblem)
    return await world.services.file_from_chat.execute(
        FileFromChatCommand(spotted.hint.id, user_id, card_mid=mid)
    )


async def test_unbound_chat_stays_silent():
    world = make_world()
    await world.services.register_chat.execute(CHAT, AUTHOR)
    assert await world.services.spot_complaint.execute(CHAT, 1, "m", LIFT_TEXT) is None


async def test_small_talk_and_unsure_texts_are_ignored():
    world = await _bound_world(category_code="other", category_confidence=0.2)
    spotted = await world.services.spot_complaint.execute(
        CHAT, AUTHOR, "m", "Кто потерял ключи у подъезда?"
    )
    assert spotted is None
    assert await world.services.spot_complaint.execute(CHAT, AUTHOR, "m", "ок") is None


async def test_filing_from_the_chat_makes_the_presser_the_reporter():
    world = await _bound_world()
    ticket = await _file(world)

    assert ticket.reporter_id == NEIGHBOUR
    assert ticket.supporter_ids == (AUTHOR,)  # the author counts as "me too"
    assert ticket.building_address == world.building.address
    assert (ticket.chat_id, ticket.chat_card_mid) == (CHAT, "card.1")
    identity = await world.services.identify.execute(NEIGHBOUR)
    assert identity.residency and identity.residency.building_id == world.building.id


async def test_two_presses_on_one_hint_give_one_ticket():
    world = await _bound_world()
    spot = world.services.spot_complaint
    spotted = await spot.execute(CHAT, AUTHOR, "m.1", LIFT_TEXT)
    assert isinstance(spotted, NewProblem)
    first = await world.services.file_from_chat.execute(
        FileFromChatCommand(spotted.hint.id, NEIGHBOUR, card_mid="c")
    )
    second = await world.services.file_from_chat.execute(
        FileFromChatCommand(spotted.hint.id, THIRD, card_mid="c")
    )
    assert first.id == second.id and len(world.store.tickets) == 1


async def test_same_problem_again_offers_me_too_instead_of_a_duplicate():
    world = await _bound_world()
    ticket = await _file(world)

    spotted = await world.services.spot_complaint.execute(CHAT, THIRD, "m.2", LIFT_TEXT)
    assert isinstance(spotted, KnownProblem) and spotted.ticket.id == ticket.id
    # people already behind the ticket are not pestered
    again = await world.services.spot_complaint.execute(CHAT, AUTHOR, "m.3", LIFT_TEXT)
    assert again is None


async def test_me_too_counts_each_neighbour_once_and_refreshes_the_card():
    world = await _bound_world()
    ticket = await _file(world)

    first = await world.services.support_ticket.execute(ticket.id, THIRD)
    repeat = await world.services.support_ticket.execute(ticket.id, THIRD)
    own = await world.services.support_ticket.execute(ticket.id, NEIGHBOUR)

    assert first.counted and not repeat.counted and not own.counted
    assert first.ticket.supporters_count == 2
    refreshes = [
        e.notification
        for e in world.store.outbox.values()
        if e.notification.kind is NotificationKind.TICKET_CARD_REFRESH
    ]
    assert [n.recipient_user_id for n in refreshes] == [CHAT]


async def test_status_change_refreshes_the_card_and_closed_ticket_takes_no_support():
    world = await _bound_world()
    ticket = await _file(world)
    await world.services.change_status.execute(
        ChangeStatusCommand(ticket.id, TicketStatus.REJECTED, ActorRole.DISPATCHER, 7)
    )
    kinds = [e.notification.kind for e in world.store.outbox.values()]
    assert NotificationKind.TICKET_CARD_REFRESH in kinds
    with pytest.raises(TicketClosedError):
        await world.services.support_ticket.execute(ticket.id, THIRD)


async def test_supporter_can_open_the_ticket_in_private():
    world = await _bound_world()
    ticket = await _file(world)
    await world.services.support_ticket.execute(ticket.id, THIRD)
    view = await world.services.get_ticket.execute(ticket.id, THIRD)
    assert view.id == ticket.id


async def test_rebinding_is_reserved_to_whoever_added_the_bot():
    world = await _bound_world()
    stranger = await world.services.bind_chat.execute(CHAT, "psk002", THIRD)
    assert stranger.building.code == "psk001"
    owner = await world.services.bind_chat.execute(CHAT, "psk002", AUTHOR)
    assert owner.building.code == "psk002"
