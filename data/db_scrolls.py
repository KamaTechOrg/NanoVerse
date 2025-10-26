
import json, os
from json import JSONDecodeError
from pathlib import Path
from core.settings import SCROLLS_JSON_PATH
from hub.scroll_message import ScrollMessage


class ScrollDB:
    """Handles saving and loading of 'scroll' messages (hidden treasures) placed on the board."""
    def __init__(self, path: Path = SCROLLS_JSON_PATH):
        self.path = path
        
    def _safe_load(self) -> dict:
        """Safely load existing scrolls JSON"""
        if not self.path.exists():
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (JSONDecodeError, ValueError):
            return {}

    def save_scroll(self, scroll: ScrollMessage) -> None:
        """Atomically save or replace a message at a specific (chunk,row,col)."""
        scrolls = self._safe_load()
        key = f"{scroll.chunk_id}_{scroll.position[0]}_{scroll.position[1]}"
        scrolls[key] = scroll.to_dict()

        tmp = self.path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(scrolls, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)

    def load_scroll(self, chunk_id: str, row: int, col: int) -> dict | None:
        """Load a scroll message at the given (chunk, row, col) if it exists."""
        scrolls = self._safe_load()
        return scrolls.get(f"{chunk_id}_{row}_{col}")
