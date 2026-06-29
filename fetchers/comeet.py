"""
Comeet careers fetcher (rebranded as Spark Hire Recruit).
Used by: Nova, Camtek, Hailo, NeuReality, Pliops, Wiliot, Autotalks,
         Innoviz, Proteantecs, DriveNets, SolarEdge.

Strategy:
  1. If uid + token are provided in config → use the official careers API.
  2. Otherwise → scrape the public careers page at comeet.com/jobs/{slug}/
     and parse embedded JSON data (Comeet embeds position data in the page).

API endpoint (when credentials available):
  GET https://www.comeet.co/careers-api/2.0/company/{uid}/positions
      ?token={token}&details=true
"""
import html
import json
import logging
import re
from typing import Any

from bs4 import BeautifulSoup

from . import _http

log = logging.getLogger(__name__)

API_BASE = "https://www.comeet.co/careers-api/2.0/company"
PUBLIC_BASE = "https://www.comeet.com/jobs"

_TAG_RE = re.compile(r"<[^>]+>")

_STUDENT_MARKERS = (
    "student", "intern", "graduate", "junior", "new grad", "co-op", "co op",
    "סטודנט", "מתמחה", "התמחות",
)


def _looks_like_student_role(title: str) -> bool:
    t = title.lower()
    return any(m in t for m in _STUDENT_MARKERS)


def _in_location(loc_obj: dict, loc_str: str, location_filter: str) -> bool:
    """Location filter for Comeet. Israeli firms with global offices (Ceragon,
    Gilat) return non-IL jobs too, so when a filter is set we keep a job only if
    its country code or location text matches. Country code is most reliable
    because Comeet's text often omits the country (e.g. 'Caesarea, Haifa District')."""
    if not location_filter:
        return True
    country = (loc_obj.get("country") or "").upper() if isinstance(loc_obj, dict) else ""
    want = location_filter.lower()
    if want in ("israel", "isr", "il"):
        return country == "IL" or "israel" in loc_str.lower()
    return want in loc_str.lower()


def _parse_comeet_api(name: str, uid: str, token: str, location_filter: str = "") -> list[dict]:
    url = f"{API_BASE}/{uid}/positions"
    try:
        # details=true returns the full posting body (in a list of named sections)
        # plus structured location — needed so the hardware/student filter has
        # real text to match, and so jobs get a correct location.
        resp = _http.get(url, params={"token": token, "details": "true"})
        positions = resp.json()
    except Exception as exc:
        log.warning("[%s] Comeet API failed: %s", name, exc)
        return []

    jobs = []
    for p in positions:
        if not isinstance(p, dict):
            continue
        job_id = p.get("uid", p.get("comeet_id", ""))

        loc_obj = p.get("location") or {}
        if isinstance(loc_obj, dict):
            loc = ", ".join(x for x in (loc_obj.get("city"), loc_obj.get("state")) if x) \
                or loc_obj.get("name", "")
        else:
            loc = str(loc_obj)

        if not _in_location(loc_obj, loc, location_filter):
            continue

        # Only feed the description to the relevance filter for student/intern-
        # titled roles, mirroring the Workday fetcher. This avoids senior roles
        # matching just because their body text mentions "graduate"/"students".
        title = p.get("name", "")
        description = ""
        if _looks_like_student_role(title):
            desc_parts = [p.get("employment_type", ""), p.get("experience_level", "")]
            det = p.get("details")
            if isinstance(det, list):
                for sec in det:
                    if isinstance(sec, dict) and sec.get("value"):
                        desc_parts.append(_TAG_RE.sub(" ", html.unescape(str(sec["value"]))))
            description = " ".join(part for part in desc_parts if part)

        url_val = (p.get("url_comeet_hosted_page") or p.get("url_active_page")
                   or p.get("position_url", ""))
        jobs.append({
            "company": name,
            "job_id": str(job_id),
            "title": p.get("name", ""),
            "location": loc,
            "description": description,
            "url": url_val,
        })
    return jobs


def _parse_comeet_page(name: str, slug: str) -> list[dict]:
    """Scrape the public Comeet careers page and extract embedded position JSON."""
    url = f"{PUBLIC_BASE}/{slug}/"
    try:
        resp = _http.get(url)
        html = resp.text
    except Exception as exc:
        log.warning("[%s] Comeet page fetch failed for slug '%s': %s", name, slug, exc)
        return []

    # Comeet embeds positions in a <script> tag as window.__POSITIONS__ or similar JSON
    patterns = [
        r'window\.__POSITIONS__\s*=\s*(\[.*?\]);',
        r'"positions"\s*:\s*(\[.*?\])',
        r'positionsData\s*=\s*(\[.*?\])',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.DOTALL)
        if m:
            try:
                positions = json.loads(m.group(1))
                break
            except json.JSONDecodeError:
                continue
    else:
        # Fallback: try BeautifulSoup to find <script type="application/json"> tags
        soup = BeautifulSoup(html, "lxml")
        positions = []
        for tag in soup.find_all("script", {"type": "application/json"}):
            try:
                data = json.loads(tag.string or "")
                if isinstance(data, list) and data and "name" in data[0]:
                    positions = data
                    break
                if isinstance(data, dict) and "positions" in data:
                    positions = data["positions"]
                    break
            except (json.JSONDecodeError, TypeError):
                continue

        if not positions:
            log.warning(
                "[%s] Comeet: could not extract positions from page '%s'. "
                "Consider adding uid+token to config.yaml.",
                name, url
            )
            return []

    jobs = []
    for p in positions:
        if not isinstance(p, dict):
            continue
        job_id = str(p.get("uid", p.get("id", p.get("comeet_id", ""))))
        loc = p.get("location", p.get("location_name", ""))
        if isinstance(loc, dict):
            loc = loc.get("text", "")
        job_url = p.get("url", f"{PUBLIC_BASE}/{slug}/")
        jobs.append({
            "company": name,
            "job_id": job_id,
            "title": p.get("name", p.get("title", "")),
            "location": str(loc),
            "url": job_url,
        })
    return jobs


def fetch_comeet(company_cfg: dict[str, Any]) -> list[dict]:
    name = company_cfg["name"]
    slug = company_cfg.get("slug", "")
    uid = company_cfg.get("uid", "")
    token = company_cfg.get("token", "")
    location_filter = company_cfg.get("location_filter", "")

    if uid and token:
        jobs = _parse_comeet_api(name, uid, token, location_filter)
    else:
        jobs = _parse_comeet_page(name, slug)

    log.info("[%s] Comeet → %d job(s)", name, len(jobs))
    return jobs
