from __future__ import annotations
from typing import List, Dict
from icalendar import Calendar, Event
from dateutil import parser as date_parser
import os


def publish_ics(events: List[Dict], out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    cal = Calendar()
    cal.add('prodid', '-//VNN Events//')
    cal.add('version', '2.0')

    for e in events:
        try:
            start = date_parser.isoparse(e["start"])
        except Exception:
            continue
        ev = Event()
        ev.add("summary", e["title"])
        ev.add("dtstart", start)
        if e.get("end"):
            try:
                ev.add("dtend", date_parser.isoparse(e["end"]))
            except Exception:
                pass
        loc_parts = [e.get("venue_name"), e.get("address"), e.get("city"), e.get("state"), e.get("postal_code")]
        ev.add("location", ", ".join([p for p in loc_parts if p]))
        if e.get("registration_url"):
            ev.add("url", e["registration_url"])
        cal.add_component(ev)

    path = os.path.join(out_dir, "events.ics")
    with open(path, "wb") as f:
        f.write(cal.to_ical())
    print(f"[publish_ics] wrote {path}")
