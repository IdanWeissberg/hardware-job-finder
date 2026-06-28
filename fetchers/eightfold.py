"""
Eightfold.ai careers API fetcher.
Used by: STMicroelectronics.

Endpoint:
  GET https://{company}.eightfold.ai/api/apply/v2/jobs
  Params: domain, query, location, num_jobs, page, fields
"""
import logging
from typing import Any

from . import _http

log = logging.getLogger(__name__)

PAGE_SIZE = 20


def fetch_eightfold(company_cfg: dict[str, Any]) -> list[dict]:
    name = company_cfg["name"]
    domain = company_cfg["domain"]
    location_filter = company_cfg.get("location_filter", "")

    # Extract company subdomain from domain (e.g. "stmicroelectronics.com" → "stmicroelectronics")
    company_slug = domain.split(".")[0]
    api_url = f"https://{company_slug}.eightfold.ai/api/apply/v2/jobs"

    jobs: list[dict] = []
    page = 0

    while True:
        params = {
            "domain": domain,
            "query": "",
            "location": location_filter,
            "num_jobs": PAGE_SIZE,
            "page": page,
            "fields": "title,id,location,canonicalPositionUrl",
        }
        try:
            resp = _http.get(api_url, params=params)
            data = resp.json()
        except Exception as exc:
            log.warning("[%s] Eightfold request failed page %d: %s", name, page, exc)
            break

        raw_jobs = data.get("positions", [])
        if not raw_jobs:
            break

        for j in raw_jobs:
            loc = j.get("location", "")
            if location_filter and location_filter.lower() not in str(loc).lower():
                continue

            job_id = str(j.get("id", ""))
            job_url = j.get("canonicalPositionUrl", f"https://{company_slug}.eightfold.ai/careers")

            jobs.append({
                "company": name,
                "job_id": job_id,
                "title": j.get("title", ""),
                "location": str(loc),
                "url": job_url,
            })

        total = data.get("count", 0)
        page += 1
        if page * PAGE_SIZE >= total:
            break

    log.info("[%s] Eightfold → %d job(s)", name, len(jobs))
    return jobs
