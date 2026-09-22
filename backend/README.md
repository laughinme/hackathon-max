# backend — бот MAX и API «Домового»

Бот в мессенджере MAX: житель описывает проблему в доме, бот определяет категорию и аварийность, показывает ответственного и срок устранения по нормативу с основанием, регистрирует заявку с номером и показывает статус и историю. Итоговая инструкция для проверяющих будет в корневом README; архитектура — [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md), решения — [`../docs/DECISIONS.md`](../docs/DECISIONS.md).

## Запуск

Всё вместе (Postgres, бот, ML-сервис), из корня репозитория:

```bash
cp backend/.env.example backend/.env   # вписать MAX_TOKEN
docker compose up --build
```

Бот работает в режиме `polling`, порт `8080` открыт только на `127.0.0.1`: `GET /health`, `GET /ready`. Миграции применяются при старте контейнера.

Локально без Docker (нужен Postgres из `DATABASE_URL`):

```bash
cd backend
uv sync
set -a && source .env && set +a
uv run alembic upgrade head
PYTHONPATH=src uv run python -m app.main
```

Продакшен (вебхук, HTTPS 443): в `backend/.env` задать `BOT_MODE=webhook`, `WEBHOOK_URL=https://<домен>/webhooks/max`, `WEBHOOK_SECRET`; на сервере `DOMAIN=<домен> docker compose --profile prod up -d --build`. Caddy сам получает сертификат Let's Encrypt. Бот переподписывается на вебхук при каждом старте.

Тестовый деплой на fly.io (из корня, D-009):

```bash
R=$(pwd); fly deploy "$R/backend" -c "$R/infra/fly/backend.toml" --dockerfile "$R/backend/Dockerfile" --ha=false --remote-only
fly logs -a domovoy-test
```

Пока там активен вебхук, локальный `polling` событий не получает (в логе будет ошибка с адресом вебхука).

REST для мини-приложения: `/api/v1/*`, Swagger — `/api/docs`, контракт — [`../docs/CONTRACTS.md`](../docs/CONTRACTS.md) §3.

Остановка: `docker compose down` (данные Postgres остаются в томе `pgdata`; `down -v` удаляет их).

## Переменные окружения

Полный список с комментариями — [`.env.example`](.env.example).

| Переменная | Обязательна | Назначение |
|---|---|---|
| `MAX_TOKEN` | да | токен бота от организаторов |
| `DATABASE_URL` | да | `postgresql+asyncpg://…`; в compose задаётся автоматически |
| `BOT_MODE` | нет | `polling` (по умолчанию) или `webhook` |
| `WEBHOOK_URL`, `WEBHOOK_SECRET` | для `webhook` | адрес вебхука и секрет для заголовка `X-Max-Bot-Api-Secret` |
| `ML_SERVICE_URL`, `ML_CONFIDENCE_THRESHOLD` | нет | сервис классификации (`ml/`) и порог уверенности; без сервиса — правила |
| `LLM_ENABLED`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` | нет | хостинговая LLM (D-007), по умолчанию выключена |
| `DEMO_MODE`, `SEED_DEMO` | нет | кнопка «войти как диспетчер» и загрузка демо-данных при старте (по умолчанию включены) |
| `POLLING_TAKEOVER` | нет | `true` — локальный polling снимает чужую подписку на вебхук (по умолчанию нет) |
| `DEV_AUTH_ENABLED` | нет | REST принимает `Authorization: dev <id>` для фронтенда вне MAX; никогда в проде |

## Структура

```
src/
  app/             main.py (FastAPI: /health, /ready, /webhooks/max или polling), config.py, services.py (сборка зависимостей)
  bot/             handlers/ (start, create, my_requests, fallback), screen.py (навигация одним сообщением),
                   texts.py, keyboards.py, presenters.py (статусы и даты для чата), callbacks.py, states.py, middleware.py (DI)
  domain/tickets/  entities.py (агрегат Ticket), state_machine.py, sla.py (нормативные сроки), calendar.py,
                   responsibility.py, catalog.py (справочник категорий), enums.py, exceptions.py
  application/     ports/ (tickets, clock, classifier, ai), tickets/ (triage, create, change_status, queries, dto)
  infrastructure/  db/ (ORM, мапперы, репозиторий, UoW, migrations/), memory/ (адаптеры для тестов),
                   ml/ (HTTP-классификатор + правила), ai/stub.py, llm/ (клиент OpenAI-совместимого API)
scripts/simulate_flow.py   оффлайн-прогон бота без API MAX (in-memory хранилище)
tests/                     unit (домен, use case'ы, HTTP), integration (Postgres)
```

## Проверки

```bash
cd backend
uv run pytest                                            # unit (домен, use case'ы, REST, initData)
TEST_DATABASE_URL=postgresql+asyncpg://… uv run pytest   # + integration на реальном Postgres (БД очищается)
PYTHONPATH=src uv run python -m scripts.simulate_flow   # 5 сценариев бота, включая диспетчера и уведомления
DATABASE_URL=… PYTHONPATH=src uv run python -m scripts.seed_demo   # демо-данные вручную
uv run ruff check src tests scripts && uv run pyright src
```

## Данные и интеграции

| Компонент | Статус |
|---|---|
| MAX Bot API | реальный (`maxapi` 1.2.2) |
| Заявки и история | PostgreSQL |
| Классификация категории и аварийности | сервис `ml/` (CatBoost, модели обучаются); при недоступности — правила по ключевым словам |
| Нормативные сроки | справочник в коде `domain/tickets/sla.py`; значения сверяются с первоисточниками |
| Система управляющей организации | не интегрируется: УО — пользователь нашего продукта (диспетчер, шаг 2) |
| Данные в демо | тестовые, помечены в боте «Тестовый режим» |

## Известные ограничения

- Повторно присланное MAX событие обрабатывается повторно (дедупликации пока нет).
- Диспетчер работает в чате бота и через REST; мини-приложение ещё не готово.
- Бот работает только в личном диалоге; групповые чаты — шаг 3.
- Производственный календарь учитывает праздники ст. 112 ТК РФ без переносов выходных.
