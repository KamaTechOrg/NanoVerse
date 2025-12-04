import sqlite3
from pathlib import Path
from ..core.settings import PLAYERS_NAME
class PlayerNameDB:
    def __init__(self):
        self.conn = sqlite3.connect(PLAYERS_NAME)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS players_name (
                id TEXT PRIMARY KEY,
                name TEXT
            )
        """)
        self.conn.commit()

    def set(self, player_id: str, name: str):
        if not name:
            return
        self.conn.execute(
            "INSERT OR REPLACE INTO players_name (id, name) VALUES (?, ?)",
            (player_id, name)
        )
        self.conn.commit()

    def get(self, player_id: str) -> str:
        cur = self.conn.execute(
            "SELECT name FROM players_name WHERE id = ?",
            (player_id,)
        )
        row = cur.fetchone()
        return row[0] if row else ""
