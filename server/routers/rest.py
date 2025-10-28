from fastapi import APIRouter
from ..storage.json_store import TOKEN_TO_PLAYER
from ..services.messages import (
    history_between,
    unread_count_for,
    mark_read_pair,
)
from ..services.presence import active_players

router = APIRouter()


@router.get("/history")
async def get_history(token: str, with_id: str):
    """
    מחזיר את ההיסטוריה של הצ'אט בין המשתמש המחובר לשחקן אחר.
    ניגש כעת למסד הנתונים SQLite הייעודי לכל זוג שחקנים.
    """
    me = TOKEN_TO_PLAYER.get(token)
    if not me:
        return {"ok": False, "reason": "invalid_token"}

    # קריאה למסרים הישנים של הצמד
    msgs = history_between(me, with_id, viewer=me)

    # פעולות קריאה לא רלוונטיות לסכמה החדשה, נשמרות כתואם (יחזרו 0)
    changed = mark_read_pair(me, with_id)
    unread = unread_count_for(me, with_id)

    return {"ok": True, "messages": msgs, "unread_now": unread, "changed": changed}


@router.get("/active")
async def get_active_players():
    """
    מחזיר רשימת שחקנים מחוברים (לצורכי תצוגת נוכחות).
    """
    return {"ok": True, "active": active_players()}
