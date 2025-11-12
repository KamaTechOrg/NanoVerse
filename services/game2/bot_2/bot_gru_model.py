# # services/game2/bot/bot_gru_model.py
# import torch
# import torch.nn as nn
# import torch.nn.functional as F

# NUM_ACTIONS = 5         # 1–5
# STATE_FEATURES = 4 * 4  # 4 directions × 4 features each
# HIST_LEN = 100
# HIDDEN_SIZE = 128

# class GRUPolicy(nn.Module):
#     def __init__(self, num_actions=NUM_ACTIONS, hidden_size=HIDDEN_SIZE):
#         super().__init__()
#         self.action_emb = nn.Embedding(num_actions + 1, 16)  # +1 for padding
#         self.state_fc = nn.Linear(STATE_FEATURES + 2, 64)    # (state + row + col)
#         self.gru = nn.GRU(16, hidden_size, batch_first=True)
#         self.fc = nn.Linear(hidden_size + 64, 64)
#         self.out = nn.Linear(64, num_actions)

#     def forward(self, rows, cols, states, actions):
#         """
#         rows, cols: (B,)
#         states: (B, STATE_FEATURES)
#         actions: (B, HIST_LEN)
#         """
#         # Embed actions history
#         act_emb = self.action_emb(actions)             # (B, HIST_LEN, 16)
#         _, h = self.gru(act_emb)                       # h: (1, B, hidden)
#         h = h.squeeze(0)                               # (B, hidden)

#         # Encode current state
#         pos_state = torch.cat([rows.unsqueeze(1), cols.unsqueeze(1), states], dim=1)
#         s = F.relu(self.state_fc(pos_state))           # (B, 64)

#         # Combine
#         x = torch.cat([s, h], dim=1)                   # (B, hidden+64)
#         x = F.relu(self.fc(x))
#         out = self.out(x)                              # (B, NUM_ACTIONS)
#         return out


# services/game2/bot/bot_gru_model.py
import torch
import torch.nn as nn
import torch.nn.functional as F

NUM_ACTIONS = 5         # 1–5
STATE_FEATURES = 4 * 4  # 4 directions × 4 features each
HIST_LEN = 100
HIDDEN_SIZE = 128

class GRUPolicy(nn.Module):
    def __init__(self, num_actions=NUM_ACTIONS, hidden_size=HIDDEN_SIZE):
        super().__init__()
        self.action_emb = nn.Embedding(num_actions + 1, 16)  # +1 for padding
        self.state_fc = nn.Linear(STATE_FEATURES + 2, 64)    # (state + row + col)
        self.gru = nn.GRU(16, hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size + 64, 64)
        self.out = nn.Linear(64, num_actions)

    def forward(self, rows, cols, states, actions):
        """
        rows, cols: (B,)
        states: (B, STATE_FEATURES)
        actions: (B, HIST_LEN)
        """
        # Embed actions history
        act_emb = self.action_emb(actions)             # (B, HIST_LEN, 16)
        _, h = self.gru(act_emb)                       # h: (1, B, hidden)
        h = h.squeeze(0)                               # (B, hidden)

        # Encode current state
        pos_state = torch.cat([rows.unsqueeze(1), cols.unsqueeze(1), states], dim=1)
        s = F.relu(self.state_fc(pos_state))           # (B, 64)

        # Combine
        x = torch.cat([s, h], dim=1)                   # (B, hidden+64)
        x = F.relu(self.fc(x))
        out = self.out(x)                              # (B, NUM_ACTIONS)
        return out
