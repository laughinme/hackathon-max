"""SFT-дообучение LoRA-адаптера на диалоговой выборке.

⚠️ Скрипт написан, но ЕЩЁ НЕ ЗАПУСКАЛСЯ: обучение запланировано
отдельным этапом. Зависимости вынесены в `requirements-ml.txt` и в
рантайм бота не тянутся — бот ходит в модель по HTTP.

Запуск (на машине с GPU):
    pip install -r requirements-ml.txt
    python -m ml.dataset.build --count 4000
    python -m ml.training.train_lora --epochs 3

Loss считается только на ответе ассистента (целевом JSON):
за это отвечает `DataCollatorForCompletionOnlyLM` и
`response_template` из конфига.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ml.training.config import TrainingConfig

logger = logging.getLogger(__name__)


def build_dataset(config: TrainingConfig):
    """Готовит датасет в формате чата для SFTTrainer."""

    from datasets import load_dataset  # noqa: PLC0415

    from ml.dataset.schema import TrainingExample  # noqa: PLC0415

    def to_chat(row: dict) -> dict:
        example = TrainingExample(**row)
        return {"messages": example.to_chat()}

    dataset = load_dataset(
        "json",
        data_files={
            "train": str(config.train_file),
            "validation": str(config.val_file),
        },
    )
    return dataset.map(to_chat, remove_columns=dataset["train"].column_names)


def build_model(config: TrainingConfig):
    """Загружает базовую модель и токенизатор."""

    import torch  # noqa: PLC0415
    from transformers import (  # noqa: PLC0415
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
    )

    quantization = None
    if config.load_in_4bit:
        quantization = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

    tokenizer = AutoTokenizer.from_pretrained(config.base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        config.base_model,
        quantization_config=quantization,
        dtype=torch.bfloat16 if config.bf16 else None,
        device_map="auto",
    )
    model.config.use_cache = False
    return model, tokenizer


def train(config: TrainingConfig) -> Path:
    """Запускает дообучение и сохраняет адаптер."""

    from peft import LoraConfig  # noqa: PLC0415
    from trl import (  # noqa: PLC0415
        DataCollatorForCompletionOnlyLM,
        SFTConfig,
        SFTTrainer,
    )

    config.validate()
    dataset = build_dataset(config)
    model, tokenizer = build_model(config)

    peft_config = LoraConfig(
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        target_modules=list(config.lora_target_modules),
        bias="none",
        task_type="CAUSAL_LM",
    )

    sft_config = SFTConfig(
        output_dir=str(config.output_dir),
        num_train_epochs=config.epochs,
        learning_rate=config.learning_rate,
        lr_scheduler_type=config.lr_scheduler_type,
        warmup_ratio=config.warmup_ratio,
        per_device_train_batch_size=config.per_device_batch_size,
        per_device_eval_batch_size=config.per_device_batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        gradient_checkpointing=True,
        max_length=config.max_seq_length,
        bf16=config.bf16,
        logging_steps=config.logging_steps,
        eval_strategy="steps",
        eval_steps=config.eval_steps,
        save_steps=config.save_steps,
        save_total_limit=5,
        load_best_model_at_end=False,
        seed=config.seed,
        report_to=[],
    )

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        args=sft_config,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        peft_config=peft_config,
        data_collator=DataCollatorForCompletionOnlyLM(
            response_template=config.response_template,
            tokenizer=tokenizer,
        ),
    )

    trainer.train()
    trainer.save_model(str(config.output_dir))
    tokenizer.save_pretrained(str(config.output_dir))

    logger.info("Адаптер сохранён в %s", config.output_dir)
    return config.output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="SFT LoRA для бота ЖКХ")
    parser.add_argument("--base-model", default=None)
    parser.add_argument("--dataset-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--epochs", type=float, default=None)
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument("--no-4bit", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    config = TrainingConfig()
    if args.base_model:
        config.base_model = args.base_model
    if args.dataset_dir:
        config.dataset_dir = args.dataset_dir
    if args.output_dir:
        config.output_dir = args.output_dir
    if args.epochs:
        config.epochs = args.epochs
    if args.learning_rate:
        config.learning_rate = args.learning_rate
    if args.no_4bit:
        config.load_in_4bit = False

    train(config)


if __name__ == "__main__":
    main()
