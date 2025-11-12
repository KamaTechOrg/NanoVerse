from __future__ import annotations
from pathlib import Path
import random
from typing import List, Dict, Any
from .data_windows import iter_events_jsonl, filter_by_time

def sample_replay_events_user(user_dir: Path, start_ts: float,
                              history_days: int = 7, max_samples: int = 3000) -> List[Dict[str, Any]]:
    hist_start = start_ts - history_days * 86400
    events = list(filter_by_time(iter_events_jsonl(user_dir/"actions.jsonl"), hist_start, start_ts))
    if len(events) > max_samples:
        events = random.sample(events, max_samples)
    return events

def sample_replay_events_pooled(users_root: Path, start_ts: float,
                                history_days: int = 7, max_users: int = 200, max_per_user: int = 2000) -> List[Dict[str, Any]]:
    users = [d for d in users_root.iterdir() if d.is_dir()]
    random.shuffle(users)
    chosen = users[:max_users]
    out: List[Dict[str, Any]] = []
    hist_start = start_ts - history_days * 86400
    for udir in chosen:
        events = list(filter_by_time(iter_events_jsonl(udir/"actions.jsonl"), hist_start, start_ts))
        if len(events) > max_per_user:
            events = random.sample(events, max_per_user)
        out.extend(events)
    return out
