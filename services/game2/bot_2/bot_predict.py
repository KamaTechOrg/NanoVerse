# # services/game2/bot/bot_predict.py
# import torch
# from bot_gru_model import GRUPolicy, NUM_ACTIONS
# from dataset import encode_state

# DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# def load_model(weights_path="gru_policy.pt"):
#     model = GRUPolicy()
#     model.load_state_dict(torch.load(weights_path, map_location=DEVICE))
#     model.to(DEVICE)
#     model.eval()
#     return model

# def predict_next(model, row, col, state, last_actions):
#     # prepare input
#     state_t = encode_state(state).unsqueeze(0).to(DEVICE)
#     row_t = torch.tensor([row], dtype=torch.float32).to(DEVICE)
#     col_t = torch.tensor([col], dtype=torch.float32).to(DEVICE)
#     acts_t = torch.tensor([last_actions], dtype=torch.long).to(DEVICE)

#     logits = model(row_t, col_t, state_t, acts_t)
#     probs = torch.softmax(logits, dim=-1)
#     action_id = torch.argmax(probs, dim=-1).item() + 1
#     return action_id, probs.detach().cpu().numpy()[0]
# services/game2/bot_2/bot_predict.py

import torch
from pathlib import Path
from .bot_gru_model import GRUPolicy, NUM_ACTIONS
from .dataset import encode_state

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# 🟢 מצביע לנתיב הנכון של המשקולות
MODEL_PATH = Path(__file__).resolve().parents[3] / "models" / "users"/ "gru_policy.pt"#??this realy good??

def load_model(weights_path: str | Path = MODEL_PATH):
    model = GRUPolicy()
    state = torch.load(weights_path, map_location=DEVICE)
    model.load_state_dict(state)
    model.to(DEVICE)
    model.eval()
    print(f"✅ Loaded GRU model from: {weights_path}")
    return model


def predict_next(model, row, col, state, last_actions):
    # prepare input
    state_t = encode_state(state).unsqueeze(0).to(DEVICE)
    row_t = torch.tensor([row], dtype=torch.float32).to(DEVICE)
    col_t = torch.tensor([col], dtype=torch.float32).to(DEVICE)
    acts_t = torch.tensor([last_actions], dtype=torch.long).to(DEVICE)

    logits = model(row_t, col_t, state_t, acts_t)
    probs = torch.softmax(logits, dim=-1)
    action_id = torch.argmax(probs, dim=-1).item() + 1

    return action_id, probs.detach().cpu().numpy()[0]


