
from __future__ import annotations
import asyncio
from collections import deque
from pathlib import Path
from typing import Dict, Optional

from services.game2.hub.types import PlayerState, ActionToken
from services.game2.hub.movement import MovementService
from services.game2.hub.world import WorldService
from services.game2.hub.scrolls import ScrollService
from services.game2.hub.color import ColorService
from services.game2.bot.bot_predict import predict_next
from services.game2.models.bot_gru import SEQ_LEN
from services.game2.data.user_logs import UserActionLogger

MOVE_DIR = {
    ActionToken.RIGHT: (0, +1),
    ActionToken.LEFT:  (0, -1),
    ActionToken.UP:    (-1, 0),
    ActionToken.DOWN:  (+1, 0),
}

class BotCtx:
    def __init__(self, user_id: str, state: PlayerState):
        self.user_id = user_id
        self.state = state
        self.task: Optional[asyncio.Task] = None

        # היסטוריית פעולה/שורה/עמודה
        self.last_actions: deque[int] = deque(maxlen=SEQ_LEN)
        self.last_rows:    deque[int] = deque(maxlen=SEQ_LEN)
        self.last_cols:    deque[int] = deque(maxlen=SEQ_LEN)


class BotService:
    """
    Bot using GRUPolicy (new architecture)
    Predicts next action from:
    - last 30 actions
    - last 30 rows
    - last 30 cols
    """

    def __init__(self, world: WorldService, movement: MovementService,
                 scroll: ScrollService, color_service: ColorService, user_logs: UserActionLogger):
        self.world = world
        self.movement = movement
        self.scroll = scroll
        self.color = color_service
        self.bots: Dict[str, BotCtx] = {}
        self.user_logs = user_logs

    async def _tick(self, user_id: str):
        ctx = self.bots[user_id]
        TICK = 0.25

        while user_id in self.bots:
            try:
                state = ctx.state

                # מוסיפים row/col להיסטוריה
                ctx.last_rows.append(state.pos.row)
                ctx.last_cols.append(state.pos.col)

                # בונים וקטורים של 30
                a = list(ctx.last_actions)
                r = list(ctx.last_rows)
                c = list(ctx.last_cols)

                # padding אם אין עדיין 30
                if len(a) < SEQ_LEN:
                    pad_len = SEQ_LEN - len(a)
                    # a = [0] * pad_len + a
                    # r = [state.pos.row] * pad_len + r
                    # c = [state.pos.col] * pad_len + c

                    a = pad_seq(ctx.last_actions, SEQ_LEN, pad_value=5)     # 5 is game COLOR, but model will map PAD separately in bot_predict
                    r = pad_seq(ctx.last_rows,    SEQ_LEN, pad_value=ctx.state.pos.row)
                    c = pad_seq(ctx.last_cols,    SEQ_LEN, pad_value=ctx.state.pos.col)

                # חיזוי פעולה
                pred = predict_next(
                    user_id=user_id,
                    last_actions=a,
                    last_rows=r,
                    last_cols=c,
                    H = 64, W = 64
                )

                token = ActionToken(pred)

                # ביצוע פעולה
                if token in MOVE_DIR:
                    dr, dc = MOVE_DIR[token]
                    # await self.movement.apply_move(ctx.state, dr, dc)
                    ##??                    
                    moved = await self.movement.apply_move(ctx.state, dr, dc)

                    if moved.old_chunk_id and moved.old_chunk_id != ctx.state.chunk_id:
                        self.scroll.sessions.update_watchers_after_chunk_change(
                            ctx.state.user_id,
                            moved.old_chunk_id,
                            ctx.state.chunk_id
                        )

                        await self.scroll.broadcast_chunk(ctx.state.chunk_id)
                        await self.scroll.broadcast_chunk(moved.old_chunk_id)
                    else:
                        await self.scroll.broadcast_chunk(ctx.state.chunk_id)

                    ##??until here, mabye I can write it more short
                    await self.scroll.broadcast_chunk(ctx.state.chunk_id)

                elif token == ActionToken.COLOR:
                    self.color.color_plus_plus(ctx.state)
                    await self.scroll.broadcast_chunk(ctx.state.chunk_id)

                # נשמור גם את הפעולה שחזינו
                ctx.last_actions.append(pred)
                self.user_logs.append(
                    user_id= user_id,
                    chunk_id= ctx.state.chunk_id,
                    row = ctx.state.pos.row,
                    col = ctx.state.pos.col,
                    token=pred,
                    # extra={"source":"bot"}
                )
                await asyncio.sleep(TICK)

            except Exception:
                import traceback
                traceback.print_exc()
                break

    def start(self, user_id: str, state: PlayerState):
        if user_id in self.bots:
            self.stop(user_id)

        ctx = BotCtx(user_id=user_id, state=state)
        self.bots[user_id] = ctx

        load_last_history_from_file(user_id, ctx, self.user_logs)
        ctx.task = asyncio.create_task(self._tick(user_id))
        print(f"[BOT] started for {user_id}")

    def stop(self, user_id: str):
        ctx = self.bots.pop(user_id, None)
        if ctx and ctx.task:
            ctx.task.cancel()

        print(f"[BOT] stopped for {user_id}")

    def is_running(self, user_id: str) -> bool:
        return user_id in self.bots


    # normalize all sequences to exactly 30
def pad_seq(seq, target=SEQ_LEN, pad_value=None):
    seq = list(seq)
    if len(seq) >= target:
        return seq[-target:]
    pad = [pad_value if pad_value is not None else (seq[-1] if seq else 0)] * (target - len(seq))
    return pad + seq


import json

# def load_last_history_from_file(user_id: str, ctx: BotCtx, logs: UserActionLogger):
#     path = logs._file(user_id)
#     if not path.exists():
#         return

#     actions = []
#     rows = []
#     cols = []

#     with path.open("r", encoding="utf-8") as f:
#         for line in f:
#             rec = json.loads(line)
#             actions.append(rec["token"])
#             rows.append(rec["row"])
#             cols.append(rec["col"])

#     actions = actions[-SEQ_LEN:]
#     rows    = rows[-SEQ_LEN:]
#     cols    = cols[-SEQ_LEN:]

#     for a in actions:
#         ctx.last_actions.append(a)

#     for r in rows:
#         ctx.last_rows.append(r)

#     for c in cols:
#         ctx.last_cols.append(c)
def load_last_history_from_file(user_id: str, ctx: "BotCtx", logs: UserActionLogger):
    path = logs._file(user_id)
    if not path.exists():
        return
    actions, rows, cols = [], [], []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("source") == "bot":   # ignore bot feedback to avoid drift
                continue
            actions.append(int(rec["token"]))
            rows.append(int(rec["row"]))
            cols.append(int(rec["col"]))
    for a in actions[-SEQ_LEN:]:
        ctx.last_actions.append(a)
    for r in rows[-SEQ_LEN:]:
        ctx.last_rows.append(r)
    for c in cols[-SEQ_LEN:]:
        ctx.last_cols.append(c)