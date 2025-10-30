from pathlib import Path
import os, torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

# בסיס המודל המקומי
BASE = "/srv/python_envs/shared_env/B/gemma-3-1b-it"

# אדפטר מקומי: מקבל מ-ADAPTER_PATH או ברירת-מחדל adapters/player1
ADAPTER = os.environ.get("ADAPTER_PATH", "adapters/player1")
if not os.path.isabs(ADAPTER):
    ADAPTER = str((Path(__file__).parent / ADAPTER).resolve())

cfg = Path(ADAPTER) / "adapter_config.json"
if not cfg.exists():
    raise FileNotFoundError(f"missing adapter_config.json in {ADAPTER}")

# בוחרים dtype תואם ל-GPU (2080Ti => בלי bf16)
use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
dtype = torch.bfloat16 if use_bf16 else torch.float16

# טוקנייזר ומודל בסיס – מקומי בלבד (ללא הורדה מהרשת)
tok = AutoTokenizer.from_pretrained(BASE, use_fast=True, local_files_only=True)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token

base = AutoModelForCausalLM.from_pretrained(
    BASE,
    device_map="auto",
    dtype=dtype,
    local_files_only=True,
)

# טעינת אדפטר מקומי (ללא HF)
model = PeftModel.from_pretrained(base, ADAPTER, is_trainable=False)
model.eval()

def chat_once(user_text: str):
    msgs = [
        {"role":"system","content":"ענה בעברית ברורה וקצרה, שמור על סגנון עקבי של השחקן."},
        {"role":"user","content":user_text},
    ]
    prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inputs = tok(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=60)
    text = tok.decode(out[0], skip_special_tokens=True)
    return text

if __name__ == "__main__":
    print(chat_once("היי! מה חדש?"))
