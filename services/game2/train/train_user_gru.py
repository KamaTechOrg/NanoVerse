from __future__ import annotations
import json
from pathlib import Path
from typing import List, Tuple
import torch
from torch.utils.data import Dataset, DataLoader, random_split
import torch.nn as nn
import torch.optim as optim

from services.game2.models.gru_policy_user import GRUPolicyUser, NUM_ACTIONS, MAX_SEQ
from services.game2.core.settings import H, W

  DATA_ROOT   = Path("data") / "users"
MODELS_ROOT = Path("models") / "users"

class UserSeqDataset(Dataset):
    """
    Builds samples: (seq<=30 previous tokens, row, col) -> next_token
    actions.jsonl lines with fields:
      ts, user_id, chunk_id, row, col, action (str), token (1..5)
    """
    def __init__(self, actions_file: Path):
        self.samples: List[Tuple[List[int], int, int, int]] = self._load(actions_file)

    def _load(self, p: Path):
        if not p.exists():
            return []
        events = []
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    tok = int(rec.get("token", 0))
                    if tok in (1,2,3,4,5):
                        events.append(rec)
                except Exception:
                    pass
        events.sort(key=lambda r: r.get("ts", 0.0))

        samples: List[Tuple[List[int], int, int, int]] = []
        hist: List[int] = []
        for rec in events:
            tok = int(rec["token"])
            row = int(rec.get("row", 0))
            col = int(rec.get("col", 0))
            if len(hist) >= 1:
                seq = hist[-MAX_SEQ:]
                samples.append((seq.copy(), row, col, tok))
            hist.append(tok)
        return samples

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        seq, row, col, target = self.samples[idx]
        pad_len = MAX_SEQ - len(seq)
        seq_tensor = torch.tensor(([0]*pad_len) + seq, dtype=torch.long)   # [T=30]
        y = torch.tensor(target - 1, dtype=torch.long)                      # to 0..4
        return seq_tensor, torch.tensor(row), torch.tensor(col), y


def train_user(user_id: str,
               epochs: int = 12,
               batch_size: int = 128,
               lr: float = 2e-3,
               device: str = "cuda" if torch.cuda.is_available() else "cpu"):
    actions_file = DATA_ROOT / user_id / "actions.jsonl"
    ds = UserSeqDataset(actions_file)
    if len(ds) < 80:
        raise RuntimeError(f"[{user_id}] Not enough samples: {len(ds)} (need ≥ 80)")

    # 90/10 split for a quick sanity validation
    n_total = len(ds)
    n_val = max(1, int(0.1 * n_total))
    n_train = n_total - n_val
    train_ds, val_ds = random_split(ds, [n_train, n_val])

    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=False)
    val_dl   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False, drop_last=False)

    model = GRUPolicyUser(board_h=H, board_w=W).to(device)
    opt = optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.CrossEntropyLoss()

    best_val = float("inf")
    patience = 3
    bad = 0

    for ep in range(1, epochs+1):
        model.train()
        tr_loss, tr_n = 0.0, 0
        for seq, row, col, y in train_dl:
            seq, row, col, y = seq.to(device), row.to(device), col.to(device), y.to(device)
            opt.zero_grad()
            logits = model(seq, row, col)
            loss = loss_fn(logits, y)
            loss.backward()
            opt.step()
            tr_loss += float(loss.item()) * y.size(0)
            tr_n += y.size(0)

        model.eval()
        va_loss, va_n = 0.0, 0
        with torch.no_grad():
            for seq, row, col, y in val_dl:
                seq, row, col, y = seq.to(device), row.to(device), col.to(device), y.to(device)
                logits = model(seq, row, col)
                loss = loss_fn(logits, y)
                va_loss += float(loss.item()) * y.size(0)
                va_n += y.size(0)

        tr_avg = tr_loss / max(1, tr_n)
        va_avg = va_loss / max(1, va_n)
        print(f"[{user_id}] ep {ep} train={tr_avg:.4f} val={va_avg:.4f}")

        if va_avg + 1e-6 < best_val:
            best_val = va_avg
            bad = 0
        else:
            bad += 1
            if bad >= patience:
                print("[early stop]")
                break

    out_dir = MODELS_ROOT / user_id
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt = {"state_dict": model.state_dict(),
            "meta": {"H": H, "W": W, "num_actions": NUM_ACTIONS, "max_seq": MAX_SEQ}}
    torch.save(ckpt, out_dir / "gru_policy.pt")
    print(f"[{user_id}] saved -> {out_dir / 'gru_policy.pt'}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python -m services.game2.train.train_user_gru <USER_ID>")
        raise SystemExit(1)
    train_user(sys.argv[1])
