"""
Eightfold careers sitemap fetcher.

Some Eightfold-powered career sites (e.g. Qualcomm) put their job-search API
behind a WAF that returns 403 to all automated requests, but expose a public
XML sitemap that is NOT protected. Each job URL's slug encodes the job id, title
and location, e.g.:
  /careers/job/446718946150-fy27-intern-digital-design-intern-tirat-carmel-haifa-haifa-district-israel

So we read the sitemap, keep URLs whose slug contains the target location, and
parse the id + title straight from the slug — no API call, no detail fetch.

Config:
  ats: eightfold_sitemap
  sitemap_url: "https://careers.qualcomm.com/careers/sitemap.xml?domain=qualcomm.com"
  location_filter: "Israel"
"""
import logging
import re
from typing import Any
from urllib.parse import unquote

from . import _http

log = logging.getLogger(__name__)

# Location-ish tokens to strip from the end of a slug so the title reads cleanly.
_LOC_WORDS = re.compile(
    r"\b(?:israel|isr|haifa|hod\s+hasharon|kfar\s+netter|tirat\s+carmel|"
    r"tel\s+aviv(?:-yafo)?|raanana|ra'anana|yokneam|petah\s+tikva|netanya|"
    r"beer\s+sheva|kiryat\s+gat|herzliya|district|central|center)\b",
    re.IGNORECASE,
)


def fetch_eightfold_sitemap(company_cfg: dict[str, Any]) -> list[dict]:
    name = company_cfg["name"]
    sitemap_url = company_cfg["sitemap_url"]
    location_filter = company_cfg.get("location_filter", "")

    try:
        resp = _http.get(sitemap_url)
        xml = resp.text
    except Exception as exc:
        log.warning("[%s] Eightfold sitemap fetch failed: %s", name, exc)
        return []

    urls = re.findall(r"<loc>([^<]+/careers/job/[^<]+)</loc>", xml)
    want = location_filter.lower()

    jobs: list[dict] = []
    seen: set[str] = set()
    for url in urls:
        decoded = unquote(url).lower()
        if want and want not in decoded:
            continue

        m = re.search(r"/job/(\d+)-(.+?)(?:\?|$)", unquote(url))
        if not m:
            continue
        job_id, slug = m.group(1), m.group(2)
        if job_id in seen:
            continue
        seen.add(job_id)

        title = slug.replace("-", " ").replace("–", " ")
        # Drop the trailing location tokens the slug appends.
        title = _LOC_WORDS.sub(" ", title)
        title = re.sub(r"\s+", " ", title).strip(" ,-")

        jobs.append({
            "company": name,
            "job_id": job_id,
            "title": title,
            "location": location_filter,
            "url": url,
        })

    log.info("[%s] Eightfold sitemap → %d job(s)", name, len(jobs))
    return jobs
