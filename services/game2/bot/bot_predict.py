from __future__ import annotations
from pathlib import Path
import torch, time

from services.game2.bot_3.model import (
    GRUActionPredictor,
    ACTIONS,
    ACTION_TO_IDX,
    SEQ_LEN,
)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

WEIGHTS_DIR  = Path("services/game2/bot_3/models_weights")
DEFAULT_PATH = WEIGHTS_DIR / "default.pt"

_model_cache: dict[str, tuple[torch.nn.Module, float]] = {}

def _safe_mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except Exception:
        return -1.0

def _try_load_state_dict(path: Path):
    try:
        return torch.load(path, map_location="cpu")
    except Exception as e:
        print(f"[bot_predict] failed to load {path}: {e}")
        return None

def _load_model_for_user(user_id: str) -> torch.nn.Module:
    user_path = WEIGHTS_DIR / f"{user_id}.pt"
    disk_path = user_path if user_path.exists() else DEFAULT_PATH
    if not disk_path.exists():
        print(f"[bot_predict] WARNING: no weights found for {user_id}, building fresh model")
        m = GRUActionPredictor().to(DEVICE).eval()
        _model_cache[user_id] = (m, -1.0)
        return m

    mtime = _safe_mtime(disk_path)
    cached = _model_cache.get(user_id)
    if cached and abs(cached[1] - mtime) < 1e-6:
        return cached[0]  

    state = _try_load_state_dict(disk_path)
    model = GRUActionPredictor()
    if state is not None:
        try:
            model.load_state_dict(state, strict=True)
        except Exception as e:
            print(f"[bot_predict] incompatible state_dict for {disk_path}: {e}")
    model.to(DEVICE).eval()
    _model_cache[user_id] = (model, mtime)
    print(f"[bot_predict] loaded weights from {disk_path}")
    return model

def predict_next(user_id: str, last_actions: list[str]) -> str:
    assert len(last_actions) == SEQ_LEN, f"expected {SEQ_LEN}, got {len(last_actions)}"
    try:
        idxs = [ACTION_TO_IDX[a] for a in last_actions]
    except KeyError as e:
        raise ValueError(f"unknown action in last_actions: {e}")

    x = torch.tensor(idxs, dtype=torch.long, device=DEVICE).unsqueeze(0)  # (1, SEQ_LEN)
    model = _load_model_for_user(user_id)

    with torch.no_grad():
        logits = model(x)
        pred_idx = int(logits.argmax(dim=1).item())
    return ACTIONS[pred_idx]
