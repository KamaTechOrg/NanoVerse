from __future__ import annotations
import os
from pathlib import Path
from functools import lru_cache
from typing import List, Dict, Optional

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TextStreamer
from peft import PeftModel

# BASE_MODEL = Path("/srv/python_envs/shared_env/B/gemma-3-1b-it")
BASE_MODEL = Path("/srv/python_envs/shared_env/B/gemma-3-4b-it")

USE_4BIT = True          
DEVICE_MAP = "auto"     
DTYPE = "auto"           


@lru_cache(maxsize=1)
def _load_base():
    tok = AutoTokenizer.from_pretrained(str(BASE_MODEL), use_fast=True)
    kwargs = dict(
        device_map=DEVICE_MAP,
        torch_dtype=DTYPE,
    )
    if USE_4BIT:
        kwargs["load_in_4bit"] = True
    mdl = AutoModelForCausalLM.from_pretrained(str(BASE_MODEL), **kwargs)
    mdl.eval()
    return tok, mdl


@lru_cache(maxsize=16)
def _load_adapter(adapter_dir: Optional[str]):
 
    tok, base = _load_base()

    if not adapter_dir:
        print("[INF] no adapter_dir given, using base model only")
        return base

    p = Path(adapter_dir)
    if not p.exists():
        print(f"[INF] adapter_dir not found: {adapter_dir} -> using base model only")
        return base

    try:
        mdl = PeftModel.from_pretrained(base, adapter_dir, device_map=DEVICE_MAP)
        mdl.eval()
        print(f"[INF] loaded adapter from {adapter_dir}")
        return mdl
    except Exception as e:
        print(f"[INF] failed loading adapter {adapter_dir}: {e} -> using base model only")
        return base


def _chatml_to_text(history: List[Dict[str, str]]) -> str:
   
    lines: List[str] = []
    for m in history:
        role = m.get("role", "user")
        text = (m.get("content") or "").strip().replace("\n", " ")
        lines.append(f"{role.upper()}: {text}")
    lines.append("ASSISTANT:")
    return "\n".join(lines)


def generate_reply(
    chatml: List[Dict[str, str]],
    adapter_dir: Optional[str],
    max_new_tokens: int = 64,
    temperature: float = 0.7,
    top_p: float = 0.9,
) -> str:
    
    tok, mdl = _load_base()  

    prompt = _chatml_to_text(chatml)
    inputs = tok(prompt, return_tensors="pt").to(mdl.device)

    with torch.inference_mode():
        out_ids = mdl.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
            pad_token_id=tok.eos_token_id,
            eos_token_id=tok.eos_token_id,
        )

    gen_ids = out_ids[0][inputs["input_ids"].shape[-1]:]
    text = tok.decode(gen_ids, skip_special_tokens=True).strip()

   
    for marker in ["\nUSER:", "\nASSISTANT:", " USER:", " ASSISTANT:"]:
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx].strip()
            break

    for prefix in ("ASSISTANT:", "assistant:", "USER:", "User:", "SYSTEM:", "System:"):
        if text.startswith(prefix):
            text = text[len(prefix):].lstrip()
            break

    for end in [".", "!", "?"]:
        idx = text.find(end)
        if idx != -1:
            text = text[: idx + 1]
            break

    return text.strip()


def warmup():
    
    _load_base()
    return True
