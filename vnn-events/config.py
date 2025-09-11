import os

# Only MT & WY
REGION_STATES = {"MT", "WY"}
# Next two months
LOOKAHEAD_DAYS = 60

# Optional API keys (can be empty)
EVENTBRITE_TOKEN = os.getenv("EVENTBRITE_TOKEN", "")
MEETUP_TOKEN = os.getenv("MEETUP_TOKEN", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

# Where your JSON/ICS will be hosted publicly
# For GitHub Pages, set to: https://jackbrandt1995.github.io/vnn-events
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://jackbrandt1995.github.io/vnn-events")

# Local output dir (this must be 'docs' so Pages serves it)
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "docs")

# If you have a public iCal URL for VUB, set it here or leave None
VUB_ICS_URL = os.getenv("VUB_ICS_URL", None)

# --- Event scope -------------------------------------------------------------
# "VETERAN" = only veteran/military-related events (recommended)
# "ALL"     = every public event in MT/WY (huge volume; likely too noisy)
EVENT_SCOPE = os.getenv("EVENT_SCOPE", "VETERAN").upper()

# Keywords used when EVENT_SCOPE="VETERAN"
VETERAN_KEYWORDS = [
    "veteran", "veterans", "military", "guard", "reserve",
    "usmc", "marine", "army", "navy", "air force", "space force",
    "gold star", "VFW", "American Legion", "DAV", "AMVETS"
]

# Bounding boxes (rough) for statewide queries
# (min_lat, min_lon, max_lat, max_lon)
MT_BBOX = (44.3582, -116.1789, 49.0011, -104.0396)
WY_BBOX = (40.9949, -111.0569, 45.0059, -104.0522)

# Public/community calendar feeds you want to include (optional; add more)
PUBLIC_ICS_URLS = [
    # "https://example.org/calendar.ics",
]

# --- Additional configuration for broader event search ---
# Event scope: "VETERAN" for veteran-specific events or "ALL" for all events
EVENT_SCOPE = os.getenv("EVENT_SCOPE", "VETERAN").upper()

# Keywords to search for when EVENT_SCOPE is "VETERAN"
VETERAN_KEYWORDS = [
    "veteran", "veterans", "military", "guard", "reserve",
    "usmc", "marine", "army", "navy", "air force", "space force",
    "gold star", "VFW", "American Legion", "DAV", "AMVETS"
]

# Bounding boxes (rough) for statewide queries (min_lat, min_lon, max_lat, max_lon)
MT_BBOX = (44.3582, -116.1789, 49.0011, -104.0396)
WY_BBOX = (40.9949, -111.0569, 45.0059, -104.0522)

# Public/community calendar feeds to include (optional; add more)
PUBLIC_ICS_URLS = [
    # Example: "https://example.org/calendar.ics",
]
