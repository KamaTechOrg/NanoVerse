from __future__ import annotations
from pathlib import Path
import json, time, datetime
from typing import Iterable, Dict, Any, List, Optional

def today_range(epoch_now: float | None = None, tz_offset_hours: int = 0):
    now_utc = datetime.datetime.utcfromtimestamp(epoch_now or time.time())
    local   = now_utc + datetime.timedelta(hours=tz_offset_hours)
    start   = local.replace(hour=0, minute=0, second=0, microsecond=0)
    end     = start + datetime.timedelta(days=1)
    start_ts = (start - datetime.timedelta(hours=tz_offset_hours)).timestamp()
    end_ts   = (end   - datetime.timedelta(hours=tz_offset_hours)).timestamp()
    return start_ts, end_ts

def iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists(): 
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                yield json.loads(line)
            except Exception:
                continue

def filter_by_time(events: Iterable[Dict[str, Any]], start_ts: float | None, end_ts: float | None):
    for e in events:
        ts = float(e.get("ts", 0.0))
        if (start_ts is None or ts >= start_ts) and (end_ts is None or ts < end_ts):
            yield e

def last_k_actions(events: Iterable[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
    buf: List[Dict[str, Any]] = []
    for e in events:
        buf.append(e)
        if len(buf) > k:
            buf.pop(0)
    return buf
