from datetime import timedelta

from application.tickets.change_status import ChangeStatusCommand
from application.tickets.create_ticket import CreateTicketCommand
from application.tickets.pulse import compute_pulse
from bot.extras_texts import guide, pulse
from domain.tickets.enums import ActorRole, ResponsibleParty, TicketStatus
from domain.tickets.responsibility_guide import GUIDE
from tests.fakes import make_world


async def _ticket(world, category="lift", text="Лифт стоит"):
    return await world.services.create_ticket.execute(
        CreateTicketCommand(42, 42, category, False, text)
    )


async def test_pulse_counts_fixed_on_time_and_overdue():
    world = make_world()
    await world.services.bind_resident.execute(42, "psk001")
    world.add_dispatcher(7)
    fast = await _ticket(world)
    late = await _ticket(world, "cleaning", "Грязно в подъезде")
    await _ticket(world, "light", "Не горит свет")

    world.clock.advance(timedelta(hours=2))
    await world.services.change_status.execute(
        ChangeStatusCommand(fast.id, TicketStatus.DONE, ActorRole.DISPATCHER, 7)
    )
    world.clock.advance(timedelta(days=9))  # past the cleaning and light deadlines
    await world.services.change_status.execute(
        ChangeStatusCommand(late.id, TicketStatus.DONE, ActorRole.DISPATCHER, 7)
    )

    data = await world.services.building_pulse.execute(world.building.id)

    assert (data.total, data.open, data.fixed, data.fixed_on_time) == (3, 1, 2, 1)
    assert data.overdue == 1  # the light ticket is still open past its deadline
    assert data.on_time_share == 0.5
    text = pulse(world.building.address, data)
    assert "50%" in text and "Просрочено сейчас: <b>1</b>" in text


def test_quiet_house_pulse():
    assert "заявок не было" in pulse("ул. Тихая, 1", compute_pulse([]))


async def test_leaflet_is_a_pdf_with_the_building_link():
    world = make_world()
    document = await world.services.leaflet.execute(world.building.id)
    assert document.content.startswith(b"%PDF")
    assert document.filename == "domovoy-psk001.pdf"


def test_guide_covers_every_party_and_the_inspection():
    parties = {entry.party for entry in GUIDE}
    assert set(ResponsibleParty) <= parties | {None}
    assert "жилищная инспекция" in guide().lower()
