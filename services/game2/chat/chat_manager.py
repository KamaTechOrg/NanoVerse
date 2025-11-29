
from typing import Dict, Optional, Tuple
from fastapi import WebSocket

from .messages import MessageService
from ..hub.sessions import SessionStore
from ..hub.world import WorldService
from ..hub.chunk_players import ChunkPlayers

import asyncio
import httpx

INACTIVITY_SEC = 10 
BOT_MESSENGER_URL = "http://127.0.0.1:8013"

class ChatManager:
    """
    High-level chat logic:
    - manages sending, receiving, reactions, typing, etc.
    - uses MessageService for DB actions
    - uses PlayerActionHistory from world for action logging

    New:
    - Inactivity timeout: if A->B and B doesn't reply within INACTIVITY_SEC,
      we call bot_messenger to reply on behalf of B.
    """

    def __init__(self, session_store: SessionStore, world: WorldService, message_service: MessageService, chunk_players: ChunkPlayers):
        self.session_store = session_store
        self.world = world
        self._selected_partner: Dict[str, Optional[str]] = {}
        self.messages = message_service
        self.chunk_players = chunk_players

        self._pending: Dict[Tuple[str, str, int], asyncio.Task] = {}
        self._http = httpx.AsyncClient(timeout=20.0)

    def set_selected_partner(self, me: str, other: Optional[str]) -> None:
        self._selected_partner[me] = other

    def get_selected_partner(self, me: str) -> Optional[str]:
        return self._selected_partner.get(me)

    async def broadcast_to_player(self, player_id: str, payload: dict) -> None:
        """
        Send a JSON payload to all sockets of a given player.
        """
        for ws in self.session_store.sockets_for_user(player_id).copy():
            try:
                await ws.send_json(payload)
            except Exception:
                self.session_store.pop(ws)

    def _key(self, a: str, b: str, msg_id: int) -> Tuple[str, str, int]:
        return (a, b, msg_id)

    def _schedule_inactivity(self, a: str, b: str, msg_id: int, ts_iso: str):
        """
        Schedule a bot-reply if 'b' doesn't reply to 'a' within INACTIVITY_SEC.
        """
        key = self._key(a, b, msg_id)

        async def _wait_and_maybe_reply():
            try:
                await asyncio.sleep(INACTIVITY_SEC)


                payload = {
                    "sender_id": b,       
                    "receiver_id": a,      
                    "history_limit": 50
                }
                try:
                    resp = await self._http.post(f"{BOT_MESSENGER_URL}/generate", json=payload)
                    resp.raise_for_status()
                    data = resp.json()  
                    bot_text = data.get("message", "[bot]")
                except Exception as e:
                    print(f"[WARN] bot_messenger error for {a}->{b} (msg_id={msg_id}): {e}")
                    return

                saved = self.messages.append_message(b, a, bot_text, None)
                out = self.messages._minimal_view(saved) | {"type": "message", "sender": b, "to": a}
                await self.broadcast_to_player(a, out)
                await self.broadcast_to_player(b, out)  # אופציונלי
            finally:
                self._pending.pop(key, None)

        if key in self._pending:
            try:
                self._pending[key].cancel()
            except Exception:
                pass
        self._pending[key] = asyncio.create_task(_wait_and_maybe_reply())

    def _cancel_for_pair(self, a: str, b: str):
        """
        Cancel any pending tasks waiting for b to reply to a.
        Useful when:
          - b DID reply (הנמען ענה),
          - or when a sends a new message (reset timer).
        """
        to_cancel = [k for k in list(self._pending.keys()) if k[0] == a and k[1] == b]
        for k in to_cancel:
            t = self._pending.pop(k, None)
            if t and not t.done():
                t.cancel()

    async def handle_chat(self, ws: WebSocket, kind: str, data: dict, player_id: str):
        """
        Handle all chat WebSocket actions.
        """
        if kind == "select":
            partner = data.get("selectedPlayer")
            self.set_selected_partner(player_id, partner)
            if partner:
                msgs = self.messages.history_between(player_id, partner, viewer=player_id)
                await ws.send_json({"type": "history", "with": partner, "messages": msgs})
            return

        if kind == "typing":
            partner = self.get_selected_partner(player_id)
            if partner:
                await self.broadcast_to_player(partner, {"type": "typing", "typing": [player_id]})
            return

        if kind == "react":
            msg_id = data.get("messageId")
            reaction = data.get("reaction")
            if not msg_id or reaction not in ("like", "dislike", "none"):
                await ws.send_json({"type": "error", "message": "invalid reaction data"})
                return
            try:
                msg_id = int(msg_id)
            except Exception:
                await ws.send_json({"type": "error", "message": "invalid message id"})
                return
            msg = self.messages.get_message_by_id(msg_id)
            if not msg:
                await ws.send_json({"type": "error", "message": "message not found"})
                return

            self.messages.update_reaction(msg_id, reaction)
            sender = msg["sender_id"]
            receiver = msg["receiver_id"]
            payload = {"type": "react", "messageId": msg_id, "my_reaction": reaction}
            await self.broadcast_to_player(sender, payload)
            await self.broadcast_to_player(receiver, payload)
            return

        if kind == "message":
            text = data.get("message", "")
            partner = data.get("selectedPlayer") or self.get_selected_partner(player_id)
            if not partner:
                await ws.send_json({"type": "error", "message": "No partner selected"})
                return

            saved = self.messages.append_message(player_id, partner, text, data.get("timestamp"))
            payload = self.messages._minimal_view(saved) | {"type": "message", "sender": player_id, "to": partner}

            await self.broadcast_to_player(partner, payload)
            await ws.send_json({
                "type": "sent",
                "to": partner,
                "id": saved["id"],
                "message": text,
                "timestamp": saved["timestamp"]
            })

            self._cancel_for_pair(a=partner, b=player_id)

            self._cancel_for_pair(a=player_id, b=partner)

            self._schedule_inactivity(a=player_id, b=partner, msg_id=int(saved["id"]), ts_iso=saved["timestamp"])
            return
