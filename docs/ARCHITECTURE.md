# Архитектура (предложение к обсуждению командой)

Цель: код, который эксперты читают и понимают за 10 минут, соразмерен MVP (критерий «техническая реализация», 20%), и при этом показывает зрелые паттерны: домен отделён от БД и транспорта, ORM не утекает в API, файлы короткие. Что берём из шаблона и что меняем — в §6. Продуктовые требования — в [PRODUCT.md](PRODUCT.md), модель данных — в [DATA.md](DATA.md), контракты — в [CONTRACTS.md](CONTRACTS.md).

## 1. Компоненты

```
MAX (мобайл/веб) ──webhook HTTPS 443──▶ Caddy (TLS) ──▶ backend (FastAPI)
      ▲  ▲                                   │              ├─ /webhooks/max   (приём событий, 200 сразу)
      │  └──── мини-приложение (React) ───────┴──▶ /api/v1  ├─ /api/v1/*      (REST для мини-приложения)
      │                                                     ├─ worker (outbox → MAX API, SLA-таймеры, дайджесты)
      └──────── сообщения бота ◀── MAX Bot API ◀────────────┤
                                                             ├─ PostgreSQL
                                                             └─ HTTP ──▶ ml (FastAPI, свой контейнер)
                                                                          POST /classify → категория + аварийность
```

- **Один процесс backend** (API + вебхук + фоновые воркеры как asyncio-задачи) — достаточно для MVP и проверки. Разделить на два контейнера (`api`, `worker`) можно флагом, если понадобится.
- **PostgreSQL** — единственное хранилище: сущности, outbox исходящих сообщений, состояния диалогов, дедупликация событий, задания планировщика. Redis в P0 не нужен; лимитер на чат и очередь живут в Postgres (`SELECT … FOR UPDATE SKIP LOCKED`).
- **Caddy** — TLS (Let's Encrypt), статика мини-приложения, прокси `/api` и `/webhooks`.
- **Frontend** — Vite + React + TypeScript, собирается в статику и раздаётся Caddy с того же домена (нет CORS, один сертификат).
- **ml** — отдельный сервис классификации жалоб (`ml/`, свой Docker-контейнер, свои зависимости; не за Caddy, только для backend внутри сети compose) — DECISIONS D-006. Backend ходит туда по HTTP и сам откатывается на правила при недоступности, поэтому падение `ml` не роняет бота — только ухудшает качество классификации до восстановления.

## 2. Слои backend (hexagonal-lite)

```
backend/src/
  app/                 composition root: create_app(), DI-провайдеры, lifespan, настройки
  api/                 HTTP-адаптеры (тонкие)
    http/v1/<resource>/  роутеры + request/response-схемы (pydantic), по файлу на ресурс
    http/deps.py         CurrentUser из initData, get_use_case-провайдеры
    webhooks/max.py      приём Update: проверка секрета → дедуп → запись в inbox → 200
  bot/                 адаптер MAX-бота
    dispatcher.py        update_type + payload-префикс → handler
    handlers/<flow>.py   один сценарий на файл: intake, my_tickets, dispatcher_actions, start
    render/              шаблоны текстов и клавиатур (чистые функции: dto → NewMessageBody)
    state.py             состояние диалога (шаг формы) в БД, не в памяти
  domain/              чистый Python, без FastAPI/SQLAlchemy/pydantic-моделей ответа
    tickets/  entities.py (Ticket, TicketEvent), enums.py (Status, Category), state_machine.py, sla.py, exceptions.py
    buildings/ entities.py (Building, ManagementCompany, ChatBinding)
    residents/ entities.py (Resident, Role)
    shared/   value_objects.py (TicketNumber, Address), events.py (доменные события), clock.py (Protocol)
  application/         use cases и порты
    tickets/  create_ticket.py, support_ticket.py, change_status.py, escalate_ticket.py, queries.py
    ports/    repositories.py (Protocol), max_gateway.py (Protocol), unit_of_work.py, notifier.py, clock.py,
              classifier.py (Protocol: classify → category/subcategory + is_emergency, оба с confidence — вход в SlaPolicy),
              ai.py (Protocol: описание по фото, уточняющий диалог при низкой уверенности — DECISIONS D-005)
    dto.py    входные/выходные DTO use case'ов (dataclasses или pydantic, но не ORM)
  infrastructure/      адаптеры
    db/  engine.py, uow.py, models/<aggregate>.py (ORM), repositories/<aggregate>.py, mappers/<aggregate>.py, migrations/
    max/ client.py (httpx + CA Минцифры + retry), gateway.py (реализация порта), schemas.py (типы Update из OpenAPI)
    ml/  http_classifier.py (HTTP-клиент сервиса ml/, порт `classifier.py`), rule_based.py (fallback без ML)
    llm/ клиент хостингового провайдера (GigaChat/YandexGPT) — описание по фото и fallback-диалог, порт `ai.py`
    outbox/ publisher.py (worker), rate_limiter.py (2 msg/s на чат)
    scheduler/ sla_watchdog.py, digest.py
    docs/  seed.py (синтетические данные, маркированные)
  shared/              errors.py (иерархия DomainError → HTTP), logging.py, tracing middleware, result.py
tests/
  unit/        domain (state machine, SLA-калькулятор, рендер), application (use cases с фейковыми портами)
  integration/ репозитории на реальном Postgres (testcontainers или compose.test), webhook → outbox
  contract/    проверка ответов API по OpenAPI (schemathesis, опционально)
```

### Правила зависимостей
1. `domain` ни от чего не зависит. `application` зависит только от `domain` и своих портов. `infrastructure`, `api`, `bot` зависят от `application` и `domain`. `app` собирает всё. Проверяется `import-linter` в CI.
2. **ORM-модели живут только в `infrastructure/db/models`.** Репозиторий принимает и возвращает доменные сущности; преобразование — явные мапперы (`to_domain`, `to_orm`). Роутеры и хендлеры бота никогда не видят ORM.
3. Use case = один класс с методом `execute(command) -> result`, один файл, ≤ ~150 строк. Роутер вызывает use case, маппит результат в response-схему. Никакой бизнес-логики в роутерах и хендлерах бота.
4. Чтение для списков и дашбордов — отдельные query-объекты (CQRS-lite): SQL → read-DTO, без прогона через доменные сущности.
5. Транзакция = один use case. `UnitOfWork` (порт) открывает сессию, коммитит, при ошибке откатывает; доменные события публикуются в outbox **в той же транзакции** (transactional outbox).
6. Все внешние эффекты (сообщения в MAX, время, генерация id) — через порты. В тестах подменяются фейками, никаких моков httpx.
7. Размер файла ≤ 300 строк, функции ≤ 40 строк; схемы pydantic разбиты по ресурсу; enum'ы в домене.
8. Ошибки: доменные исключения (`TicketNotFound`, `IllegalTransition`, `Forbidden`) → один обработчик → RFC 7807 problem+json с `error_code` (берём из шаблона). Бот получает те же исключения и рендерит понятный текст с кнопкой «повторить».

### Ключевые доменные объекты
- `Ticket` — агрегат: номер, дом, автор, категория → ответственная сторона, статус, срок по нормативу (`due_at`), поддержавшие («я тоже»), события (таймлайн). Переходы статусов — явная таблица в `state_machine.py`.
- `SlaPolicy` — чистая функция `(category, is_emergency, created_at, calendar) -> DueDates(react_by, resolve_by, legal_basis)`. Нормативы в конфиге (YAML) с ссылкой на пункт документа; юнит-тесты на каждую категорию.
- `Responsibility` — правило «категория → УО / РСО / фонд капремонта / муниципалитет» с текстом основания.
- Доменные события `TicketCreated`, `TicketStatusChanged`, `TicketSupported`, `TicketOverdue` → уведомления и обновление сообщений в чате.

## 3. Приём событий MAX

1. `POST /webhooks/max`: проверить `X-Max-Bot-Api-Secret`, распарсить `Update` (типы из OpenAPI), записать в `inbox_events` с уникальным ключом дедупликации, вернуть 200. Никакой обработки в запросе.
2. Воркер `inbox` читает необработанные события, вызывает `bot.dispatcher`, помечает обработанными; падение одного события не ломает остальные (retry с backoff, dead-letter после N).
3. Исходящие: use case пишет `outbox_messages` (адресат, тело, `dedup_key`); воркер `outbox` отправляет через `MaxGateway` с лимитом 2/с на чат и 30 RPS всего, обновляет `mid` для последующих правок.
4. При старте: `GET /subscriptions` → если нашего URL нет, `POST /subscriptions`. `GET /health` проверяет БД и возраст последнего события/успешной отправки.

## 4. Мини-приложение (frontend)

```
frontend/src/
  app/        providers (MAX Bridge, query client, theme из WebApp), router, layout
  pages/      resident/ (мои заявки, заявка, дом), dispatcher/ (очередь по домам, заявка), onboarding/
  features/   create-ticket, support-ticket, change-status, escalate
  entities/   ticket, building, user (типы, api-хуки, карточки)
  shared/     api (fetch-клиент с `Authorization: tma <initData>`), ui (MAX UI обёртки), lib (bridge, format)
```
- Авторизация: фронт шлёт `WebApp.initData`, бэкенд проверяет HMAC и выдаёт `CurrentUser` (роль: житель / диспетчер УО / председатель). Никаких паролей и форм логина.
- Тема и платформа из MAX Bridge; кнопка «Назад» через `BackButton`; уважать `prefers-reduced-motion`.
- Типы API генерируются из OpenAPI бэкенда (`openapi-typescript`) — контракт один на обе стороны.
- Состояние сервера — TanStack Query; формы — react-hook-form + zod; без глобального стора.

## 5. Качество, тесты, поставка

- Python 3.13, `uv` (lock-файл, быстрая сборка в Docker), `ruff` (lint+format), `pyright` strict для `domain` и `application`, `pytest` + `pytest-asyncio`, `import-linter`.
- Тесты, которые точно нужны: state machine, SLA-калькулятор, рендер сообщений (snapshot), use cases с фейками, интеграционный «вебхук → заявка → outbox», e2e-скрипт проверки сценария из README.
- Docker: multi-stage образ backend (uv sync → runtime slim), образ frontend собирается в Caddy-образ; `docker compose up -d` поднимает Caddy + backend + Postgres, миграции применяются при старте, сид тестовых данных — отдельная команда и флаг. Сборка ≤ 5 минут (требование кейса).
- Логи структурированные (JSON) с `request_id`/`update_id`; токен и секреты никогда не логируются.
- README по чек-листу кейса (CASE_BRIEF §7) ведём с первого дня; ADR-записи — в [DECISIONS.md](DECISIONS.md).

## 6. Ревью шаблона `template/` (что переиспользовать)

Шаблон — монолит FastAPI (`api → service → database`, `domain` = pydantic-схемы) плюс React/Vite фронтенд, ML-сервис, Caddy, compose. Оценка:

**Берём как есть или с минимальной правкой**
- `core/errors.py` + `core/error_handling.py`: иерархия `DomainError` и RFC 7807-ответы с `error_code`, `request_id`. Переносим в `shared/errors.py`.
- `core/middlewares/request_tracing.py`: `X-Request-ID`, тайминги. Берём.
- `core/config.py`: `pydantic-settings` с валидаторами. Берём идею, оставляем только нужные поля.
- `database/relational_db/session.py` (`wait_for_db`, фабрика сессий) и идея `UoW`; переписываем UoW как порт + реализацию (без `commit()` с повторным `begin()`).
- `main.py`: фабрика приложения, lifespan, `/health` и `/ready` с проверкой зависимостей. Упрощаем под Postgres.
- `Makefile`, `docker-compose*.yml`, `caddy/` (Dockerfile со сборкой фронта, Caddyfile), `.dockerignore`, `pytest.ini`, разбиение тестов на unit/integration, `tests/helpers`.
- Frontend: Vite 7 + React 19 + TS + Tailwind 4, ESLint flat config, структура FSD (`app/pages/widgets/features/entities/shared`), `axiosInstance` с интерцепторами (заменяем логику JWT на initData), `useNetworkStatus`/`OfflineBlocker`, `ErrorBoundary`, i18n-каркас.

**Не берём**
- Сервисы-«боги» (`ml_facade.py` 1095 строк, `feed/service.py` 813, `user_service.py` 538): заменяются use case'ами по одному на файл.
- Утечка ORM: `auth_user` возвращает ORM `User` в роутеры, сервисы принимают ORM и сериализуют в pydantic руками (`serialize_user`). У нас: `CurrentUser` — value object; репозитории возвращают домен; мапперы отдельно.
- `database/*_interface.py` как репозитории с бизнес-запросами (`admin_list_users`, `registrations_by_days`) — у нас репозитории только для агрегатов, аналитика в query-объектах.
- Redis, MinIO, Centrifugo, Qdrant, ML-сервис шаблона (dating-рекомендации), APScheduler-обвязка ML, JWT/cookies/CSRF, RBAC-кэш — не нужны для MVP; при необходимости добавляем по одному. Свой ML-сервис для классификации жалоб мы всё же заводим — другой домен, другая причина (DECISIONS D-006), из шаблона не переиспользуется ничего.
- `poetry` → `uv`; `dating`-домен, миграции и сиды — не переносятся.
- `template/backend/secrets/` содержит приватный ключ JWT и `db.txt` — в наш репозиторий не попадает (`template/` в `.gitignore`), но при копировании файлов из шаблона следить, чтобы не утащить.

**Что доработать относительно шаблона**
- Разбить схемы pydantic по ресурсам (в шаблоне `domain/dating/schemas.py` 445 строк).
- Явные мапперы ORM ↔ домен; доменные сущности как `@dataclass(slots=True)`.
- Транзакционный outbox вместо прямых HTTP-вызовов из сервисов (в шаблоне есть `outbox_dispatcher.py` для ML — идея верная, обобщаем).
- `import-linter` и `pyright` в CI, чтобы правила слоёв держались не на дисциплине.

## 7. Текущее состояние кода (23.09, после шага 1)

Сделано ([D-008](DECISIONS.md)): домен заявки (`domain/tickets/`: `entities.py`, `state_machine.py`, `sla.py`, `calendar.py`, `responsibility.py`), use case'ы (`application/tickets/`: `triage_complaint.py`, `create_ticket.py`, `change_status.py`, `queries.py`), порты `tickets.py` и `clock.py`, Postgres (`infrastructure/db/`: модели, мапперы, репозиторий, UoW, миграции Alembic), in-memory адаптеры для тестов, FastAPI-процесс с вебхуком или polling (`app/main.py`), DI через middleware (`bot/middleware.py`), представление статусов и сроков в `bot/presenters.py`.

| Ещё не сделано | Цель | Шаг дорожной карты ([STATUS.md](STATUS.md)) |
|---|---|---|
| нет домов, жителей и ролей | `Building`, `Membership`, роль диспетчера УО | 2 |
| нет REST и авторизации мини-приложения | `api/http/v1` по [CONTRACTS.md](CONTRACTS.md), проверка `initData` | 2 |
| смена статуса не рассылает уведомления | outbox + порт `MaxGateway` с лимитом 2 сообщения/с на чат | 2 |
| состояние диалога в `MemoryContext` (теряется при перезапуске) | своя реализация `BaseContext` на Postgres | 2 |
| бот работает только в личном диалоге | реестр чатов, подсказка в групповом чате, «Я тоже» | 3 |
| нет контроля просрочек | планировщик просрочек, эскалация в ГЖИ | 5 |

Решение по транспорту: `maxapi` остаётся (Q-06). Команды бота ставятся через `bot.set_commands()` (`PATCH /me/commands`): старый `set_my_commands()` ходит в `PATCH /me`, который MAX больше не поддерживает.
