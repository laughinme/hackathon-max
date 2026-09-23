"""Скрипт генерации синтетического датасета жалоб ЖКХ через OpenRouter API.

Предназначен для обучения классификаторов CatBoost (категория + аварийность).
Разделяет обучающий (train) и тестовый (test) датасеты по отдельным файлам,
чтобы тестовая выборка (benchmark) оставалась фиксированной при увеличении обучающей.

Поддерживает:
- Выбор провайдера OpenRouter (по имени или по минимальной цене)
- Кэширование системного промпта через cache_control для сокращения токенов и расходов

Запуск:
    cd ml
    uv sync
    PYTHONPATH=src uv run python dataset/generate.py --train-size 800 --test-size 200
"""

import argparse
import asyncio
import csv
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

# Настройки OpenRouter API
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
OPENROUTER_PROVIDER_ORDER = os.getenv("OPENROUTER_PROVIDER_ORDER", "")
OPENROUTER_PROVIDER_SORT = os.getenv("OPENROUTER_PROVIDER_SORT", "price")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Категории жалоб ЖКХ из domain/tickets/catalog.py
CATEGORIES = {
    "water": "Водоснабжение (ХВС/ГВС/канализация, напор, утечки, засор)",
    "light": "Электроснабжение (освещение подъездов/двора, щитовые, искрение, провода)",
    "heating": "Отопление (температура батарей, течи стояков, завоздушивание, пар)",
    "door": "Двери и входные группы (домофон, замки, подвал, доводчики)",
    "cleaning": "Уборка и мусор (подъезд, дворовая территория, мусоропровод, грязь)",
    "lift": "Лифт (не работает, застрял человек, шумы, кнопки)",
    "other": "Прочее и общее имущество (кровля, фасад, балкон, сосульки, вопросы)",
}

STYLES = ["formal", "voice", "typo", "emotional", "short"]

# Статическая часть системного промпта (автоматически кэшируется OpenRouter API)
STATIC_SYSTEM_PROMPT = """Ты — генератор реалистичных текстов обращений и жалоб жителей многоквартирных домов в управляющую компанию (УО) или АДС.

ПРАВИЛА ОПРЕДЕЛЕНИЯ АВАРИЙНОСТИ (is_emergency):
- is_emergency = 1 (АВАРИЯ): Ситуация требует НЕМЕДЛЕННОГО выезда Аварийно-диспетчерской службы (АДС).
  Примеры: застрял человек в лифте, прорвало трубу ГВС/ХВС с кипятком/потопом, засор канализации с розливом стоков, искрит щиток с дымом/запахом гари, лопнул радиатор отопления в мороз, заблокирована единственная дверь при задымлении, осыпаются кирпичи с фасада на тротуар.
- is_emergency = 0 (ОБЫЧНАЯ): Плановая проблема или некритичная неисправность.
  Примеры: лифт не вызывается на этаж (пустой), слабый напор воды, слегка теплая батарея, перегорела лампочка в холле, не вымыт подъезд, шумит доводчик двери, капает из крана в подвале.

СТИЛИ ТЕКСТА:
  * formal: Официальное суховатое обращение с указанием подъезда или квартиры.
  * voice: Имитация голосового ввода без знаков препинания ("да здравствуйте тут кароче лифт застрял...").
  * typo: Сообщения с телефона с опечатками и пропущенными буквами.
  * emotional: Эмоциональный восклицательный текст с руганью на УО и угрозами ГЖИ.
  * short: Короткие фразы из 3-6 слов ("вода ледяная из крана 2 подъезд").

ФОРМАТ ОТВЕТА:
Верни ТОЛЬКО JSON-объект следующего вида без лишнего текста:
{
  "samples": [
    {
      "text": "текст обращения жителя",
      "style": "название стиля (formal/voice/typo/emotional/short)",
      "subcategory": "короткое наименование подпроблемы"
    }
  ]
}
"""


def clean_json_response(raw_text: str) -> Optional[Dict[str, Any]]:
    """Извлекает и валидирует JSON из ответа модели."""
    if not raw_text:
        return None

    # Вырезаем теги рассуждений <think>...</think>
    text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()

    # Ищем блок ```json ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
    else:
        # Ищем первую { ... }
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
        else:
            return None

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


async def generate_batch(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    category_key: str,
    is_emergency: int,
    count: int = 5,
    retries: int = 4,
) -> List[Dict[str, Any]]:
    """Генерирует пачку примеров для заданной категории и аварийности."""
    if not OPENROUTER_API_KEY:
        print("[!] ОШИБКА: Задайте OPENROUTER_API_KEY в ml/.env или переменных окружения!")
        sys.exit(1)

    category_name = CATEGORIES[category_key]
    emergency_str = "АВАРИЙНАЯ СИТУАЦИЯ" if is_emergency == 1 else "ОБЫЧНАЯ НЕАВАРИЙНАЯ ЗАЯВКА"

    user_prompt = (
        f"Сгенерируй {count} уникальных обращений от первого лица на русском языке.\n\n"
        f"КАТЕГОРИЯ: {category_key} ({category_name})\n"
        f"АВАРИЙНОСТЬ: {emergency_str} (is_emergency = {is_emergency})"
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/laughinme/hackathon-max",
        "X-Title": "HackathonMAX_DatasetGen",
    }

    # Кэширование системного промпта через cache_control (OpenRouter / Anthropic / DeepSeek)
    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": STATIC_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        },
        {"role": "user", "content": user_prompt},
    ]

    payload: Dict[str, Any] = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": 0.85,
    }

    # Настройка маршрутизации провайдера OpenRouter
    provider_config: Dict[str, Any] = {}
    if OPENROUTER_PROVIDER_ORDER:
        providers = [p.strip() for p in OPENROUTER_PROVIDER_ORDER.split(",") if p.strip()]
        if providers:
            provider_config["order"] = providers
            provider_config["allow_fallbacks"] = False
    elif OPENROUTER_PROVIDER_SORT:
        provider_config["sort"] = OPENROUTER_PROVIDER_SORT

    if provider_config:
        payload["provider"] = provider_config

    async with semaphore:
        for attempt in range(1, retries + 1):
            try:
                response = await client.post(
                    OPENROUTER_URL, headers=headers, json=payload, timeout=45.0
                )
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = clean_json_response(content)

                    if parsed and "samples" in parsed and isinstance(parsed["samples"], list):
                        result = []
                        for item in parsed["samples"]:
                            text_val = item.get("text", "").strip()
                            if text_val:
                                result.append({
                                    "text": text_val,
                                    "category": category_key,
                                    "is_emergency": is_emergency,
                                    "style": item.get("style", "formal"),
                                    "subcategory": item.get("subcategory", ""),
                                })
                        if result:
                            return result

                elif response.status_code == 429:
                    print(f"  [!] OpenRouter Rate Limit (429). Попытка {attempt}/{retries}...")
                else:
                    print(f"  [!] Ошибка API ({response.status_code}): {response.text[:200]}")

            except Exception as e:
                print(f"  [!] Ошибка сети/запроса (попытка {attempt}): {e}")

            if attempt < retries:
                await asyncio.sleep(2**attempt)

    return []


async def save_dataset_files(
    data: List[Dict[str, Any]],
    base_path: Path,
    filename_prefix: str,
    lock: asyncio.Lock,
) -> int:
    """Сохраняет пачку образцов в JSON и CSV форматы под asyncio.Lock (мгновенный кэш на диск)."""
    async with lock:
        base_path.mkdir(parents=True, exist_ok=True)

        json_path = base_path / f"{filename_prefix}.json"
        csv_path = base_path / f"{filename_prefix}.csv"

        # Чтение существующих данных для предотвращения дубликатов по тексту
        existing_texts = set()
        existing_data = []

        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    for item in existing_data:
                        existing_texts.add(item.get("text", "").strip())
            except Exception:
                existing_data = []

        new_items = []
        for item in data:
            t = item.get("text", "").strip()
            if t and t not in existing_texts:
                existing_texts.add(t)
                new_items.append(item)

        if not new_items:
            return len(existing_data)

        combined_data = existing_data + new_items

        # Сохранение в JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(combined_data, f, ensure_ascii=False, indent=2)

        # Сохранение в CSV
        fieldnames = ["text", "category", "is_emergency", "style", "subcategory"]
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in combined_data:
                writer.writerow({k: item.get(k, "") for k in fieldnames})

        print(f"  [✓] {filename_prefix}: +{len(new_items)} нов. | Всего в файле: {len(combined_data)}")
        return len(combined_data)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Генератор датасета жалоб ЖКХ для CatBoost")
    parser.add_argument("--train-size", type=int, default=800, help="Целевой размер train выборки")
    parser.add_argument("--test-size", type=int, default=200, help="Целевой размер test выборки")
    parser.add_argument("--mode", choices=["all", "train_only", "test_only"], default="all", help="Режим генерации")
    parser.add_argument("--concurrency", type=int, default=4, help="Параллельные запросы к OpenRouter")
    parser.add_argument("--output-dir", type=str, default="dataset/data", help="Директория для сохранения датасета")
    parser.add_argument("--seed", type=int, default=42, help="Случайное зерно")
    args = parser.parse_args()

    random.seed(args.seed)
    output_dir = Path(args.output_dir)

    start_time = time.perf_counter()

    print("==================================================")
    print("🚀 Генерация датасета обращений ЖКХ (CatBoost)")
    print(f"Модель: {OPENROUTER_MODEL}")
    if OPENROUTER_PROVIDER_ORDER:
        print(f"Провайдеры: {OPENROUTER_PROVIDER_ORDER}")
    elif OPENROUTER_PROVIDER_SORT:
        print(f"Сортировка провайдеров: {OPENROUTER_PROVIDER_SORT}")
    print(f"Цель: Train = {args.train_size}, Test = {args.test_size}")
    print(f"Директория вывода: {output_dir.resolve()}")
    print("==================================================")

    semaphore = asyncio.Semaphore(args.concurrency)
    file_lock = asyncio.Lock()

    async with httpx.AsyncClient() as client:

        # Сетка задач: (category, is_emergency)
        combos = [(cat, em) for cat in CATEGORIES.keys() for em in (0, 1)]
        samples_per_combo_train = max(1, args.train_size // len(combos))
        samples_per_combo_test = max(1, args.test_size // len(combos))

        if args.mode in ("all", "test_only"):
            print("\n--- [1/2] Генерация ТЕСТОВОЙ выборки (Test Set / Benchmark) ---")
            tasks = []
            for cat, em in combos:
                batch_count = max(1, samples_per_combo_test // 5)
                for _ in range(batch_count):
                    tasks.append(generate_batch(client, semaphore, cat, em, count=5))

            for completed_task in asyncio.as_completed(tasks):
                batch = await completed_task
                if batch:
                    await save_dataset_files(batch, output_dir, "test", file_lock)

        if args.mode in ("all", "train_only"):
            print("\n--- [2/2] Генерация ОБУЧАЮЩЕЙ выборки (Train Set) ---")
            tasks = []
            for cat, em in combos:
                batch_count = max(1, samples_per_combo_train // 5)
                for _ in range(batch_count):
                    tasks.append(generate_batch(client, semaphore, cat, em, count=5))

            for completed_task in asyncio.as_completed(tasks):
                batch = await completed_task
                if batch:
                    await save_dataset_files(batch, output_dir, "train", file_lock)

    elapsed = time.perf_counter() - start_time
    minutes = int(elapsed // 60)
    seconds = elapsed % 60
    time_str = f"{minutes} мин {seconds:.1f} сек" if minutes > 0 else f"{seconds:.2f} сек"

    print("\n==================================================")
    print(f"✅ Генерация завершена успешно!")
    print(f"⏱ Время выполнения: {time_str}")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(main())
