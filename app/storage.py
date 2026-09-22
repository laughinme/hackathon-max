"""Хранилище обращений.

Для MVP используется in-memory репозиторий: он не требует внешних
сервисов и полностью воспроизводим при демонстрации. Интерфейс
намеренно узкий, чтобы позже заменить его на БД без правок хендлеров.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from app.models import Request, RequestStatus


class RequestRepository:
    """Потокобезопасное in-memory хранилище обращений."""

    def __init__(self) -> None:
        self._items: dict[int, Request] = {}
        self._by_user: dict[int, list[int]] = {}
        self._next_id = 1
        self._lock = asyncio.Lock()

    async def create(
        self,
        *,
        user_id: int,
        chat_id: int | None,
        title: str,
        category: str,
        text: str,
        responsible: str,
        urgency: str,
    ) -> Request:
        """Создаёт обращение и присваивает ему человекочитаемый номер."""

        async with self._lock:
            request_id = self._next_id
            self._next_id += 1

            request = Request(
                id=request_id,
                number=f"ОБР-{datetime.now():%Y}-{request_id:04d}",
                user_id=user_id,
                chat_id=chat_id,
                title=title,
                category=category,
                text=text,
                responsible=responsible,
                urgency=urgency,
            )
            request.set_status(RequestStatus.DRAFT)

            self._items[request_id] = request
            self._by_user.setdefault(user_id, []).append(request_id)
            return request

    async def get(self, request_id: int) -> Request | None:
        """Возвращает обращение по id."""

        return self._items.get(request_id)

    async def get_for_user(
        self, request_id: int, user_id: int
    ) -> Request | None:
        """Возвращает обращение, только если оно принадлежит пользователю."""

        request = self._items.get(request_id)
        if request is None or request.user_id != user_id:
            return None
        return request

    async def list_for_user(self, user_id: int) -> list[Request]:
        """Все обращения пользователя, новые сверху."""

        ids = self._by_user.get(user_id, [])
        items = [self._items[i] for i in ids if i in self._items]
        return sorted(items, key=lambda r: r.created_at, reverse=True)


repository = RequestRepository()
