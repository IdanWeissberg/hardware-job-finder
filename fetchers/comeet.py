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
import json
import logging
import re
from typing import Any

from bs4 import BeautifulSoup

from . import _http

log = logging.getLogger(__name__)

API_BASE = "https://www.comeet.co/careers-api/2.0/company"
PUBLIC_BASE = "https://www.comeet.com/jobs"


def _parse_comeet_api(name: str, uid: str, token: str) -> list[dict]:
    url = f"{API_BASE}/{uid}/positions"
    try:
        resp = _http.get(url, params={"token": token, "details": "false"})
        positions = resp.json()
    except Exception as exc:
        log.warning("[%s] Comeet API failed: %s", name, exc)
        return []

    jobs = []
    for p in positions:
        job_id = p.get("uid", p.get("comeet_id", ""))
        loc_list = p.get("details", {}).get("location", [])
        loc = ", ".join(
            item.get("text", "") for item in loc_list if isinstance(item, dict)
        ) if loc_list else p.get("location_name", "")
        url_val = p.get("url_active_version", p.get("url", ""))
        jobs.append({
            "company": name,
            "job_id": str(job_id),
            "title": p.get("name", ""),
            "location": loc,
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

    if uid and token:
        jobs = _parse_comeet_api(name, uid, token)
    else:
        jobs = _parse_comeet_page(name, slug)

    log.info("[%s] Comeet → %d job(s)", name, len(jobs))
    return jobs
