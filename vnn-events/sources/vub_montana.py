"""
Veterans Upward Bound (Montana) iCal scraper.
Set VUB_ICS_URL in config.py or environment; if missing, this source returns [].
"""

from __future__ import annotations
from typing import List, Dict
import requests
from icalendar import Calendar
from dateutil import tz
from datetime import datetime

from .base import Source, norm_event
from config import VUB_ICS_URL

DEFAULT_TZ = tz.gettz("America/Denver")

class VeteransUpwardBoundMT(Source):
    def fetch(self) -> List[Dict]:
        out: List[Dict] = []
        if not VUB_ICS_URL:
            return out
        try:
            r = requests.get(VUB_ICS_URL, timeout=25)
            r.raise_for_status()
            cal = Calendar.from_ical(r.content)
            for comp in cal.walk("VEVENT"):
                start = comp.get("dtstart").dt if comp.get("dtstart") else None
                end = comp.get("dtend").dt if comp.get("dtend") else None
                if isinstance(start, datetime) and start.tzinfo is None:
                    start = start.replace(tzinfo=DEFAULT_TZ)
                if isinstance(end, datetime) and end.tzinfo is None:
                    end = end.replace(tzinfo=DEFAULT_TZ)

                title = str(comp.get("summary", "Veterans Upward Bound"))
                loc = str(comp.get("location", "")) if comp.get("location") else ""
                state = "MT"
                if ", WY" in loc:
                    state = "WY"

                e = norm_event(
                    title=title,
                    start=start.isoformat() if isinstance(start, datetime) else None,
                    end=end.isoformat() if isinstance(end, datetime) else None,
                    city=None,
                    state=state,
                    registration_url=None,
                    source="veterans_upward_bound"
                )
                if e:
                    out.append(e)
        except Exception as ex:
            print(f"[VUB] fetch error: {ex}")
        return out
