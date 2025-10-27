from fastapi import APIRouter
from ..storage.json_store import players_data, TOKEN_TO_PLAYER
from ..services.messages import history_between, unread_summary_for, mark_read_pair, unread_count_for
from ..services.presence import active_players

router = APIRouter()

@router.get("/active-players")
async def get_active_players():
    
    result = []
    for p in players_data.get("players", []):
        pid = p.get("id") or p.get("player_id") or p.get("name")
        result.append({
            **p,
            "player_id": pid,
            "is_connected": bool(active_players.get(pid)),
        })
    return result

@router.get("/whoami")
async def whoami(token: str):
    
    pid = TOKEN_TO_PLAYER.get(token)
    if not pid:
        return {"ok": False, "reason": "invalid_token"}
    return {"ok": True, "player_id": pid}

@router.get("/history")
async def get_history(token: str, with_id: str):
   
    me = TOKEN_TO_PLAYER.get(token)
    if not me:
        return {"ok": False, "reason": "invalid_token"}
    msgs = history_between(me, with_id, viewer=me)

    changed = mark_read_pair(me, with_id)
    unread = unread_count_for(me, with_id)  
    return {"ok": True, "messages": msgs, "unread_now": unread, "changed": changed}

@router.get("/unread-summary")
async def unread_summary(token: str):
    
    me = TOKEN_TO_PLAYER.get(token)
    if not me:
        return {"ok": False, "reason": "invalid_token"}
    counts = unread_summary_for(me)
    return {"ok": True, "counts": counts}
