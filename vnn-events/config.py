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
