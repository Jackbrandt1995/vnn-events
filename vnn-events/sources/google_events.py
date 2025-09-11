from __future__ import annotations
from typing import List, Dict
import os, time, requests
from datetime import datetime, timedelta
import pytz

from .base import Source, norm_event
from ..config import SERPAPI_KEY, LOOKAHEAD_DAYS, EVENT_SCOPE, VETERAN_KEYWORDS

TZ = pytz.timezone("America/Denver")

def _window():
    now = datetime.now(TZ)
    end = now + timedelta(days=LOOKAHEAD_DAYS)
    return now.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

def _query_for(region_name: str) -> str:
    if EVENT_SCOPE == "ALL":
        return f"events in {region_name}"
    # veteran-focused
    kws = " OR ".join([f'"{k}"' for k in VETERAN_KEYWORDS])
    return f"({kws}) events in {region_name}"

def _search(region_name: str) -> List[Dict]:
    if not SERPAPI_KEY:
        return []
    start, end = _window()
    params = {
        "engine": "google_events",
        "q": _query_for(region_name),
        "hl": "en",
        "api_key": SERPAPI_KEY,
        "tbs": f"cdr:1,cd_min:{start},cd_max:{end}",
    }
    try:
        r = requests.get("https://serpapi.com/search.json", params=params, timeout=30)
        r.raise_for_status()
        return r.json().get("events_results", []) or []
    except Exception as ex:
        print(f"[SerpAPI {region_name}] {ex}")
        return []

class GoogleEvents(Source):
    def fetch(self) -> List[Dict]:
        out: List[Dict] = []
        for region in ["Montana", "Wyoming"]:
            results = _search(region)
            time.sleep(1.0)
            for item in results:
                title = item.get("title")
                when = item.get("date", {}).get("start_date") or item.get("date", {}).get("when")
                if not when:
                    when = item.get("date", {}).get("start_time")
                if not when:
                    continue
                try:
                    if len(when) >= 10 and when[4] == "-" and when[7] == "-":
                        start_iso = when if len(when) > 10 else (when + "T00:00:00-06:00")
                    else:
                        continue
                except Exception:
                    continue
                addr = item.get("address")
                city, state = None, None
                if isinstance(addr, list):
                    joined = ", ".join(addr)
                else:
                    joined = addr or ""
                if ", MT" in joined:
                    state = "MT"
                    city = joined.split(", MT")[0].split(",")[-1].strip()
                elif ", WY" in joined:
                    state = "WY"
                    city = joined.split(", WY")[0].split(",")[-1].strip()
                url = None
                if item.get("link"):
                    url = item["link"]
                elif item.get("ticket_info") and isinstance(item["ticket_info"], list):
                    url = item["ticket_info"][0].get("link")
                e = norm_event(
                    title=title,
                    start=start_iso,
                    end=None,
                    city=city,
                    state=state or ("MT" if "Montana" in joined else "WY" if "Wyoming" in joined else None),
                    address=joined or None,
                    registration_url=url,
                    source="google_events"
                )
                if e:
                    out.append(e)
        return out
