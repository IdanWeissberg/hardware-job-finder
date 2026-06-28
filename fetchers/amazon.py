"""
Amazon.jobs JSON API fetcher.
Used by: Amazon, Annapurna Labs.

Endpoint:
  GET https://www.amazon.jobs/en/search.json
  Params: base_query, location, result_limit, offset, category
"""
import logging
from typing import Any

from . import _http

log = logging.getLogger(__name__)

SEARCH_URL = "https://www.amazon.jobs/en/search.json"
PAGE_SIZE = 10


def fetch_amazon(company_cfg: dict[str, Any]) -> list[dict]:
    name = company_cfg["name"]
    location = company_cfg.get("location", "Israel")
    base_query = company_cfg.get("base_query", "")

    jobs: list[dict] = []
    offset = 0

    while True:
        params = {
            "base_query": base_query,
            "loc_query": location,
            "result_limit": PAGE_SIZE,
            "offset": offset,
            "country": "ISR",
        }
        try:
            resp = _http.get(SEARCH_URL, params=params)
            data = resp.json()
        except Exception as exc:
            log.warning("[%s] Amazon request failed at offset %d: %s", name, offset, exc)
            break

        raw_jobs = data.get("jobs", [])
        if not raw_jobs:
            break

        for j in raw_jobs:
            loc = j.get("location", "")
            job_url = "https://www.amazon.jobs" + j.get("job_path", "")
            jobs.append({
                "company": name,
                "job_id": str(j.get("id_icims", j.get("id", ""))),
                "title": j.get("title", ""),
                "location": loc,
                "url": job_url,
            })

        total = data.get("hits", 0)
        offset += PAGE_SIZE
        if offset >= total:
            break

    log.info("[%s] Amazon → %d job(s)", name, len(jobs))
    return jobs
