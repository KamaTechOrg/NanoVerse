from __future__ import annotations
import random
import torch
from ..core.settings import W, H
from .types import Coord, PlayerState, Direction

class BoardUtils:
    """Provides helper methods for board geometry: checking bounds, emptiness, edges, and random spawn cells."""
   
    @staticmethod
    def in_bounds(r: int, c: int) -> bool:
        return 0 <= r < H and 0 <= c < W
     
    @staticmethod
    def edge_direction(nr: int, nc: int) -> Direction:
        if nr < 0:
            return "up"
        if nr >= H:
            return "down"
        if nc < 0:
            return "left"
        return "right"

    @staticmethod
    def edge_target_for_direction(state: PlayerState, direction: Direction) -> Coord:
        if direction == "up":
            return Coord(H - 1, state.pos.col)
        if direction == "down":
            return Coord(0, state.pos.col)
        if direction == "left":
            return Coord(state.pos.row, W - 1)
        return Coord(state.pos.row, 0)