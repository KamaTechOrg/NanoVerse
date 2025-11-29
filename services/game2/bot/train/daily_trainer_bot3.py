from __future__ import annotations
from pathlib import Path
import json, time
from concurrent.futures import ProcessPoolExecutor, as_completed

from services.game2.bot_3.train.data_utils_actions import today_range
from services.game2.bot_3.train.fine_tune_default_bot3 import fine_tune_default_bot3
from services.game2.bot_3.train.fine_tune_user_bot3 import fine_tune_user_bot3

USERS_DIR   = Path("services/game2/bot_3/users")
WEIGHTS_DIR = Path("services/game2/bot_3/models_weights")

def all_users():
    for d in USERS_DIR.iterdir():
        if d.is_dir():
            yield d.name

def _train_one(uid, start_ts, end_ts, use_last_k):
    try:
        ok = fine_tune_user_bot3(uid, start_ts, end_ts, init_from_previous=True,
                                 use_last_k=use_last_k)
        return (uid, ok, None)
    except Exception as e:
        return (uid, False, str(e))

def main(tz_offset_hours: int = 0, max_workers: int = 6, use_last_k: int | None = None):
    start_ts, end_ts = today_range(tz_offset_hours=tz_offset_hours)
    ok_default = False
    try:
        ok_default = fine_tune_default_bot3(start_ts, end_ts, init_from_previous=True,
                                            use_last_k=use_last_k)
    except Exception as e:
        print("[daily] default training failed:", e)

    updated, failed = [], []
    uids = list(all_users())
    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(_train_one, uid, start_ts, end_ts, use_last_k) for uid in uids]
        for fut in as_completed(futs):
            uid, ok, err = fut.result()
            if ok: updated.append(uid)
            else:  failed.append({"user": uid, "err": err or "unknown"})

    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    info = {"updated_users": updated, "default_ok": bool(ok_default),
            "start_ts": start_ts, "end_ts": end_ts, "ts": time.time()}
    (WEIGHTS_DIR/"model_version.json").write_text(json.dumps(info), encoding="utf-8")


if __name__ == "__main__":
    main(tz_offset_hours=2, max_workers=6, use_last_k=None)
