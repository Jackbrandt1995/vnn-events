from __future__ import annotations
import json, os
from typing import List, Dict


def publish_json(events: List[Dict], out_dir: str, public_base_url: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    # Sort events by start date, then city, then title
    events_sorted = sorted(events, key=lambda e: (e["start"], e.get("city") or "", e.get("title") or ""))
    path = os.path.join(out_dir, "events.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"generated": True, "events": events_sorted}, f, ensure_ascii=False)
    print(f"[publish_json] wrote {path} | public: {public_base_url}/events.json")
