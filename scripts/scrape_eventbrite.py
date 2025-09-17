#!/usr/bin/env python3
import os
import sys
import time
import json
import requests

API_BASE = "https://www.eventbriteapi.com/v3"

def fetch_events(token, query="veteran OR veterans", states=None, within="500mi"):
    if states is None:
        states = ["Montana", "Wyoming"]
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    all_events = []
    for state in states:
        params = {
            "q": query,
            "location.address": state,
            "location.within": within,
            "expand": "venue",
            "page": 1,
        }
        session = requests.Session()
        while True:
            resp = session.get(f"{API_BASE}/events/search", headers=headers, params=params, timeout=30)
            if resp.status_code == 404:
                # Path not found; write a warning but continue with other states
                print(f"[WARN] API path not found for state {state}")
                break
            if resp.status_code != 200:
                raise RuntimeError(f"Eventbrite API returned status {resp.status_code}: {resp.text}")
            data = resp.json()
            all_events.extend(data.get("events", []) or [])
            if not data.get("pagination", {}).get("has_more_items"):
                break
            params["page"] += 1
            time.sleep(0.5)
    return all_events

def main():
    token = os.environ.get("EVENTBRITE_TOKEN")
    if not token:
        save_results({"generated": False, "error": "EVENTBRITE_TOKEN environment variable not set"})
        sys.exit(2)
    try:
        events = fetch_events(token)
        save_results({"generated": True, "events": events})
    except Exception as exc:
        save_results({"generated": False, "error": str(exc)})
        sys.exit(1)
