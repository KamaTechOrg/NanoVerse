from __future__ import annotations

from datetime import datetime
from typing import List, Optional
import httpx

from ..config import MODEL_SERVER_URL, BOT_ORIGIN, BOT_MODEL
from ..storage.sqlite import chat_store
from ..storage.json_store import players_data
from ..services.messages import history_between, minimal_view
from ..services.presence import send_to_all


# -------------------------------------------------------
# עוזר: הוספת הודעה חדשה של בוט למסד הנתונים (SQLite)
# -------------------------------------------------------
def _append_message_bot(fr: str, to: str, text: str, ts: Optional[str] = None) -> dict:
    ts = ts or (datetime.utcnow().isoformat() + "Z")
    # נכניס למסד הנתונים (טבלת chat_<a>__<b>.sqlite3)
    msg = chat_store.insert_message(
        sender_id=fr,
        receiver_id=to,
        content=text or "",
        timestamp=ts,
        reaction="none",
    )
    msg["origin"] = BOT_ORIGIN
    msg["model"] = BOT_MODEL
    return msg


# -------------------------------------------------------
# קריאה לשרת המודל (LLM)
# -------------------------------------------------------
async def _call_model_generate(turns: List[dict]) -> List[str]:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{MODEL_SERVER_URL}/generate",
                json={
                    "messages": turns,
                    "max_new_tokens": 1024,
                    "temperature": 0.7,
                },
            )
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and isinstance(data.get("text"), str):
            return [data["text"]]
        return []
    except Exception:
        return []


# -------------------------------------------------------
# בניית רצף דיאלוגים (turns) לצורך שליחת בקשה למודל
# -------------------------------------------------------
def _build_turns(sender: str, receiver: str) -> List[dict]:
    # נשלף את ההיסטוריה בין שני המשתמשים
    raw = history_between(receiver, sender)

    turns: List[dict] = [
        {
            "role": "system",
            "content": f"Respond succinctly and naturally as '{sender}'. Keep a friendly tone.",
        }
    ]

    for m in raw:
        txt = (m.get("message") or "").strip()
        if not txt:
            continue
        role = "assistant" if m.get("from") == sender else "user"
        if turns and turns[-1]["role"] == role and role != "system":
            turns[-1]["content"] += "\n" + txt
        else:
            turns.append({"role": role, "content": txt})

    # הבטחת התחלה עם הודעת משתמש
    first_idx = 0
    while first_idx < len(turns) and turns[first_idx]["role"] == "system":
        first_idx += 1
    if first_idx >= len(turns) or turns[first_idx]["role"] != "user":
        turns.insert(first_idx, {"role": "user", "content": "Hi"})

    # איחוד הודעות רצופות מאותו סוג
    compact: List[dict] = []
    for t in turns:
        if compact and compact[-1]["role"] == t["role"] and t["role"] != "system":
            compact[-1]["content"] += "\n" + t["content"]
        else:
            compact.append(t)

    if compact[-1]["role"] != "user":
        compact.append({"role": "user", "content": "Continue."})

    return compact


# -------------------------------------------------------
# פונקציה ראשית: שליחת הודעה על ידי הבוט
# -------------------------------------------------------
async def handle_bot_send(
    on_behalf_of: str,
    to: str,
    mode: str = "generate",
    text: Optional[str] = None,
    system_hint: Optional[str] = None,
):
    # אימות קיום משתמשים
    known = {p.get("id") or p.get("player_id") or p.get("name") for p in players_data.get("players", [])}
    if on_behalf_of not in known or to not in known:
        return {
            "ok": False,
            "reason": "unknown_player",
            "details": {"sender": on_behalf_of, "receiver": to},
        }

    # -----------------------------
    # מצב 1: שימוש בטקסט נתון ישירות
    # -----------------------------
    if mode == "use_text":
        txt = (text or "").strip()
        if not txt:
            return {"ok": False, "reason": "missing_text"}

        msg = _append_message_bot(on_behalf_of, to, txt)
        payload = minimal_view(msg) | {"type": "message", "sender": on_behalf_of, "to": to}

        # שליחה לצדדים
        await send_to_all(on_behalf_of, payload)
        await send_to_all(to, payload)
        return {"ok": True, "mode": "use_text", "message_id": msg["id"]}

    # -----------------------------
    # מצב 2: יצירת טקסט באמצעות המודל
    # -----------------------------
    turns = _build_turns(sender=on_behalf_of, receiver=to)
    if system_hint:
        turns.insert(0, {"role": "system", "content": system_hint.strip()})

    outs = await _call_model_generate(turns)
    if not outs:
        return {"ok": False, "reason": "model_empty_response"}

    txt = outs[0].strip()
    if not txt:
        return {"ok": False, "reason": "empty_text_after_strip"}

    msg = _append_message_bot(on_behalf_of, to, txt)
    payload = minimal_view(msg) | {"type": "message", "sender": on_behalf_of, "to": to}

    # שליחה לצדדים
    await send_to_all(on_behalf_of, payload)
    await send_to_all(to, payload)

    return {"ok": True, "mode": "generate", "message_id": msg["id"], "text": txt}
