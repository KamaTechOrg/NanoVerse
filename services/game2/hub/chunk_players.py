from collections import defaultdict
from typing import Dict, List, Optional
import threading
from ..data.db_players import PlayerDB


class ChunkPlayers:
    """
    Handles all players' positions in memory, synchronized with PlayerDB.
    - Keeps a live map of chunk_id → player positions.
    - Loads chunk data automatically from DB when needed.
    """

    def __init__(self, player_db: PlayerDB):
        self.db = player_db
        # {chunk_id: {player_id: {"row": int, "col": int}}}
        self.chunk_player_map: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(dict)
        self._lock = threading.Lock()
        self._load_all_from_db()


    def _load_all_from_db(self):
        """Load all player positions from DB at startup."""
        print("[ChunkPlayers] Loading all players from DB...")
        cur = self.db.conn.execute("SELECT chunk_id, user_id, row, col FROM players")
        rows = cur.fetchall()
        for chunk_id, user_id, row, col in rows:
            self.chunk_player_map[chunk_id][user_id] = {"row": row, "col": col}
            

    def _load_chunk_from_db(self, chunk_id: str):
        """Load all players of a given chunk into memory (if not yet loaded)."""
        cur = self.db.conn.execute(
            "SELECT user_id, row, col FROM players WHERE chunk_id=?",
            (chunk_id,),
        )
        rows = cur.fetchall()
        for user_id, row, col in rows:
            self.chunk_player_map[chunk_id][user_id] = {"row": row, "col": col}
        if rows:
            print(f"[ChunkPlayers] Loaded {len(rows)} players from chunk {chunk_id}.")


    def add_player(self, chunk_id: str, player_id: str, row: int, col: int):
        """
        Add a player to the chunk.
        Automatically ensures the chunk's other players are loaded from DB.
        """
        with self._lock:
            if chunk_id not in self.chunk_player_map:
                self._load_chunk_from_db(chunk_id)

            self.chunk_player_map[chunk_id][player_id] = {"row": row, "col": col}
            self.db.upsert(player_id, chunk_id, row, col)


    def update_player_position(self, chunk_id: str, player_id: str, row: int, col: int):
        """Update player's coordinates inside a chunk."""
        with self._lock:
            if player_id in self.chunk_player_map.get(chunk_id, {}):
                self.chunk_player_map[chunk_id][player_id] = {"row": row, "col": col} #??can I take it out??
                self.db.upsert(player_id, chunk_id, row, col)
                

    def move_player_to_chunk(self, old_chunk_id: str, new_chunk_id: str,
                             player_id: str, row: int, col: int):
        """
        Move player from one chunk to another.
        Automatically loads new chunk players from DB.
        """
        with self._lock:
            if new_chunk_id not in self.chunk_player_map:
                self._load_chunk_from_db(new_chunk_id)

            if player_id in self.chunk_player_map.get(old_chunk_id, {}):
                del self.chunk_player_map[old_chunk_id][player_id]
                if not self.chunk_player_map[old_chunk_id]:
                    del self.chunk_player_map[old_chunk_id]

            self.chunk_player_map[new_chunk_id][player_id] = {"row": row, "col": col}
            self.db.upsert(player_id, new_chunk_id, row, col)


    def remove_player(self, player_id: str):
        """Remove player completely (disconnect)."""
        with self._lock:
            for chunk_id in list(self.chunk_player_map.keys()):
                if player_id in self.chunk_player_map[chunk_id]:
                    del self.chunk_player_map[chunk_id][player_id]
                    if not self.chunk_player_map[chunk_id]:
                        del self.chunk_player_map[chunk_id]
            self.db.remove_player(player_id)


    def get_player_position(self, player_id: str) -> Optional[Dict[str, int]]:
        """Return the player's current position as {'chunk_id', 'row', 'col'}."""
        for chunk_id, players in self.chunk_player_map.items():
            if player_id in players:
                pos = players[player_id]
                return {"chunk_id": chunk_id, "row": pos["row"], "col": pos["col"]}
        return None

    def get_players_in_chunk(self, chunk_id: str) -> List[Dict[str, int]]:
        """List all players in the given chunk."""
        if chunk_id not in self.chunk_player_map:
            self._load_chunk_from_db(chunk_id)
        return [
            {"id": uid, "row": p["row"], "col": p["col"]}
            for uid, p in self.chunk_player_map.get(chunk_id, {}).items()
        ]

    def is_cell_free(self, chunk_id: str, row: int, col: int) -> bool:
        """Check if the given cell is free (auto-loads chunk from DB if missing)."""
        if chunk_id not in self.chunk_player_map:
            self._load_chunk_from_db(chunk_id)

        players_in_chunk = self.chunk_player_map.get(chunk_id, {})
        for pos in players_in_chunk.values():
            if pos["row"] == row and pos["col"] == col:
                return False
        return True


    def close(self):
        """Close DB connection."""
        self.db.close()
