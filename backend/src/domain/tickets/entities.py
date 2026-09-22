"""Доменные модели: обращение жителя и его жизненный цикл."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class RequestStatus(str, Enum):
    """Статусы обращения."""

    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    REJECTED = "rejected"

    @property
    def title(self) -> str:
        return STATUS_TITLES[self]

    @property
    def emoji(self) -> str:
        return STATUS_EMOJI[self]

    @property
    def label(self) -> str:
        return f"{self.emoji} {self.title}"


STATUS_TITLES: dict[RequestStatus, str] = {
    RequestStatus.DRAFT: "Черновик",
    RequestStatus.SENT: "Отправлено в УК",
    RequestStatus.ACCEPTED: "Принято в работу",
    RequestStatus.IN_PROGRESS: "Выполняется",
    RequestStatus.DONE: "Выполнено",
    RequestStatus.REJECTED: "Отклонено",
}

STATUS_EMOJI: dict[RequestStatus, str] = {
    RequestStatus.DRAFT: "📝",
    RequestStatus.SENT: "📤",
    RequestStatus.ACCEPTED: "✅",
    RequestStatus.IN_PROGRESS: "🔧",
    RequestStatus.DONE: "🏁",
    RequestStatus.REJECTED: "⛔️",
}


@dataclass
class StatusEvent:
    """Одно изменение статуса — для истории обращения."""

    status: RequestStatus
    at: datetime
    comment: str | None = None


@dataclass
class Request:
    """Обращение в управляющую организацию."""

    id: int
    number: str
    user_id: int
    chat_id: int | None
    title: str
    category: str
    text: str
    status: RequestStatus = RequestStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    responsible: str = "Управляющая организация"
    urgency: str = "обычная"
    external_id: str | None = None
    is_mock_integration: bool = True
    history: list[StatusEvent] = field(default_factory=list)

    def set_status(self, status: RequestStatus, comment: str | None = None) -> None:
        """Меняет статус и пишет запись в историю."""

        self.status = status
        self.updated_at = datetime.now()
        self.history.append(
            StatusEvent(status=status, at=self.updated_at, comment=comment)
        )

    @property
    def short_title(self) -> str:
        """Короткая подпись для кнопки в списке «Мои обращения»."""

        title = self.title.strip().replace("\n", " ")
        if len(title) > 28:
            title = title[:27].rstrip() + "…"
        return title
