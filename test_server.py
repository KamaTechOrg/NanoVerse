import pytest
import json
from fastapi.testclient import TestClient
from server import app  # יש להחליף בנתיב של קובץ הסרבר שלך
client = TestClient(app)
# פונקציה לקרוא טוקנים מקובץ JSON
def get_valid_token():
    with open("data/tokens.json", "r", encoding="utf-8") as f:
        tokens_data = json.load(f)
    # בחר טוקן תקין מתוך הרשימה
    return tokens_data["tokens"][0]["token"]  # לדוגמה, אנחנו לוקחים את ה-token של player1
valid_token = get_valid_token()  # קריאת הטוקן התקין
# ------------------- טסטים ל-REST -------------------
# טסט לבדיקת חיבור וסטטוס של שחקנים פעילים
def test_get_active_players():
    response = client.get("/active-players")
    assert response.status_code == 200
    assert isinstance(response.json(), list)  # אכן מחזיר רשימה
# טסט לבדיקת ההיסטוריה בין שני שחקנים
def test_get_history():
    response = client.get("/history", params={"token": valid_token, "with_id": "player2"})
    assert response.status_code == 200
    assert "messages" in response.json()  # היסטוריה נמצאת
# טסט לסיכום הודעות שלא נקראו
def test_unread_summary():
    response = client.get("/unread-summary", params={"token": valid_token})
    assert response.status_code == 200
    assert "counts" in response.json()  # סיכום קריאות הודעות נמצא
# טסט לבדיקת חיבור עם טוקן לא תקין
def test_invalid_token():
    response = client.get("/whoami", params={"token": "invalid_token"})
    assert response.status_code == 401  # אמור להחזיר טעות של טוקן לא תקין
# טסט לבדיקת חיבור עם טוקן תקין
def test_valid_token():
    response = client.get("/whoami", params={"token": valid_token})
    assert response.status_code == 200
    assert "player_id" in response.json()  # נוודא ש-id שחקן נמצא בתשובה
# ------------------- טסטים ל- WebSocket -------------------
# טסט לחיבור WebSocket
# @pytest.mark.asyncio
# async def test_chat_websocket():
#     # יצירת WebSocket
#     websocket = client.websocket_connect(f"/chat?token={valid_token}")
#     # טסט לשליחת הודעה
#     websocket.send_text(json.dumps({"type": "message", "message": "Hello", "selectedPlayer": "player2"}))
#     response = websocket.receive_text()  # החזרת התגובה
#     assert json.loads(response)["type"] == "message"  # נוודא שההודעה התקבלה
#     # טסט לחיבור שחקן אחר
#     websocket.send_text(json.dumps({"type": "select", "selectedPlayer": "player2"}))
#     response = websocket.receive_text()
#     assert json.loads(response)["type"] == "history"  # היסטוריה תקבלה
#     # טסט לשליחת לייק להודעה
#     websocket.send_text(json.dumps({"type": "like", "messageId": "message1"}))
#     response = websocket.receive_text()
#     assert json.loads(response)["type"] == "like"  # לוודא ששליחת הלייק הצליחה
#     assert "myLike" in json.loads(response)  # לוודא שהכיל את המידע על הלייק
#     # טסט לסימון הודעות כנקראו
#     websocket.send_text(json.dumps({"type": "read", "with": "player2"}))
#     response = websocket.receive_text()
#     assert json.loads(response)["type"] == "unread"  # לוודא שהגיב עם מידע חדש על קריאות
#     assert "count" in json.loads(response)  # לוודא שמספר הקריאות מעודכן
#     # סגור את החיבור בסיום
#     websocket.close()