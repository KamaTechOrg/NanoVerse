from __future__ import annotations
import json, time, datetime
from pathlib import Path
from typing import Iterable, Dict, Any, Optional

def iter_events_jsonl(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                yield json.loads(line)
            except Exception:
                continue

def filter_by_time(events: Iterable[Dict[str, Any]],
                   start_ts: Optional[float] = None,
                   end_ts: Optional[float] = None):
    for e in events:
        ts = float(e.get("ts", 0.0))
        if (start_ts is None or ts >= start_ts) and (end_ts is None or ts < end_ts):
            yield e

def today_range(epoch_now: Optional[float] = None, tz_offset_hours: int = 0):
    now_utc = datetime.datetime.utcfromtimestamp(epoch_now or time.time())
    local = now_utc + datetime.timedelta(hours=tz_offset_hours)
    start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + datetime.timedelta(days=1)
    start_ts = (start_local - datetime.timedelta(hours=tz_offset_hours)).timestamp()
    end_ts   = (end_local   - datetime.timedelta(hours=tz_offset_hours)).timestamp()
    return start_ts, end_ts
