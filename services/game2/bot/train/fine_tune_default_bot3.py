from __future__ import annotations
from pathlib import Path
from typing import List
import random, torch
from torch.utils.data import Dataset, DataLoader, random_split, ConcatDataset
import torch.nn as nn, torch.optim as optim

from services.game2.bot_3.model import GRUActionPredictor, ACTION_TO_IDX, SEQ_LEN
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



def _sample_user_sequences(user_dir: Path, start_ts: float, end_ts: float,
                           per_user_limit: int = 400, use_last_k: int | None = None) -> List[dict]:
    ev = list(iter_jsonl(user_dir/"actions.jsonl"))
    ev = last_k_actions(ev, use_last_k) if use_last_k else list(filter_by_time(ev, start_ts, end_ts))
    if len(ev) > per_user_limit:
        ev = random.sample(ev, per_user_limit)
    return ev

def fine_tune_default_bot3(start_ts: float, end_ts: float,
                           per_user_limit: int = 400, use_last_k: int | None = None,
                           epochs=6, batch_size=128, lr=8e-4, min_sequences=1000,
                           init_from_previous=True):
    pooled: List[dict] = []
    for udir in USERS_DIR.iterdir():
        if not udir.is_dir(): continue
        pooled.extend(_sample_user_sequences(udir, start_ts, end_ts, per_user_limit, use_last_k))

    ds = SeqDatasetFromEvents(pooled)
    if len(ds) < min_sequences:
        print(f"[default] skipped — only {len(ds)} seqs (<{min_sequences})")
        return False

    val_size = max(1, int(0.2*len(ds)))
    train_ds, val_ds = random_split(ds, [len(ds)-val_size, val_size])
    dl_tr = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    dl_va = DataLoader(val_ds,   batch_size=batch_size)

    # device = "cuda" if torch.cuda.is_available() else "cpu"
    device = "cpu"
    model  = GRUActionPredictor().to(device)
    out_path = WEIGHTS_DIR/"default.pt"

    if init_from_previous and out_path.exists():
        state = torch.load(out_path, map_location="cpu")
        model.load_state_dict(state)
        print("[default] init from previous weights")

    loss_fn = nn.CrossEntropyLoss()
    opt     = optim.Adam(model.parameters(), lr=lr)

    for ep in range(1, epochs+1):
        model.train(); trL=trN=trC=0
        for seq,y in dl_tr:
            seq,y = seq.to(device), y.to(device)
            opt.zero_grad()
            logits = model(seq)
            loss   = loss_fn(logits,y)
            loss.backward(); opt.step()
            trL += float(loss.item())*y.size(0); trN += y.size(0); trC += (logits.argmax(1)==y).sum().item()
        model.eval(); vaL=vaN=vaC=0
        with torch.no_grad():
            for seq,y in dl_va:
                seq,y = seq.to(device), y.to(device)
                logits = model(seq); loss = loss_fn(logits,y)
                vaL += float(loss.item())*y.size(0); vaN += y.size(0); vaC += (logits.argmax(1)==y).sum().item()
        print(f"[default] ep{ep} tr_acc={trC/max(1,trN):.3f} va_acc={vaC/max(1,vaN):.3f} tr_loss={trL/max(1,trN):.4f} va_loss={vaL/max(1,vaN):.4f}")

    safe_save_state_dict(model, out_path, build_model_fn=lambda: GRUActionPredictor(), keep_backup=True)
    print(f"[default] ✅ saved -> {out_path}")
    return True
