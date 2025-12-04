
"""
sft_train.py — TRL 0.24 SFT with optional QLoRA and early stopping.

Implements LoRA fine-tuning for chat models (Gemma, Mistral, etc.) with:
- Split to train/validation sets.
- Early stopping when eval loss stops improving.
- Compatible with both LoRA and QLoRA.
"""

from pathlib import Path
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    EarlyStoppingCallback,
    set_seed
)
from peft import LoraConfig, PeftModel
from trl import SFTTrainer, SFTConfig
import argparse, torch, os, os.path as osp


# ======== TOKENIZER + MODEL BUILDERS ========
def build_tokenizer(model_name_or_path: str, local: bool = False):
    kw = {"local_files_only": True} if local else {}
    tok = AutoTokenizer.from_pretrained(model_name_or_path, use_fast=True, **kw)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"
    return tok


def build_model(model_name_or_path: str, use_qlora: bool = False, local: bool = False):
    quant_cfg = None
    if use_qlora:
        quant_cfg = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
    kw = {"local_files_only": True} if local else {}
    model = AutoModelForCausalLM.from_pretrained(
        model_name_or_path,
        dtype=torch.bfloat16,
        quantization_config=quant_cfg,
        **kw,
    )
    return model


# ======== MAIN ========
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="google/gemma-3-1b-it")
    ap.add_argument("--data_file", required=True, help="path to JSONL dataset")
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--epochs", type=int, default=1000)  # large max, early stop handles cutoff
    ap.add_argument("--bsz", type=int, default=2)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--max_len", type=int, default=1024)
    ap.add_argument("--qlora", action="store_true")
    ap.add_argument("--resume_adapter_dir", default=None)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    # --- Setup & Reproducibility ---
    set_seed(args.seed)
    is_local = osp.isdir(args.model)
    if is_local:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")

    # --- Tokenizer & Model ---
    tok = build_tokenizer(args.model, local=is_local)
    tok.model_max_length = args.max_len

    model = build_model(args.model, use_qlora=args.qlora, local=is_local)

    if args.resume_adapter_dir and Path(args.resume_adapter_dir).exists():
        model = PeftModel.from_pretrained(model, args.resume_adapter_dir, is_trainable=True)

    # --- LoRA config ---
    lora_cfg = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )

    # --- Dataset split (train/validation) ---
    ds = load_dataset("json", data_files=args.data_file, split="train")
    ds_train = ds.select(range(int(0.9 * len(ds))))
    ds_eval = ds.select(range(int(0.9 * len(ds)), len(ds)))

    # --- Early stopping ---
    early_stopping = EarlyStoppingCallback(
        early_stopping_patience=3,
        early_stopping_threshold=0.0,
    )

    # --- SFT Config ---
    sft_cfg = SFTConfig(
        output_dir=args.out_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.bsz,
        gradient_accumulation_steps=max(1, 4 // args.bsz),
        per_device_eval_batch_size=args.bsz,
        learning_rate=args.lr,
        logging_steps=10,
        save_steps=200,
        save_total_limit=2,
        bf16=True,
        eval_strategy="steps",
        eval_steps=10,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        eval_on_start=True,
        load_best_model_at_end=True,
        packing=False,
    )

    # --- Trainer ---
    trainer = SFTTrainer(
        model=model,
        args=sft_cfg,
        train_dataset=ds_train,
        eval_dataset=ds_eval,
        peft_config=lora_cfg,
        processing_class=tok,
        callbacks=[early_stopping],
    )

    trainer.train()
    trainer.model.save_pretrained(args.out_dir)
    tok.save_pretrained(args.out_dir)


if __name__ == "__main__":
    main()
