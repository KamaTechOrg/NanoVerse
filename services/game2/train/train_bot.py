import json
from pathlib import Path
import torch
from torch.utils.data import Dataset, DataLoader, random_split
import torch.nn as nn
import torch.optim as optim
import matplotlib.pyplot as plt

from services.game2.models.bot_gru import GRUPolicy, SEQ_LEN, PAD_IDX, NUM_ACTIONS
from services.game2.train.safe_io import safe_save_state_dict
from services.game2.models.bot_gru import GRUPolicy
GAME_TO_IDX = {1:0, 2:1, 3:2, 4:3, 5:4}

class BotDataset(Dataset):
    """
    Builds sliding windows of length SEQ_LEN over the user's actions.jsonl.
    Each sample = (actions_seq_idx, rows_seq, cols_seq, target_idx).
    Sequences are left-padded with PAD_IDX for actions, and with first observed row/col for rc.
    """
    def __init__(self, jsonl_path: Path, H=64, W=64):
        self.H, self.W = H, W
        self.actions = []
        self.rows    = []
        self.cols    = []

        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                if rec.get("source") == "bot":
                    continue
                self.actions.append(GAME_TO_IDX.get(int(rec["token"]), 0))
                self.rows.append(int(rec["row"]))
                self.cols.append(int(rec["col"]))

        self.samples = []
        T = len(self.actions)
        for t in range(SEQ_LEN, T):
            # window [t-SEQ_LEN, t)
            a = self.actions[t-SEQ_LEN:t]
            r = self.rows[t-SEQ_LEN:t]
            c = self.cols[t-SEQ_LEN:t]
            y = self.actions[t]  # next action index (0..4)

            self.samples.append((a, r, c, y))

    def __len__(self):
        return len(self.samples)

    @staticmethod
    def _pad_left(seq, target_len, pad_value):
        if len(seq) >= target_len:
            return seq[-target_len:]
        return [pad_value] * (target_len - len(seq)) + list(seq)

    def __getitem__(self, idx):
        a, r, c, y = self.samples[idx]
        # already exact length, but keep the helper in case
        a = torch.tensor(a, dtype=torch.long)
        r = torch.tensor(r, dtype=torch.float32)
        c = torch.tensor(c, dtype=torch.float32)
        y = torch.tensor(y, dtype=torch.long)
        return a, r, c, y

def _class_weights_from_counts(counts):
    # inverse frequency weights
    total = sum(counts)
    freqs = [max(c, 1)/total for c in counts]
    inv   = [1.0/f for f in freqs]
    # normalize to mean=1
    m = sum(inv)/len(inv)
    return torch.tensor([w/m for w in inv], dtype=torch.float32)

def train_for_user(user_id: str, H=64, W=64, lr=1e-3, epochs=12, batch_size=64):
    data_path  = Path("data/users") / user_id / "actions.jsonl"
    model_path = Path("models/users") / f"{user_id}.pt"
    model_path.parent.mkdir(parents=True, exist_ok=True)

    dataset = BotDataset(data_path, H=H, W=W)

    # Compute class weights to reduce COLOR dominance
    counts = [0]*NUM_ACTIONS
    for _, _, _, y in dataset:
        counts[int(y)] += 1
    cls_w = _class_weights_from_counts(counts)

    # Split train/val
    val_size = max(1, int(0.2 * len(dataset)))
    train_size = max(0, len(dataset) - val_size)
    train_ds, val_ds = random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=False)
    val_loader   = DataLoader(val_ds, batch_size=batch_size, shuffle=False, drop_last=False)

    model = GRUPolicy()
    criterion = nn.CrossEntropyLoss(weight=cls_w)
    optimizer = optim.Adam(model.parameters(), lr=lr)

    train_losses, val_losses, train_accs, val_accs = [], [], [], []

    for epoch in range(epochs):
        # ---- train ----
        model.train()
        total, correct, tot_loss = 0, 0, 0.0
        for a, r, c, y in train_loader:
            optimizer.zero_grad()
            logits = model(a, r, c, H=H, W=W)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()

            tot_loss += loss.item() * len(y)
            total    += len(y)
            correct  += (logits.argmax(1) == y).sum().item()

        train_losses.append(tot_loss/total if total else 0.0)
        train_accs.append(correct/total if total else 0.0)

        # ---- val ----
        model.eval()
        total, correct, tot_loss = 0, 0, 0.0
        with torch.no_grad():
            for a, r, c, y in val_loader:
                logits = model(a, r, c, H=H, W=W)
                loss = criterion(logits, y)
                tot_loss += loss.item() * len(y)
                total    += len(y)
                correct  += (logits.argmax(1) == y).sum().item()

        val_losses.append(tot_loss/total if total else 0.0)
        val_accs.append(correct/total if total else 0.0)

        print(f"Epoch {epoch+1}/{epochs} | "
              f"Train Acc={train_accs[-1]:.3f}, Val Acc={val_accs[-1]:.3f} | "
              f"Train Loss={train_losses[-1]:.4f}, Val Loss={val_losses[-1]:.4f}")


    torch.save(model.state_dict(), model_path)

    print(" Saved:", model_path)

    # Graphs
    plt.figure(figsize=(12,5))
    plt.subplot(1,2,1)
    plt.plot(train_losses, label="Train Loss")
    plt.plot(val_losses, label="Val Loss"); plt.legend(); plt.title("Loss"); plt.xlabel("Epoch")
    plt.subplot(1,2,2)
    plt.plot(train_accs, label="Train Acc")
    plt.plot(val_accs, label="Val Acc"); plt.legend(); plt.title("Accuracy"); plt.xlabel("Epoch")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python -m services.game2.train.train_bot <user_id>")
        sys.exit(1)
    train_for_user(sys.argv[1])
