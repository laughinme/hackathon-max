"""Bodies of the integration API. The ticket and event shapes are the ones
webhooks carry too (built by `application.integrations.payload`)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from application.integrations.dto import IntegrationView
from domain.integrations.entities import ALL_EVENT_TYPES, IntegrationEventType
from domain.tickets.enums import ActorRole, ResponsibleParty, TicketStatus


class CategoryOut(BaseModel):
    code: str
    title: str


class BuildingOut(BaseModel):
    id: UUID
    address: str


class DeadlinesOut(BaseModel):
    react_by: datetime | None = Field(description="Срок реакции (аварии: 30 минут)")
    resolve_by: datetime = Field(description="Нормативный срок устранения")
    legal_basis: str = Field(description="Норма, из которой взят срок")


class TimelineEntryOut(BaseModel):
    status: TicketStatus
    actor: ActorRole
    at: datetime
    comment: str | None


class ExternalOut(BaseModel):
    id: str = Field(description="Id записи в вашей системе")
    number: str | None = Field(description="Номер, который видят люди: АДС-58391")
    url: str | None
    status: str | None = Field(description="Последний статус в вашей системе")


class TicketOut(BaseModel):
    """Заявка в каноническом виде: одинаково в API, вебхуках и ленте событий."""

    id: UUID
    number: str = Field(examples=["2026-00042"])
    status: TicketStatus
    category: CategoryOut
    is_emergency: bool
    description: str
    building: BuildingOut
    responsible_party: ResponsibleParty
    responsibility_basis: str
    deadlines: DeadlinesOut
    is_overdue: bool
    source: Literal["house_chat", "max_bot"]
    supporters_count: int = Field(description="Соседи, нажавшие «У меня тоже»")
    photo_urls: list[str]
    escalated_at: datetime | None = Field(description="Житель запросил жалобу в ГЖИ")
    created_at: datetime
    updated_at: datetime
    timeline: list[TimelineEntryOut]
    external: ExternalOut | None = Field(description="Ваша запись, если связана")
    crm_status: str | None = Field(
        description="Статус в ваших кодах по таблице соответствия, если задана"
    )


class EventOut(BaseModel):
    """Конверт события: тело вебхука и элемент ленты `GET /events`."""

    id: UUID = Field(description="Уникален: по нему отбрасывайте повторы")
    seq: int | None = Field(description="Позиция в ленте; null у тестового ping")
    type: Literal[
        "ticket.created",
        "ticket.status_changed",
        "ticket.supported",
        "ticket.overdue",
        "ticket.escalated",
        "ping",
    ]
    schema_version: int
    occurred_at: datetime
    integration_id: UUID
    ticket: TicketOut | None = Field(description="Заявка на момент события")
    data: dict[str, Any] = Field(
        description="ticket.status_changed: previous_status, status, actor "
        "(resident | dispatcher | integration), comment; ticket.supported: "
        "supporters_count"
    )


class EventPageOut(BaseModel):
    events: list[EventOut]
    next_after: int = Field(description="Передайте как `after` в следующий запрос")
    has_more: bool


class TicketPageOut(BaseModel):
    tickets: list[TicketOut]
    next_cursor: str | None = Field(description="null — это последняя страница")


class ExternalIn(BaseModel):
    id: str = Field(min_length=1, max_length=200, examples=["58391"])
    number: str | None = Field(default=None, max_length=200, examples=["АДС-58391"])
    url: str | None = Field(default=None, max_length=2048)
    status: str | None = Field(default=None, max_length=100)


class StatusIn(BaseModel):
    status: str = Field(
        min_length=1,
        max_length=100,
        description="Наш код (acknowledged, in_progress, done, rejected) или ваш "
        "код из таблицы соответствия",
        examples=["in_progress", "WORKING"],
    )
    comment: str | None = Field(
        default=None, max_length=500, description="Увидит житель в MAX"
    )
    external: ExternalIn | None = Field(
        default=None, description="Заодно связать заявку с вашей записью"
    )


class StatusResultOut(BaseModel):
    applied: bool = Field(
        description="false — у заявки уже был этот статус, ничего не изменилось"
    )
    ticket: TicketOut


class WebhookIn(BaseModel):
    url: str | None = Field(
        description="https://… вашего приёмника; null выключает вебхук",
        examples=["https://crm.example.ru/hooks/domovoy"],
    )
    event_types: list[IntegrationEventType] = Field(
        default_factory=lambda: sorted(ALL_EVENT_TYPES)
    )
    rotate_secret: bool = Field(default=False, description="Выпустить новый секрет")


class WebhookOut(BaseModel):
    url: str | None
    event_types: list[str]
    secret: str | None = Field(
        description="Секрет подписи: HMAC-SHA256 от «<timestamp>.<тело>» в "
        "заголовке X-Domovoy-Signature"
    )


class StatusMapIn(BaseModel):
    map: dict[str, str] = Field(
        description="Ваш код статуса → наш",
        examples=[
            {
                "NEW": "registered",
                "ACCEPTED": "acknowledged",
                "WORKING": "in_progress",
                "DONE": "done",
                "CANCELLED": "rejected",
            }
        ],
    )


class WebhookStateOut(BaseModel):
    url: str | None
    event_types: list[str]
    pending_events: int
    delivered_seq: int
    last_success_at: datetime | None
    last_error: str | None
    next_attempt_at: datetime | None


class IntegrationOut(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    enabled: bool
    created_at: datetime
    status_map: dict[str, str]
    webhook: WebhookStateOut

    @classmethod
    def from_view(cls, view: IntegrationView) -> IntegrationOut:
        return cls(
            id=view.id,
            name=view.name,
            key_prefix=view.key_prefix,
            enabled=view.enabled,
            created_at=view.created_at,
            status_map=view.status_map,
            webhook=WebhookStateOut(
                url=view.webhook_url,
                event_types=list(view.event_types),
                pending_events=view.pending_events,
                delivered_seq=view.delivered_seq,
                last_success_at=view.last_success_at,
                last_error=view.last_error,
                next_attempt_at=view.next_attempt_at,
            ),
        )


class PingOut(BaseModel):
    ok: bool
    status_code: int | None
    error: str | None
    answer: dict[str, Any] | None


class SlaIn(BaseModel):
    category_code: str = Field(examples=["lift"], description="Код из GET /reference")
    is_emergency: bool = False
    registered_at: datetime | None = Field(
        default=None, description="Время регистрации; по умолчанию — сейчас"
    )


class SlaOut(BaseModel):
    category: CategoryOut
    is_emergency: bool
    registered_at: datetime
    react_by: datetime | None
    resolve_by: datetime
    legal_basis: str
    responsible_party: ResponsibleParty
    responsibility_basis: str
    needs_verification: bool = Field(
        description="Норма взята из вторичных источников и ждёт юридической сверки"
    )
    warnings: list[str]


class StatusRefOut(BaseModel):
    code: TicketStatus
    title: str
    integration_can_set: bool = Field(
        description="Можно ли выставить через POST /tickets/{ref}/status"
    )


class ReferenceOut(BaseModel):
    categories: list[CategoryOut]
    statuses: list[StatusRefOut]
    event_types: list[str]
