from __future__ import annotations
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
USERS = ROOT / "data" / "users"
MIN = 60  

def make_chat(pid: str, n=MIN):
    items = []
    for i in range(n//2):
        items.append({"role":"user","content":f"היי {pid}, מה המצב? #{i}"})
        items.append({"role":"assistant","content":f"היי! הכל אחלה, #{i}"})
    return items

for pdir in USERS.glob("player*_split"):
    pid = pdir.name.removeprefix("player").removesuffix("_split")
    train = pdir/"train.jsonl"
    val   = pdir/"val.jsonl"
    if not train.exists():
        train.parent.mkdir(parents=True, exist_ok=True)
        with train.open("w", encoding="utf-8") as f:
            for ex in make_chat(pid, 80):
                f.write(json.dumps(ex, ensure_ascii=False)+"\n")
        print("WROTE", train)
    if not val.exists():
        with val.open("w", encoding="utf-8") as f:
            for ex in make_chat(pid, 20):
                f.write(json.dumps(ex, ensure_ascii=False)+"\n")
        print("WROTE", val)
print("OK.")
