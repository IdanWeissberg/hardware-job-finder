"""
Workday CXS API fetcher.
Used by: Intel, Qualcomm, NVIDIA, Marvell, Broadcom, Analog Devices,
         Cadence, Applied Materials, KLA, Cisco (and others).

Endpoint pattern:
  POST https://{company}.wd{N}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
"""
import logging
from typing import Any

from . import _http

log = logging.getLogger(__name__)

PAGE_SIZE = 20


def _location_matches(location_text: str, filter_str: str) -> bool:
    if not filter_str:
        return True
    return filter_str.lower() in location_text.lower()


def fetch_workday(company_cfg: dict[str, Any]) -> list[dict]:
    name = company_cfg["name"]
    url = company_cfg["workday_url"]
    base_url = company_cfg["base_url"]
    location_filter = company_cfg.get("location_filter", "")
    search_text = company_cfg.get("search_text", "")

    jobs: list[dict] = []
    offset = 0

    while True:
        payload = {
            "appliedFacets": {},
            "limit": PAGE_SIZE,
            "offset": offset,
            "searchText": search_text,
        }
        try:
            resp = _http.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        except Exception as exc:
            log.warning("[%s] Workday request failed at offset %d: %s", name, offset, exc)
            break

        data = resp.json()
        postings = data.get("jobPostings", [])
        if not postings:
            break

        for p in postings:
            loc = p.get("locationsText", "")
            if location_filter and not _location_matches(loc, location_filter):
                continue

            external_path = p.get("externalPath", "")
            job_id = (
                p.get("bulletFields", [None])[0]
                or external_path.rsplit("/", 1)[-1]
                or p.get("jobPostingId", "")
            )
            job_url = f"{base_url}{external_path}" if external_path else base_url

            jobs.append({
                "company": name,
                "job_id": str(job_id),
                "title": p.get("title", ""),
                "location": loc,
                "url": job_url,
            })

        total = data.get("total", 0)
        offset += PAGE_SIZE
        if offset >= total:
            break

    log.info("[%s] Workday → %d job(s) matching location filter", name, len(jobs))
    return jobs
