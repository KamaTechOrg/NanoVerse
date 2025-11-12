from __future__ import annotations
from pathlib import Path
import json, time
from concurrent.futures import ProcessPoolExecutor, as_completed

from .data_windows import today_range
from .fine_tune_default import fine_tune_default
from .fine_tune_user import fine_tune_user
from .alerts import send_alert

def all_users():
    root = Path("data/users")
    for d in root.iterdir():
        if d.is_dir():
            yield d.name

def _train_one(uid, start_ts, end_ts):
    try:
        ok = fine_tune_user(uid, start_ts, end_ts, init_from_previous=True)
        return (uid, ok, None)
    except Exception as e:
        return (uid, False, str(e))

def main(tz_offset_hours: int = 0, max_workers: int = 6):
    start_ts, end_ts = today_range(tz_offset_hours=tz_offset_hours)

    ok_default = False
    try:
        ok_default = fine_tune_default(start_ts, end_ts, init_from_previous=True)
    except Exception as e:
        send_alert("❌ default model training failed", {"err": str(e)})

    updated, failed = [], []
    uids = list(all_users())
    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(_train_one, uid, start_ts, end_ts) for uid in uids]
        for fut in as_completed(futs):
            uid, ok, err = fut.result()
            if ok: updated.append(uid)
            else:  failed.append({"user": uid, "err": err or "unknown"})

    Path("models/users").mkdir(parents=True, exist_ok=True)
    info = {"updated_users": updated, "default_ok": bool(ok_default),
            "start_ts": start_ts, "end_ts": end_ts, "ts": time.time()}
    (Path("models/users")/"model_version.json").write_text(json.dumps(info), encoding="utf-8")

    if failed:
        send_alert("❌ Daily training failures", {"count": len(failed), "items": failed})
    else:
        send_alert("✅ Daily training finished successfully",
                   {"updated_users": len(updated), "default_ok": bool(ok_default)})

if __name__ == "__main__":
    main(tz_offset_hours=2, max_workers=6)
