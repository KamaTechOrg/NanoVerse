
from pathlib import Path
import os

# Root for all adapters
ADAPTERS_ROOT = Path(os.environ.get(
    "GEMMA_ADAPTERS_ROOT",
    "/srv/python_envs/shared_env/A/NanoVerse/finetune_gemma/adapters"
))

# generic fallback adapter for players without their own adapter
FALLBACK_PLAYER = "player_bigtest"


def adapter_dir_for(user_id: str) -> Path:
    
    uid = str(user_id)

    if uid.startswith("player"):
        base = ADAPTERS_ROOT / uid
    else:
        base = ADAPTERS_ROOT / f"player{uid}"

    latest = base / "latest"

    if latest.exists() and (latest / "adapter_config.json").exists():
        return latest

    fallback = ADAPTERS_ROOT / FALLBACK_PLAYER / "latest"
    return fallback
