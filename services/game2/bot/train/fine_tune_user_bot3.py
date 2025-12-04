from __future__ import annotations
from pathlib import Path
from typing import List
import torch
from torch.utils.data import Dataset, DataLoader, random_split
import torch.nn as nn, torch.optim as optim

from services.game2.bot_3.model import GRUActionPredictor, ACTIONS, ACTION_TO_IDX, SEQ_LEN
from services.game2.bot_3.train.data_utils_actions import iter_jsonl, filter_by_time, last_k_actions
from services.game2.bot_3.train.safe_io import safe_save_state_dict

WEIGHTS_DIR = Path("services/game2/bot_3/models_weights")
USERS_DIR   = Path("services/game2/bot_3/users")

class SeqDatasetFromEvents(Dataset):
    def __init__(self, events: List[dict], seq_len: int = SEQ_LEN):
        from services.game2.bot_3.model import ACTION_TO_IDX
        acts = []
        for rec in events:
            a = rec.get("action", None)
            if a in ACTION_TO_IDX:
                acts.append(ACTION_TO_IDX[a])
        self.seq_len = seq_len
        self.samples = []
        for i in range(len(acts) - self.seq_len - 1):
            seq = acts[i:i+self.seq_len]
            y   = acts[i+self.seq_len]
            self.samples.append((seq, y))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        import torch as T
        seq, y = self.samples[idx]
        return T.tensor(seq, dtype=T.long), T.tensor(y, dtype=T.long)



def fine_tune_user_bot3(user_id: str, start_ts: float, end_ts: float,
                        epochs=6, batch_size=128, lr=8e-4,
                        min_sequences=300, use_last_k: int | None = None,
                        init_from_previous=True):
    user_file = USERS_DIR / user_id / "actions.jsonl"
    events = list(iter_jsonl(user_file))
    if use_last_k:
        events = last_k_actions(events, use_last_k)
    else:
        events = list(filter_by_time(events, start_ts, end_ts))

    ds = SeqDatasetFromEvents(events)
    if len(ds) < min_sequences:
        return False

    val_size = max(1, int(0.2*len(ds)))
    train_ds, val_ds = random_split(ds, [len(ds)-val_size, val_size])
    dl_tr = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    dl_va = DataLoader(val_ds,   batch_size=batch_size)

    # device = "cuda" if torch.cuda.is_available() else "cpu"
    device = "cpu"

    model  = GRUActionPredictor().to(device)

    out_path     = WEIGHTS_DIR / f"{user_id}.pt"
    default_path = WEIGHTS_DIR / "default.pt"

    if init_from_previous and out_path.exists():
        state = torch.load(out_path, map_location="cpu")
        model.load_state_dict(state)
    elif default_path.exists():
        state = torch.load(default_path, map_location="cpu")
        model.load_state_dict(state)
  
    loss_fn = nn.CrossEntropyLoss()
    opt     = optim.Adam(model.parameters(), lr=lr)

    for ep in range(1, epochs+1):
        model.train(); trL=trN=trC=0
        for seq,y in dl_tr:
            seq,y = seq.to(device), y.to(device)
            opt.zero_grad()
            logits = model(seq)
            loss   = loss_fn(logits, y)
            loss.backward(); opt.step()
            trL += float(loss.item())*y.size(0); trN += y.size(0); trC += (logits.argmax(1)==y).sum().item()
        model.eval(); vaL=vaN=vaC=0
        with torch.no_grad():
            for seq,y in dl_va:
                seq,y = seq.to(device), y.to(device)
                logits = model(seq); loss = loss_fn(logits,y)
                vaL += float(loss.item())*y.size(0); vaN += y.size(0); vaC += (logits.argmax(1)==y).sum().item()
        print(f"[{user_id}] ep{ep} tr_acc={trC/max(1,trN):.3f} va_acc={vaC/max(1,vaN):.3f} tr_loss={trL/max(1,trN):.4f} va_loss={vaL/max(1,vaN):.4f}")

    safe_save_state_dict(model, out_path, build_model_fn=lambda: GRUActionPredictor(), keep_backup=True)
    return True
