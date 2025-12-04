import torch
import torch.nn as nn

ACTIONS = ["UP", "DOWN", "LEFT", "RIGHT", "COLOR"]
ACTION_TO_IDX = {a: i for i, a in enumerate(ACTIONS)}
NUM_ACTIONS = len(ACTIONS)

SEQ_LEN = 100
EMB = 32
HIDDEN = 64


class GRUActionPredictor(nn.Module):
    def __init__(self):
        super().__init__()
        self.emb = nn.Embedding(NUM_ACTIONS, EMB)
        self.gru = nn.GRU(EMB, HIDDEN, batch_first=True)
        self.fc = nn.Linear(HIDDEN, NUM_ACTIONS)

    def forward(self, x):
        # x: (B, SEQ_LEN) int indices
        e = self.emb(x)          # (B, SEQ_LEN, EMB)
        out, h = self.gru(e)     # (B, SEQ_LEN, HIDDEN)
        last = out[:, -1, :]     # (B, HIDDEN)
        logits = self.fc(last)   # (B, NUM_ACTIONS)
        return logits
