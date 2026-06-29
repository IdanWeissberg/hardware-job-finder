"""
Apple careers fetcher.

Apple exposes a working public JSON search API (verified June 2026):
  POST https://jobs.apple.com/api/v1/search
  body: {"query":"","filters":{"locations":["postLocation-ISR"]},"page":N,
         "locale":"en-us","sort":"newest"}
  -> res.searchResults (20/page), res.totalRecords

Each record has postingTitle, jobSummary (description), positionId, and a
locations[] list. We paginate through all pages. An HTML scrape of the search
page is kept as a fallback in case the API shape changes.
"""
import logging
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from . import _http

log = logging.getLogger(__name__)

SEARCH_API = "https://jobs.apple.com/api/v1/search"
PAGE_SIZE = 20

_STUDENT_MARKERS = (
    "student", "intern", "graduate", "junior", "new grad", "co-op", "co op",
)


def _looks_like_student_role(title: str) -> bool:
    t = title.lower()
    return any(m in t for m in _STUDENT_MARKERS)


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
    jobs, seen = [], set()
    for tag in soup.find_all("a", href=re.compile(r"/details/\d+")):
        href = tag["href"]
        full_url = urljoin("https://jobs.apple.com", href)
        if full_url in seen:
            continue
        seen.add(full_url)
        m = re.search(r"/details/(\d+)", href)
        jobs.append({
            "company": name,
            "job_id": m.group(1) if m else href.rsplit("/", 1)[-1],
            "title": tag.get_text(strip=True) or tag.get("aria-label", ""),
            "location": "Israel",
            "url": full_url,
        })
    return jobs


def fetch_apple(company_cfg: dict[str, Any]) -> list[dict]:
    name = company_cfg["name"]
    location_id = company_cfg.get("location_id", "ISR")

    referer = f"https://jobs.apple.com/en-us/search?location=israel-{location_id}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Referer": referer,
    }

    # Prime the shared session with cookies — the search API returns empty results
    # without the cookies set by first loading the search page.
    try:
        _http.get(referer)
    except Exception:
        pass

    jobs: list[dict] = []
    page = 1
    while True:
        body = {
            "query": "",
            "filters": {"locations": [f"postLocation-{location_id}"]},
            "page": page,
            "locale": "en-us",
            # Apple's API silently returns 0 results if this field is absent.
            "format": {"longDate": "MMMM D, YYYY", "mediumDate": "MMM D, YYYY"},
            "sort": "newest",
        }
        try:
            resp = _http.post(SEARCH_API, json=body, headers=headers)
            data = resp.json()
        except Exception as exc:
            if page == 1:
                log.warning("[%s] Apple API failed: %s — using HTML fallback", name, exc)
                return _scrape_apple_html(name, location_id)
            break

        res = data.get("res", {}) if isinstance(data, dict) else {}
        records = res.get("searchResults", []) if isinstance(res, dict) else []
        if not records:
            break

        for j in records:
            title = j.get("postingTitle", "")
            locs = j.get("locations", []) or []
            loc = ", ".join(
                x for x in (locs[0].get("name"), locs[0].get("countryName")) if x
            ) if locs and isinstance(locs[0], dict) else "Israel"
            pos_id = str(j.get("positionId", j.get("id", "")))
            # jobSummary comes free in the response; use it only for student-titled
            # roles so senior roles don't match on body text (mirrors other fetchers).
            description = j.get("jobSummary", "") if _looks_like_student_role(title) else ""

            jobs.append({
                "company": name,
                "job_id": pos_id,
                "title": title,
                "location": loc,
                "description": description,
                "url": f"https://jobs.apple.com/en-us/details/{pos_id}",
            })

        total = res.get("totalRecords", 0)
        if page * PAGE_SIZE >= total:
            break
        page += 1

    log.info("[%s] Apple → %d job(s)", name, len(jobs))
    return jobs
