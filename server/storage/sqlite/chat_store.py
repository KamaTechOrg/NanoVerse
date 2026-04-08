# server/storage/sqlite/chat_store.py
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from datetime import datetime

# שורש הפרויקט: .../server/storage/sqlite -> ../.. (server) -> .. (root)
ROOT_DIR = Path(__file__).resolve().parents[3]
DB_DIR = ROOT_DIR / "Data" / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)

def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

def _pair_key(a: str, b: str) -> Tuple[str, str]:
    return (a, b) if a <= b else (b, a)

def pair_db_path(a: str, b: str) -> Path:
    p1, p2 = _pair_key(a, b)
    return DB_DIR / f"chat_{p1}__{p2}.sqlite3"

def _connect(a: str, b: str) -> sqlite3.Connection:
    db_path = pair_db_path(a, b)
    first_time = not db_path.exists()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    if first_time:
        _init_schema(conn)
    return conn

def _init_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            sender_id TEXT NOT NULL,
            reciver_id TEXT NOT NULL,
            contant TEXT NOT NULL,
            reaction TEXT NOT NULL DEFAULT 'none'
                CHECK(reaction IN ('like','dislike','none'))
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(timestamp);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(reciver_id);")
    conn.commit()

def add_message(sender_id: str, reciver_id: str, contant: str, timestamp: Optional[str] = None) -> int:
    ts = timestamp or _now_iso()
    conn = _connect(sender_id, reciver_id)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (timestamp, sender_id, reciver_id, contant, reaction) VALUES (?, ?, ?, ?, 'none')",
        (ts, sender_id, reciver_id, contant),
    )
    conn.commit()
    return int(cur.lastrowid)

def fetch_history(a: str, b: str, limit: int = 128) -> List[Dict]:
    conn = _connect(a, b)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, timestamp, sender_id, reciver_id, contant, reaction
        FROM messages
        ORDER BY datetime(timestamp) ASC, id ASC
        LIMIT ?
        """,
        (limit,),
    )
    return [dict(r) for r in cur.fetchall()]

def set_reaction_by_pair(a: str, b: str, msg_id: int, new_reaction: Optional[str]) -> bool:
    rx = "none" if not new_reaction or new_reaction == "none" else new_reaction
    if rx not in ("like", "dislike", "none"):
        raise ValueError("reaction must be like/dislike/none")
    conn = _connect(a, b)
    cur = conn.cursor()
    cur.execute("UPDATE messages SET reaction = ? WHERE id = ?", (rx, msg_id))
    conn.commit()
    return cur.rowcount > 0
