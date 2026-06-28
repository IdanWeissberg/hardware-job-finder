"""
Workable public careers API fetcher.
Used by: Vayyar.

Endpoint:
  GET https://apply.workable.com/api/v3/accounts/{slug}/jobs
  Body (POST): {"query": "", "location": [], "department": [], "worktype": [], "remote": []}
"""
import logging
from typing import Any

from . import _http

log = logging.getLogger(__name__)

PAGE_SIZE = 100


def fetch_workable(company_cfg: dict[str, Any]) -> list[dict]:
    name = company_cfg["name"]
    slug = company_cfg["slug"]

    api_url = f"https://apply.workable.com/api/v3/accounts/{slug}/jobs"
    payload = {
        "query": "",
        "location": [],
        "department": [],
        "worktype": [],
        "remote": [],
    }

    try:
        resp = _http.post(
            api_url,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        data = resp.json()
    except Exception as exc:
        log.warning("[%s] Workable request failed: %s", name, exc)
        return []

    raw_jobs = data.get("results", [])
    jobs: list[dict] = []

    for j in raw_jobs:
        loc = j.get("location", {})
        if isinstance(loc, dict):
            city = loc.get("city", "")
            country = loc.get("country", "")
            loc_str = f"{city}, {country}".strip(", ")
        else:
            loc_str = str(loc)

        shortcode = j.get("shortcode", "")
        job_url = f"https://apply.workable.com/{slug}/j/{shortcode}/" if shortcode else ""

        jobs.append({
            "company": name,
            "job_id": shortcode or str(j.get("id", "")),
            "title": j.get("title", ""),
            "location": loc_str,
            "url": job_url,
        })

    log.info("[%s] Workable → %d job(s)", name, len(jobs))
    return jobs
