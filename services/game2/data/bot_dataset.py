# services/game2/data/bot_dataset.py
import json
from pathlib import Path
import torch
from torch.utils.data import Dataset

SEQ_LEN = 30

class BotDataset(Dataset):
    def __init__(self, jsonl_path: Path):
        self.samples = []

        # טוענים את כל השורות
        with open(jsonl_path, "r") as f:
            rows = [json.loads(line) for line in f]

        # ממיינים לפי זמן (חשוב!)
        rows.sort(key=lambda x: x["ts"])

        # ממירים לרשימות פשוטות
        actions  = [r["token"] for r in rows]
        r_list   = [r["row"] for r in rows]
        c_list   = [r["col"] for r in rows]

        # חותכים לחלונות
        for i in range(len(rows) - SEQ_LEN):
            seq_actions = actions[i:i+SEQ_LEN]
            seq_rows    = r_list[i:i+SEQ_LEN]
            seq_cols    = c_list[i:i+SEQ_LEN]
            next_action = actions[i+SEQ_LEN]

            self.samples.append(
                (
                    torch.tensor(seq_actions, dtype=torch.long),
                    torch.tensor(seq_rows, dtype=torch.float32),
                    torch.tensor(seq_cols, dtype=torch.float32),
                    torch.tensor(next_action, dtype=torch.long)
                )
            )

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx]
