from __future__ import annotations
from typing import List, Dict
from rapidfuzz import fuzz


def _key(e: Dict) -> str:
    title = (e.get("title") or "").lower()
    start = (e.get("start") or "")[:10]
    city = e.get("city") or ""
    state = e.get("state") or ""
    return title + "|" + start + "|" + city + "|" + state


def _choose_better(a: Dict, b: Dict) -> Dict:
    score_a = (len(a.get("description") or "") > len(b.get("description") or "")) + (1 if a.get("registration_url") else 0)
    return a if score_a >= 1 else b


def dedupe(events: List[Dict]) -> List[Dict]:
    seen: Dict[str, Dict] = {}
    out: List[Dict] = []
    for e in events:
        k = _key(e)
        if k in seen:
            other = seen[k]
            score = fuzz.token_set_ratio(e["title"], other["title"])
            if score >= 90:
                better = _choose_better(e, other)
                if better is other:
                    continue
                else:
                    idx = out.index(other)
                    out[idx] = better
                    seen[k] = better
                    continue
        seen[k] = e
        out.append(e)
    return out
