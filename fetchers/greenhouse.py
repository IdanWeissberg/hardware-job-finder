"""
Greenhouse Job Board API fetcher.
Used by: Samsung Semiconductor.

Endpoint:
  GET https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true
"""
import html
import logging
import re
from typing import Any

from . import _http

log = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")


def fetch_greenhouse(company_cfg: dict[str, Any]) -> list[dict]:
    name = company_cfg["name"]
    board = company_cfg["board"]
    location_filter = company_cfg.get("location_filter", "")

    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
    try:
        resp = _http.get(url, params={"content": "true"})
    except Exception as exc:
        log.warning("[%s] Greenhouse request failed: %s", name, exc)
        return []

    data = resp.json()
    raw_jobs = data.get("jobs", [])
    jobs: list[dict] = []

    for j in raw_jobs:
        loc = j.get("location", {}).get("name", "")
        if location_filter and location_filter.lower() not in loc.lower():
            continue

        # content=true returns the full posting (HTML-escaped) at no extra cost;
        # feed it to the relevance filter so titles that don't name the domain
        # can still match on description.
        raw_content = j.get("content", "") or ""
        description = _TAG_RE.sub(" ", html.unescape(raw_content))

        jobs.append({
            "company": name,
            "job_id": str(j.get("id", "")),
            "title": j.get("title", ""),
            "location": loc,
            "description": description,
            "url": j.get("absolute_url", ""),
        })

    log.info("[%s] Greenhouse → %d job(s)", name, len(jobs))
    return jobs
