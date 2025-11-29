
from __future__ import annotations
import json, sqlite3, argparse
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, List, Tuple

DB_PATH_DEFAULT  = "/srv/python_envs/shared_env/A/NanoVerse/project/NanoVerse/data/chat.dev.db"
OUT_DIR_DEFAULT  = "/srv/python_envs/shared_env/A/NanoVerse/finetune_gemma/data/users"  # זהה ל-USERS_DIR ב-nightly
HISTORY_DEFAULT  = 6

def fetch_messages_from_db(db_path: str) -> List[Dict[str, Any]]:
    dbp = Path(db_path)
    if not dbp.exists():
        raise SystemExit(f"❌ לא נמצא קובץ DB: {dbp}")

    con = sqlite3.connect(str(dbp))
    cur = con.cursor()
    
    cur.execute("""
        SELECT sender_id, receiver_id, content
        FROM messages
        ORDER BY timestamp ASC, id ASC
    """)
    rows = cur.fetchall()
    con.close()

    messages = []
    for sender, receiver, content in rows:
        if not content or not sender:
            continue
        messages.append({
            "sender_id": str(sender),
            "receiver_id": str(receiver) if receiver is not None else "",
            "content": str(content).strip()
        })

    print(f"📥 נטענו {len(messages)} הודעות מה-DB ({dbp.name})")
    return messages

def build_user_datasets(messages: List[Dict[str, Any]], history_size: int = HISTORY_DEFAULT):
    
    per_user_samples = defaultdict(list)
    N = len(messages)
    for i in range(N):
        target_user = messages[i]["sender_id"]
        start = max(0, i - history_size)
        context = messages[start:i+1]  

        msg_fmt = []
        for mm in context:
            role = "assistant" if mm["sender_id"] == target_user else "user"
            msg_fmt.append({"role": role, "content": mm["content"]})

        if len(msg_fmt) >= 2:
            per_user_samples[target_user].append({"messages": msg_fmt})

    return per_user_samples

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db",       default=DB_PATH_DEFAULT)
    ap.add_argument("--out_dir",  default=OUT_DIR_DEFAULT)
    ap.add_argument("--history",  type=int, default=HISTORY_DEFAULT)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    messages = fetch_messages_from_db(args.db)
    if not messages:
        raise SystemExit("There are not messages in the DB")

    per_user = build_user_datasets(messages, history_size=args.history)

    total_samples = 0
    for uid, samples in per_user.items():
        p = out_dir / f"user_{uid}.jsonl"
        with p.open("w", encoding="utf-8") as f:
            for s in samples:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        total_samples += len(samples)


if __name__ == "__main__":
    main()
