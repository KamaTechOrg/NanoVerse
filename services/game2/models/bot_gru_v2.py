# # models/bot_gru_v2.py
# import torch
# import torch.nn as nn
# import torch.nn.functional as F

# HIDDEN_SIZE = 128
# USER_EMB_DIM = 32
# ACTION_BITS = 8
# NUM_ACTIONS = 7  # 1..7
# CNN_CHANNELS = 16  # קטן ומהיר

# class SmallCNN(nn.Module):##how can I see that I do it on the board??
#     def __init__(self):
#         super().__init__()
#         self.c1 = nn.Conv2d(1, CNN_CHANNELS, 5, padding=2)   # [B,16,64,64]
#         self.c2 = nn.Conv2d(CNN_CHANNELS, CNN_CHANNELS, 3, padding=1)
#         self.c3 = nn.Conv2d(CNN_CHANNELS, 32, 3, padding=1)  # [B,32,64,64]
#         self.pool = nn.MaxPool2d(2)                          # ↓ מרחבי
#         # אחרי שני פולים: 64→16 (פעמיים /2)
#         self.fc = nn.Linear(32*16*16, 128)

#     def forward(self, x):  # x: [B,1,64,64]
#         x = F.relu(self.c1(x))
#         x = self.pool(x)
#         x = F.relu(self.c2(x))
#         x = self.pool(x)
#         x = F.relu(self.c3(x))
#         x = x.view(x.size(0), -1)
#         x = self.fc(x)  # [B,128]
#         return x

# class GRUPolicyV2(nn.Module):
#     def __init__(self, num_users: int):
#         super().__init__()
#         self.cnn = SmallCNN()
#         self.user_emb = nn.Embedding(num_users+1, USER_EMB_DIM)  # 0=UNK
#         self.gru = nn.GRU(input_size=128+ACTION_BITS+USER_EMB_DIM, hidden_size=HIDDEN_SIZE, batch_first=True)
#         self.head_action = nn.Linear(HIDDEN_SIZE, NUM_ACTIONS)      # softmax לטוקן הבא
#         self.head_wait   = nn.Linear(HIDDEN_SIZE, 1)                # זמן המתנה (שניות), ReLU

#     def _make_step_input(self, board_feat, abits, user_idx):
#         # חיבור: [B, 128] || [B, 8] || [B, 32] => [B,168]
#         ue = self.user_emb(user_idx)                 # [B,32]
#         return torch.cat([board_feat, abits, ue], dim=1)

#     def forward_sequence(self, X_board, X_abits, user_idx, h0=None):
#         """
#         אימון: קלטים ברצף.
#         X_board: [B,T,1,64,64]
#         X_abits: [B,T,8]
#         user_idx: [B]  (אותו משתמש לכל הרצף)
#         """
#         B, T = X_board.size(0), X_board.size(1)
#         # CNN בכל צעד
#         boards = X_board.view(B*T, 1, 64, 64)
#         bf = self.cnn(boards)                # [B*T,128]
#         bf = bf.view(B, T, 128)
#         ab = X_abits                         # [B,T,8]
#         ue = self.user_emb(user_idx).unsqueeze(1).expand(B, T, USER_EMB_DIM)
#         step_in = torch.cat([bf, ab, ue], dim=2)  # [B,T,168]
#         out, hN = self.gru(step_in, h0)           # out: [B,T,128]
#         logits = self.head_action(out)            # [B,T,7]
#         wait   = F.relu(self.head_wait(out)).squeeze(-1)  # [B,T]
#         return logits, wait, hN

#     @torch.no_grad()
#     def forward_step(self, board, last_token:int, user_idx:int, h=None):
#         """
#         אינפרנס צעד-אחד (כמו ה־BotService).
#         board: [1,1,64,64] float32
#         last_token: int
#         user_idx: int
#         h: [1,1,128] או None
#         החזרה: (logits_next_action: [1,7]), h_new
#         """
#         self.eval()
#         bfeat = self.cnn(board)                 # [1,128]
#         abits = torch.zeros(1, ACTION_BITS, dtype=torch.float32, device=bfeat.device)
#         n = int(last_token)
#         for i in range(8):
#             if (n>>i)&1: abits[0,i] = 1.0
#         u = torch.tensor([user_idx], dtype=torch.long, device=bfeat.device)
#         step_in = self._make_step_input(bfeat, abits, u).unsqueeze(1)  # [1,1,168]
#         out, hN = self.gru(step_in, h)           # out: [1,1,128]
#         logits = self.head_action(out[:, -1, :]) # [1,7]
#         # אפשר להוציא גם זמן המתנה אם נדרש:
#         # wait  = F.relu(self.head_wait(out[:, -1, :]))  # [1,1]
#         return logits, hN


# models/bot_gru_v2.py
import torch
import torch.nn as nn
import torch.nn.functional as F

HIDDEN_SIZE = 128
USER_EMB_DIM = 32
ACTION_BITS = 8
NUM_ACTIONS = 7  # 1..7
CNN_CHANNELS = 16  # קטן ומהיר


class SmallCNN(nn.Module):
    """
    A small CNN that converts a [1,64,64] board into a [128] embedding vector.
    """
    def __init__(self):
        super().__init__()
        self.c1 = nn.Conv2d(1, CNN_CHANNELS, 5, padding=2)
        self.c2 = nn.Conv2d(CNN_CHANNELS, CNN_CHANNELS, 3, padding=1)
        self.c3 = nn.Conv2d(CNN_CHANNELS, 32, 3, padding=1)
        self.pool = nn.MaxPool2d(2)
        self.fc = nn.Linear(32 * 16 * 16, 128)

    def forward(self, x):  # x: [B,1,64,64]
        x = F.relu(self.c1(x))
        x = self.pool(x)
        x = F.relu(self.c2(x))
        x = self.pool(x)
        x = F.relu(self.c3(x))
        x = x.view(x.size(0), -1)
        x = self.fc(x)  # [B,128]
        return x


class GRUPolicyV2(nn.Module):
    def __init__(self, num_users: int):
        super().__init__()
        self.cnn = SmallCNN()
        self.user_emb = nn.Embedding(num_users + 1, USER_EMB_DIM)  # 0=UNK
        self.gru = nn.GRU(
            input_size=128 + ACTION_BITS + USER_EMB_DIM,
            hidden_size=HIDDEN_SIZE,
            batch_first=True,
        )
        self.head_action = nn.Linear(HIDDEN_SIZE, NUM_ACTIONS)
        self.head_wait = nn.Linear(HIDDEN_SIZE, 1)

    def _make_step_input(self, board_feat, abits, user_idx):
        ue = self.user_emb(user_idx)  # [B,32]
        return torch.cat([board_feat, abits, ue], dim=1)  # [B,168]

    def forward_sequence(self, X_board, X_abits, user_idx, h0=None):
        """
        Training forward — sequential mode.
        X_board: [B,T,1,64,64]
        X_abits: [B,T,8]
        user_idx: [B]
        """
        B, T = X_board.size(0), X_board.size(1)
        boards = X_board.view(B * T, 1, 64, 64)
        bf = self.cnn(boards)  # [B*T,128]
        bf = bf.view(B, T, 128)
        ab = X_abits  # [B,T,8]
        ue = self.user_emb(user_idx).unsqueeze(1).expand(B, T, USER_EMB_DIM)
        step_in = torch.cat([bf, ab, ue], dim=2)  # [B,T,168]
        out, hN = self.gru(step_in, h0)
        logits = self.head_action(out)  # [B,T,7]
        wait = F.relu(self.head_wait(out)).squeeze(-1)  # [B,T]
        return logits, wait, hN

    @torch.no_grad()
    def forward_step(self, board, last_token, user_idx, h=None):
        """
        One-step inference (used by BotService).
        board: [1,1,64,64] float32
        last_token: int or 0-dim tensor
        user_idx: int or tensor
        h: [1,1,128] or None
        Returns: (logits_next_action: [1,7], wait_seconds: [1,1], h_new)
        """
        self.eval()

        # --- Ensure valid scalar types ---
        if isinstance(last_token, torch.Tensor):
            last_token = int(last_token.item())
        if isinstance(user_idx, torch.Tensor):
            user_idx = int(user_idx.item())

        # --- Encode inputs ---
        bfeat = self.cnn(board)  # [1,128]

        # Convert last_token → 8-bit binary tensor
        abits = torch.zeros(1, ACTION_BITS, dtype=torch.float32, device=bfeat.device)
        n = int(last_token)
        for i in range(ACTION_BITS):
            if (n >> i) & 1:
                abits[0, i] = 1.0

        u = torch.tensor([user_idx], dtype=torch.long, device=bfeat.device)
        step_in = self._make_step_input(bfeat, abits, u).unsqueeze(1)  # [1,1,168]

        # --- GRU step ---
        out, hN = self.gru(step_in, h)
        out_step = out[:, -1, :]  # [1,128]

        # --- Outputs ---
        logits = self.head_action(out_step)  # [1,7]
        wait = F.relu(self.head_wait(out_step))  # [1,1]

        return logits, wait, hN
