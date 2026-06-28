"""
SmartRecruiters public postings API fetcher.
Used by: Western Digital.

Endpoint:
  GET https://api.smartrecruiters.com/v1/companies/{company_id}/postings
  No auth required for public postings.
"""
import logging
from typing import Any

from . import _http

log = logging.getLogger(__name__)

API_BASE = "https://api.smartrecruiters.com/v1/companies"
PAGE_SIZE = 100


def fetch_smartrecruiters(company_cfg: dict[str, Any]) -> list[dict]:
    name = company_cfg["name"]
    company_id = company_cfg["company_id"]
    location_filter = company_cfg.get("location_filter", "")

    url = f"{API_BASE}/{company_id}/postings"
    jobs: list[dict] = []
    offset = 0

    while True:
        params = {"limit": PAGE_SIZE, "offset": offset}
        try:
            resp = _http.get(url, params=params)
            data = resp.json()
        except Exception as exc:
            log.warning("[%s] SmartRecruiters request failed: %s", name, exc)
            break

        content = data.get("content", [])
        if not content:
            break

        for j in content:
            loc_obj = j.get("location", {})
            city = loc_obj.get("city", "")
            country = loc_obj.get("country", "")
            loc = f"{city}, {country}".strip(", ")

            if location_filter and location_filter.lower() not in loc.lower():
                continue

            ref = j.get("ref", "")
            job_url = f"https://careers.smartrecruiters.com/{company_id}/{ref}" if ref else ""

            jobs.append({
                "company": name,
                "job_id": str(j.get("id", ref)),
                "title": j.get("name", ""),
                "location": loc,
                "url": job_url,
            })

        total = data.get("totalFound", 0)
        offset += PAGE_SIZE
        if offset >= total:
            break

    log.info("[%s] SmartRecruiters → %d job(s)", name, len(jobs))
    return jobs
