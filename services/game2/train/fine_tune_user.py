from __future__ import annotations
from pathlib import Path
from typing import List
import torch, random
from torch.utils.data import Dataset, DataLoader, random_split, ConcatDataset
import torch.nn as nn
import torch.optim as optim

from services.game2.models.bot_gru import GRUPolicy, SEQ_LEN
from .data_windows import iter_events_jsonl, filter_by_time
from .replay import sample_replay_events_user
from .safe_io import safe_save_state_dict

GAME_TO_IDX = {1:0,2:1,3:2,4:3,5:4}

class UserSeqDataset(Dataset):
    def __init__(self, events: List[dict], H=64, W=64):
        acts, rows, cols = [], [], []
        for rec in events:
            if rec.get("source") == "bot": continue
            tok = int(rec.get("token", 0))
            if tok not in (1,2,3,4,5): continue
            acts.append(GAME_TO_IDX[tok])
            rows.append(int(rec.get("row",0)))
            cols.append(int(rec.get("col",0)))
        self.samples=[]
        for t in range(SEQ_LEN, len(acts)):
            a=acts[t-SEQ_LEN:t]; r=rows[t-SEQ_LEN:t]; c=cols[t-SEQ_LEN:t]; y=acts[t]
            self.samples.append((a,r,c,y))
        self.H, self.W = H, W
    def __len__(self): return len(self.samples)
    def __getitem__(self, i):
        import torch as T
        a,r,c,y = self.samples[i]
        return (T.tensor(a,dtype=T.long),
                T.tensor(r,dtype=T.float32),
                T.tensor(c,dtype=T.float32),
                T.tensor(y,dtype=T.long))

def _class_weights(ds: Dataset, num_actions=5):
    counts = [0]*num_actions
    for _,_,_,y in ds:
        counts[int(y)] += 1
    total = sum(counts) or 1
    inv = [total/max(c,1) for c in counts]
    m = sum(inv)/len(inv)
    import torch as T
    return T.tensor([w/m for w in inv], dtype=T.float32)

def fine_tune_user(user_id: str, start_ts: float, end_ts: float,
                   H=64, W=64, lr=8e-4, epochs=6, batch_size=128,
                   min_samples=200, replay_ratio=0.2, history_days=7,
                   init_from_previous=True):
    user_dir = Path("data/users")/user_id
    day_events = list(filter_by_time(iter_events_jsonl(user_dir/"actions.jsonl"), start_ts, end_ts))
    if len(day_events) < min_samples:
        print(f"[{user_id}] skipped — only {len(day_events)} samples (<{min_samples})")
        return False

    replay_events = sample_replay_events_user(user_dir, start_ts, history_days=history_days)
    k = min(int(len(day_events)*replay_ratio), len(replay_events))
    if k>0:
        import random
        day_events = day_events + random.sample(replay_events, k)

    ds = UserSeqDataset(day_events, H=H, W=W)
    val_size = max(1, int(0.2*len(ds)))
    train_ds, val_ds = random_split(ds, [len(ds)-val_size, val_size])
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_dl   = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = GRUPolicy().to(device)

    model_path = Path("models/users")/f"{user_id}.pt"
    if init_from_previous and model_path.exists():
        state = torch.load(model_path, map_location="cpu")
        model.load_state_dict(state)
        print(f"[{user_id}] init from previous weights")

    loss_fn = nn.CrossEntropyLoss(weight=_class_weights(train_ds, num_actions=5).to(device))
    opt = optim.Adam(model.parameters(), lr=lr)

    for ep in range(1, epochs+1):
        model.train()
        trL,trN = 0.0,0
        for a,r,c,y in train_dl:
            a,r,c,y = a.to(device), r.to(device), c.to(device), y.to(device)
            opt.zero_grad()
            logits = model(a,r,c,H=H,W=W)
            loss = loss_fn(logits,y)
            loss.backward(); opt.step()
            trL += float(loss.item())*y.size(0); trN += y.size(0)
        model.eval()
        vaL,vaN = 0.0,0
        with torch.no_grad():
            for a,r,c,y in val_dl:
                a,r,c,y = a.to(device), r.to(device), c.to(device), y.to(device)
                logits = model(a,r,c,H=H,W=W)
                loss = loss_fn(logits,y)
                vaL += float(loss.item())*y.size(0); vaN += y.size(0)
        print(f"[{user_id}] ep {ep} tr={trL/max(1,trN):.4f} va={vaL/max(1,vaN):.4f}")

    from services.game2.models.bot_gru import GRUPolicy as Build
    safe_save_state_dict(model, model_path, build_model_fn=lambda: Build(), H=H, W=W, keep_backup=True)
    print(f"[{user_id}] ✅ saved -> {model_path}")
    return True
