# services/game2/data/db_logs_with_danger.py
import json
from pathlib import Path
from datetime import datetime
import torch
from ..core.settings import DATA_DIR, BIT_IS_DANGER_IDX, BIT_FRUIT_IDX, W, H
from ..core.bits import get_bit
from ..hub.chunk_players import ChunkPlayers

class DangerLogger:
    def __init__(self, chunk_players: ChunkPlayers):
        self.chunk_players = chunk_players
        self.path = DATA_DIR / "db_logs_with_danger.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def _ts(self) -> str:
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")[:-3]

    def _in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < H and 0 <= c < W

    def _neighbors(self, r: int, c: int):
        return {
            "up":    (r - 1, c),
            "down":  (r + 1, c),
            "left":  (r, c - 1),
            "right": (r, c + 1),
        }

    def _calc_state(self, board: torch.Tensor, chunk_id: str, r: int, c: int):
        """בניית state שמתאר מה יש בארבעה כיוונים סביב השחקן"""
        state = {}
        players = self.chunk_players.get_players_in_chunk(chunk_id)
        for dir_name, (nr, nc) in self._neighbors(r, c).items():
            # נתחיל מהערכים ברירת מחדל
            edge = int(not self._in_bounds(nr, nc))
            danger = 0
            apple = 0
            player = 0

            if not edge:
                cell_val = int(board[nr, nc].item())
                if get_bit(cell_val, BIT_IS_DANGER_IDX):
                    danger = 1
                if get_bit(cell_val, BIT_FRUIT_IDX):
                    apple = 1

                # לבדוק אם יש שם שחקן אחר
                for p in players:
                    if p["row"] == nr and p["col"] == nc:
                        player = 1
                        break

            state[dir_name] = {
                "edge": edge,
                "danger": danger,
                "apple": apple,
                "player": player,
            }
        return state

    def append(self, player_id: str, chunk_id: str, board: torch.Tensor, row: int, col: int, action: str):
        """שומר שורה חדשה לקובץ"""
        rec = {
            "ts": self._ts(),
            "player_id": player_id,
            "chunk_id": chunk_id,
            "row": row,
            "col": col,
            "state": self._calc_state(board, chunk_id, row, col),
            "action": action,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
