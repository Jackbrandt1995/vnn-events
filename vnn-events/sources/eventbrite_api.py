from __future__ import annotations
from typing import List, Dict
import requests
from datetime import datetime, timedelta
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base import Source, norm_event
from ..config import LOOKAHEAD_DAYS, EVENT_SCOPE, VETERAN_KEYWORDS

class EventbriteMTWY(Source):
    """
    Comprehensive veteran events source with real HTML parsing.
    
    Since Eventbrite discontinued their public search API, this source now
    scrapes real events from veteran organization websites, government calendars,
    and community sources.
    """
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        # Extended veteran keywords for better filtering
        self.veteran_keywords = VETERAN_KEYWORDS + [
            'vso', 'service officer', 'disabled american veterans',
            'veterans of foreign wars', 'american legion auxiliary
