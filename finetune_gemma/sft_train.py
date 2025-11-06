"""
train_lora_sft.py — TRL 0.24 SFT with optional QLoRA.

What this does:
- Fine-tunes a base chat model using LoRA via TRL's SFTTrainer.
- Optional QLoRA (4-bit) reduces VRAM usage by quantizing base weights while keeping bfloat16 compute.

Typical VRAM on an RTX 2080 Ti (11GB), Gemma-3-1B-IT, LoRA r=16:
- Full-precision (fp16/bf16), bs=1: ~7–8 GB idle, ~9–10 GB during training.
- QLoRA 4-bit (nf4), bs=1: ~3.5–4.5 GB idle, ~6–7 GB during training.
These are ballpark numbers; exact usage varies by sequence length, optimizer states, and driver/runtime.
"""

from pathlib import Path
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, PeftModel
from trl import SFTTrainer, SFTConfig
import argparse, torch, os, os.path as osp
from transformers import set_seed


def build_tokenizer(model_name_or_path: str, local: bool = False):
    """
    Build a tokenizer and make sure PAD is defined.

    Why set PAD=EOS?
    - Some chat templates expect a PAD token; if it's missing, HF falls back and logs warnings.
    - Using EOS as PAD is a common, safe default that keeps attention masks consistent.

    VRAM impact:
    - None. This only changes tokenizer metadata and padding behavior.
    """
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="google/gemma-3-1b-it")
    ap.add_argument("--data_file", required=True, help="path to JSONL with {'messages': [...]}")
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--bsz", type=int, default=2)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--max_len", type=int, default=1024)
    ap.add_argument("--qlora", action="store_true")
    ap.add_argument("--resume_adapter_dir", default=None)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    set_seed(args.seed)

    is_local = osp.isdir(args.model)
    if is_local:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")

    tok = build_tokenizer(args.model, local=is_local)
    tok.model_max_length = args.max_len

    model = build_model(args.model, use_qlora=args.qlora, local=is_local)

    if args.resume_adapter_dir and Path(args.resume_adapter_dir).exists():
        model = PeftModel.from_pretrained(model, args.resume_adapter_dir, is_trainable=True)

    lora_cfg = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05,
        target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"]
    )

    # Preprocessing is handled upstream; dataset here is expected to be clean.
    ds = load_dataset("json", data_files=args.data_file, split="train")

    sft_cfg = SFTConfig(
        output_dir=args.out_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.bsz,
        learning_rate=args.lr,
        logging_steps=10,
        save_steps=200,
        save_total_limit=2,
        bf16=True,
        # packing=False keeps one sample → one sequence. Safer with some chat templates and avoids
        # sequence boundary artifacts; can be revisited once template compatibility is verified.
        packing=False,
    )

    trainer = SFTTrainer(
        model=model,
        args=sft_cfg,
        train_dataset=ds,
        peft_config=lora_cfg,
        processing_class=tok,
    )

    trainer.train()
    trainer.model.save_pretrained(args.out_dir)
    tok.save_pretrained(args.out_dir)

if __name__ == "__main__":
    main()
