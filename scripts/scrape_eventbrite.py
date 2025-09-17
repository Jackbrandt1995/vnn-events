#!/usr/bin/env python3
import os
import sys
import time
import json
import requests

API_BASE = "https://www.eventbriteapi.com/v3"

def save_results(payload: dict, path: str = "output/events.json") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def get_token() -> str:
    token = os.environ.get("EVENTBRITE_TOKEN")
    return token

def fetch_events(token: str, states=None, within="500mi", query="veteran OR veterans") -> list:
    if states is None:
        states = ["Montana", "Wyoming"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    results = []
    session = requests.Session()
    for state in states:
        params = {
            "q": query,
            "location.address": state,
            "location.within": within,
            "expand": "venue",
            "page": 1,
        }
        while True:
            resp = session.get(f"{API_BASE}/events/search/", headers=headers, params=params, timeout=30)
            if resp.status_code != 200:
                raise RuntimeError(f"Eventbrite API returned status {resp.status_code}: {resp.text}")
            data = resp.json()
            events = data.get("events", []) or []
            results.extend(events)
            pagination = data.get("pagination", {})
            if not pagination.get("has_more_items"):
                break
            params["page"] += 1
            time.sleep(0.5)
    return results

def main() -> None:
    token = get_token()
    if not token:
        msg = "EVENTBRITE_TOKEN environment variable not set."
        print(msg, file=sys.stderr)
        save_results({"generated": False, "error": msg})
        sys.exit(1)
    try:
        events = fetch_events(token)
        save_results({"generated": True, "events": events})
        print(f"Fetched {len(events)} events")
    except Exception as exc:
        err_msg = str(exc)
        print(err_msg, file=sys.stderr)
        save_results({"generated": False, "error": err_msg})
        sys.exit(2)

if __name__ == "__main__":
    main()
