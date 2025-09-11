"""
Adaptive Performance Center events scraper.
If the site renders via JS, we still try to capture event elements present in the HTML.
"""

from __future__ import annotations
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import pytz

from .base import Source, norm_event

TZ = pytz.timezone("America/Denver")
EVENTS_URL = "https://www.adaptiveperformancecenter.org/events/"

class AdaptivePerformanceCenter(Source):
    def fetch(self) -> List[Dict]:
        out: List[Dict] = []
        try:
            r = requests.get(EVENTS_URL, timeout=25)
            r.raise_for_status()
            s = BeautifulSoup(r.text, "lxml")
            items = s.select(".tribe-events-calendar-list__event, .event, article, li")
            for it in items:
                title_el = it.select_one(".tribe-events-calendar-list__event-title, h3, h2, a")
                title = title_el.get_text(strip=True) if title_el else None
                if not title:
                    continue

                time_el = it.select_one("time")
                when = time_el.get("datetime") if time_el and time_el.has_attr("datetime") else (time_el.get_text(strip=True) if time_el else None)
                start = None
                if when:
                    try:
                        start = date_parser.parse(when)
                        if start and not start.tzinfo:
                            start = TZ.localize(start)
                    except Exception:
                        pass
                if not start:
                    continue

                link_el = it.select_one("a[href]")
                href = link_el["href"] if link_el else EVENTS_URL

                e = norm_event(
                    title=title,
                    start=start.isoformat(),
                    end=None,
                    venue_name=None,
                    city="Billings",
                    state="MT",
                    registration_url=href,
                    source="adaptive_performance_center"
                )
                if e:
                    out.append(e)
        except Exception as ex:
            print(f"[AdaptivePerformanceCenter] fetch error: {ex}")
        return out
