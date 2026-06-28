"""
Microsoft careers fetcher.

Microsoft migrated from GCS Services (gcsservices.careers.microsoft.com) to an
Eightfold-powered platform. As of mid-2026, the GCS endpoint returns 404.

Current approach:
  Eightfold API via Microsoft's careers domain:
  GET https://careers.microsoft.com/api/apply/v2/jobs
  Params: domain=microsoft.com, query, location, num_jobs, page

Fallback: scrape careers.microsoft.com search page HTML.
"""
import json
import logging
import re
from typing import Any

from bs4 import BeautifulSoup

from . import _http

log = logging.getLogger(__name__)

EIGHTFOLD_URL = "https://careers.microsoft.com/api/apply/v2/jobs"
SEARCH_PAGE = "https://careers.microsoft.com/us/en/search-results"
PAGE_SIZE = 20


def _try_eightfold(name: str, location_filter: str) -> list[dict] | None:
    """Try the Eightfold API via Microsoft's own domain."""
    params = {
        "domain": "microsoft.com",
        "query": "",
        "location": location_filter,
        "num_jobs": PAGE_SIZE,
        "page": 0,
    }
    try:
        resp = _http.get(EIGHTFOLD_URL, params=params)
        if "application/json" not in resp.headers.get("content-type", ""):
            return None
        data = resp.json()
        positions = data.get("positions", [])
        if not isinstance(positions, list):
            return None

        jobs = []
        for j in positions:
            job_id = str(j.get("id", ""))
            loc = j.get("location", "")
            job_url = j.get("canonicalPositionUrl", f"https://careers.microsoft.com/global/en/job/{job_id}")
            jobs.append({
                "company": name,
                "job_id": job_id,
                "title": j.get("title", ""),
                "location": str(loc),
                "url": job_url,
            })
        return jobs
    except Exception as exc:
        log.debug("[%s] Eightfold attempt failed: %s", name, exc)
        return None


def _scrape_microsoft(name: str, location_filter: str) -> list[dict]:
    """Fallback: parse HTML search page for job links."""
    url = f"{SEARCH_PAGE}?keywords=hardware+intern&location={location_filter}"
    try:
        resp = _http.get(url)
        html = resp.text
    except Exception as exc:
        log.warning("[%s] Microsoft HTML fallback failed: %s", name, exc)
        return []

    soup = BeautifulSoup(html, "lxml")
    jobs = []
    seen = set()

    for tag in soup.find_all("a", href=re.compile(r"/job/")):
        href = tag["href"]
        full_url = href if href.startswith("http") else f"https://careers.microsoft.com{href}"
        if full_url in seen:
            continue
        seen.add(full_url)

        job_id = re.search(r"/job/(\d+)", href)
        job_id_str = job_id.group(1) if job_id else href.rsplit("/", 1)[-1]
        title = tag.get_text(strip=True)

        jobs.append({
            "company": name,
            "job_id": job_id_str,
            "title": title,
            "location": location_filter,
            "url": full_url,
        })

    return jobs


def fetch_microsoft(company_cfg: dict[str, Any]) -> list[dict]:
    name = company_cfg["name"]
    location_filter = company_cfg.get("location_filter", "Israel")

    jobs = _try_eightfold(name, location_filter)
    if jobs is not None:
        log.info("[%s] Microsoft (Eightfold) → %d job(s)", name, len(jobs))
        return jobs

    # Fall back to HTML scraper
    log.info("[%s] Microsoft: Eightfold API unavailable, using HTML scraper", name)
    jobs = _scrape_microsoft(name, location_filter)
    log.info("[%s] Microsoft (HTML scraper) → %d job(s)", name, len(jobs))
    return jobs
