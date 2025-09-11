"""
Impact Montana events scraper.
NOTE: CSS selectors may need occasional adjustment as site markup changes.
"""

from __future__ import annotations
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import pytz

from .base import Source, norm_event

TZ = pytz.timezone("America/Denver")
EVENTS_URL = "https://impactmontana.org/events"  # adjust if their URL changes

class ImpactMontana(Source):
    def fetch(self) -> List[Dict]:
        out: List[Dict] = []
        try:
            r = requests.get(EVENTS_URL, timeout=25)
            r.raise_for_status()
            s = BeautifulSoup(r.text, "lxml")
            # Try a few common selectors:
            cards = s.select("[data-event-card], .event, .event-card, .tribe-events-calendar-list__event")
            if not cards:
                # Fallback: try list items with links that look like events
                cards = s.select("a[href*='/event'], article, li")
            for card in cards:
                title_el = card.select_one(".event-title, .tribe-events-calendar-list__event-title, h3, h2, a")
                title = title_el.get_text(strip=True) if title_el else None
                if not title:
                    continue

                time_el = card.select_one("time")
                when = time_el.get("datetime") if time_el and time_el.has_attr("datetime") else (time_el.get_text(strip=True) if time_el else None)
                if not when:
                    # fallback: look for date-like text
                    dt_text = card.get_text(" ", strip=True)
                    when = dt_text

                start = None
                try:
                    start = date_parser.parse(when)
                    if start and not start.tzinfo:
                        start = TZ.localize(start)
                except Exception:
                    continue

                link_el = card.select_one("a[href]")
                href = link_el["href"] if link_el else EVENTS_URL
                if href and href.startswith("//"):
                    href = "https:" + href

                # Try to infer location text
                loc_el = card.select_one(".event-location")
                city, state = None, "MT"
                if loc_el:
                    txt = loc_el.get_text(" ", strip=True)
                    if ", WY" in txt:
                        state = "WY"
                        city = txt.split(", WY")[0].split(",")[-1].strip()
                    elif ", MT" in txt:
                        state = "MT"
                        city = txt.split(", MT")[0].split(",")[-1].strip()

                e = norm_event(
                    title=title,
                    start=start.isoformat() if start else None,
                    end=None,
                    city=city,
                    state=state,
                    registration_url=href,
                    source="impact_montana"
                )
                if e:
                    out.append(e)
        except Exception as ex:
            print(f"[ImpactMontana] fetch error: {ex}")
        return out
