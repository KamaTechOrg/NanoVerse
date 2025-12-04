import torch
from .world import WorldService
from .scrolls import ScrollService
from ..core.settings import DTYPE
from .types import PlayerState

class ColorService:
    """Handles player color changes and updates the board and database accordingly."""

    def __init__(self, world: WorldService, scroll: ScrollService):
        self.world = world
        self.scroll = scroll
    
    
    def color_plus_plus(self, state: PlayerState) -> None:
        board = self.world.ensure_chunk(state.chunk_id)
        r0, c0 = state.pos.row, state.pos.col   

        val = int(board[r0, c0].item()) 

        color_code = val & 0b111111 

        # Add +1
        new_code = (color_code + 1) & 0b111111  

        # Keep flags
        keep_flags = val & 0b11000000  # bits 6 & 7 

        new_val = keep_flags | new_code 

        board[r0, c0] = torch.tensor(new_val, dtype=DTYPE)
        
        self.world._mark_dirty(state.chunk_id)  
