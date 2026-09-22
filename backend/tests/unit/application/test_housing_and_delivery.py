from datetime import timedelta

import pytest

from application.notifications.deliver import MAX_ATTEMPTS, DeliverNotifications
from application.tickets.change_status import ChangeStatusCommand
from application.tickets.create_ticket import CreateTicketCommand
from domain.housing.exceptions import BuildingNotFoundError
from domain.tickets.enums import ActorRole, TicketStatus
from infrastructure.memory.tickets import InMemoryOutboxReader
from tests.fakes import RecordingSender, make_world


async def test_bind_resident_and_move_to_another_building():
    world = make_world()
    identity = await world.services.bind_resident.execute(42, "psk001")
    assert identity.residency and identity.residency.address == "ул. Тестовая, 1"
    identity = await world.services.bind_resident.execute(42, "psk002")
    assert identity.residency and identity.residency.building_code == "psk002"
    with pytest.raises(BuildingNotFoundError):
        await world.services.bind_resident.execute(42, "nope")


async def test_demo_dispatcher_role():
    world = make_world()
    identity = await world.services.become_demo_dispatcher.execute(42)
    assert identity.dispatcher and identity.dispatcher.company_id == world.company.id
    assert identity.residency is None


async def _world_with_notification():
    world = make_world()
    await world.services.bind_resident.execute(42, "psk001")
    world.add_dispatcher(7)
    ticket = await world.services.create_ticket.execute(
        CreateTicketCommand(42, 42, "lift", False, "Лифт")
    )
    await world.services.change_status.execute(
        ChangeStatusCommand(ticket.id, TicketStatus.DONE, ActorRole.DISPATCHER, 7)
    )
    return world


async def test_delivery_sends_once():
    world = await _world_with_notification()
    sender = RecordingSender()
    deliver = DeliverNotifications(
        InMemoryOutboxReader(world.store), sender, world.clock
    )
    assert await deliver.execute() == 1
    assert await deliver.execute() == 0
    assert sender.sent[0].status == "done"


async def test_delivery_retries_with_backoff_then_gives_up():
    world = await _world_with_notification()
    sender = RecordingSender(fail_times=MAX_ATTEMPTS)
    deliver = DeliverNotifications(
        InMemoryOutboxReader(world.store), sender, world.clock
    )
    for _ in range(MAX_ATTEMPTS):
        assert await deliver.execute() == 0
        world.clock.advance(timedelta(hours=1))
    [entry] = world.store.outbox.values()
    assert entry.attempts == MAX_ATTEMPTS
    assert entry.next_attempt_at is None and entry.sent_at is None
