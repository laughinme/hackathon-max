# Контракты

Источник истины после старта разработки — OpenAPI, генерируемая FastAPI (`/api/openapi.json`) и типы фронтенда из неё. Здесь — договорённости, которые нужны до кода. Формат ошибок и слои — в [ARCHITECTURE.md](ARCHITECTURE.md), API MAX — в [PLATFORM.md](PLATFORM.md) и [`max/GUIDE.md`](max/GUIDE.md).

## 1. Входящий вебхук MAX

**Реализовано (шаг 1):**
- `POST /webhooks/max` — только в режиме `BOT_MODE=webhook`; тело `Update`; заголовок `X-Max-Bot-Api-Secret` должен совпадать с `WEBHOOK_SECRET`, иначе `403` (проверяет `maxapi`, тест — `backend/tests/unit/app/test_http.py`). Ответ `200 {"ok": true}` после обработки события хендлером (синхронно; пределы MAX — 30 с).
- `GET /health` → `200 {"status": "ok", "bot_mode": "polling" | "webhook"}` — процесс жив.
- `GET /ready` → `200 {"database": "ok"}` или `503 {"database": "unavailable"}` — для healthcheck Docker и uptime-монитора.
- При старте в режиме `webhook`: `GET /subscriptions`, и если нашего URL нет — `POST /subscriptions` с `update_types = [message_created, message_callback, bot_started, bot_added, bot_removed]` и секретом. В режиме `polling` подписки удаляются (`maxapi.delete_webhook`).

**План (шаг 2):**
- Обработка через `inbox_events`, ответ `200` сразу.
- Ключ дедупликации: `message_created` → `mid`; `message_callback` → `callback_id`; `bot_started`/`bot_added`/`user_added` и прочие → `update_type + chat_id + user_id + timestamp`.
- Подписка при старте: `update_types = [message_created, message_callback, bot_started, bot_added, bot_removed, user_added, user_removed, bot_admin_permissions_changed]`.

## 2. Соглашения по payload кнопок и диплинков

Payload callback-кнопок (≤ 1024 символов, ASCII): `<ns>:<action>:<args>`
- `tk:new:<category>` — начать заявку из подсказки бота в чате;
- `tk:sup:<ticket_id>` — «Я тоже»;
- `tk:ok:<ticket_id>` / `tk:no:<ticket_id>` — подтверждение выполнения;
- `tk:esc:<ticket_id>` — сформировать обращение в ГЖИ;
- `tk:watch:<ticket_id>` — следить в личке;
- `form:<flow>:<step>:<value>` — шаги пошаговой формы;
- `demo:role:<resident|dispatcher>` — переключение роли в демо.

Реализовано в боте сейчас (формат `<действие>:<аргумент>`, `bot/callbacks.py`): `menu`, `new`, `cat:<категория>`, `emg:yes|no` (подтверждение аварийности), `draft_done`, `draft_restart`, `my`, `item:<uuid>`, `bld:<код дома>`, `home`, `demo_disp`, `dq` (очередь), `dt:<uuid>` (карточка диспетчера), `ds:<uuid>:<статус>`, `dsc` (без комментария), `ok:<uuid>` / `reopen:<uuid>` (ответ жителя из уведомления). Диплинк дома: `?start=h_<код>` (например `h_psk001`). Переход на схему `ns:action:args` выше — вместе с групповым чатом (шаг 3).

Диплинки: `?start=h_<building_code>` (дом), `?start=t_<ticket_number>` (заявка), `?startapp=house_<code>`, `?startapp=ticket_<id>`, `?startapp=dispatcher`. Без персональных данных.

## 3. REST для мини-приложения (v1)

**Реализовано (шаг 2), клиент — мини-приложение `frontend/` (шаг 4), которое бэкенд отдаёт по `/` того же домена.** Типы фронтенда генерируются из схемы: `npm run api:types`. Живая схема: `GET /api/openapi.json`, Swagger — `/api/docs` (на тесте: `https://domovoy-test.fly.dev/api/docs`). Код — `backend/src/api/http/v1/`, тесты — `backend/tests/unit/app/test_http.py`.

Авторизация: `Authorization: tma <WebApp.initData>`; подпись HMAC по токену бота, `auth_date` не старше 1 часа, пользователь — `user.id`. Для работы фронтенда вне MAX: `Authorization: dev <max_user_id>`, только при `DEV_AUTH_ENABLED=true` на бэкенде. Ошибки — `application/problem+json` с `error_code`: `invalid_init_data` 401, `not_a_dispatcher` / `action_not_allowed` / `not_ticket_reporter` 403, `ticket_not_found` / `building_not_found` 404, `illegal_transition` / `resident_not_bound` 409.

| Метод | Путь | Кто | Ответ |
|---|---|---|---|
| GET | `/api/v1/me` | все | `{max_user_id, residency: {building_id, building_code, address, company_name, company_phone} \| null, dispatcher: {company_id, company_name} \| null, demo_mode}` |
| GET | `/api/v1/tickets` | житель | мои заявки, новые сверху, `TicketOut[]` |
| GET | `/api/v1/tickets/{id}` | автор или диспетчер УО дома | `TicketOut` |
| GET | `/api/v1/dispatcher/queue?include_closed=false` | диспетчер | заявки УО: открытые первыми, по сроку `resolve_by`, до 50 |
| POST | `/api/v1/tickets/{id}/status` | диспетчер УО дома | тело `{status: acknowledged\|in_progress\|done\|rejected, comment?}`; жителю уходит уведомление |
| POST | `/api/v1/tickets/{id}/confirmation` | автор | тело `{resolved: bool, comment?}`: `true` → `confirmed`, `false` → `in_progress` |
| POST | `/api/v1/tickets/{id}/demo/expire-deadline` | автор, только `DEMO_MODE` и заявки демо-УО | `200 TicketOut`: срок сдвинут в прошлое, уведомления о просрочке уже в очереди; иначе `403 demo_action_not_allowed` |
| POST | `/api/v1/tickets/{id}/escalation` | автор просроченной открытой заявки | `202 TicketOut`; бот присылает PDF жалобы в чат; до срока — `409 ticket_not_overdue` |

`TicketOut`: `id, number, building_id, building_address, category_code, is_emergency, description, responsible_party, responsibility_basis, status, resolve_by, react_by, deadline_basis, is_overdue, created_at, updated_at, events[{status, actor_role, at, comment}], available_statuses[]` — последнее поле говорит фронтенду, какие кнопки показать текущему пользователю.

**Планируется:** создание заявки из мини-приложения с фото, карточка дома и «пульс дома», справочники `reference/sla` и `reference/responsibility`.

## 4. Внутренний ML-сервис (классификация жалоб)

Отдельный сервис `ml/`, не часть публичного API — доступен только бэкенду внутри сети `compose` (не за Caddy). Решение и обоснование — [DECISIONS.md D-005, D-006](DECISIONS.md). Реализация — `ml/src/mlsvc/main.py`.

| Метод | Путь | Назначение |
|---|---|---|
| POST | `/classify` | `{text: str}` → `200 {category_code, category_confidence: float, is_emergency: bool, emergency_confidence: float}`, либо `503`, если модели ещё не обучены |
| GET | `/health` | `200 {status: "ok"}` — процесс жив, не зависит от того, загружены ли модели |
| GET | `/ready` | `200 {category_model_loaded: bool, emergency_model_loaded: bool}` |

Бэкенд вызывает `/classify` из `infrastructure/ml/http_classifier.py`; при недоступности, не-200 или таймауте сам откатывается на классификацию по ключевым словам (`RuleBasedClassifier`) — вызывающий код (use case создания заявки) от этого не зависит и всегда получает `Classification`, ошибки наружу не пробрасываются.

## 5. Сообщения бота (текстовые контракты)

Карточка заявки в чате (одно сообщение, редактируется):
```
🧾 Заявка №Л5-1042 · Лифт не работает · подъезд 2
Ответственный: УО «Комфорт» (общее имущество, ЖК РФ ст. 161)
Срок устранения: до 23.09 14:10 (≤ 1 сутки, Правила № 170, прил. 2)
Статус: принята в работу · мастер 23.09 к 10:00
Поддержали: 4 соседа
[Я тоже] [Следить] [Открыть]
```
Все шаблоны — чистые функции `render_*` с snapshot-тестами; тексты на русском, без канцелярита; в демо — бейдж «тестовые данные».
