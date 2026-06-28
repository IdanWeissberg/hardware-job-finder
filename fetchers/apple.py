"""
Apple careers fetcher.

Apple's jobs API has changed over time. Current approach:
  - Primary: POST https://jobs.apple.com/api/role/search
    (requires session authentication as of mid-2025; returns 401 without login)
  - Fallback: scrape https://jobs.apple.com/en-us/search?location=israel-ISR

NOTE: If Apple's API is accessible, it uses location IDs like "postLocation-ISR".
If the primary endpoint returns 401, we fall back to their HTML search page
which is parsed via the generic scraper (limited but resilient).
"""
import logging
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from . import _http

log = logging.getLogger(__name__)

SEARCH_URL = "https://jobs.apple.com/api/role/search"
FALLBACK_URL = "https://jobs.apple.com/en-us/search?location=israel-ISR"


def _scrape_apple_html(name: str, location_id: str) -> list[dict]:
    """Fallback: scrape Apple's jobs HTML page for Israel."""
    search_url = f"https://jobs.apple.com/en-us/search?location=israel-{location_id}"
    try:
        resp = _http.get(search_url, headers={"Referer": "https://jobs.apple.com/"})
        html = resp.text
    except Exception as exc:
        log.warning("[%s] Apple HTML fallback failed: %s", name, exc)
        return []

    soup = BeautifulSoup(html, "lxml")
    jobs = []
    seen = set()

    # Apple's job listing links typically contain '/details/'
    for tag in soup.find_all("a", href=re.compile(r"/details/\d+")):
        href = tag["href"]
        full_url = urljoin("https://jobs.apple.com", href)
        if full_url in seen:
            continue
        seen.add(full_url)

        job_id = re.search(r"/details/(\d+)", href)
        job_id_str = job_id.group(1) if job_id else href.rsplit("/", 1)[-1]
        title = tag.get_text(strip=True) or tag.get("aria-label", "")

        jobs.append({
            "company": name,
            "job_id": job_id_str,
            "title": title,
            "location": "Israel",
            "url": full_url,
        })

    return jobs


def fetch_apple(company_cfg: dict[str, Any]) -> list[dict]:
    name = company_cfg["name"]
    location_id = company_cfg.get("location_id", "ISR")

    jobs: list[dict] = []
    page = 1

    while True:
        payload = {
            "query": "",
            "locale": "en-us",
            "filters": {
                "postingpostLocation": [f"postLocation-{location_id}"],
            },
            "page": page,
        }
        try:
            resp = _http.post(
                SEARCH_URL,
                json=payload,
                headers={"Content-Type": "application/json", "Referer": "https://jobs.apple.com/"},
            )
            if resp.status_code == 401:
                log.info(
                    "[%s] Apple API requires authentication (401) — falling back to HTML scraper. "
                    "This may miss some jobs. Monitor https://jobs.apple.com for API changes.",
                    name
                )
                return _scrape_apple_html(name, location_id)
            data = resp.json()
        except Exception as exc:
            log.warning("[%s] Apple API failed: %s — using HTML fallback", name, exc)
            return _scrape_apple_html(name, location_id)

        search_results = data.get("searchResults", [])
        if not search_results:
            break

        for j in search_results:
            posting_id = j.get("positionId", "")
            job_url = f"https://jobs.apple.com/en-us/details/{posting_id}"
            loc_obj = j.get("location", {})
            loc = loc_obj.get("name", "") if isinstance(loc_obj, dict) else str(loc_obj)

            jobs.append({
                "company": name,
                "job_id": str(posting_id),
                "title": j.get("postingTitle", ""),
                "location": loc,
                "url": job_url,
            })

        total_pages = data.get("totalPages", 1)
        if page >= total_pages:
            break
        page += 1

    log.info("[%s] Apple → %d job(s)", name, len(jobs))
    return jobs
