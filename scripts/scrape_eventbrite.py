#!/usr/bin/env python3
import os
import sys
import time
import json
import requests


def get_token():
    token = os.environ.get("EVENTBRITE_TOKEN")
    if not token:
        print("ERROR: EVENTBRITE_TOKEN environment variable not set.", file=sys.stderr)
        sys.exit(1)
    return token


def fetch_events(token, query="veteran", states=None, within="300mi"):
    if states is None:
        states = ["Montana", "Wyoming"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    results = []
    for state in states:
        params = {
            "q": query,
            "location.address": state,
            "location.within": within,
            "expand": "venue",
            "page": 1,
        }
        while True:
            resp = requests.get("https://www.eventbriteapi.com/v3/events/search/", headers=headers, params=params, timeout=30)
            if resp.status_code != 200:
                print(f"ERROR: Eventbrite API returned status {resp.status_code} for state {state} page {params['page']}", file=sys.stderr)
                try:
                    print(resp.json(), file=sys.stderr)
                except Exception:
                    print(resp.text, file=sys.stderr)
                break
            data = resp.json()
            events = data.get("events", [])
            results.extend(events)
            pagination = data.get("pagination", {})
            if not pagination.get("has_more_items"):
                break
            params["page"] += 1
            time.sleep(0.5)
    return results


def save_results(events, path="output/events.json"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)


def main():
    token = get_token()
    events = fetch_events(token=token, query="veteran", states=["Montana","Wyoming"], within="300mi")
    print(f"Fetched {len(events)} events")
    save_results(events)


if __name__ == "__main__":
    main()
