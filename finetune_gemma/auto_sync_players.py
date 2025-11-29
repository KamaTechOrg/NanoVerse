from __future__ import annotations
import os, sqlite3, json, random
from pathlib import Path
from typing import List, Dict, Tuple

NV_ROOT = Path("/srv/python_envs/shared_env/A/NanoVerse")
PROJ    = NV_ROOT / "project" / "NanoVerse"
FT      = NV_ROOT / "finetune_gemma"

PLAYERS_DB = Path(os.getenv("PLAYERS_DB", str(PROJ / "data" / "players.db")))
CHAT_DB    = Path(os.getenv("CHAT_DB",    str(PROJ / "data" / "chat.db")))
USERS_DIR  = Path(os.getenv("USERS_DIR",  str(FT / "data" / "users")))
ADAPT_DIR  = Path(os.getenv("ADAPT_DIR",  str(FT / "adapters")))

ALLOW_CREATE_DIRS = os.getenv("ALLOW_CREATE_DIRS", "0") == "1"

random.seed(17)


def q(db: Path, sql: str, params: Tuple = ()) -> List[Tuple]:
    con = sqlite3.connect(str(db))
    cur = con.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    con.close()
    return rows


def list_players() -> List[Tuple[str, str]]:
    
    try:
        rows = q(PLAYERS_DB, "SELECT user_id, adapter_path FROM players ORDER BY user_id")
        return [(str(u), str(p) if p is not None else "") for (u, p) in rows]
    except Exception as e:
        print(f"[SYNC] ERR reading players: {e}")
        return []


def fetch_msgs_between(a: str, b: str) -> List[Tuple[str, str, str, str]]:
   
    sql = """
    SELECT timestamp, sender_id, receiver_id, content
    FROM messages
    WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
    ORDER BY timestamp ASC
    """
    return q(CHAT_DB, sql, (a, b, b, a))


def _looks_like_human_chat(text: str) -> bool:
    
    if not text:
        return False
    text = str(text).strip()
    if not text:
        return False

    lower = text.lower()

    bad_markers = [
        "this is an assistant script for a chatbot",
        "you are a user.",
        "you are an assistant",
        "here are some ways you can use this script",
        "the function should",
        "```",
        "if (is_array(input))",
    ]

    for m in bad_markers:
        if m in lower:
            return False

    if "[stub]" in text:
        return False

    if len(text) > 500:
        return False

    return True


def make_pairs_for_pid(pid: str, limit_per_peer: int = 500) -> List[Dict]:
    
    rows = q(
        CHAT_DB,
        "SELECT DISTINCT CASE WHEN sender_id=? THEN receiver_id ELSE sender_id END AS peer "
        "FROM messages WHERE sender_id=? OR receiver_id=?",
        (pid, pid, pid),
    )
    peers = [r[0] for r in rows]

    items: List[Dict] = []
    for peer in peers:
        dialog = fetch_msgs_between(pid, peer)
        for i in range(len(dialog) - 1):
            t0, s0, r0, c0 = dialog[i]
            t1, s1, r1, c1 = dialog[i + 1]
            if not c0 or not c1:
                continue

            if s0 == peer and r0 == pid and s1 == pid and r1 == peer:
                if not (_looks_like_human_chat(c0) and _looks_like_human_chat(c1)):
                    continue

                items.append({
                    "messages": [
                        {"role": "user", "content": str(c0)},
                        {"role": "assistant", "content": str(c1)},
                    ]
                })

        if limit_per_peer and len(items) > limit_per_peer:
            items = items[:limit_per_peer]

    return items


def write_jsonl(path: Path, rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def sync_player(pid: str) -> Tuple[int, int]:
    
    split_dir = USERS_DIR / f"player{pid}_split"
    train_p = split_dir / "train.jsonl"
    val_p   = split_dir / "val.jsonl"

    if not split_dir.exists():
        if ALLOW_CREATE_DIRS:
            split_dir.mkdir(parents=True, exist_ok=True)
            print(f"[SYNC] WARN created missing dir for {pid}: {split_dir}")
        else:
            print(f"[SYNC] SKIP {pid}: dir missing -> {split_dir}")
            return (0, 0)

    items = make_pairs_for_pid(pid)
    if not items:
        # לייצר קבצים ריקים אם צריך
        write_jsonl(train_p, [])
        write_jsonl(val_p,   [])
        return (0, 0)

    random.shuffle(items)
    k = max(1, int(len(items) * 0.1)) if len(items) >= 10 else 1
    val = items[:k]
    train = items[k:]

    write_jsonl(train_p, train)
    write_jsonl(val_p,   val)
    return (len(train), len(val))


def main():
    print(f"[SYNC] players DB = {PLAYERS_DB}")
    print(f"[SYNC] chat DB    = {CHAT_DB}")
    print(f"[SYNC] out users  = {USERS_DIR}")
    print(f"[SYNC] adapters   = {ADAPT_DIR}")
    if ALLOW_CREATE_DIRS:
        print("[SYNC] mode: CREATE-MISSING-DIRS = ON")
    else:
        print("[SYNC] mode: create-missing-dirs = OFF (sync only)")

    total_tr = total_vl = 0
    for pid, adapter in list_players():
        ntr, nvl = sync_player(pid)
        total_tr += ntr
        total_vl += nvl
        print(f"[SYNC] player {pid}: train={ntr} val={nvl} -> {USERS_DIR / ('player'+pid+'_split')}")

    print(f"[SYNC] DONE. total train={total_tr}, val={total_vl}")


if __name__ == "__main__":
    main()
