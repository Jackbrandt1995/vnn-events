from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

class Source(ABC):
    @abstractmethod
    def fetch(self) -> List[Dict]:
        """Return a list of normalized Event dicts."""
        raise NotImplementedError

def norm_event(**kwargs) -> Optional[Dict]:
    e = {
        "title": (kwargs.get("title") or "").strip(),
        "start": kwargs.get("start"),
        "end": kwargs.get("end"),
        "timezone": kwargs.get("timezone", "America/Denver"),
        "venue_name": (kwargs.get("venue_name") or None),
        "address": kwargs.get("address"),
        "city": kwargs.get("city"),
        "state": kwargs.get("state"),
        "postal_code": kwargs.get("postal_code"),
        "country": "US",
        "cost": kwargs.get("cost"),
        "registration_url": kwargs.get("registration_url"),
        "source": kwargs.get("source"),
        "description": kwargs.get("description"),
        "tags": kwargs.get("tags") or ["veterans"],
        "lat": kwargs.get("lat"),
        "lon": kwargs.get("lon"),
    }
    if not e["title"] or not e["start"] or not e["state"]:
        return None
    return e
