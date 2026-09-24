"""A neighbour pressed "file it" under the bot's hint in the house chat."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from application.ports.clock import Clock
from application.ports.ticket_queries import TicketQueries
from application.ports.unit_of_work import UnitOfWorkFactory
from application.tickets.dto import TicketView
from application.tickets.registration import NewTicket, register_ticket
from domain.chats.exceptions import ChatNotBoundError, HintNotFoundError
from domain.housing.entities import ResidencyKind, Resident
from domain.tickets.sla import SlaPolicy


@dataclass(frozen=True, slots=True)
class FileFromChatCommand:
    hint_id: UUID
    user_id: int
    #: The card replaces the hint message; its id is where the card lives.
    card_mid: str
    #: The answer to "is it an emergency?", None when the bot did not ask.
    is_emergency: bool | None = None


class FileFromChat:
    """The person who pressed becomes the reporter (they will get the updates);
    the author of the message, if someone else, is counted as a supporter.
    A member of a house chat is taken as a resident of that house."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        queries: TicketQueries,
        sla: SlaPolicy,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._queries = queries
        self._sla = sla
        self._clock = clock

    async def execute(self, command: FileFromChatCommand) -> TicketView:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            hint = await uow.chats.get_hint(command.hint_id)
            if hint is None:
                raise HintNotFoundError()
            if hint.ticket_id is not None:  # a neighbour was faster
                ticket_id = hint.ticket_id
            else:
                chat = await uow.chats.get(hint.chat_id)
                if chat is None or chat.building_id is None:
                    raise ChatNotBoundError()
                building = await uow.housing.get_building(chat.building_id)
                if building is None:
                    raise ChatNotBoundError()

                if await uow.housing.get_resident(command.user_id) is None:
                    await uow.housing.save_resident(
                        Resident(
                            max_user_id=command.user_id,
                            building_id=building.id,
                            kind=ResidencyKind.UNKNOWN,
                            joined_at=now,
                        )
                    )
                emergency = (
                    hint.is_emergency
                    if command.is_emergency is None
                    else command.is_emergency
                )
                ticket = await register_ticket(
                    uow,
                    self._sla,
                    building,
                    NewTicket(
                        reporter_id=command.user_id,
                        chat_id=hint.chat_id,
                        category_code=hint.category_code,
                        is_emergency=emergency,
                        description=hint.text,
                        photos=hint.photos,
                    ),
                    now,
                )
                if hint.author_id != command.user_id:
                    ticket.support(hint.author_id, now)
                ticket.attach_chat_card(hint.chat_id, command.card_mid)
                await uow.tickets.add(ticket)
                hint.mark_filed(ticket.id)
                await uow.chats.save_hint(hint)
                await uow.commit()
                ticket_id = ticket.id

        view = await self._queries.get(ticket_id, now)
        assert view is not None
        return view
