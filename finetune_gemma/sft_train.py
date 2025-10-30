# train_lora_sft.py — TRL 0.24 + robust data sanitizing for messages alternation
from pathlib import Path
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, PeftModel
from trl import SFTTrainer, SFTConfig
import argparse, torch, os, os.path as osp

def build_tokenizer(model_name_or_path: str, local: bool = False):
    kw = {"local_files_only": True} if local else {}
    tok = AutoTokenizer.from_pretrained(model_name_or_path, use_fast=True, **kw)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
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
        device_map="auto",
        quantization_config=quant_cfg,
        **kw,
    )
    return model

# ---------- utilities to sanitize messages ----------
def _merge_same_role(turns):
    if not turns: return []
    out = [turns[0].copy()]
    for t in turns[1:]:
        if t.get("role") == out[-1].get("role"):
            out[-1]["content"] = (out[-1].get("content","") + "\n" + t.get("content","")).strip()
        else:
            out.append({"role": t.get("role"), "content": (t.get("content","") or "").strip()})
    return out

def _only_user_assistant(turns):
    fixed=[]
    for t in turns:
        role=t.get("role")
        if role not in ("user","assistant"):  # זרוק תפקידים אחרים
            continue
        txt=(t.get("content","") or "").strip()
        if not txt:
            continue
        fixed.append({"role":role, "content":txt})
    return fixed

def _enforce_alternation(turns):
    # הסר מובילים עד שמתחיל ב-user
    i=0
    while i < len(turns) and turns[i]["role"]!="user":
        i+=1
    turns = turns[i:]
    # הסר מסיימים עד שמסתיים ב-assistant
    while turns and turns[-1]["role"]!="assistant":
        turns.pop()
    # מיזוג כפולים
    turns = _merge_same_role(turns)
    # בדיקת התחלפות מלאה
    if len(turns) < 2: return None
    if turns[0]["role"]!="user" or turns[-1]["role"]!="assistant":
        return None
    for a,b in zip(turns, turns[1:]):
        if a["role"] == b["role"]:
            return None
    return turns

def _sanitize_batch(batch):
    msgs_list = batch["messages"]
    new_msgs = []
    valid = []
    for msgs in msgs_list:
        msgs = _only_user_assistant(msgs or [])
        msgs = _merge_same_role(msgs)
        msgs = _enforce_alternation(msgs)
        if msgs is None:
            valid.append(False)
            # לא נוסיף placeholder; נשאיר ריק ונפיל בסינון
            new_msgs.append([{"role":"user","content":"."},{"role":"assistant","content":"."}])
        else:
            valid.append(True)
            new_msgs.append(msgs)
    return {"messages": new_msgs, "valid": valid}
# ----------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="google/gemma-3-1b-it")
    ap.add_argument("--data_file", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--bsz", type=int, default=2)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--max_len", type=int, default=1024)
    ap.add_argument("--qlora", action="store_true")
    ap.add_argument("--resume_adapter_dir", default=None)
    args = ap.parse_args()

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

    ds = load_dataset("json", data_files=args.data_file, split="train")

    # ניקוי/סינון הדאטה לפני SFTTrainer — כדי למנוע TemplateError
    orig_cols = ds.column_names
    ds = ds.map(_sanitize_batch, batched=True, remove_columns=[c for c in orig_cols if c!="messages"])
    before = ds.num_rows
    ds = ds.filter(lambda valid: valid, input_columns=["valid"])
    ds = ds.remove_columns("valid")
    after = ds.num_rows
    print(f"[CLEAN] kept {after}/{before} samples after strict alternation filtering")

    sft_cfg = SFTConfig(
        output_dir=args.out_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.bsz,
        learning_rate=args.lr,
        logging_steps=10,
        save_steps=200,
        save_total_limit=2,
        bf16=True,
        packing=False,  # יציב עבור flash-attn לא נתמך
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
