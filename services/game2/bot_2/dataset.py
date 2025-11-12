# # services/game2/bot/dataset.py
# import json
# import torch
# from torch.utils.data import Dataset

# ACTION_MAP = {"move_right": 1, "move_left": 2, "move_up": 3, "move_down": 4, "color": 5}

# def encode_state(state):
#     # flatten [up, down, left, right] × [edge, danger, apple, player]
#     flat = []
#     for d in ["up", "down", "left", "right"]:
#         flat.extend([
#             state[d]["edge"],
#             state[d]["danger"],
#             state[d]["apple"],
#             state[d]["player"],
#         ])
#     return torch.tensor(flat, dtype=torch.float32)

# class BotDataset(Dataset):
#     def __init__(self, path, hist_len=100):
#         self.samples = []
#         self.hist_len = hist_len

#         with open(path, "r") as f:
#             lines = [json.loads(l) for l in f]

#         history = []
#         for line in lines:
#             act_id = ACTION_MAP[line["action"]]
#             state = encode_state(line["state"])
#             row, col = line["row"], line["col"]

#             # Pad history if shorter than hist_len
#             hist = ([0] * (hist_len - len(history)) + history)[-hist_len:]
#             self.samples.append((row, col, state, hist, act_id))
#             history.append(act_id)

#     def __len__(self):
#         return len(self.samples)

#     def __getitem__(self, idx):
#         row, col, state, hist, act_id = self.samples[idx]
#         return (
#             torch.tensor(row, dtype=torch.float32),
#             torch.tensor(col, dtype=torch.float32),
#             state,
#             torch.tensor(hist, dtype=torch.long),
#             torch.tensor(act_id, dtype=torch.long),
#         )


# services/game2/bot/dataset.py
import json
import torch
from torch.utils.data import Dataset

ACTION_MAP = {"move_right": 1, "move_left": 2, "move_up": 3, "move_down": 4, "color": 5}

def encode_state(state):
    # flatten [up, down, left, right] × [edge, danger, apple, player]
    flat = []
    for d in ["up", "down", "left", "right"]:
        flat.extend([
            state[d]["edge"],
            state[d]["danger"],
            state[d]["apple"],
            state[d]["player"],
        ])
    return torch.tensor(flat, dtype=torch.float32)

class BotDataset(Dataset):
    def __init__(self, path, hist_len=100):
        self.samples = []
        self.hist_len = hist_len

        with open(path, "r") as f:
            lines = [json.loads(l) for l in f]

        history = []
        for line in lines:
            act_id = ACTION_MAP[line["action"]]
            state = encode_state(line["state"])
            row, col = line["row"], line["col"]

            # Pad history if shorter than hist_len
            hist = ([0] * (hist_len - len(history)) + history)[-hist_len:]
            self.samples.append((row, col, state, hist, act_id))
            history.append(act_id)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        row, col, state, hist, act_id = self.samples[idx]
        return (
            torch.tensor(row, dtype=torch.float32),
            torch.tensor(col, dtype=torch.float32),
            state,
            torch.tensor(hist, dtype=torch.long),
            torch.tensor(act_id, dtype=torch.long),
        )
