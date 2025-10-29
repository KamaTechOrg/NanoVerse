from __future__ import annotations
from typing import List, Optional, Dict
from datetime import datetime
from ..storage.json_store import chats_data, save_json, CHATS_PATH
from ..utils.time_ids import msg_id as _msg_id

def minimal_view(m: dict, viewer: Optional[str]=None) -> dict:
    v = {
        "id": m["id"],
        "from": m["from"],
        "to": m["to"],
        "message": m.get("message", ""),
        "timestamp": m["timestamp"],
        "read_by": m.get("read_by", []),
        "deleted": m.get("deleted", False),
    }
    if m.get("quoted_id"):
        v["quotedId"] = m["quoted_id"]
    if viewer:
        v["my_reaction"] = m.get("reactions", {}).get(viewer)
    return v

def get_message_by_id(mid: str) -> Optional[dict]:
    msgs = chats_data.get("chats", [{}])[0].get("messages", [])
    for m in msgs:
        if (m.get("id") or "") == mid:
            return m
    return None

def append_message(fr: str, to: str, text: str, ts: Optional[str]=None, quoted_id: Optional[str]=None) -> dict:
    ts = ts or datetime.utcnow().isoformat() + "Z"
    msg = {
        "id": _msg_id(ts, fr, text),
        "from": fr,
        "to": to,
        "message": text or "",
        "timestamp": ts,
        "quoted_id": quoted_id or None,
        "reactions": {},
        "read_by": [fr],
        "deleted": False,
        "origin": None,
        "model": None,
    }
    chats_data["chats"][0]["messages"].append(msg)
    save_json(CHATS_PATH, chats_data)
    return msg

def history_between(a: str, b: str, viewer: Optional[str]=None) -> List[dict]:
    msgs = chats_data.get("chats", [{}])[0].get("messages", [])
    out: List[dict] = []
    for m in msgs:
        if (m.get("from")==a and m.get("to")==b) or (m.get("from")==b and m.get("to")==a):
            m.setdefault("timestamp", datetime.utcnow().isoformat()+"Z")
            m.setdefault("id", _msg_id(m["timestamp"], m.get("from",""), m.get("message","")))
            m.setdefault("reactions", {})
            m.setdefault("read_by", [m.get("from")] if m.get("from") else [])
            m.setdefault("deleted", False)
            m.setdefault("origin", None)
            m.setdefault("model", None)
            out.append(minimal_view(m, viewer))
    return out[-128:] 

def unread_count_for(me: str, from_id: str) -> int:
    msgs = chats_data.get("chats", [{}])[0].get("messages", [])
    return sum(
        1 for m in msgs
        if m.get("from")==from_id and m.get("to")==me and me not in m.get("read_by", [])
    )

def mark_read_pair(me: str, with_id: str) -> int:
    msgs = chats_data.get("chats", [{}])[0].get("messages", [])
    updated = 0
    for m in msgs:
        if m.get("from")==with_id and m.get("to")==me:
            rb = m.setdefault("read_by", [])
            if me not in rb:
                rb.append(me)
                updated += 1
    if updated:
        save_json(CHATS_PATH, chats_data)
    return updated

def unread_summary_for(me: str) -> Dict[str, int]:
    peers = set()
    msgs = chats_data.get("chats", [{}])[0].get("messages", [])
    for m in msgs:
        if m.get("to")==me:
            peers.add(m.get("from"))
    return {pid: unread_count_for(me, pid) for pid in peers if pid and pid != me}

def soft_delete_message_by_id(message_id: str, requester_id: str) -> Optional[dict]:
    msgs = chats_data.get("chats", [{}])[0].get("messages", [])
    for m in msgs:
        if (m.get("id") or "") == message_id:
            if m.get("from") != requester_id:
                return None
            if not m.get("deleted", False):
                m["deleted"] = True
                m["message"] = ""
                m["updated_at"] = datetime.utcnow().isoformat()+"Z"
                save_json(CHATS_PATH, chats_data)
            return m
    return None
from __future__ import annotations
from typing import List, Optional, Dict

# Storage layer: one SQLite DB file per players pair under project/Data/db/
from server.storage.sqlite import chat_store


# ---------------------------------------------------------------------
# Minimal view formatter (keeps client-facing shape stable)
# NOTE: The new DB schema is minimal and does not track read_by/deleted.
# We add compatibility fields so the UI can keep working unchanged.
# ---------------------------------------------------------------------
def minimal_view(m: dict, viewer: Optional[str] = None) -> dict:
    v = {
        "id": m.get("id"),
        "from": m.get("from"),
        "to": m.get("to"),
        "message": m.get("message", ""),
        "timestamp": m.get("timestamp"),
        # compatibility fields (not persisted in the new schema)
        "read_by": m.get("read_by", []),
        "deleted": m.get("deleted", False),
    }
    reaction = m.get("reaction", "none")
    v["reaction"] = reaction
    if viewer:
        # historically there was a per-viewer reaction; we mirror the global one
        v["my_reaction"] = reaction
    # keep support if quoted_id is ever passed from callers
    if m.get("quoted_id"):
        v["quotedId"] = m["quoted_id"]
    return v


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------
def get_message_by_id(mid: str) -> Optional[dict]:
    """
    Not supported with per-pair DBs without knowing the pair (a,b).
    Kept for signature compatibility; returns None.
    """
    return None


def append_message(fr: str, to: str, text: str, ts: Optional[str] = None, quoted_id: Optional[str] = None) -> dict:
    """
    Insert a new message into the dedicated DB file for (fr,to) and return a message dict.
    """
    msg = chat_store.insert_message(
        sender_id=fr,
        receiver_id=to,
        content=text or "",
        timestamp=ts,     # if None, chat_store will generate ISO timestamp
        reaction="none",
    )
    # Cast numeric DB id to string for client compatibility
    msg["id"] = str(msg.get("id"))
    # add compatibility fields expected by the UI (not persisted)
    msg.setdefault("read_by", [fr])
    msg.setdefault("deleted", False)
    if quoted_id:
        msg["quoted_id"] = quoted_id
    return msg


def set_reaction(message_id: int | str, a: str, b: str, reaction: str) -> dict:
    """
    Update reaction ('like'|'dislike'|'none') for a message in the (a,b) DB.
    """
    mid = int(message_id)
    upd = chat_store.update_reaction(message_id=mid, for_a=a, for_b=b, reaction=reaction)
    # keep id as string for client consistency
    upd["id"] = str(upd["id"])
    return upd


def history_between(a: str, b: str, viewer: Optional[str] = None) -> List[dict]:
    """
    Return chat history for (a,b) from their dedicated DB as a list of minimal-view messages.
    """
    rows = chat_store.fetch_history(a, b, limit=1000)  # tune limit if needed
    out: List[dict] = []
    for r in rows:
        # normalize id to string for client compatibility
        r["id"] = str(r.get("id"))
        # add compatibility fields (not stored in DB)
        r.setdefault("read_by", [])
        r.setdefault("deleted", False)
        out.append(minimal_view(r, viewer))
    return out


# ---------------------------------------------------------------------
# Unread/read markers (no-op with the minimal schema)
# ---------------------------------------------------------------------
def unread_count_for(me: str, from_id: str) -> int:
    """
    Not tracked in the minimal schema; return 0 to keep UI logic stable.
    """
    return 0


def mark_read_pair(me: str, with_id: str) -> int:
    """
    Not tracked in the minimal schema; return 0 (no updates).
    """
    return 0


def unread_summary_for(me: str) -> Dict[str, int]:
    """
    Not tracked in the minimal schema; return empty summary.
    """
    return {}


# ---------------------------------------------------------------------
# Soft delete (not supported in the minimal schema)
# ---------------------------------------------------------------------
def soft_delete_message_by_id(message_id: str, requester_id: str) -> Optional[dict]:
    """
    Soft delete is not supported by the given schema (no 'deleted'/'updated_at' columns).
    Return None to indicate not supported.
    """
    return None
