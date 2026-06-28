"""
Google Careers fetcher.

Google's careers.google.com is a React SPA; it uses an internal API
that can be queried directly.

Endpoint (reverse-engineered):
  GET https://careers.google.com/api/jobs/search/
  Params: q, location, distance, hl, page_size, page
"""
import logging
from typing import Any

from . import _http

log = logging.getLogger(__name__)

SEARCH_URL = "https://careers.google.com/api/jobs/search/"
PAGE_SIZE = 20


def fetch_google(company_cfg: dict[str, Any]) -> list[dict]:
    name = company_cfg["name"]
    location = company_cfg.get("location", "Israel")

    jobs: list[dict] = []
    page = 1

    while True:
        params = {
            "q": "",
            "location": location,
            "distance": "50",
            "hl": "en_US",
            "page_size": PAGE_SIZE,
            "page": page,
            "employment_type": "INTERN,FULL_TIME,PART_TIME",
        }
        try:
            resp = _http.get(SEARCH_URL, params=params)
            data = resp.json()
        except Exception as exc:
            log.warning("[%s] Google Careers request failed page %d: %s", name, page, exc)
            break

        raw_jobs = data.get("jobs", [])
        if not raw_jobs:
            break

        for j in raw_jobs:
            locations = j.get("locations", [])
            loc = ", ".join(locations) if locations else ""
            job_id = j.get("id", "")
            # Google job URLs are constructed from the job ID
            job_url = f"https://careers.google.com/jobs/results/{job_id}"

            jobs.append({
                "company": name,
                "job_id": str(job_id),
                "title": j.get("title", ""),
                "location": loc,
                "url": job_url,
            })

        count = data.get("count", 0)
        if page * PAGE_SIZE >= count:
            break
        page += 1

    log.info("[%s] Google Careers → %d job(s)", name, len(jobs))
    return jobs
