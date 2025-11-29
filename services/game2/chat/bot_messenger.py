
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
import sys  

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parents[5]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from finetune_gemma.infer_runtime import generate_reply
from finetune_gemma.config_adapters import adapter_dir_for 

from ..data.db_players import PlayerDB
from ..data.db_chat import ChatDB


ROOT = Path(__file__).resolve().parents[2]       
DATA_DIR = ROOT.parents[0] / "data"                

PLAYERS_DB = DATA_DIR / "players.db"
CHAT_DB    = DATA_DIR / "chat.db"


app = FastAPI(title="Bot Messenger", version="1.0.0")


class BotRequest(BaseModel):
    sender_id: str
    receiver_id: str
    history_limit: int = 50


class BotResponse(BaseModel):
    message: str
    used_adapter: Optional[str] = None


@app.get("/health")
def health():
    return {"ok": True}


SYSTEM_PROMPT = (
    "You are a friendly player in NanoVerse, a 2D grid world made of chunks. "
    "Answer in simple, friendly English, in one short sentence. "
    "You may answer naturally to any general question, including preferences and opinions. "
    "You may mention game elements like chunks, colors, tiles, coins, and apples when it fits, "
    "but not in every answer. "
    "Stay in character as a NanoVerse player, but speak naturally. "
    "Do not mention AI, prompts, or the real world."
)

def fetch_dialog_messages(sender_id: str, receiver_id: str, limit: int = 50) -> List[Dict]:
    if not CHAT_DB.exists():
        return []

    try:
        con = sqlite3.connect(str(CHAT_DB))
        cur = con.cursor()
        cur.execute(
            """
            SELECT timestamp, sender_id, receiver_id, content
            FROM messages
            WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (sender_id, receiver_id, receiver_id, sender_id, limit),
        )
        rows = cur.fetchall()
        con.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"chat.db error: {e}")

    rows.reverse()
    return [
        {"ts": r[0], "sender": r[1], "receiver": r[2], "text": r[3]}
        for r in rows
    ]


def to_chatml(sender_id: str, rows: List[Dict]) -> List[Dict[str, str]]:
    msgs: List[Dict[str, str]] = []
    for r in rows:
        role = "assistant" if r["sender"] == sender_id else "user"
        msgs.append({"role": role, "content": r["text"] or ""})
    return msgs


def build_chatml_with_system(sender_id: str, rows: List[Dict]) -> List[Dict[str, str]]:
    history = to_chatml(sender_id, rows)
    return [{"role": "system", "content": SYSTEM_PROMPT}] + history

@app.post("/generate", response_model=BotResponse)
def generate(req: BotRequest):

    rows = fetch_dialog_messages(req.sender_id, req.receiver_id, req.history_limit)
    chatml = build_chatml_with_system(req.sender_id, rows)

    adapter_path = None
    print(f"[DBG] sender={req.sender_id} receiver={req.receiver_id} adapter=BASE_MODEL_ONLY")

    try:
        reply = generate_reply(chatml, adapter_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model inference error: {e}")

    return BotResponse(message=reply, used_adapter="BASE_MODEL")
