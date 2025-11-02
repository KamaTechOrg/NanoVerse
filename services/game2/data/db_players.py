import sqlite3
from typing import Optional, Tuple, List, Dict
from pathlib import Path
from ..core.settings import PLAYERS_DB_PATH


class PlayerDB:
    """   
    Unified player database:
    - Each player has one record (user_id → chunk_id, row, col)
    - Efficient queries for both per-player and per-chunk lookups
    """

    def __init__(self, db_path: Path = PLAYERS_DB_PATH):
        self.conn = sqlite3.connect(db_path, isolation_level=None)
        self.conn.execute("PRAGMA journal_mode=WAL")

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id TEXT PRIMARY KEY,
            chunk_id TEXT NOT NULL,
            row INTEGER NOT NULL,
            col INTEGER NOT NULL
        )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_chunk ON players (chunk_id)")


    def upsert(self, user_id: str, chunk_id: str, row: int, col: int) -> None:
        """Insert or update player position."""
        self.conn.execute("""
        INSERT INTO players (user_id, chunk_id, row, col)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET chunk_id=excluded.chunk_id,
                      row=excluded.row,
                      col=excluded.col
        """, (user_id, chunk_id, row, col))
   
    def get_position(self, user_id: str) -> Optional[Tuple[str, int, int]]:
        """Return (chunk_id, row, col) for given player_id."""
        row = self.conn.execute(
            "SELECT chunk_id, row, col FROM players WHERE user_id=?",
            (user_id,),
        ).fetchone()
        return row if row else None

    def remove_player(self, user_id: str) -> None:
        """Remove player completely (disconnect)."""
        self.conn.execute("DELETE FROM players WHERE user_id=?", (user_id,))


    def list_players_in_chunk(self, chunk_id: str) -> List[Dict[str, int]]:
        """Return all players currently inside the given chunk."""
        cur = self.conn.execute(
            "SELECT user_id, row, col FROM players WHERE chunk_id=?",
            (chunk_id,),
        )
        
        return cur.fetchall()
    def clear_chunk(self, chunk_id: str) -> None:
        """Remove all players from the given chunk."""
        self.conn.execute("DELETE FROM players WHERE chunk_id=?", (chunk_id,))


    def is_cell_free(self, chunk_id: str, row: int, col: int) -> bool:
        """Check if a cell in a chunk is empty (no player occupies it)."""
        cur = self.conn.execute(
            "SELECT 1 FROM players WHERE chunk_id=? AND row=? AND col=? LIMIT 1",
            (chunk_id, row, col),
        )
        return cur.fetchone() is None

    def close(self) -> None:
        self.conn.close()
