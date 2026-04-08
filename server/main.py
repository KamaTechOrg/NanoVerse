from __future__ import annotations

import json
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .routers import rest, bot, chat_manager


def create_app() -> FastAPI:
    app = FastAPI(
        title="Game Chat Server",
        version="1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],        # התאימי לפי הצורך
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers רגילים
    app.include_router(rest.router)
    app.include_router(bot.router)

    # אם ל-chat_manager יש router (עם @router.websocket("/ws")), נחבר אותו
    if hasattr(chat_manager, "router"):
        app.include_router(chat_manager.router)

    # אחרת—נגדיר כאן WebSocket ונעשה delegate ל-chat_manager.chat_endpoint
    elif hasattr(chat_manager, "chat_endpoint"):
        @app.websocket("/ws")
        async def ws_handler(ws: WebSocket):
            from .storage.json_store import TOKEN_TO_PLAYER  # מיפוי token -> player_id

            # אימות טוקן
            token = ws.query_params.get("token")
            if not token or token not in TOKEN_TO_PLAYER:
                await ws.close()
                return
            player_id = TOKEN_TO_PLAYER[token]

            await ws.accept()

            try:
                while True:
                    # קבלת הודעה גולמית
                    raw = await ws.receive_text()
                    try:
                        data = json.loads(raw)
                    except Exception:
                        await ws.send_json({"type": "error", "message": "bad_json"})
                        continue

                    typ = (data.get("type") or "").lower().strip()

                    # העברה ל-handler של chat_manager
                    await chat_manager.chat_endpoint(ws, typ, data, player_id)

            except WebSocketDisconnect:
                # ניתוק שקט
                pass

    else:
        # למקרה שאין router וגם אין chat_endpoint — זה עוזר בזמן פיתוח
        @app.get("/ws-missing")
        async def _ws_missing():
            return {"ok": False, "reason": "chat_manager has no router or chat_endpoint"}

    return app


app = create_app()
