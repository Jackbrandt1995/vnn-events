from __future__ import annotations
from typing import List, Dict
import requests
from datetime import datetime, timedelta
import pytz

from .base import Source, norm_event
from ..config import MEETUP_TOKEN, LOOKAHEAD_DAYS, EVENT_SCOPE, VETERAN_KEYWORDS, MT_BBOX, WY_BBOX

TZ = pytz.timezone("America/Denver")

def _headers():
    return {"Authorization": f"Bearer {MEETUP_TOKEN}"}

def _window_ms():
    now = int(datetime.now(TZ).timestamp() * 1000)
    end = int((datetime.now(TZ) + timedelta(days=LOOKAHEAD_DAYS)).timestamp() * 1000)
    return now, end

def _fetch(center_lat, center_lon, query=None) -> List[Dict]:
    if not MEETUP_TOKEN:
        return []
    params = {
        "lat": center_lat,
        "lon": center_lon,
        "radius": "300",  # miles
        "page": 200,
    }
    if query:
        params["text"] = query
    try:
        r = requests.get("https://api.meetup.com/find/upcoming_events", headers=_headers(), params=params, timeout=25)
        r.raise_for_status()
        return (r.json().get("events") or [])
    except Exception as ex:
        print(f"[Meetup] {ex}")
        return []

class MeetupMTWY(Source):
    def fetch(self) -> List[Dict]:
        if not MEETUP_TOKEN:
            return []
        q = None if EVENT_SCOPE == "ALL" else " ".join(VETERAN_KEYWORDS)
        out: List[Dict] = []
        for (min_lat, min_lon, max_lat, max_lon), label in [(MT_BBOX,"MT"), (WY_BBOX,"WY")]:
            lat = (min_lat + max_lat) / 2
            lon = (min_lon + max_lon) / 2
            for ev in _fetch(lat, lon, q):
                name = ev.get("name")
                start_ms = (ev.get("time") or 0)
                if not name or not start_ms:
                    continue
                city = (ev.get("venue") or {}).get("city")
                state = (ev.get("venue") or {}).get("state")
                url = ev.get("link")
                start_iso = datetime.fromtimestamp(start_ms/1000, TZ).isoformat()
                e = norm_event(
                    title=name,
                    start=start_iso,
                    end=None,
                    city=city,
                    state=state if state in ("MT","WY") else label,
                    address=None,
                    registration_url=url,
                    source="meetup"
                )
                if e:
                    out.append(e)
        return out
