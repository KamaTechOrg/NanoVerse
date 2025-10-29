# from fastapi import APIRouter, Body
# from ..models.schemas import BotSendRequest
# from ..services.bot import handle_bot_send

# router = APIRouter()

# @router.post("/bot/send")
# async def bot_send(req: BotSendRequest):
#     return await handle_bot_send(
#         on_behalf_of=req.on_behalf_of,
#         to=req.to,
#         mode=req.mode,
#         text=req.text,
#         system_hint=req.system_hint,
#     )

# @router.post("/demo/bot-ping")
# async def demo_bot_ping(body: dict = Body(...)):
#     return await handle_bot_send(
#         on_behalf_of=body.get("as"),
#         to=body.get("to"),
#         mode=body.get("mode", "generate"),
#         text=body.get("text"),
#         system_hint=body.get("system_hint"),
#     )
