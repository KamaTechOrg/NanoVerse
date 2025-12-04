from __future__ import annotations
from pathlib import Path
import os, time, torch

def _dummy_forward_check(state_dict, build_model_fn):
    model = build_model_fn()
    model.load_state_dict(state_dict, strict=True)
    model.eval()
    import torch as T
    from services.game2.bot_3.model import SEQ_LEN
    x = T.zeros((1, SEQ_LEN), dtype=T.long)
    with T.no_grad():
        logits = model(x)
        assert logits.ndim == 2 and logits.size(0) == 1
    return True

def safe_save_state_dict(model, final_path: Path, build_model_fn, keep_backup: bool = True):
    final_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = final_path.with_suffix(final_path.suffix + ".tmp")
    torch.save(model.state_dict(), tmp_path)

    state_check = torch.load(tmp_path, map_location="cpu")
    _dummy_forward_check(state_check, build_model_fn)

    if keep_backup and final_path.exists():
        ts = time.strftime("%Y%m%d-%H%M%S")
        bak = final_path.with_suffix(f".{ts}.bak")
        try:
            old_state = torch.load(final_path, map_location="cpu")
            torch.save(old_state, bak)
        except Exception:
            pass

    os.replace(tmp_path, final_path)
    return True
