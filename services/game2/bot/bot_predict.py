# services/game2/bot/bot_predict.py
import torch
from pathlib import Path
from services.game2.models.bot_gru import GRUPolicy, SEQ_LEN, PAD_IDX, NUM_ACTIONS

# mapping between game tokens (1..5) and model indices (0..4)
GAME_TO_IDX = {1:0, 2:1, 3:2, 4:3, 5:4}
IDX_TO_GAME = {v:k for k,v in GAME_TO_IDX.items()}

_model_cache = {}
def _load_model(user_id: str) -> GRUPolicy:
    if user_id in _model_cache:
        return _model_cache[user_id]

    # --- paths ---
    user_path = Path("models/users") / f"{user_id}.pt"
    default_path = Path("models/users") / "default.pt"

    model = GRUPolicy()

    if user_path.exists():
        # load user-specific weights
        state = torch.load(user_path, map_location="cpu")
        model.load_state_dict(state)
        print(f"[bot_predict] Loaded model for user {user_id}")

    elif default_path.exists():
        # fallback to default model
        print(f"[bot_predict] WARNING: no model for {user_id}, loading default.pt")
        state = torch.load(default_path, map_location="cpu")
        model.load_state_dict(state)

    else:
        # fallback to random weights
        print(f"[bot_predict] ERROR: no model for {user_id} AND no default.pt — using random weights!")

    model.eval()
    _model_cache[user_id] = model
    return model

def _pad_left(seq, target_len, pad_value):
    seq = list(seq)
    if len(seq) >= target_len:
        return seq[-target_len:]
    return [pad_value] * (target_len - len(seq)) + seq

def predict_next(user_id: str, last_actions, last_rows, last_cols, H=64, W=64):
    """
    last_actions: list[int] (game tokens 1..5, arbitrary length)
    last_rows:    list[int]
    last_cols:    list[int]
    """
    # Map actions to model indices; PAD with PAD_IDX
    last_actions_idx = [GAME_TO_IDX.get(a, 0) for a in last_actions]
    a = torch.tensor([_pad_left(last_actions_idx, SEQ_LEN, PAD_IDX)], dtype=torch.long)
    r = torch.tensor([_pad_left(last_rows,    SEQ_LEN, last_rows[-1] if last_rows else 0)], dtype=torch.float32)
    c = torch.tensor([_pad_left(last_cols,    SEQ_LEN, last_cols[-1] if last_cols else 0)], dtype=torch.float32)

    model = _load_model(user_id)
    with torch.no_grad():
        logits = model(a, r, c, H=H, W=W)     # (1, NUM_ACTIONS)
        pred_idx = int(torch.argmax(logits, dim=1).item())
    return IDX_TO_GAME[pred_idx]              # return game token (1..5)
