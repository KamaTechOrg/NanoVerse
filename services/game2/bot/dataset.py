# services/game2/bot_3/dataset.py
import json
from pathlib import Path
from torch.utils.data import Dataset
import torch

from services.game2.bot_3.model import ACTIONS, ACTION_TO_IDX, SEQ_LEN


class ActionDataset(Dataset):

    def __init__(self, path: str):
        self.items = []
        path = Path(path)

        with path.open("r", encoding="utf8") as f:
            records = [json.loads(line) for line in f]

        actions = []
        for rec in records:
            act = rec.get("action")
            if act in ACTION_TO_IDX:
                actions.append(ACTION_TO_IDX[act])

        for i in range(len(actions) - SEQ_LEN - 1):
            seq = actions[i:i + SEQ_LEN]
            target = actions[i + SEQ_LEN]
            self.items.append((seq, target))

    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        seq, target = self.items[idx]
        seq = torch.tensor(seq, dtype=torch.long)
        target = torch.tensor(target, dtype=torch.long)
        return seq, target
