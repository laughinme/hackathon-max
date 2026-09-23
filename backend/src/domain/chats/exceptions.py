from __future__ import annotations

from domain.errors import DomainError


class ChatNotBoundError(DomainError):
    code = "chat_not_bound"

    def __init__(self) -> None:
        super().__init__("This chat is not linked to a building yet")


class HintNotFoundError(DomainError):
    code = "hint_not_found"

    def __init__(self) -> None:
        super().__init__("The bot's hint is gone")
