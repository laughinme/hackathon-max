# hackathon-max — точка входа для ассистентов и команды

**Проект одной фразой:** чат-бот + мини-приложение в MAX для трека «Умный город» хакатона MAX: заявка из домового чата с нормативным сроком, диспетчерская для УО, эскалация при просрочке. Дедлайн MVP — **30.09.2026 12:00 МСК**.

**Текущая фаза:** Create. Шаги 1–2 дорожной карты сделаны (ядро заявки; дома, роли, REST, уведомления), тестовый деплой — `https://domovoy-test.fly.dev`; план и следующий шаг — [docs/STATUS.md](docs/STATUS.md). LLM — только хостинговая по API, без дообучения ([D-007](docs/DECISIONS.md)).

## Что читать и в каком порядке

1. [docs/STATUS.md](docs/STATUS.md) — где мы, **дорожная карта реализации**, план по дням, риски.
2. [docs/CASE_BRIEF.md](docs/CASE_BRIEF.md) — кейс, критерии с весами, сроки, ответы организаторов (факты).
3. [docs/PRODUCT.md](docs/PRODUCT.md) — что строим, сценарий, приоритеты P0/P1/P2, демо (предложение).
4. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — слои, правила зависимостей, что взято из шаблона.
5. [docs/PLATFORM.md](docs/PLATFORM.md) — что умеет MAX и где ограничения; детали — [docs/max/GUIDE.md](docs/max/GUIDE.md).
6. [docs/DATA.md](docs/DATA.md), [docs/CONTRACTS.md](docs/CONTRACTS.md) — модель данных, нормативный справочник, API.
7. [docs/MARKET.md](docs/MARKET.md) — рынок, конкуренты, ниши.
8. [docs/DECISIONS.md](docs/DECISIONS.md) — принятые решения и открытые вопросы.
9. [docs/PROTOTYPE_REVIEW.md](docs/PROTOTYPE_REVIEW.md) — что уже в коде, что с ним не так и что делать дальше.

Брифинг для команды (страница по всем документам разом): https://claude.ai/artifact/T7CU7dR1LcdhpwNwqLKvbv

## Карта репозитория

| Путь | Что | Правила |
|---|---|---|
| `case/` | официальные материалы кейса, саммари вебинаров и Q&A ([навигация](case/README.md)) | только чтение; ничего не менять по смыслу |
| `docs/` | наши документы (см. список выше) | по темам, без дублирования: ссылаться, а не копировать |
| `docs/max/` | снимок документации MAX Bot API и мини-приложений, OpenAPI-схема, `maxapi` | обновлять скриптом из [docs/max/README.md](docs/max/README.md) |
| `backend/` | бэкенд: `src/app` (FastAPI, сборка), `src/bot` (хендлеры MAX), `src/domain`, `src/application`, `src/infrastructure` (Postgres, ML, LLM); `tests/`; `scripts/simulate_flow.py`; `uv` | структура и команды — [backend/README.md](backend/README.md), правила слоёв — ARCHITECTURE.md §2, состояние — §7 |
| `ml/` | отдельный сервис классификации жалоб (категория + аварийность), свой `pyproject.toml`/Docker/`uv`, порт 8100; каркас LoRA от 22.09 удалён и не связан с этим кодом ([DECISIONS.md D-005, D-006](docs/DECISIONS.md)) | структура и HTTP-контракт — [ml/README.md](ml/README.md), [docs/CONTRACTS.md §4](docs/CONTRACTS.md); модели (`*.cbm`) — в `ml/models/`, в `.gitignore`, не коммитить |
| `infra/fly/` | конфиги временного тестового деплоя на fly.io (`domovoy-test`, `domovoy-test-db`) | прод — Yandex Cloud ([D-009](docs/DECISIONS.md)) |
| `compose.yaml`, `infra/caddy/` | запуск одной командой (`docker compose up --build`: Postgres, бот, ML); профиль `prod` добавляет Caddy с HTTPS для вебхука | требование кейса |
| `frontend/` | мини-приложение (Vite + React + TS) | структура — ARCHITECTURE.md §4 |
| `template/` | старый проект команды для переиспользования | в `.gitignore`; копировать файлы осознанно, там есть секреты в `backend/secrets/` |

## Правила работы

- Факты организаторов отделяем от гипотез; на слайдах и в документах — ссылка на источник (`PDF стр.`, `Q&A §`, URL). Сомнительные цифры помечаем «оценка».
- Секреты только в `.env` (в `.gitignore`); `.env.example` без значений. Токен бота не выводить в логи и чат.
- Данные в демо и тестах — синтетические, промаркированные «тестовые данные» в README, на слайде и в боте.
- Архитектурные правила ([ARCHITECTURE.md](docs/ARCHITECTURE.md)): ORM не выходит за репозитории, use case на файл, файлы ≤ ~300 строк, ошибки через доменные исключения.
- Перед работой с API MAX — [docs/max/GUIDE.md](docs/max/GUIDE.md) (URL `platform-api2.max.ru`, заголовок `Authorization: <token>` без Bearer, CA Минцифры, только вебхуки в проде, лимит 2 сообщения/с на чат).
- После существенного изменения прогонять основной сценарий целиком (совет экспертов).

## Куда что записывать

- Изменилось состояние, план, риск → `docs/STATUS.md` (коротко, без истории).
- Приняли решение или появился вопрос → `docs/DECISIONS.md` (решение / почему / альтернативы).
- Новый факт от организаторов → `docs/CASE_BRIEF.md` со ссылкой; исходник — в `case/`.
- Новое ограничение или возможность MAX → `docs/PLATFORM.md`; детали → `docs/max/GUIDE.md`.
- Изменилась модель данных или API → `docs/DATA.md`, `docs/CONTRACTS.md`.
- Всё для проверяющих (запуск, сценарий проверки, ограничения) → корневой `README.md` (по чек-листу CASE_BRIEF §7).

## Бот

`@t446_hakaton_max_bot` · `https://max.ru/t446_hakaton_max_bot` · `user_id` 411198009. Токен — `backend/.env` → `MAX_TOKEN`. Настройки бота (приватность для групп, URL мини-приложения) — у организаторов; ссылку на мини-приложение отправлять через форму из [case/README.md](case/README.md).
