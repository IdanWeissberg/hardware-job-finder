"""
Generic HTML scraper — fallback for companies without a clean JSON API.
Marked as `fragile: true` in config.yaml.

Used by: Texas Instruments, Synopsys, Infineon, Tower Semiconductor,
         Ceva, Valens, Next Silicon, Speedata, Lightbits, Newsight.

Strategy: fetch the page, parse with BeautifulSoup, look for common
<a> tag patterns that contain job titles and links.
"""
import hashlib
import logging
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from . import _http

log = logging.getLogger(__name__)

# Patterns that typically appear in job listing links
JOB_LINK_PATTERNS = [
    r"/job[s]?/",
    r"/career[s]?/",
    r"/opening[s]?/",
    r"/position[s]?/",
    r"/work-with-us/",
    r"apply",
]

# Text to exclude (navigation, generic buttons)
EXCLUDE_TEXT = {
    "apply now", "apply", "learn more", "read more", "view all",
    "all jobs", "back to jobs", "home", "careers", "jobs",
    "submit", "search", "", "see all positions",
}


def _looks_like_job_link(href: str, text: str) -> bool:
    text_lower = text.strip().lower()
    if text_lower in EXCLUDE_TEXT or len(text_lower) < 5:
        return False
    if not href or href.startswith("#") or href.startswith("mailto:"):
        return False
    return any(re.search(p, href, re.IGNORECASE) for p in JOB_LINK_PATTERNS)


def _stable_id(company: str, url: str, title: str) -> str:
    raw = f"{company}|{url}|{title}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def fetch_scraper(company_cfg: dict[str, Any]) -> list[dict]:
    name = company_cfg["name"]
    careers_url = company_cfg["careers_url"]
    fragile = company_cfg.get("fragile", False)

    if fragile:
        log.debug("[%s] Using HTML scraper (fragile — may break if site changes)", name)

    try:
        resp = _http.get(careers_url)
        html = resp.text
    except Exception as exc:
        log.warning("[%s] Scraper fetch failed: %s", name, exc)
        return []

    soup = BeautifulSoup(html, "lxml")
    base_domain = f"{urlparse(careers_url).scheme}://{urlparse(careers_url).netloc}"

    # 1. Try to extract structured JSON-LD first (most reliable when present)
    jobs_from_jsonld = _extract_jsonld(soup, name, base_domain)
    if jobs_from_jsonld:
        log.info("[%s] Scraper (JSON-LD) → %d job(s)", name, len(jobs_from_jsonld))
        return jobs_from_jsonld

    # 2. Fall back to link heuristic
    seen_urls: set[str] = set()
    jobs: list[dict] = []

    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        text = tag.get_text(separator=" ", strip=True)

        if not _looks_like_job_link(href, text):
            continue

        full_url = urljoin(base_domain, href) if not href.startswith("http") else href
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        # Try to find a location nearby
        parent = tag.find_parent(["li", "div", "tr", "article"])
        loc_text = ""
        if parent:
            loc_candidates = parent.find_all(
                string=re.compile(r"israel|haifa|tel aviv|raanana|petah tikva|herzliya|jerusalem|beer sheva|rehovot", re.I)
            )
            if loc_candidates:
                loc_text = loc_candidates[0].strip()

        jobs.append({
            "company": name,
            "job_id": _stable_id(name, full_url, text),
            "title": text,
            "location": loc_text or "Israel",
            "url": full_url,
        })

    log.info("[%s] Scraper (HTML links) → %d job(s) from %s", name, len(jobs), careers_url)
    return jobs


def _extract_jsonld(soup: BeautifulSoup, name: str, base_domain: str) -> list[dict]:
    """Extract JobPosting items from JSON-LD structured data."""
    import json

    jobs = []
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            if item.get("@type") != "JobPosting":
                continue

            loc_obj = item.get("jobLocation", {})
            if isinstance(loc_obj, dict):
                addr = loc_obj.get("address", {})
                loc = addr.get("addressLocality", "") + ", " + addr.get("addressCountry", "")
                loc = loc.strip(", ")
            else:
                loc = str(loc_obj)

            url = item.get("url", base_domain)
            title = item.get("title", "")
            job_id = _stable_id(name, url, title)

            jobs.append({
                "company": name,
                "job_id": job_id,
                "title": title,
                "location": loc,
                "url": url,
            })

    return jobs
