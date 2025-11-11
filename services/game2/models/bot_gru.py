# services/game2/models/bot_gru.py
import torch
import torch.nn as nn

# Game action tokens in your engine are 1..5 (RIGHT=1, LEFT=2, UP=3, DOWN=4, COLOR=5)
# Model uses 0-based indices: 0..4 for actions; PAD_IDX=5 for padding inside sequences.
NUM_ACTIONS = 5           # number of real actions (no PAD)
PAD_IDX     = 5           # padding token index used inside sequences
VOCAB_SIZE  = NUM_ACTIONS + 1  # 6 (0..5)
SEQ_LEN     = 100         # history window
EMB         = 32
HIDDEN      = 128

class GRUPolicy(nn.Module):
    def __init__(self):
        super().__init__()
        # Use padding_idx so the PAD embedding stays zeroed and is not updated
        self.embed = nn.Embedding(VOCAB_SIZE, EMB, padding_idx=PAD_IDX)

        self.gru = nn.GRU(
            input_size=EMB + 2,   # +2 for normalized (row,col)
            hidden_size=HIDDEN,
            num_layers=1,
            batch_first=True,
        )

        self.fc = nn.Linear(HIDDEN, NUM_ACTIONS)

    @staticmethod
    def _norm_rc(rows: torch.Tensor, cols: torch.Tensor, H: int, W: int):
        """
        rows, cols: (B, T) integer or float tensors
        returns: (B, T, 2) normalized to [0,1]
        """
        r = rows.float() / float(max(H - 1, 1))
        c = cols.float() / float(max(W - 1, 1))
        return torch.stack([r, c], dim=-1)

    def forward(self, actions, rows, cols, H=64, W=64):
        """
        actions: (B, T) long, values in {0..4, PAD_IDX}
        rows:    (B, T) long/float raw indices
        cols:    (B, T) long/float raw indices
        """
        a = self.embed(actions)             # (B,T,EMB)
        rc = self._norm_rc(rows, cols, H, W)  # (B,T,2)
        x = torch.cat([a, rc], dim=-1)      # (B,T,EMB+2)

        out, _ = self.gru(x)                # (B,T,HIDDEN)
        last = out[:, -1, :]                # (B,HIDDEN)
        return self.fc(last)                # (B, NUM_ACTIONS)
