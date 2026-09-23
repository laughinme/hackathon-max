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
  (загрузка `.cbm`-файлов и инференс), `features.py` (формат входа модели —
  общий для обучения и сервиса), `config.py`, `schemas.py`.
- `dataset/` — генератор синтетического датасета и сами `train`/`test`
  ([dataset/README.md](dataset/README.md)).
- `training/train.py` — обучение обеих моделей.
- `models/` — обученные `.cbm` (~10 МБ на обе) и `metrics.json`, лежат в
  репозитории: после клона сервис работает сразу, без обучения. Пути для
  сервиса — через `.env` (см. `.env.example`).
- `tests/` — тесты сервиса и стыковки «обучение → сервис».

## Обучение

```bash
cd ml
uv sync --group train
PYTHONPATH=src uv run python training/train.py                    # обе модели
PYTHONPATH=src uv run python training/train.py --task emergency   # одна
```

Около минуты на CPU. Скрипт учится на `dataset/data/train.csv` (15% из него
отрезается на валидацию для ранней остановки), оценивает на
`dataset/data/test.csv` и сохраняет в `models/`:

- `category_classifier.cbm` — многоклассовый (`water`, `light`, `heating`,
  `door`, `cleaning`, `lift`, `other` — коды из
  `backend/src/domain/tickets/catalog.py`);
- `emergency_classifier.cbm` — бинарный, класс `1` = авария;
- `metrics.json` — accuracy, macro-F1, отчёт по классам, матрица ошибок,
  для аварийности отдельно recall/precision, и доля ответов ниже порога
  уверенности бэкенда (0.6) — столько жалоб ушло бы в уточняющий диалог.

`test` в обучении не участвует ни как train, ни как валидация — это
фиксированный бенчмарк, по нему метрики сравнимы между запусками. Ранняя
остановка — по logloss, не по F1: F1 выходит на плато за десяток итераций при
ещё «плоских» вероятностях, и тогда почти треть жалоб оказывается ниже порога
уверенности.

Текст подаётся модели одним текстовым признаком CatBoost; токенизация
(нижний регистр, отделение пунктуации, буквенные триграммы против опечаток)
задана в `src/mlsvc/features.py`. Меняете признаки — меняйте их там: этот же
модуль использует сервис, а `tests/test_training.py` проверяет, что
обученная модель грузится и отвечает через `ClassifierModels`.

Чтобы сервис подхватил новые модели — перезапустить его (`docker compose
restart ml`), бот трогать не нужно. Переобученные модели коммитьте вместе с
`metrics.json`, чтобы было видно, какие метрики у версии в репозитории.
Каждое переобучение добавляет в историю git ещё ~10 МБ — коммитьте модели,
когда они действительно лучше, а не после каждого эксперимента.

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
uv run ruff check src tests training
```

## HTTP-контракт

Подробно — [../docs/CONTRACTS.md](../docs/CONTRACTS.md). Коротко:

| Метод | Путь | Ответ |
|---|---|---|
| GET | `/health` | `200 {"status": "ok"}` — процесс жив |
| GET | `/ready` | `200 {"category_model_loaded": bool, "emergency_model_loaded": bool}` |
| POST | `/classify` | `{"text": str}` → `200 {category_code, category_confidence, is_emergency, emergency_confidence}`, или `503`, если модели не загружены. `emergency_confidence` — уверенность в `is_emergency` (0.5–1), не вероятность аварии |
