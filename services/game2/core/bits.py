"""Low-level bit manipulation utilities for encoding game board cells (colors, flags, etc.)."""
import hashlib
import torch
from typing import Tuple
from .settings import (
    DTYPE, COLOR_BITS,

     BIT_R0_IDX, BIT_R1_IDX, BIT_G0_IDX, BIT_G1_IDX, BIT_B0_IDX, BIT_B1_IDX, BIT_HAS_LINK_IDX
)
    
def set_bit(v: torch.Tensor, bit: int, one: bool) -> torch.Tensor:
    """Set/Clear single bit on an 8-bit tensor value."""
    mask = torch.tensor(1 << bit, dtype=DTYPE)
    return (v | mask) if one else (v & (~mask & torch.tensor(0xFF, dtype=DTYPE)))
    
def get_bit(v: torch.Tensor, bit: int) -> torch.Tensor:
    return (v >> bit) & 1

def get2(v: torch.Tensor, b0: int, b1: int) -> torch.Tensor:
    return ((v >> b1) & 1) * 2 + ((v >> b0) & 1)
      
def set2(v: torch.Tensor, b0: int, b1: int, x: int) -> torch.Tensor:
    """Set 2-bit value (0–3) into given bits."""
    x &= 3
    v = v & (~(torch.tensor((1 << b0) | (1 << b1), dtype=DTYPE)) & torch.tensor(0xFF, dtype=DTYPE))
    if x & 1:
        v = v | torch.tensor(1 << b0, dtype=DTYPE)
    if x & 2:
        v = v | torch.tensor(1 << b1, dtype=DTYPE)
    return v

def make_color(r2: int, g2: int, b2: int) -> torch.Tensor:
    """Compose color (2 bits per channel) into a single 8-bit value."""
    v = torch.tensor(0, dtype=DTYPE)
    v = set2(v, BIT_R0_IDX, BIT_R1_IDX, r2)
    v = set2(v, BIT_G0_IDX, BIT_G1_IDX, g2)
    v = set2(v, BIT_B0_IDX, BIT_B1_IDX , b2)
    print("user_id color--",v )

    return v

def get_player_color_by_user_id(uid: str | int) -> torch.Tensor:
    uid = int(uid)

    base = uid & 0b111111   # take lowest 6 bits

    
    b2 = base & 0b11
    g2 = (base >> 2) & 0b11
    r2 = (base >> 4) & 0b11

    # Add +1 ("add 32" concept)
    r2 = (r2 + 1) & 3
    g2 = (g2 + 1) & 3
    b2 = (b2 + 1) & 3
    return make_color(r2, g2, b2)
