from __future__ import annotations
from typing import List, Dict
import requests
from datetime import datetime, timedelta
import pytz

from .base import Source, norm_event
from ..config import EVENTBRITE_TOKEN, LOOKAHEAD_DAYS, EVENT_SCOPE, VETERAN_KEYWORDS, MT_BBOX, WY_BBOX

TZ = pytz.timezone("America/Denver")

def _headers():
    return {"Authorization": f"Bearer {EVENTBRITE_TOKEN}"}

def _time_window():
    now = datetime.now(TZ)
    end = now + timedelta(days=LOOKAHEAD_DAYS)
    return now.isoformat(), end.isoformat()

def _query_for_state(box, q: str | None):
    (min_lat, min_lon, max_lat, max_lon) = box
    params = {
        "expand": "venue",
        "sort_by": "date",
        "location.within": "300mi",
    }
    params["location.latitude"] = (min_lat + max_lat) / 2
    params["location.longitude"] = (min_lon + max_lon) / 2
    if q:
        params["q"] = q
    start, end = _time_window()
    params["start_date.range_start"] = start
    params["start_date.range_end"] = end
    return params

def _events_for(box, label, q):
    try:
        resp = requests.get("https://www.eventbriteapi.com/v3/events/search/",
                            headers=_headers(), params=_query_for_state(box, q), timeout=25)
        resp.raise_for_status()
        data = resp.json()
        return data.get("events", []) or []
    except Exception as ex:
        print(f"[Eventbrite {label}] {ex}")
        return []

class EventbriteMTWY(Source):
    def fetch(self) -> List[Dict]:
        if not EVENTBRITE_TOKEN:
            return []
        q = None if EVENT_SCOPE == "ALL" else " OR ".join(VETERAN_KEYWORDS)
        out: List[Dict] = []
        for box, label in [(MT_BBOX, "MT"), (WY_BBOX, "WY")]:
            for ev in _events_for(box, label, q):
                name = ev.get("name", {}).get("text")
                start_iso = (ev.get("start") or {}).get("utc")
                if not name or not start_iso:
                    continue
                venue = (ev.get("venue") or {})
                city = venue.get("address", {}).get("city")
                state = venue.get("address", {}).get("region")
                url = ev.get("url")
                e = norm_event(
                    title=name,
                    start=start_iso,
                    end=(ev.get("end") or {}).get("utc"),
                    city=city,
                    state=(state if state in ("MT","WY") else (label if state in (None, "") else None)),
                    address=venue.get("address", {}).get("localized_address_display"),
                    registration_url=url,
                    source="eventbrite"
                )
                if e:
                    out.append(e)
        return out
