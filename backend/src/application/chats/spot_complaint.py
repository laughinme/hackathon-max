"""Notice a complaint among neighbours' messages and decide how to react.

Most chat messages are not complaints ("спасибо", "кто потерял ключи?"), so the
bot speaks only when the classifier is confident. If the same problem of this
building is already an open ticket, the bot offers "me too" instead of a
duplicate: one ticket with ten neighbours behind it beats ten tickets.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from application.chats.bind_chat import GetChatBinding
from application.ports.classifier import Classifier
from application.ports.clock import Clock
from application.ports.ticket_queries import TicketQueries
from application.ports.unit_of_work import UnitOfWorkFactory
from application.tickets.dto import TicketView
from domain.chats.complaint_signals import sounds_like_complaint
from domain.chats.entities import ChatHint
from domain.housing.entities import Building
from domain.tickets.entities import TicketPhoto
from domain.tickets.sla import Deadlines, SlaPolicy

OTHER_CATEGORY = "other"
MIN_LENGTH = 12
#: A ticket this fresh with the same category is most likely the same problem.
DUPLICATE_WINDOW = timedelta(days=3)


@dataclass(frozen=True, slots=True)
class NewProblem:
    hint: ChatHint
    building: Building
    deadlines: Deadlines


@dataclass(frozen=True, slots=True)
class KnownProblem:
    ticket: TicketView


Spotted = NewProblem | KnownProblem


class SpotComplaint:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        queries: TicketQueries,
        classifier: Classifier,
        sla: SlaPolicy,
        clock: Clock,
        confidence_threshold: float,
    ) -> None:
        self._uow_factory = uow_factory
        self._queries = queries
        self._classifier = classifier
        self._sla = sla
        self._clock = clock
        self._threshold = confidence_threshold
        self._binding = GetChatBinding(uow_factory)

    async def execute(
        self,
        chat_id: int,
        author_id: int,
        message_mid: str,
        text: str,
        photos: tuple[TicketPhoto, ...] = (),
    ) -> Spotted | None:
        text = text.strip()
        if len(text) < MIN_LENGTH or text.startswith("/"):
            return None
        binding = await self._binding.execute(chat_id)
        if binding is None:
            return None

        result = await self._classifier.classify(text)
        confident_category = (
            result.category_code != OTHER_CATEGORY
            and result.category_confidence >= self._threshold
        )
        confident_emergency = (
            result.is_emergency and result.emergency_confidence >= self._threshold
        )
        complaint = confident_category and sounds_like_complaint(text)
        if not (confident_emergency or complaint):
            return None

        now = self._clock.now()
        known = await self._queries.find_open_duplicate(
            binding.building.id, result.category_code, now - DUPLICATE_WINDOW, now
        )
        if known is not None:
            involved = (
                known.reporter_id == author_id or author_id in known.supporter_ids
            )
            return None if involved else KnownProblem(known)

        unsure = result.emergency_confidence < self._threshold
        hint = ChatHint(
            chat_id=chat_id,
            message_mid=message_mid,
            author_id=author_id,
            text=text,
            category_code=result.category_code,
            is_emergency=result.is_emergency or unsure,
            needs_emergency_confirmation=unsure,
            created_at=now,
            photos=photos,
        )
        async with self._uow_factory() as uow:
            await uow.chats.add_hint(hint)
            await uow.commit()
        deadlines = self._sla.deadlines(hint.category_code, hint.is_emergency, now)
        return NewProblem(hint, binding.building, deadlines)
