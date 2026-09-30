"""The public integration API, mounted at /integration/v1 with its own docs.

Separate from the mini-app API: a different audience (machines of the
management company, not MAX users), a different auth (API key, not
initData) and its own compatibility promise.
"""

from __future__ import annotations

from fastapi import FastAPI

from api.http.errors import register_error_handlers
from api.integration import connection, reference, tickets
from api.integration.schemas import EventOut
from app.services import Services

PREFIX = "/integration/v1"

DESCRIPTION = """
Подключение CRM, 1С или АДС управляющей организации к «Домовому» — **без
отдельного адаптера под каждую систему**. Пошаговое руководство с примерами:
`docs/INTEGRATIONS.md` в репозитории.

**Как это устроено**

* **Мы → вам.** События по заявкам (`ticket.created`, `ticket.status_changed`,
  …) приходят POST-запросом на ваш URL (`PUT /webhook`), подписанные
  HMAC-SHA256. Нельзя принимать входящие запросы — забирайте те же события
  из ленты `GET /events?after=<seq>`.
* **Вы → нам.** Меняйте статус (`POST /tickets/{ref}/status`) — житель сразу
  получит уведомление в MAX. Храните свой номер заявки
  (`PUT /tickets/{ref}/external`) или просто верните его в ответе на вебхук.
* **Ваши коды.** Таблица `PUT /status-map` (`WORKING` → `in_progress`): дальше
  вы шлёте и получаете свои статусы как есть.

**Ключ** выдаёт диспетчер УО в мини-приложении: `Authorization: Bearer dmv_…`
(или `X-Api-Key`). Все данные — только своей УО.

**Гарантии.** Каждое событие доставляется хотя бы раз и по порядку;
отбрасывайте повторы по `id`. Повтор любого нашего метода безопасен.
Подтвердить устранение может только житель.
"""

TAGS = [
    {"name": "connection", "description": "Ключ, вебхук, таблица статусов"},
    {"name": "events", "description": "Лента событий — альтернатива вебхуку"},
    {"name": "tickets", "description": "Заявки: чтение, связывание, статус"},
    {"name": "sla", "description": "Нормативный срок как сервис"},
    {"name": "reference", "description": "Справочники кодов"},
]


def build_integration_app(services: Services) -> FastAPI:
    api = FastAPI(
        title="«Домовой» — API интеграции с CRM",
        version="1.0",
        description=DESCRIPTION,
        openapi_tags=TAGS,
        servers=[{"url": PREFIX}],
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    api.state.services = services
    register_error_handlers(api)
    api.include_router(connection.router)
    api.include_router(tickets.router)
    api.include_router(reference.router)

    @api.webhooks.post(
        "ticket-event",
        summary="Событие по заявке на ваш URL",
        description="Заголовки: `X-Domovoy-Event-Id`, `X-Domovoy-Event-Type`, "
        "`X-Domovoy-Timestamp` (unix-время), `X-Domovoy-Signature: "
        "sha256=<hex>` — HMAC-SHA256 секретом вебхука от строки "
        "`<timestamp>.<сырое тело>`. Ответьте 2xx за 10 секунд. 5xx, 408, 409, "
        "425, 429, 3xx и сетевые ошибки повторяются с паузой до 30 минут, "
        "остальные 4xx — событие пропускается. В ответе на `ticket.created` "
        'можно вернуть `{"external_id": "58391", "external_number": '
        '"АДС-58391"}` — заявка свяжется с вашей записью.',
    )
    def ticket_event(body: EventOut) -> None:  # pragma: no cover - docs only
        """Documented in OpenAPI `webhooks`; never called."""

    return api
