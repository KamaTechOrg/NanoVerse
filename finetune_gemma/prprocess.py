from pathlib import Path
import json, os, sys
from typing import Dict, Any, List

ROOT = Path(__file__).resolve().parents[1]
TOP = ROOT.parent
if str(TOP) not in sys.path:
    sys.path.insert(0, str(TOP))

from prepare_user_jsonl import load_json, normalize_messages, build_user_datasets

def split_train_test(samples: List[Dict[str, Any]], train_ratio: float = 0.9):
    n = len(samples)
    k = int(n * train_ratio)
    return samples[:k], samples[k:]

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def write_jsonl(path: Path, rows: List[Dict[str, Any]]):
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def main(cfg_path: str = "preprocess/ds.json"):
    cfg = json.loads(Path(cfg_path).read_text(encoding="utf-8"))
    chats_path = Path(cfg["input_chats"]).resolve()
    if not chats_path.exists():
        raise FileNotFoundError(f"Missing chats file: {chats_path}")

    raw = load_json(chats_path)
    messages = normalize_messages(raw)
    if not messages:
        raise SystemExit(" No messages found in chats.json")

    per_user = build_user_datasets(messages, history_size=cfg.get("history", 6))

    out_root = Path(cfg["out_root"])
    train_ratio = cfg.get("train_ratio", 0.9)
    users = cfg.get("users") or list(per_user.keys())

    for uid in users:
        rows = per_user.get(uid, [])
        user_dir = out_root / f"{uid}_split"
        train, test = split_train_test(rows, train_ratio=train_ratio)
        write_jsonl(user_dir / "train.jsonl", train)
        write_jsonl(user_dir / "test.jsonl", test)

if __name__ == "__main__":
    main()
