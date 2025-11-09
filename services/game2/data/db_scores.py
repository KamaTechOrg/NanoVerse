# from __future__ import annotations
# import sqlite3
# from pathlib import Path
# from typing import Optional
# from ..core.settings import SCORES_DB_PATH

# class ScoresDB:
#     def __init__(self, path: str | Path = SCORES_DB_PATH):
#         self.path = Path(path)
#         self.path.parent.mkdir(parents=True, exist_ok=True)
#         self.conn = sqlite3.connect(self.path)
#         self._init_schema()

#     def _init_schema(self) -> None:
#         self.conn.execute("""
#         CREATE TABLE IF NOT EXISTS scores (
#             user_id TEXT PRIMARY KEY,
#             score   INTEGER NOT NULL DEFAULT 0
#         )
#         """)
#         self.conn.commit()

#     def add_score(self, user_id: str, delta: int) -> int:
#         cur = self.conn.cursor()
#         cur.execute("INSERT INTO scores(user_id, score) VALUES(?, 0) ON CONFLICT(user_id) DO NOTHING", (user_id,))
#         cur.execute("UPDATE scores SET score = score + ? WHERE user_id = ?", (delta, user_id))
#         self.conn.commit()
#         cur = self.conn.execute("SELECT score FROM scores WHERE user_id=?", (user_id,))
#         row = cur.fetchone()
#         return int(row[0]) if row else 0

#     def get_score(self, user_id: str) -> int:
#         cur = self.conn.execute("SELECT score FROM scores WHERE user_id=?", (user_id,))
#         row = cur.fetchone()
#         return int(row[0]) if row else 0

#     def close(self) -> None:
#         self.conn.close()

# services/game2/data/db_scores.py
import sqlite3
from pathlib import Path

try:
    from ..core.settings import DATA_DIR
except Exception:
    DATA_DIR = Path("data")

class ScoresDB:
    def __init__(self, db_path: str | None = None):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.path = str(DATA_DIR / "scores.db") if db_path is None else db_path
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.commit()

    def ensure_schema(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                user_id TEXT PRIMARY KEY,
                score   INTEGER NOT NULL DEFAULT 0
            )
        """)
        self.conn.commit()

    def get_score(self, user_id: str) -> int:
        cur = self.conn.execute("SELECT score FROM scores WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return int(row[0]) if row else 0

    def add_score(self, user_id: str, delta: int) -> int:
        self.conn.execute("INSERT OR IGNORE INTO scores(user_id, score) VALUES(?, 0)", (user_id,))
        self.conn.execute("UPDATE scores SET score = score + ? WHERE user_id = ?", (delta, user_id))
        self.conn.commit()
        return self.get_score(user_id)

    def top_n(self, n: int = 10) -> list[tuple[str, int]]:
        cur = self.conn.execute(
            "SELECT user_id, score FROM scores ORDER BY score DESC, user_id ASC LIMIT ?",
            (max(1, n),),
        )
        return [(r[0], int(r[1])) for r in cur.fetchall()]


