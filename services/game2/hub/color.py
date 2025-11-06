import random
import torch
from .world import WorldService
from .scrolls import ScrollService
from ..core.settings import DTYPE
from ..core.bits import make_color, get_bit, set_bit

from ..core.settings import BIT_HAS_LINK_IDX, DTYPE, BIT_HAS_LINK_IDX
from ..core.bits import get_player_color_by_user_id, get_player_color_by_user_id, make_color, get_bit,set_bit
from .types import PlayerState
from ..data.db_history import ActionToken

class ColorService:
    """Handles player color changes and updates the board and database accordingly."""

    def __init__(self, world: WorldService, scroll: ScrollService):
        self.world = world
        self.scroll = scroll
    
    
    def color_plus_plus(self, state: PlayerState) -> None:##??change that he will store also the has_bit
        """
        Increments the color code (0–63) stored directly (not shifted).
        Example: 0 -> 1 -> 2 -> ... -> 63 -> 0.
        The board stores this value directly.
        """
        
        def _has_link(v: int) -> bool:
            return get_bit(v, BIT_HAS_LINK_IDX)

        def _set_link(v: int, on: bool = True) -> int:##check how can I add it??
            return int(set_bit(v, BIT_HAS_LINK_IDX, on))

        board = self.world.ensure_chunk(state.chunk_id)
        r0, c0 = state.pos.row, state.pos.col

        val = int(board[r0, c0].item())
        color_code = val & 0b111111  # use only lower 6 bits

        new_color_code = (color_code + 1) % 64
        new_base = (val & ~0b111111) | new_color_code  # replace just bottom 6 bits

        board[r0, c0] = torch.tensor(new_base, dtype=DTYPE)
        state.underlying_cell = torch.tensor(new_base, dtype=DTYPE)

        self.world._mark_dirty(state.chunk_id)
        print(f"[Color++] ({r0},{c0}) code={color_code} → {new_color_code}, stored={new_base}")
