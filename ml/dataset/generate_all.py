"""Скрипт пакетной генерации датасетов для всех моделей из models.txt.

Автоматически:
1. Читает модели из ml/dataset/models.txt
2. Формирует понятный префикс (qwen, phi, glm, ministral)
3. Запускает generate.py для каждой модели (320 train, 80 test)
4. Вызывает combine.py для объединения всех моделей (включая deepseek) в итоговые train.json/test.json

Запуск:
    cd ml
    PYTHONPATH=src uv run python dataset/generate_all.py
"""

import subprocess
import sys
from pathlib import Path

DATASET_DIR = Path(__file__).resolve().parent
MODELS_FILE = DATASET_DIR / "models.txt"


def derive_prefix(model_name: str) -> str:
    """Извлекает понятный короткий префикс из OpenRouter названия модели."""
    name = model_name.split("/")[-1].split(":")[0].lower()
    for key in ["qwen", "phi", "glm", "ministral", "mistral", "llama", "deepseek", "gemma", "claude"]:
        if key in name:
            return key
    clean = name.replace(".", "_").replace("-", "_")
    return clean[:12]


def main() -> None:
    if not MODELS_FILE.is_file():
        print(f"[!] Файл {MODELS_FILE} не найден!")
        sys.exit(1)

    lines = MODELS_FILE.read_text(encoding="utf-8").splitlines()
    models = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]

    if not models:
        print("[!] Файл models.txt пуст!")
        sys.exit(1)

    print("==================================================")
    print(f"🚀 ПАКЕТНАЯ ГЕНЕРАЦИЯ ДАТАСЕТА ({len(models)} моделей)")
    for m in models:
        print(f"  - {m} (префикс: {derive_prefix(m)})")
    print("==================================================")

    prefixes = ["deepseek"]  # Исходный датасет DeepSeek у нас уже готов!

    for model in models:
        prefix = derive_prefix(model)
        if prefix not in prefixes:
            prefixes.append(prefix)

        print(f"\n▶ [{models.index(model)+1}/{len(models)}] Запуск генерации для {model} (префикс: '{prefix}')")
        cmd = [
            sys.executable,
            str(DATASET_DIR / "generate.py"),
            "--model",
            model,
            "--prefix",
            prefix,
            "--train-size",
            "320",
            "--test-size",
            "80",
        ]
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"  [!] Модель {model} завершилась с ошибкой ({result.returncode}), переходим к следующей...")

    print("\n==================================================")
    print("🔄 ОБЪЕДИНЕНИЕ ВСЕХ СГЕНЕРИРОВАННЫХ ДАТАСЕТОВ")
    print("==================================================")
    combine_cmd = [
        sys.executable,
        str(DATASET_DIR / "combine.py"),
        "combine",
        "--prefixes",
        *prefixes,
    ]
    subprocess.run(combine_cmd)


if __name__ == "__main__":
    main()
