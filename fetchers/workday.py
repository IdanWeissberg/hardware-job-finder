"""
Workday CXS API fetcher.
Used by: Intel, Qualcomm, NVIDIA, Marvell, Broadcom, Analog Devices,
         Cadence, Applied Materials, KLA, Cisco (and others).

Endpoint pattern:
  POST https://{company}.wd{N}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
"""
import logging
import re
from typing import Any

from . import _http

log = logging.getLogger(__name__)

PAGE_SIZE = 20

# Titles containing any of these are treated as candidate student/intern roles.
# This only gates WHICH jobs we fetch full descriptions for (an efficiency
# optimization); the authoritative relevance decision is still made by
# filter.py using the keyword lists in config.yaml.
_STUDENT_MARKERS = (
    "student", "intern", "graduate", "junior", "new grad", "co-op", "co op",
    "סטודנט", "מתמחה", "התמחות",
)

_TAG_RE = re.compile(r"<[^>]+>")


def _looks_like_student_role(title: str) -> bool:
    t = title.lower()
    return any(m in t for m in _STUDENT_MARKERS)


def _fetch_description(detail_base: str, external_path: str) -> str:
    """Fetch a single job's full description text (HTML stripped)."""
    if not external_path:
        return ""
    try:
        resp = _http.get(f"{detail_base}{external_path}",
                         headers={"Accept": "application/json"})
        info = resp.json().get("jobPostingInfo", {})
        raw = info.get("jobDescription", "") or ""
        return _TAG_RE.sub(" ", raw)
    except Exception:
        return ""


# Map a human location filter to the various tokens Workday tenants use in
# their locationsText. Some use "Israel, Haifa", others "Rehovot,ISR".
_LOCATION_TOKENS = {
    "israel": ("israel", "isr"),
}


def _location_tokens(filter_str: str) -> tuple[str, ...]:
    key = filter_str.lower().strip()
    return _LOCATION_TOKENS.get(key, (key,))


def _location_matches(location_text: str, filter_str: str) -> bool:
    """True if the job is (or may be) in the target location.

    Handles two Workday quirks:
      1. Location-naming varies by tenant ("Israel, Haifa" vs "Rehovot,ISR"),
         so we accept any of several tokens.
      2. Multi-location jobs collapse to a placeholder like "2 Locations"
         instead of naming the cities — we keep those rather than risk dropping
         a job that includes the target location.
    """
    if not filter_str:
        return True
    loc = location_text.lower()
    if any(tok in loc for tok in _location_tokens(filter_str)):
        return True
    if "location" in loc and any(ch.isdigit() for ch in loc):
        return True
    return False


def _collect_postings(name: str, url: str, search: str, page_cap: int) -> list[dict]:
    """Paginate the Workday search and return raw posting dicts.

    Resilient: a transient failure on one page is skipped (with retry handled by
    _http) rather than aborting the whole company, which previously truncated
    results to ~0.
    """
    postings: list[dict] = []
    offset = 0
    pages = 0
    while pages < page_cap:
        payload = {"appliedFacets": {}, "limit": PAGE_SIZE, "offset": offset, "searchText": search}
        try:
            resp = _http.post(url, json=payload, headers={"Content-Type": "application/json"})
            data = resp.json()
        except Exception as exc:
            log.warning("[%s] Workday page at offset %d failed: %s", name, offset, exc)
            break
        batch = data.get("jobPostings", [])
        if not batch:
            break
        postings.extend(batch)
        total = data.get("total", 0)
        offset += PAGE_SIZE
        pages += 1
        if offset >= total:
            break
    return postings


def fetch_workday(company_cfg: dict[str, Any]) -> list[dict]:
    name = company_cfg["name"]
    url = company_cfg["workday_url"]
    base_url = company_cfg["base_url"]
    location_filter = company_cfg.get("location_filter", "")
    search_text = company_cfg.get("search_text", "")

    # Detail endpoint shares the CXS base, swapping the trailing "/jobs" for the
    # per-job externalPath (e.g. .../cxs/intel/External/job/Israel/...).
    detail_base = url[: -len("/jobs")] if url.endswith("/jobs") else url

    # Strategy 1: let Workday's own search narrow by location (fast: a couple
    # pages). Works for tenants that index "Israel" in their searchable text.
    effective_search = " ".join(t for t in (search_text, location_filter) if t).strip()
    raw = _collect_postings(name, url, effective_search, page_cap=15)

    # Strategy 2: some tenants name locations differently ("Rehovot,ISR") and
    # return nothing for an "Israel" text search. If the targeted search came up
    # empty but the board clearly has jobs, scan everything and filter locally.
    if not raw and location_filter:
        log.info("[%s] Workday: location search empty, scanning all jobs", name)
        raw = _collect_postings(name, url, search_text, page_cap=80)

    jobs: list[dict] = []
    for p in raw:
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
        title = p.get("title", "")

        # For candidate student/intern roles, pull the full description so the
        # hardware keyword filter has real text to match (titles like
        # "Formal Verification Student" don't name the hardware domain).
        description = ""
        if _looks_like_student_role(title):
            description = _fetch_description(detail_base, external_path)

        jobs.append({
            "company": name,
            "job_id": str(job_id),
            "title": title,
            "location": loc,
            "description": description,
            "url": job_url,
        })

    log.info("[%s] Workday → %d job(s) matching location filter", name, len(jobs))
    return jobs
