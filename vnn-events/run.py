# run.py.py
from __future__ import annotations
from typing import List, Dict
import logging
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
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

# Basic logging configuration; allow DEBUG via env var VNN_DEBUG=1
LOG_LEVEL = logging.DEBUG if os.getenv("VNN_DEBUG", "") in ("1", "true", "True") else logging.INFO
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("vnn-events")

def main() -> int:
    """
    Entrypoint for running the VNN events collection pipeline.
    Returns 0 on success, non-zero on failure.
    """
    logger.info("vnn-events: starting run (lookahead=%d days) output=%s", LOOKAHEAD_DAYS, OUTPUT_DIR)

    # Ensure output dir exists
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    except Exception:
        logger.exception("Failed to create OUTPUT_DIR=%r", OUTPUT_DIR)
        return 2

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
        src_name = src.__class__.__name__
        try:
            logger.info("Fetching from source: %s", src_name)
            evs = src.fetch()
            if evs is None:
                evs = []
            logger.info("[%s] %d events", src_name, len(evs))
            collected.extend(evs)
        except Exception:
            logger.exception("[%s] failed while fetching events", src_name)

    logger.info("Raw collected events: %d", len(collected))

    try:
        filtered = clean_and_filter(collected, LOOKAHEAD_DAYS, REGION_STATES)
    except Exception:
        logger.exception("clean_and_filter failed")
        filtered = []

    try:
        unique = dedupe(filtered)
    except Exception:
        logger.exception("dedupe failed")
        unique = filtered or []

    logger.info("[Summary] collected=%d filtered=%d unique=%d", len(collected), len(filtered), len(unique))

    # Publish
    try:
        publish_json(unique, OUTPUT_DIR, PUBLIC_BASE_URL)
        logger.info("publish_json succeeded (output dir: %s)", OUTPUT_DIR)
    except Exception:
        logger.exception("publish_json failed")
        return 3

    try:
        publish_ics(unique, OUTPUT_DIR)
        logger.info("publish_ics succeeded (output dir: %s)", OUTPUT_DIR)
    except Exception:
        logger.exception("publish_ics failed")
        return 4

    logger.info("vnn-events: run completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
