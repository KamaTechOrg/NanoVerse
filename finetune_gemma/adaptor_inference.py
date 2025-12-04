from __future__ import annotations

import os
from pathlib import Path
import argparse
from dataclasses import dataclass
from typing import Optional, List, Dict

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
from peft import PeftModel


# -------- Defaults (override with flags/env) --------
DEFAULT_BASE = "/srv/python_envs/shared_env/B/gemma-3-1b-it"
DEFAULT_ADAPTER = os.environ.get("ADAPTER_PATH", "adapters/player1/latest")


@dataclass
class GenParams:
    max_new_tokens: int = 48
    temperature: float = 0.0          # deterministic by default
    do_sample: bool = False
    repetition_penalty: float = 1.15
    top_k: Optional[int] = None       # keep None to avoid HF warnings
    top_p: Optional[float] = None     # keep None to avoid HF warnings


class LoraModel:
    """Loads local base model and attaches a local LoRA adapter."""

    def __init__(self, base_model_path: str) -> None:
        self.base_model_path = base_model_path

        # dtype: use bf16 when supported, else fp16 (fits 2080Ti better than fp32)
        use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
        self.dtype = torch.bfloat16 if use_bf16 else torch.float16

        # tokenizer from BASE (stable)
        self.tok = AutoTokenizer.from_pretrained(
            base_model_path, use_fast=True, local_files_only=True
        )
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token

        # base model from disk only (no downloads)
        print(f"🔹 Base: {self.base_model_path}")
        self.base = AutoModelForCausalLM.from_pretrained(
            base_model_path,
            device_map="auto",
            dtype=self.dtype,
            local_files_only=True,
        )
        self.model = self.base.eval()

    def load_adapter(self, adapter_path: str) -> None:
        ap = adapter_path
        if not os.path.isabs(ap):
            ap = str((Path(__file__).parent / ap).resolve())

        # Validate adapter contents for clearer errors
        required = ["adapter_model.safetensors", "adapter_config.json"]
        missing = [f for f in required if not (Path(ap) / f).exists()]
        if missing:
            raise FileNotFoundError(f"Missing adapter files in {ap}: {missing}")

        print(f"🔹 Adapter: {ap}")
        self.model = PeftModel.from_pretrained(self.base, ap, is_trainable=False).eval()

    def _render_chat(self, system_prompt: Optional[str], user_text: str) -> str:
        msgs: List[Dict[str, str]] = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append({"role": "user", "content": user_text})
        return self.tok.apply_chat_template(
            msgs, tokenize=False, add_generation_prompt=True
        )

    def generate(self, user_text: str, system_prompt: Optional[str], gen: GenParams) -> str:
        prompt = self._render_chat(system_prompt, user_text)
        enc = self.tok(prompt, return_tensors="pt")
        enc = {k: v.to(self.model.device) for k, v in enc.items()}
        input_len = enc["input_ids"].shape[1]

        gconf = GenerationConfig(
            max_new_tokens=gen.max_new_tokens,
            temperature=gen.temperature,
            do_sample=gen.do_sample,
            repetition_penalty=gen.repetition_penalty,
            eos_token_id=self.tok.eos_token_id,
            pad_token_id=self.tok.pad_token_id,
        )
        if gen.top_k is not None:
            gconf.top_k = gen.top_k
        if gen.top_p is not None:
            gconf.top_p = gen.top_p

        with torch.no_grad():
            out = self.model.generate(**enc, generation_config=gconf)

        # decode only the newly generated part
        gen_ids = out[0][input_len:]
        reply = self.tok.decode(gen_ids, skip_special_tokens=True).strip()
        # keep the first line to reduce rambling on tiny datasets
        return reply.splitlines()[0].strip() if reply else reply


def _resolve_adapter(arg_value: Optional[str]) -> str:
    return arg_value.strip() if arg_value else DEFAULT_ADAPTER


def main() -> None:
    p = argparse.ArgumentParser(description="Gemma-3 + LoRA adapter inference (local paths only)")
    p.add_argument("--base", type=str, default=DEFAULT_BASE, help="Base model path")
    p.add_argument("--adapter", type=str, default=None, help="Adapter path (env ADAPTER_PATH overrides)")
    p.add_argument("--msg", type=str, default="Hi!", help="User message")
    p.add_argument(
        "--system",
        type=str,
        default="Answer in clear, concise Hebrew in the player's consistent style.",
        help="System instruction",
    )
    p.add_argument("--max_new_tokens", type=int, default=48)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--repetition_penalty", type=float, default=1.15)
    p.add_argument("--top_k", type=int, default=None)
    p.add_argument("--top_p", type=float, default=None)
    args = p.parse_args()

    lm = LoraModel(args.base)
    lm.load_adapter(_resolve_adapter(args.adapter))

    gen = GenParams(
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        do_sample=(args.temperature > 0.0),
        repetition_penalty=args.repetition_penalty,
        top_k=args.top_k,
        top_p=args.top_p,
    )

    print(lm.generate(args.msg, args.system, gen))


if __name__ == "__main__":
    main()
