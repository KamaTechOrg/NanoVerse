from __future__ import annotations
from pathlib import Path
import os, time
import torch

def _dummy_forward_check(state_dict, build_model_fn, H=64, W=64):
    model = build_model_fn()
    model.load_state_dict(state_dict, strict=True)
    model.eval()
    with torch.no_grad():
        from services.game2.models.bot_gru import SEQ_LEN, PAD_IDX
        import torch as T
        a = T.full((1, SEQ_LEN), PAD_IDX, dtype=T.long)
        r = T.zeros((1, SEQ_LEN), dtype=T.float32)
        c = T.zeros((1, SEQ_LEN), dtype=T.float32)
        logits = model(a, r, c, H=H, W=W)
        assert logits.ndim == 2 and logits.size(0) == 1
    return True

def safe_save_state_dict(model, final_path: Path, build_model_fn, H=64, W=64, keep_backup=True):
    final_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = final_path.with_suffix(final_path.suffix + ".tmp")
    state = model.state_dict()
    torch.save(state, tmp_path)
    # validate tmp
    state_check = torch.load(tmp_path, map_location="cpu")
    _dummy_forward_check(state_check, build_model_fn, H=H, W=W)
    # backup old
    if keep_backup and final_path.exists():
        ts = time.strftime("%Y%m%d-%H%M%S")
        bak_path = final_path.with_suffix(f".{ts}.bak")
        try:
            old_state = torch.load(final_path, map_location="cpu")
            torch.save(old_state, bak_path)
        except Exception:
            pass
    os.replace(tmp_path, final_path)
    return True
