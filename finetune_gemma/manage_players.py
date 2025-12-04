
from __future__ import annotations
from pathlib import Path

FT_ROOT = Path(__file__).resolve().parent

USERS_ROOT    = FT_ROOT / "data" / "users"
ADAPTERS_ROOT = FT_ROOT / "adapters"

def ensure_player_dirs(player_id: str) -> dict:
  
    user_dir = USERS_ROOT / f"player{player_id}_split"
    user_dir.mkdir(parents=True, exist_ok=True)
    train_p = user_dir / "train.jsonl"
    val_p   = user_dir / "val.jsonl"

    if not train_p.exists():
        train_p.write_text("", encoding="utf-8")
    if not val_p.exists():
        val_p.write_text("", encoding="utf-8")

    adp_dir = ADAPTERS_ROOT / f"player{player_id}" / "latest"
    adp_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = adp_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("", encoding="utf-8")

    info = {
        "player_id": player_id,
        "train_jsonl": str(train_p),
        "val_jsonl": str(val_p),
        "adapter_dir": str(adp_dir),
    }
    print(f"[OK] Prepared dirs for player {player_id}: {info}")
    return info

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python3 manage_players.py <PLAYER_ID>")
        sys.exit(1)
    ensure_player_dirs(sys.argv[1])
