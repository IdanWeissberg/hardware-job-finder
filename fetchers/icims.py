"""
iCIMS jobs search fetcher.
Used by: AMD.

iCIMS exposes a JSON search endpoint for public job boards.
Endpoint:
  GET https://{subdomain}.icims.com/jobs/search
  Params: ss=1, searchKeyword=, searchLocation=, format=json
"""
import logging
from typing import Any

from . import _http

log = logging.getLogger(__name__)


def fetch_icims(company_cfg: dict[str, Any]) -> list[dict]:
    name = company_cfg["name"]
    subdomain = company_cfg["subdomain"]
    location_filter = company_cfg.get("location_filter", "")

    base = f"https://{subdomain}.icims.com"
    search_url = f"{base}/jobs/search"

    params = {
        "ss": "1",
        "searchKeyword": "",
        "searchLocation": location_filter,
        "searchRadius": "100",
        "searchZip": "",
        "in_iframe": "1",
        "format": "json",
    }

    try:
        resp = _http.get(search_url, params=params)
        data = resp.json()
    except Exception as exc:
        log.warning("[%s] iCIMS request failed: %s", name, exc)
        return []

    raw_jobs = data if isinstance(data, list) else data.get("jobs", [])
    jobs: list[dict] = []

    for j in raw_jobs:
        loc = j.get("joblocation", j.get("location", ""))
        if location_filter and location_filter.lower() not in str(loc).lower():
            continue

        job_id = str(j.get("id", j.get("jobid", "")))
        job_url = f"{base}/jobs/{job_id}/job" if job_id else base

        jobs.append({
            "company": name,
            "job_id": job_id,
            "title": j.get("jobtitle", j.get("title", "")),
            "location": str(loc),
            "url": job_url,
        })

    log.info("[%s] iCIMS → %d job(s)", name, len(jobs))
    return jobs
