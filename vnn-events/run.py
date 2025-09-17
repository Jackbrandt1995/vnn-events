"""
Main entry point for running the VNN events pipeline.

This script orchestrates the fetching of events from all sources, normalizes and
deduplicates them, filters by region and date window, then publishes the
consolidated feeds. To add new sources, simply import the corresponding
class and append an instance to the ``sources`` list.

This implementation includes robust logging, output directory creation, and
per-source error handling so that a single failing scraper does not abort the
entire run. It also supports toggling debug logging via the ``VNN_DEBUG``
environment variable.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import List, Dict
# Ensure local modules are discoverable when run from repository root
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


from config import REGION_STATES, LOOKAHEAD_DAYS, OUTPUT_DIR, PUBLIC_BASE_URL
from utils.normalize import clean_and_filter
from utils.dedupe import dedupe
from publisher.publish_json import publish_json
from publisher.publish_ics import publish_ics

# Import source classes. Extend this list as new scrapers are implemented.
from sources.impact_montana import ImpactMontana
from sources.adaptive_pc import AdaptivePerformanceCenter
from sources.vub_montana import VeteransUpwardBoundMT

# Optional sources may not be present in all deployments. Wrap imports in
# try/except so the pipeline still runs even if additional scrapers are
# unavailable. If you add new scrapers under ``sources/``, import them here.
try:
    from sources.google_events import GoogleEvents  # type: ignore
except Exception:
    GoogleEvents = None  # type: ignore

try:
    from sources.eventbrite_api import EventbriteMTWY  # type: ignore
except Exception:
    EventbriteMTWY = None  # type: ignore

try:
    from sources.meetup_api import MeetupMTWY  # type: ignore
except Exception:
    MeetupMTWY = None  # type: ignore

try:
    from sources.generic_ics import GenericICS  # type: ignore
except Exception:
    GenericICS = None  # type: ignore


# Basic logging configuration; allow DEBUG via VNN_DEBUG=1
LOG_LEVEL = logging.DEBUG if os.getenv("VNN_DEBUG", "").lower() in ("1", "true") else logging.INFO
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("vnn-events")


def main() -> int:
    """Entry point for running the VNN events collection pipeline.

    Returns 0 on success, non-zero on failure. This function should be
    invoked from a __main__ block to allow the exit code to propagate
    properly in calling environments such as cron jobs or CI runners.
    """
    logger.info(
        "vnn-events: starting run (lookahead=%d days) output=%s", LOOKAHEAD_DAYS, OUTPUT_DIR
    )

    # Ensure the output directory exists early on. Without this, subsequent
    # publishes will fail when writing files.
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    except Exception:
        logger.exception("Failed to create OUTPUT_DIR=%r", OUTPUT_DIR)
        return 2

    # Assemble the list of source instances. If an optional scraper failed
    # import above, it will be ``None`` here and thus skipped.
    sources: List[object] = [
        ImpactMontana(),
        AdaptivePerformanceCenter(),
    ]
    if GoogleEvents:
        sources.append(GoogleEvents())
    if EventbriteMTWY:
        sources.append(EventbriteMTWY())
    if MeetupMTWY:
        sources.append(MeetupMTWY())
    if GenericICS:
        sources.append(GenericICS())
    # VeteransUpwardBoundMT is added last so its events can override duplicates
    # if they share the same titles/dates as those from generic calendar feeds.
    sources.append(VeteransUpwardBoundMT())

    collected: List[Dict] = []
    # Fetch events from each source. If a particular source raises an
    # exception during fetch(), it is logged and the run continues. This
    # prevents a single misbehaving scraper from aborting the entire pipeline.
    for src in sources:
        src_name = src.__class__.__name__
        try:
            logger.info("Fetching from source: %s", src_name)
            events = src.fetch()
            if events is None:
                events = []
            logger.info("[%s] %d events", src_name, len(events))
            collected.extend(events)
        except Exception:
            logger.exception("[%s] failed while fetching events", src_name)

    logger.info("Raw collected events: %d", len(collected))

    # Clean and filter events to the allowed states and time window. Any
    # exceptions thrown here will be logged but will not abort the run. The
    # filtered list defaults to an empty list on error.
    try:
        filtered = clean_and_filter(collected, LOOKAHEAD_DAYS, REGION_STATES)
    except Exception:
        logger.exception("clean_and_filter failed")
        filtered = []

    # Deduplicate events using fuzzy matching. If deduplication fails, use
    # the filtered events as-is.
    try:
        unique = dedupe(filtered)
    except Exception:
        logger.exception("dedupe failed")
        unique = filtered or []

    logger.info(
        "[Summary] collected=%d filtered=%d unique=%d", len(collected), len(filtered), len(unique)
    )

    # Publish the JSON feed. On failure, log and return a non-zero code so
    # external schedulers can detect the error. The path returned by
    # publish_json is not used here but could be returned or logged.
    try:
        publish_json(unique, OUTPUT_DIR, PUBLIC_BASE_URL)
        logger.info("publish_json succeeded (output dir: %s)", OUTPUT_DIR)
    except Exception:
        logger.exception("publish_json failed")
        return 3

    # Publish the iCal feed. This is optional; on failure the run returns
    # a distinct exit code.
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
