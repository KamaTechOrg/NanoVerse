from __future__ import annotations
import asyncio
from collections import deque
from typing import Dict, Optional
import json
from pathlib import Path
from services.game2.hub.types import PlayerState, ActionToken
from services.game2.hub.movement import MovementService
from services.game2.hub.world import WorldService
from services.game2.hub.scrolls import ScrollService
from services.game2.hub.color import ColorService

from services.game2.bot.bot_predict import predict_next
from services.game2.bot.model import SEQ_LEN

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
        self.last_actions: deque[str] = deque(maxlen=SEQ_LEN)


class BotService:
    """
    Bot using GRUActionPredictor (bot)
    Predicts next action from last SEQ_LEN actions בלבד
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
        print("bot tick started for: ", user_id)
        ctx = self.bots[user_id]
        TICK = 0.25

        while user_id in self.bots:
            try:
                state = ctx.state

                actions_seq = pad_seq(ctx.last_actions, SEQ_LEN, pad_value="COLOR")

                # predicted_action_name = predict_next(actions_seq)
                predicted_action_name = predict_next(
                user_id=user_id,
                last_actions=actions_seq
            )

                token = ActionToken[predicted_action_name]

                if token in MOVE_DIR:
                    dr, dc = MOVE_DIR[token]
                    moved = await self.movement.apply_move(ctx.state, dr, dc)

                    if moved.old_chunk_id and moved.old_chunk_id != ctx.state.chunk_id:
                        self.scroll.sessions.update_watchers_after_chunk_change(
                            ctx.state.user_id,
                            moved.old_chunk_id,
                            ctx.state.chunk_id,
                        )

                        await self.scroll.broadcast_chunk(ctx.state.chunk_id)
                        await self.scroll.broadcast_chunk(moved.old_chunk_id)
                    else:
                        await self.scroll.broadcast_chunk(ctx.state.chunk_id)

                elif token == ActionToken.COLOR:
                    self.color.color_plus_plus(ctx.state)
                    await self.scroll.broadcast_chunk(ctx.state.chunk_id)

                ctx.last_actions.append(predicted_action_name)

                self.user_logs.append(
                    user_id=user_id,
                    chunk_id=ctx.state.chunk_id,
                    row=ctx.state.pos.row,
                    col=ctx.state.pos.col,
                    token=token,      
                
                )

                await asyncio.sleep(TICK)

            except Exception:
                import traceback
                traceback.print_exc()
                break

    def start(self, user_id: str, state: PlayerState):
        print("start bot for", user_id)
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


def pad_seq(seq, target=SEQ_LEN, pad_value=None):
    """
    מנרמל רשימה (deque או list) לאורך קבוע target.
    משתמש ב-pad_value, ואם None – חוזר על האיבר האחרון או 0.
    """
    seq = list(seq)
    if len(seq) >= target:
        return seq[-target:]
    if len(seq) == 0:
        fill = pad_value if pad_value is not None else 0
        return [fill] * target
    last = seq[-1]
    fill = pad_value if pad_value is not None else last
    pad = [fill] * (target - len(seq))
    return pad + seq

BOT3_USERS_DIR = Path("services/game2/bot/users")


def load_last_history_from_file(user_id: str, ctx: "BotCtx", logs: UserActionLogger):
    user_dir = BOT3_USERS_DIR / user_id
    path = user_dir / "actions.jsonl"

    print(f"[HISTORY] loading for {user_id} from {path}")

    if not path.exists():
        print("[HISTORY] file not found, skipping")
        return

    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except Exception as e:
                    print("[HISTORY] bad JSON, skipping:", e)
                    continue

                # לדלג על רשומות בוט
                if rec.get("source") == "bot":
                    continue

                act = rec.get("action")
                if isinstance(act, str):
                    ctx.last_actions.append(act)

        print(f"[HISTORY] loaded {len(ctx.last_actions)} actions for {user_id}")

    except Exception as e:
        print("[HISTORY] ERROR:", e)
        import traceback
        traceback.print_exc()
