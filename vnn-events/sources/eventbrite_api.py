from __future__ import annotations
from typing import List, Dict
import requests
from datetime import datetime, timedelta
import pytz
import time

from .base import Source, norm_event
from ..config import EVENTBRITE_TOKEN, LOOKAHEAD_DAYS, EVENT_SCOPE, VETERAN_KEYWORDS, MT_BBOX, WY_BBOX

TZ = pytz.timezone("America/Denver")
API_BASE = "https://www.eventbriteapi.com/v3"

def _headers():
    """Get headers for Eventbrite API requests."""
    return {
        "Authorization": f"Bearer {EVENTBRITE_TOKEN}",
        "Accept": "application/json",
        "User-Agent": "VNN-Events/1.0"
    }

def _time_window():
    """Get the time window for event searches."""
    now = datetime.now(TZ)
    end = now + timedelta(days=LOOKAHEAD_DAYS)
    return now.isoformat(), end.isoformat()

def _query_for_state(box, q: str | None):
    """Build query parameters for a state bounding box."""
    (min_lat, min_lon, max_lat, max_lon) = box
    params = {
        "expand": "venue",
        "sort_by": "date",
        "location.within": "300mi",
    }
    
    # Use center of bounding box
    params["location.latitude"] = (min_lat + max_lat) / 2
    params["location.longitude"] = (min_lon + max_lon) / 2
    
    if q:
        params["q"] = q
    
    # Add date range
    start, end = _time_window()
    params["start_date.range_start"] = start
    params["start_date.range_end"] = end
    
    return params

def _validate_token():
    """Validate the Eventbrite token."""
    if not EVENTBRITE_TOKEN:
        return False
    
    try:
        resp = requests.get(f"{API_BASE}/users/me/", headers=_headers(), timeout=15)
        return resp.status_code == 200
    except Exception:
        return False

def _events_for(box, label, q):
    """Fetch events for a specific bounding box."""
    if not _validate_token():
        print(f"[Eventbrite {label}] Invalid or missing token")
        return []
    
    all_events = []
    page = 1
    max_pages = 20  # Prevent infinite loops
    
    try:
        while page <= max_pages:
            params = _query_for_state(box, q)
            params["page"] = page
            
            print(f"[Eventbrite {label}] Fetching page {page}")
            
            resp = requests.get(f"{API_BASE}/events/search/", 
                              headers=_headers(), 
                              params=params, 
                              timeout=25)
            
            if resp.status_code != 200:
                if resp.status_code in (401, 403):
                    print(f"[Eventbrite {label}] Auth error: {resp.status_code}")
                    break
                elif resp.status_code == 429:
                    print(f"[Eventbrite {label}] Rate limited, waiting...")
                    time.sleep(5)
                    continue
                else:
                    print(f"[Eventbrite {label}] HTTP {resp.status_code}: {resp.text[:200]}")
                    break
            
            try:
                data = resp.json()
            except Exception as e:
                print(f"[Eventbrite {label}] JSON parse error: {e}")
                break
            
            page_events = data.get("events", []) or []
            all_events.extend(page_events)
            print(f"[Eventbrite {label}] Found {len(page_events)} events on page {page}")
            
            # Check for more pages
            pagination = data.get("pagination", {})
            if not pagination.get("has_more_items", False):
                print(f"[Eventbrite {label}] No more pages")
                break
            
            page += 1
            time.sleep(0.5)  # Rate limiting
        
        print(f"[Eventbrite {label}] Total events: {len(all_events)}")
        return all_events
        
    except Exception as ex:
        print(f"[Eventbrite {label}] Error: {ex}")
        return []

class EventbriteMTWY(Source):
    def fetch(self) -> List[Dict]:
        """Fetch events from Eventbrite for MT and WY."""
        if not EVENTBRITE_TOKEN:
            print("[EventbriteMTWY] No token provided, skipping")
            return []
        
        # Determine search query based on scope
        q = None if EVENT_SCOPE == "ALL" else " OR ".join(VETERAN_KEYWORDS)
        print(f"[EventbriteMTWY] Search query: {q or 'ALL EVENTS'}")
        
        out: List[Dict] = []
        
        # Search both states
        for box, label in [(MT_BBOX, "MT"), (WY_BBOX, "WY")]:
            print(f"[EventbriteMTWY] Searching {label}")
            events = _events_for(box, label, q)
            
            for ev in events:
                try:
                    # Extract event data safely
                    name_obj = ev.get("name", {})
                    name = name_obj.get("text") if isinstance(name_obj, dict) else str(name_obj) if name_obj else None
                    
                    start_obj = ev.get("start", {})
                    start_iso = None
                    if isinstance(start_obj, dict):
                        # Prefer UTC time, fall back to local
                        start_iso = start_obj.get("utc") or start_obj.get("local")
                    
                    end_obj = ev.get("end", {})
                    end_iso = None
                    if isinstance(end_obj, dict):
                        end_iso = end_obj.get("utc") or end_obj.get("local")
                    
                    if not name or not start_iso:
                        continue
                    
                    # Extract venue information
                    venue = ev.get("venue", {}) or {}
                    address = venue.get("address", {}) or {}
                    
                    city = address.get("city")
                    state = address.get("region")
                    
                    # Validate state - ensure it's MT or WY
                    if state not in ("MT", "WY", "Montana", "Wyoming"):
                        # Use the search region as fallback
                        state = label if label in ("MT", "WY") else None
                    
                    # Normalize state abbreviation
                    if state in ("Montana", "montana"):
                        state = "MT"
                    elif state in ("Wyoming", "wyoming"):
                        state = "WY"
                    
                    url = ev.get("url")
                    
                    # Create normalized event
                    e = norm_event(
                        title=name,
                        start=start_iso,
                        end=end_iso,
                        city=city,
                        state=state,
                        venue_name=venue.get("name"),
                        address=address.get("localized_address_display"),
                        registration_url=url,
                        cost="Free" if ev.get("is_free") else None,
                        source="eventbrite"
                    )
                    
                    if e:
                        out.append(e)
                        
                except Exception as ex:
                    print(f"[EventbriteMTWY] Error processing event {ev.get('id', 'unknown')}: {ex}")
                    continue
        
        print(f"[EventbriteMTWY] Final normalized events: {len(out)}")
        return out
