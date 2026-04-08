from __future__ import annotations
import json
from typing import Optional

from fastapi import WebSocket

from ..services.presence import (
    send_to_all, get_selected, set_selected
)
from ..services.messages import (
    append_message, history_between, mark_read_pair, unread_count_for,
    minimal_view, set_reaction
)


async def chat_endpoint(ws: WebSocket, typ: str, data, player_id: str):
    """
    Unified WS handler for chat events.
    Expects `data` to be a JSON-decoded dict with a "type" field (or uses `typ`).
    """
    kind = (data.get("type") or typ or "").lower().strip()

    # ------------------------------
    # Select partner (open thread)
    # ------------------------------
    if kind == "select":
        partner = data.get("selectedPlayer") or data.get("with") or data.get("partner")
        set_selected(player_id, partner)

        if partner:
            # Load history for this pair from their dedicated DB
            msgs = history_between(player_id, partner, viewer=player_id)
            await ws.send_json({"type": "history", "with": partner, "messages": msgs})

            # Mark-as-read is a no-op under the minimal schema, but we keep the API shape
            if mark_read_pair(player_id, partner):
                await send_to_all(player_id, {
                    "type": "unread",
                    "from": partner, "to": player_id,
                    "count": unread_count_for(player_id, partner)
                })
        else:
            await ws.send_json({"type": "error", "message": "No partner selected"})
        return

    # ------------------------------
    # Mark messages as read (no-op)
    # ------------------------------
    if kind == "read":
        partner = data.get("with") or data.get("partner") or get_selected(player_id)
        if partner:
            mark_read_pair(player_id, partner)
            await send_to_all(player_id, {
                "type": "unread",
                "from": partner, "to": player_id,
                "count": unread_count_for(player_id, partner)  # returns 0 with current schema
            })
        else:
            await ws.send_json({"type": "error", "message": "missing partner for read"})
        return

    # ------------------------------
    # Typing indicator passthrough
    # ------------------------------
    if kind == "typing":
        partner = get_selected(player_id)
        if partner:
            await send_to_all(partner, {"type": "typing", "typing": [player_id]})
        return

    # ------------------------------
    # Reaction (like / dislike / none)
    # ------------------------------
    if kind in ("react", "reaction"):
        message_id = data.get("messageId") or data.get("id")
        partner = data.get("with") or data.get("partner") or data.get("selectedPlayer") or get_selected(player_id)
        raw_reaction = (data.get("reaction") or "").lower().strip()

        # Map legacy values to the new schema
        if raw_reaction in ("up", "+1", "like"):
            reaction = "like"
        elif raw_reaction in ("down", "-1", "dislike"):
            reaction = "dislike"
        elif raw_reaction in ("none", "", None):
            reaction = "none"
        else:
            await ws.send_json({"type": "error", "message": f"invalid reaction: {raw_reaction}"})
            return

        if message_id is None:
            await ws.send_json({"type": "error", "message": "missing messageId"})
            return
        if not partner:
            await ws.send_json({"type": "error", "message": "missing partner for reaction"})
            return

        # Update in the per-pair DB
        upd = set_reaction(message_id=message_id, a=player_id, b=partner, reaction=reaction)

        # Notify both sides
        await send_to_all(player_id, {"type": "message_updated", "data": upd})
        await send_to_all(partner,   {"type": "message_updated", "data": upd})

        # Acknowledge to sender (keeps older UI flows happy)
        await ws.send_json({"type": "react", "messageId": str(upd["id"]), "my_reaction": reaction})
        return

    # ------------------------------
    # Send a message
    # ------------------------------
    if kind == "message":
        text = data.get("message", "")
        partner = data.get("selectedPlayer") or data.get("with") or data.get("partner") or get_selected(player_id)
        quoted_id = data.get("quotedId") or data.get("quoted_id")
        ts = data.get("timestamp")  # optional; if None, messages layer generates ISO timestamp

        if not partner:
            await ws.send_json({"type": "error", "message": "No partner selected"})
            return
        if not isinstance(text, str) or text.strip() == "":
            await ws.send_json({"type": "error", "message": "Empty message"})
            return

        saved = append_message(player_id, partner, text, ts, quoted_id=quoted_id)
        payload = minimal_view(saved) | {"type": "message", "sender": player_id, "to": partner}

        # Broadcast to both parties
        await send_to_all(player_id, payload)
        await send_to_all(partner, payload)

        # Ack to sender
        await ws.send_json({
            "type": "sent",
            "to": partner,
            "id": saved["id"],
            "message": text,
            "timestamp": saved["timestamp"]
        })

        # Unread counter event (schema returns 0; event kept for UI contract)
        await send_to_all(partner, {
            "type": "unread",
            "from": player_id, "to": partner,
            "count": unread_count_for(partner, player_id)
        })
        return

    # ------------------------------
    # Unknown
    # ------------------------------
    await ws.send_json({"type": "error", "message": f"unknown type: {kind}"})
