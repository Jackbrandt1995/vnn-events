from __future__ import annotations
from typing import List, Dict
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import pytz


def within_lookahead(iso_str: str, days: int) -> bool:
    if not iso_str:
        return False
    now = datetime.now(pytz.timezone("America/Denver"))
    try:
        dt = date_parser.isoparse(iso_str)
    except Exception:
        return False
    return now <= dt <= (now + timedelta(days=days))


def clean_and_filter(events: List[Dict], lookahead_days: int, allowed_states: set[str]) -> List[Dict]:
    out: List[Dict] = []
    for e in events:
        if not e:
            continue
        if e.get("state") not in allowed_states:
            continue
        if not within_lookahead(e.get("start"), lookahead_days):
            continue
        out.append(e)
    return out
