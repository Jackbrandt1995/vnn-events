from __future__ import annotations
from typing import List, Dict

from config import REGION_STATES, LOOKAHEAD_DAYS, OUTPUT_DIR, PUBLIC_BASE_URL
from utils.normalize import clean_and_filter
from utils.dedupe import dedupe
from publisher.publish_json import publish_json
from publisher.publish_ics import publish_ics

# Sources
from sources.impact_montana import ImpactMontana
from sources.adaptive_pc import AdaptivePerformanceCenter
from sources.vub_montana import VeteransUpwardBoundMT
from sources.google_events import GoogleEvents
from sources.eventbrite_api import EventbriteMTWY
from sources.meetup_api import MeetupMTWY
from sources.generic_ics import GenericICS


def main():
    sources = [
        ImpactMontana(),
        AdaptivePerformanceCenter(),
                GoogleEvents(),
        EventbriteMTWY(),
        MeetupMTWY(),
        GenericICS(),

        VeteransUpwardBoundMT(),  # uses VUB_ICS_URL if present
    ]

    collected: List[Dict] = []
    for src in sources:
        try:
            evs = src.fetch()
            print(f"[{src.__class__.__name__}] {len(evs)} events")
            collected.extend(evs)
        except Exception as ex:
            print(f"[WARN] {src.__class__.__name__} failed: {ex}")

    filtered = clean_and_filter(collected, LOOKAHEAD_DAYS, REGION_STATES)
    unique = dedupe(filtered)
    print(f"[Summary] collected={len(collected)} filtered={len(filtered)} unique={len(unique)}")

    publish_json(unique, OUTPUT_DIR, PUBLIC_BASE_URL)
    publish_ics(unique, OUTPUT_DIR)

if __name__ == "__main__":
    main()
