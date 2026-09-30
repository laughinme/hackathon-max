# Датасет для ML-сервиса (CatBoost)

В этой папке находится генератор синтетического датасета текстов жалоб жителей ЖКХ для обучения классификатора `domovoy-ml`.

## Архитектура и требования

Модель CatBoost решает две задачи классификации ([docs/DATA.md §7](../../docs/DATA.md)):
1. **`category`**: Категория проблемы из справочника (`water`, `light`, `heating`, `door`, `cleaning`, `lift`, `other`).
2. **`is_emergency`**: Флаг аварийной ситуации (`1` — требуется немедленный выезд АДС, `0` — плановая/обычная заявка).

Синтетический датасет генерируется через различные LLM-модели (DeepSeek, Qwen, Phi) для достижения максимального разнообразия формулировок и стиля изложения.

---

## Раздельное хранение по моделям

Каждая LLM-модель генерирует датасет в свои отдельные файлы в папке `data/`:
* `train_deepseek.json` (и `.csv`) — 1100+ обучающих примеров от DeepSeek
* `test_deepseek.json` (и `.csv`) — 80+ тестовых примеров от DeepSeek
* `train_qwen.json` (и `.csv`) — 320 обучающих примеров от Qwen
* `test_qwen.json` (и `.csv`) — 80 тестовых примеров от Qwen
* `train_phi.json` (и `.csv`) — 320 обучающих примеров от Phi
* `test_phi.json` (и `.csv`) — 80 тестовых примеров от Phi

Финальные файлы **`data/train.json` / `data/train.csv`** и **`data/test.json` / `data/test.csv`** формируются путем объединения выбранных выборок утилитой `combine.py`.

---

## Инструкция по генерации

### 1. Переменные окружения (`ml/.env`)
```env
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=deepseek/deepseek-chat
```

### 2. Генерация датасета для конкретной модели

**Qwen 2.5 72B (320 train, 80 test):**
```bash
cd ml
PYTHONPATH=src uv run python dataset/generate.py \
  --model qwen/qwen-2.5-72b-instruct \
  --prefix qwen \
  --train-size 320 \
  --test-size 80
```

**Microsoft Phi-4 (320 train, 80 test):**
```bash
cd ml
PYTHONPATH=src uv run python dataset/generate.py \
  --model microsoft/phi-4 \
  --prefix phi \
  --train-size 320 \
  --test-size 80
```

**DeepSeek Chat:**
```bash
cd ml
PYTHONPATH=src uv run python dataset/generate.py \
  --model deepseek/deepseek-chat \
  --prefix deepseek \
  --train-size 320 \
  --test-size 80
```

---

## Инструкция по объединению и проверке

### 1. Просмотр статуса всех имеющихся датасетов
```bash
cd ml
PYTHONPATH=src uv run python dataset/combine.py status
```

### 2. Сборка итогового датасета (`train.json` и `test.json`)
```bash
cd ml
PYTHONPATH=src uv run python dataset/combine.py combine --prefixes deepseek qwen phi
```
Скрипт объединит файлы `train_deepseek.json`, `train_qwen.json`, `train_phi.json` в `train.json` (и `.csv`), удалит дубликаты по тексту и выведет итоговую статистику.

---

## Обучение CatBoost на объединённом датасете

После выполнения `combine.py`, обучить модели классификации можно стандартной командой:
```bash
cd ml
uv sync --group train
PYTHONPATH=src uv run python training/train.py
```
