"""Конфигурация дообучения.

Базовая модель выбрана по трём причинам:
- лицензия Apache-2.0 — можно использовать на хакатоне без оговорок;
- сильный русский язык из коробки;
- 7B помещается в LoRA-дообучение на одной GPU 24 ГБ в 4-битном режиме.

Всё переопределяется переменными окружения или аргументами CLI.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"


@dataclass
class TrainingConfig:
    """Параметры SFT-дообучения LoRA-адаптера."""

    base_model: str = os.getenv("ML_BASE_MODEL", DEFAULT_BASE_MODEL)
    dataset_dir: Path = Path(os.getenv("ML_DATASET_DIR", "data/dataset"))
    output_dir: Path = Path(os.getenv("ML_OUTPUT_DIR", "data/adapter"))

    # Квантизация базовой модели: 4 бита экономят память на 24 ГБ карте.
    load_in_4bit: bool = True
    bf16: bool = True

    # LoRA.
    lora_r: int = 32
    lora_alpha: int = 64
    lora_dropout: float = 0.05
    lora_target_modules: tuple[str, ...] = (
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    )

    # Обучение.
    epochs: float = 3.0
    learning_rate: float = 1e-4
    lr_scheduler_type: str = "cosine"
    warmup_ratio: float = 0.03
    per_device_batch_size: int = 2
    gradient_accumulation_steps: int = 8
    max_seq_length: int = 2048
    logging_steps: int = 10
    eval_steps: int = 50
    save_steps: int = 100
    seed: int = 42

    #: Маркер начала ответа ассистента — по нему считается loss
    #: только на целевом JSON, а не на промпте и репликах жителя.
    response_template: str = "<|im_start|>assistant\n"

    extra: dict[str, str] = field(default_factory=dict)

    @property
    def train_file(self) -> Path:
        return self.dataset_dir / "train.jsonl"

    @property
    def val_file(self) -> Path:
        return self.dataset_dir / "val.jsonl"

    def validate(self) -> None:
        """Проверяет, что выборка на месте."""

        for path in (self.train_file, self.val_file):
            if not path.exists():
                raise FileNotFoundError(
                    f"Не найден файл выборки {path}. "
                    "Сначала выполните: python -m ml.dataset.build"
                )
