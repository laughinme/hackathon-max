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

**Реализовано (шаг 2), клиент — мини-приложение `frontend/` (шаг 4), которое бэкенд отдаёт по `/` того же домена.** Типы фронтенда генерируются из схемы: `npm run api:types`. Живая схема: `GET /api/openapi.json`, Swagger — `/api/docs` (стенд: `https://domovoy.prooood.ru/api/docs`). Код — `backend/src/api/http/v1/`, тесты — `backend/tests/unit/app/test_http.py`.

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
| GET | `/api/v1/buildings/demo?limit=3` | все | `[{code, address}]` — демо-дома для выбора (в жизни дом задаёт QR) |
| PUT | `/api/v1/me/residency` | все | тело `{building_code}` → `MeOut`; неизвестный код — `404 building_not_found` |
| POST | `/api/v1/me/demo-dispatcher` | все, только `DEMO_MODE` | `MeOut` с ролью диспетчера демо-УО; иначе `403 demo_action_not_allowed` |
| DELETE | `/api/v1/me` | все | `{detached_tickets}`: снять дом и роли, отвязать заявки (как `/privacy` в боте, но без черновика диалога) |
| GET | `/api/v1/me/building` | житель | `{building_code, address, company_name, company_phone, pulse, leaflet_path, leaflet_filename}`; без дома — `409 resident_not_bound` |
| GET | `/api/v1/buildings/{id}/leaflet.pdf?sig=…` | по подписанной ссылке, **без** `Authorization` | PDF листовки с QR; неверная подпись — `404` |
| POST | `/api/v1/intake/analyze` | житель | тело `{turns: [{role: user\|bot, text}], category_code?}` → `{ready, explanation, question, draft, triage}`; `triage = {category_code, is_emergency, needs_emergency_confirmation, responsible_party, responsibility_basis, resolve_by, react_by, deadline_basis}` |
| POST | `/api/v1/intake/preview` | житель | тело `{category_code, is_emergency}` → `triage` после ответа «Это авария?» |
| POST | `/api/v1/intake/refine` | житель | тело `{draft, comment}` → `{draft}` |
| POST | `/api/v1/tickets` | житель | тело `{category_code, is_emergency, description}` → `201 TicketOut` |
| GET | `/api/v1/reference/categories` | без авторизации | быстрые сценарии с первым уточняющим вопросом, «другое» последним |
| GET | `/api/v1/reference/responsibility` | без авторизации | навигатор «кто за что отвечает» |
| GET | `/api/v1/dispatcher/integrations` | диспетчер | подключённые системы УО (CRM, 1С) и состояние доставки вебхука ([§6](#6-api-интеграции-с-crm-integrationv1)) |
| POST | `/api/v1/dispatcher/integrations` | диспетчер | тело `{name}` → `201 {integration, api_key, api_base_url, docs_url}`; ключ показывается один раз |
| DELETE | `/api/v1/dispatcher/integrations/{id}` | диспетчер своей УО | `204`, ключ перестаёт работать сразу |

Диалог создания заявки на сервере без состояния: мини-приложение хранит переписку и присылает её целиком ([D-015](DECISIONS.md)).

`TicketOut`: `id, number, building_id, building_address, category_code, is_emergency, description, responsible_party, responsibility_basis, status, resolve_by, react_by, deadline_basis, is_overdue, created_at, updated_at, events[{status, actor_role, at, comment}], available_statuses[]` — последнее поле говорит фронтенду, какие кнопки показать текущему пользователю.

**Планируется:** фото к заявке из мини-приложения (загрузка через `/uploads` Bot API), справочник `reference/sla`.

## 4. Внутренний ML-сервис (классификация жалоб)

Отдельный сервис `ml/`, не часть публичного API — доступен только бэкенду внутри сети `compose` (не за Caddy). Решение и обоснование — [DECISIONS.md D-005, D-006](DECISIONS.md). Реализация — `ml/src/mlsvc/main.py`.

| Метод | Путь | Назначение |
|---|---|---|
| POST | `/classify` | `{text: str}` → `200 {category_code, category_confidence: float, is_emergency: bool, emergency_confidence: float}`, либо `503`, если модели ещё не обучены. `category_confidence` — вероятность выбранной категории; `emergency_confidence` — уверенность в значении `is_emergency` (от 0.5 до 1), **не** вероятность аварии: бэкенд сравнивает оба поля с порогом fallback-диалога |
| GET | `/health` | `200 {status: "ok"}` — процесс жив, не зависит от того, загружены ли модели |
| GET | `/ready` | `200 {category_model_loaded: bool, emergency_model_loaded: bool}` |

Бэкенд вызывает `/classify` из `infrastructure/ml/http_classifier.py`; при недоступности, не-200 или таймауте сам откатывается на классификацию по ключевым словам (`RuleBasedClassifier`) — вызывающий код (use case создания заявки) от этого не зависит и всегда получает `Classification`, ошибки наружу не пробрасываются.

При `CLASSIFIER=catboost+llm` (`infrastructure/ml/double_check.py`, Q-18) бэкенд параллельно спрашивает ML-сервис и LLM: категория — от CatBoost; авария — если её видит CatBoost или LLM с уверенностью не ниже `ML_CONFIDENCE_THRESHOLD`; «нет» или неуверенность LLM ответ CatBoost не понижают. Без LLM (сбой или ответ дольше 5 с) — чистый CatBoost, без ML-сервиса — одна LLM, без обоих — правила.

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

## 6. API интеграции с CRM (`/integration/v1`)

**Реализовано 30.09 ([D-016](DECISIONS.md)).** Публичный контракт для CRM, 1С и АДС управляющей организации — отдельно от REST мини-приложения: другие клиенты (машины УО, а не пользователи MAX), другая авторизация (`Authorization: Bearer dmv_…` или `X-Api-Key`, ключ выдаёт диспетчер, доступ только к своей УО), своя схема `GET /integration/v1/openapi.json` (вместе с описанием исходящего вебхука `ticket-event`) и Swagger `/integration/v1/docs`. Код — `backend/src/api/integration/`, руководство с примерами подписи на Python/Node.js/PHP и наброском для 1С — [INTEGRATIONS.md](INTEGRATIONS.md).

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/me` | подключение, таблица статусов, состояние вебхука (`pending_events`, `last_error`, `next_attempt_at`) |
| PUT | `/webhook` | `{url \| null, event_types[], rotate_secret}` → `{url, event_types, secret}` |
| POST | `/webhook/test` | подписанный `ping` сейчас → `{ok, status_code, error, answer}` |
| PUT | `/status-map` | `{map: {ваш_код: наш_статус}}` |
| GET | `/events?after=&limit=` | лента событий по курсору `seq` → `{events[], next_after, has_more}` |
| GET | `/tickets?cursor=&limit=` | все заявки УО по `(updated_at, id)` → `{tickets[], next_cursor}` |
| GET | `/tickets/{ref}` | карточка; `ref` — UUID, номер `2026-00042` или `ext:<id во внешней системе>` |
| PUT | `/tickets/{ref}/external` | `{id, number?, url?, status?}` — связать с записью системы |
| POST | `/tickets/{ref}/status` | `{status, comment?, external?}` → `{applied, ticket}`; жителю — уведомление в MAX |
| POST | `/sla/calculate` | `{category_code, is_emergency, registered_at?}` → сроки, основание, ответственный |
| GET | `/reference` | коды категорий, статусов (с `integration_can_set`), событий |

Вебхук: POST JSON-конверта `{id, seq, type, schema_version, occurred_at, integration_id, ticket, data}` с заголовками `X-Domovoy-Event-Id`, `X-Domovoy-Event-Type`, `X-Domovoy-Timestamp`, `X-Domovoy-Signature: sha256=HMAC(secret, "<timestamp>.<body>")`. Доставка хотя бы один раз, по порядку. `5xx/408/409/425/429/3xx` и сетевые ошибки повторяются (10 с → 1 мин → 5 мин → 30 мин), остальные `4xx` — событие пропускается. Ответ `2xx` с `{external_id, external_number?}` связывает заявку. Ошибки — problem+json: `invalid_api_key` 401, `action_not_allowed` 403, `ticket_not_found` 404, `illegal_transition` / `external_id_taken` 409, `unknown_status` / `webhook_url_rejected` 422, `invalid_cursor` 400.
