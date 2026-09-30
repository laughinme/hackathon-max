"""Скрипт для утилиты управления и объединения датасетов жалоб ЖКХ.

Поддерживает:
- Сохранение/сэмплирование датасетов по моделям (DeepSeek, Qwen, Phi)
- Балансированное сэмплирование (320 train, 80 test)
- Объединение датасетов нескольких моделей в итоговые train.json / test.json (и CSV)
- Проверку статистики и распределения по категориям и аварийности

Запуск:
    # Посмотреть статус всех датасетов:
    PYTHONPATH=src uv run python dataset/combine.py status

    # Объединить датасеты разных моделей в основные train.json и test.json:
    PYTHONPATH=src uv run python dataset/combine.py combine --prefixes deepseek qwen phi
"""

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

DATA_DIR = Path(__file__).resolve().parent / "data"
FIELDNAMES = ["text", "category", "is_emergency", "style", "subcategory"]


def load_dataset(path: Path) -> List[Dict[str, Any]]:
    """Загружает JSON датасет."""
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_dataset(data: List[Dict[str, Any]], json_path: Path, csv_path: Path) -> None:
    """Сохраняет датасет в JSON и CSV форматы."""
    json_path.parent.mkdir(parents=True, exist_ok=True)

    # Запись JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Запись CSV
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for item in data:
            writer.writerow({k: item.get(k, "") for k in FIELDNAMES})


def sample_balanced(data: List[Dict[str, Any]], target_size: int, seed: int = 42) -> List[Dict[str, Any]]:
    """Стратифицированный сэмплинг датасета по (category, is_emergency)."""
    if len(data) <= target_size:
        return list(data)

    random.seed(seed)
    # Группировка по (category, is_emergency)
    groups: Dict[Tuple[str, int], List[Dict[str, Any]]] = {}
    for item in data:
        key = (item.get("category", "other"), int(item.get("is_emergency", 0)))
        groups.setdefault(key, []).append(item)

    # Перемешивание внутри каждой группы
    for key in groups:
        random.shuffle(groups[key])

    num_groups = len(groups)
    base_per_group = target_size // num_groups
    remainder = target_size % num_groups

    sampled: List[Dict[str, Any]] = []
    sorted_keys = sorted(groups.keys())

    for idx, key in enumerate(sorted_keys):
        take = base_per_group + (1 if idx < remainder else 0)
        group_items = groups[key]
        sampled.extend(group_items[:take])

    random.shuffle(sampled)
    return sampled


def cmd_status(data_dir: Path) -> None:
    """Отображает статус и размер всех датасетов в директории."""
    print("==================================================")
    print("📊 СТАТУС ДАТАСЕТОВ В ml/dataset/data")
    print("==================================================")

    json_files = sorted(data_dir.glob("*.json"))
    if not json_files:
        print("Датасеты не найдены.")
        return

    for path in json_files:
        data = load_dataset(path)
        cats = Counter(x.get("category", "") for x in data)
        emergencies = Counter(x.get("is_emergency", 0) for x in data)
        print(f"\n📄 {path.name}: {len(data)} записей")
        print(f"   Категории: {dict(cats)}")
        print(f"   Аварийность: emergency=1: {emergencies[1]}, emergency=0: {emergencies[0]}")


def cmd_sample(
    input_file: Path,
    output_prefix: str,
    train_size: int,
    test_size: int,
    data_dir: Path,
    seed: int = 42,
) -> None:
    """Сэмплирует исходный большой датасет на train и test заданного размера."""
    train_full_path = data_dir / f"train_{input_file}.json" if not input_file.is_file() else input_file
    if not train_full_path.is_file():
        train_full_path = data_dir / f"{input_file}.json"

    data = load_dataset(train_full_path)
    if not data:
        print(f"[!] Файл {train_full_path} пуст или не найден!")
        return

    sampled_train = sample_balanced(data, train_size, seed=seed)

    out_train_json = data_dir / f"train_{output_prefix}.json"
    out_train_csv = data_dir / f"train_{output_prefix}.csv"
    save_dataset(sampled_train, out_train_json, out_train_csv)
    print(f"  [✓] Сохранён train_{output_prefix}: {len(sampled_train)} записей -> {out_train_json.name}")


def cmd_combine(prefixes: List[str], data_dir: Path) -> None:
    """Объединяет несколько датасетов (train_* и test_*) в итоговые train.json/test.json."""
    print("==================================================")
    print(f"🔄 ОБЪЕДИНЕНИЕ ДАТАСЕТОВ ДЛЯ ПРЕФИКСОВ: {', '.join(prefixes)}")
    print("==================================================")

    for split in ("train", "test"):
        combined_data: List[Dict[str, Any]] = []
        seen_texts: Set[str] = set()

        for prefix in prefixes:
            json_name = f"{split}_{prefix}.json"
            file_path = data_dir / json_name

            if not file_path.exists():
                print(f"  [!] Файл {json_name} не найден, пропускаем...")
                continue

            data = load_dataset(file_path)
            added_from_file = 0
            for item in data:
                t = item.get("text", "").strip()
                if t and t not in seen_texts:
                    seen_texts.add(t)
                    combined_data.append(item)
                    added_from_file += 1
            print(f"  [+] {json_name}: добавлено {added_from_file} уник. примеров из {len(data)}")

        out_json = data_dir / f"{split}.json"
        out_csv = data_dir / f"{split}.csv"
        save_dataset(combined_data, out_json, out_csv)
        print(f"  [✓] ИТОГО {split}: {len(combined_data)} записей сохранены в {out_json.name} и {out_csv.name}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Управление и объединение датасетов ЖКХ")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Команда status
    subparsers.add_parser("status", help="Показать размер и статистику всех датасетов")

    # Команда combine
    combine_p = subparsers.add_parser("combine", help="Объединить датасеты указанных моделей в train.json / test.json")
    combine_p.add_argument(
        "--prefixes",
        nargs="+",
        default=["deepseek", "qwen", "phi"],
        help="Список префиксов моделей (например, deepseek qwen phi)",
    )

    # Команда sample
    sample_p = subparsers.add_parser("sample", help="Сэмплировать существующий датасет в заданный размер")
    sample_p.add_argument("--input-file", type=Path, default=Path("train_deepseek_full.json"))
    sample_p.add_argument("--output-prefix", type=str, default="deepseek")
    sample_p.add_argument("--train-size", type=int, default=320)
    sample_p.add_argument("--test-size", type=int, default=80)
    sample_p.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()

    if args.command == "status":
        cmd_status(DATA_DIR)
    elif args.command == "combine":
        cmd_combine(args.prefixes, DATA_DIR)
    elif args.command == "sample":
        cmd_sample(
            args.input_file,
            args.output_prefix,
            args.train_size,
            args.test_size,
            DATA_DIR,
            args.seed,
        )


if __name__ == "__main__":
    main()
