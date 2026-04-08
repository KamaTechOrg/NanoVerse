"""
Per-pair SQLite store for chat messages.

Creates one DB file per players pair:
  project/Data/db/chat_<player_a>__<player_b>.sqlite3
(players sorted lexicographically in the filename)

Schema:
- timestamp   TEXT   (ISO-8601 with 'Z')
- sender_id   TEXT
- receiver_id TEXT
- content     TEXT
- reaction    TEXT   ('like' | 'dislike' | 'none')
"""

from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

# ---------- Resolve project/Data/db directory ----------
# chat_store.py -> sqlite (0) -> storage (1) -> server (2) -> project root (3)
ROOT_DIR = Path(__file__).resolve().parents[3]
# Data is a sibling of server/
DATA_DIR_CANDIDATES = [ROOT_DIR / "Data", ROOT_DIR / "data"]
for _cand in DATA_DIR_CANDIDATES:
    if _cand.exists():
        DATA_DIR = _cand
        break
else:
    DATA_DIR = ROOT_DIR / "Data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_DIR = DATA_DIR / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)

# ---------- Helpers ----------
def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="microseconds") + "Z"

def _pair_key(a: str, b: str) -> Tuple[str, str]:
    return (a, b) if a <= b else (b, a)

def pair_db_path(a: str, b: str) -> Path:
    p1, p2 = _pair_key(a, b)
    fname = f"chat_{p1}__{p2}.sqlite3"
    return DB_DIR / fname

# cache connections per DB file
_CONN_CACHE: Dict[Path, sqlite3.Connection] = {}

def _connect(a: str, b: str) -> sqlite3.Connection:
    db_path = pair_db_path(a, b)
    first_time = not db_path.exists()
    conn = _CONN_CACHE.get(db_path)
    if conn is None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        _CONN_CACHE[db_path] = conn
    if first_time:
        _init_schema(conn)
    return conn

def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS messages (
          id           INTEGER PRIMARY KEY AUTOINCREMENT,
          timestamp    TEXT    NOT NULL,
          sender_id    TEXT    NOT NULL,
          receiver_id  TEXT    NOT NULL,
          content      TEXT    NOT NULL,
          reaction     TEXT    NOT NULL DEFAULT 'none'
        );
        CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(timestamp);
        """
    )
    conn.commit()

# ---------- Public API ----------
def insert_message(
    sender_id: str,
    receiver_id: str,
    content: str,
    *,
    timestamp: Optional[str] = None,
    reaction: str = "none",
) -> Dict[str, Any]:
    if reaction not in ("like", "dislike", "none"):
        raise ValueError("reaction must be 'like' | 'dislike' | 'none'")
    if not content:
        raise ValueError("content must be a non-empty string")

    ts = timestamp or _now_iso()
    conn = _connect(sender_id, receiver_id)
    cur = conn.execute(
        "INSERT INTO messages (timestamp, sender_id, receiver_id, content, reaction) "
        "VALUES (?, ?, ?, ?, ?)",
        (ts, sender_id, receiver_id, content, reaction),
    )
    conn.commit()
    msg_id = int(cur.lastrowid)
    return {
        "id": msg_id,
        "timestamp": ts,
        "from": sender_id,
        "to": receiver_id,
        "message": content,
        "reaction": reaction,
    }

def update_reaction(message_id: int, for_a: str, for_b: str, reaction: str) -> Dict[str, Any]:
    if reaction not in ("like", "dislike", "none"):
        raise ValueError("reaction must be 'like' | 'dislike' | 'none'")
    conn = _connect(for_a, for_b)
    cur = conn.execute("UPDATE messages SET reaction=? WHERE id=?", (reaction, message_id))
    conn.commit()
    if cur.rowcount == 0:
        raise KeyError(f"message id {message_id} not found")
    return {"id": message_id, "reaction": reaction}

def fetch_message_by_id(message_id: int, a: str, b: str) -> Optional[Dict[str, Any]]:
    conn = _connect(a, b)
    row = conn.execute(
        "SELECT id, timestamp, sender_id, receiver_id, content, reaction "
        "FROM messages WHERE id=?",
        (message_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "timestamp": row["timestamp"],
        "from": row["sender_id"],
        "to": row["receiver_id"],
        "message": row["content"],
        "reaction": row["reaction"],
    }

def fetch_history(
    a: str,
    b: str,
    *,
    limit: int = 200,
    before_ts: Optional[str] = None,
    since_ts: Optional[str] = None,
    ascending: bool = True,
) -> List[Dict[str, Any]]:
    conn = _connect(a, b)
    where = []
    params: list[Any] = []

    if since_ts:
        where.append("timestamp >= ?")
        params.append(since_ts)
    if before_ts:
        where.append("timestamp < ?")
        params.append(before_ts)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    order_sql = "ASC" if ascending else "DESC"

    sql = (
        "SELECT id, timestamp, sender_id, receiver_id, content, reaction "
        "FROM messages "
        f"{where_sql} "
        f"ORDER BY timestamp {order_sql} "
        "LIMIT ?"
    )
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()

    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append({
            "id": r["id"],
            "timestamp": r["timestamp"],
            "from": r["sender_id"],
            "to": r["receiver_id"],
            "message": r["content"],
            "reaction": r["reaction"],
        })
    return out

def delete_db_for_pair(a: str, b: str) -> None:
    db_path = pair_db_path(a, b)
    conn = _CONN_CACHE.pop(db_path, None)
    if conn is not None:
        conn.close()
    if db_path.exists():
        db_path.unlink()

__all__ = [
    "pair_db_path",
    "insert_message",
    "update_reaction",
    "fetch_message_by_id",
    "fetch_history",
    "delete_db_for_pair",
]
