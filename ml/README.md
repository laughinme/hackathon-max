# domovoy-ml

Отдельный сервис классификации жалоб: категория + аварийность
(`is_emergency`). Решение и обоснование — [../docs/DECISIONS.md](../docs/DECISIONS.md)
(D-005 — что классифицируем и зачем, D-006 — почему отдельным сервисом,
а не в процессе бота). Модель данных и нормативный справочник, в который
уходит результат классификации, — [../docs/DATA.md §7](../docs/DATA.md).

Бэкенд (`backend/`) ходит сюда по HTTP через
`backend/src/infrastructure/ml/http_classifier.py` и сам откатывается на
классификатор по ключевым словам, если этот сервис недоступен или модели ещё
не обучены — так что можно разрабатывать и обучать модели независимо, не
трогая и не ломая бота.

## Что тут лежит

- `src/mlsvc/` — FastAPI-приложение: `main.py` (роуты), `classifier.py`
  (загрузка `.cbm`-файлов и инференс), `config.py`, `schemas.py`.
- `models/` — сюда кладутся обученные файлы (в `.gitignore`, бинарники не
  коммитятся). Пути настраиваются через `.env` (см. `.env.example`).
- `tests/` — юнит-тесты сервиса.

## Обучение

Датасет и скрипт обучения этот каркас не включает — это отдельная задача
(разметка текстов жалоб по категории и аварийности, см. открытый вопрос в
D-005). На выходе тренировки должно получиться два файла:

- `category_classifier.cbm` — многоклассовый классификатор, классы — коды
  категорий из `backend/src/domain/tickets/catalog.py` (`water`, `light`,
  `heating`, `door`, `cleaning`, `lift`, `other`).
- `emergency_classifier.cbm` — бинарный классификатор, класс `1` = авария.

`src/mlsvc/classifier.py` вызывает `model.predict_proba([text])`, то есть
ждёт модель, обученную на сыром тексте жалобы как одном текстовом признаке
(`text_features` в CatBoost). Если пайплайн признаков другой (TF-IDF,
эмбеддинги, доп. колонки) — поправьте `predict_category`/`predict_emergency`
под него, контракт `/classify` наружу от этого не изменится.

## Запуск

```bash
cd ml
uv sync
cp .env.example .env
PYTHONPATH=src uv run uvicorn mlsvc.main:app --reload --port 8100
```

Без файлов моделей сервис поднимется, `GET /health` ответит `200`,
`GET /ready` — `{"category_model_loaded": false, ...}`, а `POST /classify`
вернёт `503`. Как только положите `.cbm`-файлы в `models/` (пути — из
`.env`) и перезапустите процесс — заработает по-настоящему.

Через `docker compose up --build` (из корня репозитория) сервис поднимается
вместе с ботом — см. `compose.yaml`.

## Тесты и проверки

```bash
cd ml
uv sync --group dev
PYTHONPATH=src uv run pytest
uv run ruff check src tests
```

## HTTP-контракт

Подробно — [../docs/CONTRACTS.md](../docs/CONTRACTS.md). Коротко:

| Метод | Путь | Ответ |
|---|---|---|
| GET | `/health` | `200 {"status": "ok"}` — процесс жив |
| GET | `/ready` | `200 {"category_model_loaded": bool, "emergency_model_loaded": bool}` |
| POST | `/classify` | `{"text": str}` → `200 {category_code, category_confidence, is_emergency, emergency_confidence}`, или `503`, если модели не загружены |
