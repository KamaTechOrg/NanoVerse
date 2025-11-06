# prepare_user_jsonl.py
from __future__ import annotations
import json, os, argparse
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, List

MSG_TEXT_KEYS = ["content", "text", "message", "body"]
SENDER_KEYS   = ["sender_id", "author_id", "from", "user_id"]
DELETED_KEYS  = ["deleted", "is_deleted"]

def _extract(d: Dict[str, Any], keys: List[str], default=None):
    for k in keys:
        if k in d:
            return d[k]
    return default

def _is_deleted(d: Dict[str, Any]) -> bool:
    for k in DELETED_KEYS:
        if k in d and bool(d[k]) is True:
            return True
    return False

def _msg_text(d: Dict[str, Any]) -> str | None:
    v = _extract(d, MSG_TEXT_KEYS)
    if v is None:
        return None
    if isinstance(v, str):
        return v.strip()
    return str(v)

def load_json(p: Path):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def normalize_messages(raw: Any) -> List[Dict[str, Any]]:
    chats = []
    if isinstance(raw, list):
        chats = raw
    elif isinstance(raw, dict):
        if "chats" in raw and isinstance(raw["chats"], list):
            chats = raw["chats"]
        elif "messages" in raw and isinstance(raw["messages"], list):
            return raw["messages"]
        else:
            for v in raw.values():
                if isinstance(v, list) and v and isinstance(v[0], dict) and ("messages" in v[0] or "content" in v[0] or "text" in v[0]):
                    chats = v
                    break

    all_msgs = []
    for chat in chats:
        msgs = chat.get("messages") if isinstance(chat, dict) else None
        if isinstance(msgs, list):
            all_msgs.extend(msgs)
    return all_msgs

def build_user_datasets(messages: List[Dict[str, Any]], history_size: int = 6):
    per_user_samples = defaultdict(list)

    norm = []
    for m in messages:
        if _is_deleted(m):
            continue
        sender = _extract(m, SENDER_KEYS)
        text   = _msg_text(m)
        if sender is None or not text:
            continue
        norm.append({"sender": str(sender), "text": text})

    for i, m in enumerate(norm):
        target_user = m["sender"]
        start = max(0, i - history_size)
        context = norm[start:i+1]

        messages_fmt = []
        for mm in context:
            role = "assistant" if mm["sender"] == target_user else "user"
            messages_fmt.append({"role": role, "content": mm["text"]})

        if len(messages_fmt) >= 2:
            per_user_samples[target_user].append({"messages": messages_fmt})

    return per_user_samples

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chats", default="data/chats.json")
    ap.add_argument("--out_dir", default="data/users")
    ap.add_argument("--history", type=int, default=6)
    args = ap.parse_args()

    out_dir = Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    raw = load_json(Path(args.chats))
    messages = normalize_messages(raw)
    if not messages:
        raise SystemExit("❌ לא נמצאו הודעות ב-chats.json")

    per_user = build_user_datasets(messages, history_size=args.history)

    for uid, samples in per_user.items():
        p = out_dir / f"user_{uid}.jsonl"
        with p.open("w", encoding="utf-8") as f:
            for s in samples:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        print(f"✅ wrote {p}  ({len(samples)} samples)")

if __name__ == "__main__":
    main()
