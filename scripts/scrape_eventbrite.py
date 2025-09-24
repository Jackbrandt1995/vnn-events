#!/usr/bin/env python3
"""
Fixed Eventbrite scraper that matches the GitHub workflow expectations.
This file should be saved as scripts/scrape_eventbrite.py
"""

import os
import sys
import time
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

API_BASE = "https://www.eventbriteapi.com/v3"
DEFAULT_STATES = ["Montana", "Wyoming"]
DEFAULT_QUERY = "veteran OR veterans OR military OR service member"
DEFAULT_WITHIN = "500mi"
LOOKAHEAD_DAYS = 60
OUTPUT_DIR = "output"


def save_results(payload: Dict, filename: str = "events.json") -> None:
    """Save results to the output directory expected by the GitHub workflow."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Results saved to {filepath}")


def validate_token(token: str) -> bool:
    """Validate the Eventbrite API token."""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    try:
        resp = requests.get(f"{API_BASE}/users/me/", headers=headers, timeout=15)
        if resp.status_code == 200:
            print("Token validation successful")
            return True
        else:
            print(f"Token validation failed: {resp.status_code} - {resp.text[:256]}")
            return False
    except requests.RequestException as exc:
        print(f"Token validation request error: {exc}")
        return False


def search_region(
    session: requests.Session,
    headers: Dict[str, str],
    query: str,
    location_address: str,
    within: str,
) -> Tuple[List[Dict], List[str]]:
    """Search for events in a specific region."""
    # Add date range to ensure we get upcoming events
    start_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    end_date = (datetime.utcnow() + timedelta(days=LOOKAHEAD_DAYS)).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    params = {
        "q": query,
        "location.address": location_address,
        "location.within": within,
        "start_date.range_start": start_date,
        "start_date.range_end": end_date,
        "expand": "venue",
        "sort_by": "date",
        "page": 1,
    }
    
    print(f"Searching {location_address} for: {query}")
    
    results: List[Dict] = []
    warnings: List[str] = []
    max_pages = 20  # Prevent infinite loops
    
    for page_num in range(1, max_pages + 1):
        params["page"] = page_num
        
        try:
            resp = session.get(f"{API_BASE}/events/search/", headers=headers, params=params, timeout=30)
            print(f"Page {page_num}: Status {resp.status_code}")
            
            if resp.status_code == 404:
                warnings.append(f"404_not_found:{location_address}")
                break
            elif resp.status_code in (401, 403):
                warnings.append(f"auth_error:{location_address}:{resp.status_code}")
                break
            elif resp.status_code == 429:
                warnings.append(f"rate_limited:{location_address}")
                time.sleep(5)  # Wait longer for rate limits
                break
            elif resp.status_code != 200:
                warnings.append(f"http_error:{location_address}:{resp.status_code}")
                break
                
            try:
                data = resp.json()
            except ValueError:
                warnings.append(f"invalid_json:{location_address}")
                break
            
            page_events = data.get("events", [])
            results.extend(page_events)
            print(f"  Found {len(page_events)} events on page {page_num}")
            
            # Check if there are more pages
            pagination = data.get("pagination", {})
            if not pagination.get("has_more_items", False):
                print(f"  No more pages for {location_address}")
                break
                
            time.sleep(0.5)  # Rate limiting delay
            
        except requests.RequestException as exc:
            warnings.append(f"request_error:{location_address}:{exc}")
            break
    
    print(f"Total events found for {location_address}: {len(results)}")
    return results, warnings


def normalize_event(event_data: Dict) -> Dict:
    """Normalize Eventbrite event data to our standard format."""
    try:
        # Handle nested name structure
        name_obj = event_data.get("name", {})
        title = name_obj.get("text") if isinstance(name_obj, dict) else str(name_obj) if name_obj else "Unnamed Event"
        
        # Handle nested start/end structure  
        start_obj = event_data.get("start", {})
        start = start_obj.get("local") if isinstance(start_obj, dict) else None
        
        end_obj = event_data.get("end", {})
        end = end_obj.get("local") if isinstance(end_obj, dict) else None
        
        # Handle venue information
        venue = event_data.get("venue", {}) or {}
        address = venue.get("address", {}) or {}
        
        return {
            "id": event_data.get("id"),
            "title": title,
            "start": start,
            "end": end,
            "url": event_data.get("url"),
            "is_free": event_data.get("is_free"),
            "status": event_data.get("status"),
            "city": address.get("city"),
            "state": address.get("region"),
            "venue_name": venue.get("name"),
            "address": address.get("localized_address_display"),
            "source": "eventbrite"
        }
    except Exception as ex:
        print(f"Error normalizing event {event_data.get('id', 'unknown')}: {ex}")
        return {}


def filter_upcoming_events(events: List[Dict]) -> List[Dict]:
    """Filter events to only include those in the next LOOKAHEAD_DAYS."""
    now = datetime.utcnow()
    cutoff = now + timedelta(days=LOOKAHEAD_DAYS)
    filtered = []
    
    for event in events:
        start_str = event.get("start")
        if not start_str:
            continue
            
        try:
            # Parse the datetime string
            if start_str.endswith('Z'):
                start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            else:
                start_dt = datetime.fromisoformat(start_str)
            
            # Remove timezone info for comparison with naive UTC datetime
            if start_dt.tzinfo is not None:
                start_dt = start_dt.replace(tzinfo=None)
                
            if now <= start_dt <= cutoff:
                filtered.append(event)
                
        except (ValueError, AttributeError) as ex:
            print(f"Error parsing datetime '{start_str}': {ex}")
            continue
    
    return filtered


def deduplicate_events(events: List[Dict]) -> List[Dict]:
    """Remove duplicate events based on title and start time."""
    seen = set()
    unique = []
    
    for event in events:
        key = (event.get("title", ""), event.get("start", ""))
        if key not in seen:
            seen.add(key)
            unique.append(event)
        else:
            print(f"Skipping duplicate: {event.get('title', 'Unknown')}")
    
    return unique


def fetch_events(token: str, query: str = DEFAULT_QUERY, states: List[str] = None, within: str = DEFAULT_WITHIN) -> Dict:
    """Main function to fetch events from Eventbrite API."""
    if states is None:
        states = DEFAULT_STATES
    
    # Validate token first
    if not validate_token(token):
        raise RuntimeError("Invalid or expired Eventbrite token")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "VNN-Events-Scraper/1.0"
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    all_events = []
    all_warnings = []
    
    # Fetch events from each state
    for state in states:
        print(f"\n--- Fetching events for {state} ---")
        events, warnings = search_region(session, headers, query, state, within)
        all_events.extend(events)
        all_warnings.extend(warnings)
    
    print(f"\n--- Processing {len(all_events)} raw events ---")
    
    # Normalize events
    normalized = []
    for event in all_events:
        norm_event = normalize_event(event)
        if norm_event and norm_event.get("title") and norm_event.get("start"):
            normalized.append(norm_event)
    
    print(f"Normalized: {len(normalized)} events")
    
    # Filter to upcoming events only
    upcoming = filter_upcoming_events(normalized)
    print(f"Upcoming: {len(upcoming)} events")
    
    # Deduplicate
    unique = deduplicate_events(upcoming)
    print(f"Unique: {len(unique)} events")
    
    return {
        "generated": True,
        "source": "eventbrite",
        "query": query,
        "regions": states,
        "within": within,
        "count": len(unique),
        "events": unique,
        "warnings": all_warnings,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


def main():
    """Main entry point."""
    print("=== Eventbrite Events Scraper ===")
    
    token = os.environ.get("EVENTBRITE_TOKEN")
    if not token:
        error_msg = "EVENTBRITE_TOKEN environment variable not set"
        print(f"ERROR: {error_msg}")
        save_results({"generated": False, "error": error_msg})
        sys.exit(2)
    
    try:
        # Fetch events
        result = fetch_events(token.strip())
        
        # Save results
        save_results(result)
        
        print(f"\n=== SUCCESS ===")
        print(f"Found {result['count']} events")
        
        if result.get("warnings"):
            print(f"Warnings: {len(result['warnings'])}")
            for warning in result["warnings"]:
                print(f"  - {warning}")
        
        return 0
        
    except Exception as exc:
        error_msg = f"Scraper failed: {exc}"
        print(f"ERROR: {error_msg}")
        save_results({"generated": False, "error": error_msg})
        return 1


if __name__ == "__main__":
    sys.exit(main())
