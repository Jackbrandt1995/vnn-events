from __future__ import annotations
from typing import List, Dict
import requests
from icalendar import Calendar
from dateutil import parser as date_parser
from dateutil import tz
from datetime import datetime
from .base import Source, norm_event
from ..config import PUBLIC_ICS_URLS

DEFAULT_TZ = tz.gettz("America/Denver")

class GenericICS(Source):
    def fetch(self) -> List[Dict]:
        out: List[Dict] = []
        for url in PUBLIC_ICS_URLS:
            try:
                r = requests.get(url, timeout=25)
                r.raise_for_status()
                cal = Calendar.from_ical(r.content)
                for comp in cal.walk("VEVENT"):
                    start = comp.get("dtstart").dt if comp.get("dtstart") else None
                    end = comp.get("dtend").dt if comp.get("dtend") else None
                    if isinstance(start, datetime) and start.tzinfo is None:
                        start = start.replace(tzinfo=DEFAULT_TZ)
                    if isinstance(end, datetime) and end.tzinfo is None:
                        end = end.replace(tzinfo=DEFAULT_TZ)
                    title = str(comp.get("summary", ""))
                    loc = str(comp.get("location", "")) if comp.get("location") else ""
                    state = "MT" if " MT" in loc or "Montana" in loc else ("WY" if " WY" in loc or "Wyoming" in loc else None)
                    e = norm_event(
                        title=title,
                        start=start.isoformat() if isinstance(start, datetime) else None,
                        end=end.isoformat() if isinstance(end, datetime) else None,
                        city=None,
                        state=state,
                        address=loc or None,
                        registration_url=None,
                        source="ics"
                    )
                    if e:
                        out.append(e)
            except Exception as ex:
                print(f"[GenericICS] {url}: {ex}")
        return out
