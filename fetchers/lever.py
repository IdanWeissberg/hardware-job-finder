"""
Lever public postings API fetcher.
Used by: Mobileye.

Endpoint:
  GET https://api.lever.co/v0/postings/{company}?mode=json&limit=100
"""
import logging
from typing import Any

from . import _http

log = logging.getLogger(__name__)


def fetch_lever(company_cfg: dict[str, Any]) -> list[dict]:
    name = company_cfg["name"]
    company = company_cfg["company"]
    location_filter = company_cfg.get("location_filter", "")
    # Some companies use the EU Lever instance (jobs.eu.lever.co)
    eu = company_cfg.get("eu", False)
    base = "https://api.eu.lever.co" if eu else "https://api.lever.co"

    url = f"{base}/v0/postings/{company}"
    try:
        resp = _http.get(url, params={"mode": "json", "limit": 200})
    except Exception as exc:
        log.warning("[%s] Lever request failed: %s", name, exc)
        return []

    raw_jobs = resp.json()
    jobs: list[dict] = []

    for j in raw_jobs:
        categories = j.get("categories", {})
        loc = categories.get("location", "")
        if location_filter and location_filter.lower() not in loc.lower():
            continue

        jobs.append({
            "company": name,
            "job_id": j.get("id", ""),
            "title": j.get("text", ""),
            "location": loc,
            "url": j.get("hostedUrl", ""),
        })

    log.info("[%s] Lever → %d job(s)", name, len(jobs))
    return jobs
