#!/usr/bin/env python3
"""
Scrape Eventbrite for veteran events in Montana and Wyoming over the next 60 days.
This script uses the Eventbrite API and writes a JSON file with a list of events or an error message.
"""

import json
import os
import sys
import time
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

import requests

API_BASE = "https://www.eventbriteapi.com/v3"
OUT_FILE = "events.json"

DEFAULT_STATES = ["Montana", "Wyoming"]
DEFAULT_QUERY = os.environ.get(
    "EVENTBRITE_QUERY",
    "veteran OR veterans OR military OR service member",
)
DEFAULT_WITHIN = os.environ.get("EVENTBRITE_WITHIN", "500mi")
LOOKAHEAD_DAYS = int(os.environ.get("EVENTBRITE_DAYS", "60"))
PAGE_DELAY_SEC = float(os.environ.get("EVENTBRITE_PAGE_DELAY_SEC", "0.5"))

def save_json(payload: Dict, path: str = OUT_FILE) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def get_token() -> str:
    token = os.environ.get("EVENTBRITE_TOKEN")
    if not token:
        save_json({"generated": False, "error": "EVENTBRITE_TOKEN is not set"})
        sys.exit(2)
    return token

def validate_token(session: requests.Session, headers: Dict[str, str]) -> None:
    url = f"{API_BASE}/users/me/"
    resp = session.get(url, headers=headers, timeout=15)
    if resp.status_code == 200:
        return
    if resp.status_code in (401, 403):
        raise RuntimeError(f"Token invalid or forbidden (HTTP {resp.status_code}): {resp.text[:200]}")
    if resp.status_code == 429:
        raise RuntimeError(f"Rate limited during token validation: {resp.text[:200]}")
    raise RuntimeError(f"Unexpected status {resp.status_code} during token validation: {resp.text[:200]}")

def search_region(session: requests.Session, headers: Dict[str, str], query: str,
                  location_address: str, within: str) -> Tuple[List[Dict], List[str]]:
    params = {
        "q": query,
        "location.address": location_address,
        "location.within": within,
        "expand": "venue",
        "sort_by": "date",
        "page": 1,
    }
    results: List[Dict] = []
    warnings: List[str] = []
    while True:
        resp = session.get(f"{API_BASE}/events/search", headers=headers, params=params, timeout=30)
        if resp.status_code == 404:
            warnings.append(f"404 for {location_address}: {resp.text[:200]}")
            break
        if resp.status_code in (401, 403):
            warnings.append(f"Auth error {resp.status_code} for {location_address}: {resp.text[:200]}")
            break
        if resp.status_code == 429:
            warnings.append(f"Rate limit (429) for {location_address}: {resp.text[:200]}")
            break
        if resp.status_code != 200:
            warnings.append(f"HTTP {resp.status_code} for {location_address}: {resp.text[:200]}")
            break
        try:
            data = resp.json()
        except ValueError:
            warnings.append(f"Invalid JSON response for {location_address}: {resp.text[:200]}")
            break
        results.extend(data.get("events", []) or [])
        if not data.get("pagination", {}).get("has_more_items"):
            break
        params["page"] += 1
        time.sleep(PAGE_DELAY_SEC)
    return results, warnings

def normalize_events(events: List[Dict]) -> List[Dict]:
    normalized: List[Dict] = []
    for e in events:
        venue = e.get("venue") or {}
        address = venue.get("address") or {}
        normalized.append({
            "name": (e.get("name") or {}).get("text"),
            "url": e.get("url"),
            "start": (e.get("start") or {}).get("local"),
            "end": (e.get("end") or {}).get("local"),
            "city": address.get("city"),
            "state": address.get("region"),
            "venue_name": venue.get("name"),
            "address": address.get("localized_address_display"),
        })
    return normalized

def filter_upcoming(events: List[Dict], days: int = LOOKAHEAD_DAYS) -> List[Dict]:
    now = datetime.utcnow()
    cutoff = now + timedelta(days=days)
    filtered: List[Dict] = []
    for e in events:
        start = e.get("start")
        if not start:
            continue
        try:
            dt = datetime.fromisoformat(start)
        except ValueError:
            continue
        if now <= dt <= cutoff:
            filtered.append(e)
    return filtered

def fetch_events(token: str, query: str = DEFAULT_QUERY, states: List[str] = None, within: str = DEFAULT_WITHIN) -> Dict:
    if states is None:
        states = DEFAULT_STATES
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "mt-wy-veteran-scraper/1.0",
    }
    session = requests.Session()
    validate_token(session, headers)
    all_raw: List[Dict] = []
    all_warnings: List[str] = []
    for state in states:
        events, warns = search_region(session, headers, query, state, within)
        all_raw.extend(events)
        all_warnings.extend(warns)
    normalized = normalize_events(all_raw)
    upcoming = filter_upcoming(normalized, LOOKAHEAD_DAYS)
    seen = set()
    unique: List[Dict] = []
    for e in upcoming:
        key = (e.get("name"), e.get("start"))
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return {
        "generated": True,
        "events": unique,
        "count": len(unique),
        "warnings": all_warnings,
    }

def main() -> int:
    token = get_token()
    try:
        payload = fetch_events(token)
        save_json(payload)
        return 0
    except Exception as exc:
        save_json({"generated": False, "error": str(exc)})
        return 1

if __name__ == "__main__":
    sys.exit(main())
