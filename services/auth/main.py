from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from jose import jwt
import os, json, time, re, sys

app = FastAPI()

# ====== קובץ users.json (DB קטן להרשמה) ======
DATA = Path(__file__).parent / "users.json"
DATA.parent.mkdir(parents=True, exist_ok=True)
if not DATA.exists():
    DATA.write_text(json.dumps({"users": []}, ensure_ascii=False, indent=2), encoding="utf-8")

JWT_SECRET = os.getenv("AUTH_JWT_SECRET", "CHANGE_ME_123456789")
JWT_ALG = "HS256"
BIN8_RE = re.compile(r"^[01]{8}$")  # "00000000" .. "11111111"

# ====== אינטגרציה עם finetune_gemma ======
# נעלה ל-root של NanoVerse ומשם נטען את הסקריפטים של ה-finetune:
NANO_ROOT = Path(__file__).resolve().parents[4]
FT_DIR = NANO_ROOT / "finetune_gemma"
if str(FT_DIR) not in sys.path:
    sys.path.append(str(FT_DIR))

try:
    # יוצר לשחקן: data/users/player{ID}_split/{train.jsonl,val.jsonl} + adapters/player{ID}/latest
    from manage_players import ensure_player_dirs
except Exception as _e:
    ensure_player_dirs = None
    print("[AUTH] WARN: could not import ensure_player_dirs from finetune_gemma:", _e)

try:
    # מעדכן players.dev.db / players.db עם הנתיב של האדפטר (עמודת adapter_path)
    from link_adapter_to_db import link_adapter
except Exception as _e:
    link_adapter = None
    print("[AUTH] WARN: could not import link_adapter:", _e)

# ====== מודלים ======
class RegisterIn(BaseModel):
    username: str
    email: EmailStr

class LoginIn(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    user_id: Optional[Union[int, str]] = None  # יכול להיות "00000010" או 10

# ====== Utils ======
def to_bin8(n: int) -> str:
    return f"{(n & 0xFF):08b}"

def normalize_users(users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for u in users:
        uid = u.get("id")
        if isinstance(uid, int):
            u["id"] = to_bin8(uid)
        elif isinstance(uid, str) and BIN8_RE.fullmatch(uid):
            pass
        else:
            try:
                n = int(uid)
                u["id"] = to_bin8(n)
            except Exception:
                raise HTTPException(500, f"bad_user_id_format: {uid!r}")
    return users

def load_db() -> Dict[str, Any]:
    with open(DATA, "r", encoding="utf-8") as f:
        db = json.load(f)
    db["users"] = normalize_users(db.get("users", []))
    return db

def save_db(obj: Dict[str, Any]):
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def next_free_id(users: List[Dict[str, Any]]) -> str:
    used_nums = set()
    for u in users:
        uid = u.get("id")
        if isinstance(uid, str) and BIN8_RE.fullmatch(uid):
            used_nums.add(int(uid, 2))
        elif isinstance(uid, int):
            used_nums.add(uid & 0xFF)
        else:
            raise HTTPException(500, "corrupted_user_id")
    for n in range(256):
        if n not in used_nums:
            return to_bin8(n)
    raise HTTPException(409, "id_space_exhausted_0_255")

# ====== Endpoints ======
@app.post("/register")
def register(inp: RegisterIn):
    db = load_db()
    users = db.get("users", [])

    if any(u["username"].lower() == inp.username.lower() for u in users):
        raise HTTPException(409, "username_taken")
    if any(u["email"].lower() == inp.email.lower() for u in users):
        raise HTTPException(409, "email_taken")

    uid = next_free_id(users)
    user = {"id": uid, "username": inp.username, "email": inp.email}
    users.append(user)
    db["users"] = users
    save_db(db)

    # 1) יצירת תיקיות אימון + תיקיית אדפטר (Idempotent)
    if ensure_player_dirs:
        try:
            info = ensure_player_dirs(uid)
            print(f"[AUTH] prepared finetune dirs for {uid}: {info}")
        except Exception as e:
            print(f"[AUTH] WARN: could not prepare dirs for {uid}: {e}")

    # 2) כתיבת adapter_path ל-players.dev.db / players.db (לפי ההגדרה בסקריפט)
    if link_adapter:
        try:
            adapter_dir = link_adapter(uid)
            print(f"[AUTH] linked adapter for {uid}: {adapter_dir}")
        except Exception as e:
            print(f"[AUTH] WARN: could not link adapter for {uid}: {e}")

    now = int(time.time())
    token = jwt.encode({"sub": user["id"], "username": user["username"], "iat": now},
                       JWT_SECRET, algorithm=JWT_ALG)
    return {"ok": True, "user": user, "token": token, "player_id": user["id"]}

@app.post("/login")
def login(inp: LoginIn):
    print(f"[AUTH] /login called with: username={inp.username}, email={inp.email}, user_id={inp.user_id}")
    db = load_db()
    users = db.get("users", [])
    print(f"[AUTH] loaded {len(users)} users")

    user = None

    if inp.user_id is not None:
        print(f"[AUTH] searching by user_id={inp.user_id}")
        if isinstance(inp.user_id, int):
            wanted = to_bin8(inp.user_id)
        elif isinstance(inp.user_id, str):
            wanted = inp.user_id if BIN8_RE.fullmatch(inp.user_id) else to_bin8(int(inp.user_id))
        else:
            raise HTTPException(400, "bad_user_id_type")
        user = next((u for u in users if u["id"] == wanted), None)

    if not user and inp.username:
        print(f"[AUTH] searching by username={inp.username}")
        user = next((u for u in users if u["username"].lower() == inp.username.lower()), None)

    if not user and inp.email:
        print(f"[AUTH] searching by email={inp.email}")
        user = next((u for u in users if u["email"].lower() == inp.email.lower()), None)

    if not user:
        print("[AUTH] user not found ❌")
        raise HTTPException(401, "user_not_found")

    now = int(time.time())
    token = jwt.encode({"sub": user["id"], "username": user["username"], "iat": now},
                       JWT_SECRET, algorithm=JWT_ALG)
    print(f"[AUTH] ✅ success for {user['username']} id={user['id']}")
    return {"ok": True, "user": user, "token": token, "player_id": user["id"]}

@app.get("/players")
async def get_players():
    try:
        if not DATA.exists():
            print(f"[AUTH] users.json not found at {DATA}")
            return {"players": []}
        with open(DATA, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"players": data.get("users", [])}
    except Exception as e:
        print(f"[AUTH] Error reading players:", e)
        return {"players": []}

@app.get("/whoami")
async def whoami(token: str = Query(...)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return {"ok": True, "player": {"id": payload.get("sub"), "username": payload.get("username")}}
    except Exception as e:
        return JSONResponse({"ok": False, "reason": str(e)}, status_code=401)

@app.get("/health")
def health():
    return {"ok": True, "service": "auth"}
