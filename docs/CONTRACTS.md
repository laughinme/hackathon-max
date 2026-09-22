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

Реализовано в боте сейчас (формат `<действие>:<аргумент>`, `bot/callbacks.py`): `menu`, `new`, `cat:<категория>`, `emg:yes|no` (подтверждение аварийности), `draft_done`, `draft_restart`, `my`, `item:<uuid заявки>`. Переход на схему `ns:action:args` выше — вместе с групповым чатом (шаг 3).

Диплинки: `?start=h_<building_code>` (дом), `?start=t_<ticket_number>` (заявка), `?startapp=house_<code>`, `?startapp=ticket_<id>`, `?startapp=dispatcher`. Без персональных данных.

## 3. REST для мини-приложения (v1, черновик)

Авторизация: заголовок `Authorization: tma <WebApp.initData>`; бэкенд проверяет HMAC и `auth_date` (≤ 1 ч), определяет `CurrentUser {max_user_id, memberships[], role}`. Ошибки — RFC 7807 `application/problem+json` с `error_code`.

| Метод | Путь | Кто | Назначение |
|---|---|---|---|
| GET | `/api/v1/me` | все | профиль, роли, дома, демо-флаг |
| GET | `/api/v1/buildings/{id}` | житель дома, диспетчер УО | карточка дома, УО, чат, статистика |
| GET | `/api/v1/buildings/{id}/pulse?period=week` | те же | «пульс дома» |
| GET | `/api/v1/tickets?building_id=&status=&mine=true&cursor=` | житель (свой дом), диспетчер (свои дома) | список с курсорной пагинацией |
| POST | `/api/v1/tickets` | житель | создать заявку `{building_id, category, subcategory?, description, is_emergency?, entrance?, photos[]?}` → `201 Ticket` с `react_by`, `resolve_by`, `legal_basis` |
| GET | `/api/v1/tickets/{id}` | участники дома, диспетчер | карточка + таймлайн |
| POST | `/api/v1/tickets/{id}/support` | житель | «Я тоже» (идемпотентно) |
| POST | `/api/v1/tickets/{id}/status` | диспетчер | `{status: acknowledged|in_progress|done|rejected, comment?, eta?}` |
| POST | `/api/v1/tickets/{id}/confirm` | автор или поддержавший | `{confirmed: bool, comment?}` |
| POST | `/api/v1/tickets/{id}/escalation` | автор/поддержавший, если просрочена | создать пакет → `{document_url}` |
| GET | `/api/v1/dispatcher/queue?company_id=&sort=sla&status=` | диспетчер | очередь по домам с SLA |
| GET | `/api/v1/reference/responsibility` | все | матрица «кто отвечает» |
| GET | `/api/v1/reference/sla` | все | справочник сроков с основаниями |
| POST | `/api/v1/uploads/photos` | житель | загрузка фото (лимит 5 МБ, jpeg/png) |
| GET | `/health`, `/ready` | инфраструктура | состояние БД, вебхука, outbox |

Правила: денежных и персональных полей нет; все времена — ISO 8601 с зоной; пагинация курсорная; `PATCH` не используем, статусы меняются только через явные действия.

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
