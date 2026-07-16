"""
LinkedIn public-post finder (via Google Programmable Search / Custom Search API).

A lot of Israeli hardware/chip roles never become formal job postings — someone
just writes a LinkedIn post like "מחפשים סטודנט/ית לחומרה, פנו אליי בפרטי". These
never show up in any ATS. We can't scrape LinkedIn directly (it blocks automated
access, requires login, and it's against their ToS), but Google *indexes* the
public posts — so we search Google's official API, restricted to linkedin.com
posts, for recent hardware + student posts, and surface the links.

Setup (one time): create a Google API key + a Programmable Search Engine, then
set two env vars / GitHub Secrets:
    GOOGLE_API_KEY   — Google Cloud API key with "Custom Search API" enabled
    GOOGLE_CSE_ID    — the Programmable Search Engine id (cx)

Config entry:
    - name: "LinkedIn Posts"
      ats: linkedin_search
      queries: [ '<google query 1>', '<google query 2>' ]
      days: 21          # optional, only posts from the last N days (default 21)
"""
import hashlib
import logging
import os
import re
from typing import Any

from . import _http

log = logging.getLogger(__name__)

CSE_URL = "https://www.googleapis.com/customsearch/v1"

# Snippets/titles that suggest a hiring / "reach out to me" post (EN + HE).
_INTENT = re.compile(
    r"(hiring|looking for|we[' ]?re looking|reach out|dm me|message me|send me|"
    r"join (?:us|our|my)|open (?:role|position)|"
    r"מחפש|מחפשת|מגייס|מגייסת|דרוש|דרושה|פנו אלי|פנו אליי|שלחו לי|"
    r"מוזמנ|בפרטי|הצטרפ|למי שמתאים|תייגו)",
    re.IGNORECASE,
)


def _post_id(url: str) -> str:
    m = re.search(r"(?:activity|ugcPost|posts)[:/-]([0-9]{6,})", url)
    if m:
        return m.group(1)
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def fetch_linkedin_search(company_cfg: dict[str, Any]) -> list[dict]:
    name = company_cfg.get("name", "LinkedIn Posts")
    queries = company_cfg.get("queries", [])
    days = company_cfg.get("days", 21)

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    cse_id = os.environ.get("GOOGLE_CSE_ID", "")
    if not api_key or not cse_id:
        log.warning("[%s] GOOGLE_API_KEY / GOOGLE_CSE_ID not set — skipping LinkedIn search", name)
        return []

    jobs: list[dict] = []
    seen_urls: set[str] = set()

    for query in queries:
        # Restrict to public LinkedIn posts and to recent results.
        q = f"site:linkedin.com/posts {query}"
        params = {
            "key": api_key,
            "cx": cse_id,
            "q": q,
            "num": 10,
            "dateRestrict": f"d{int(days)}",
        }
        try:
            resp = _http.get(CSE_URL, params=params)
            data = resp.json()
        except Exception as exc:
            log.warning("[%s] Google CSE query failed: %s", name, exc)
            continue

        for item in data.get("items", []):
            url = item.get("link", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            title = item.get("title", "")
            snippet = item.get("snippet", "")
            blob = f"{title} {snippet}"

            # Only keep posts that read like an actual hiring / reach-out post.
            if not _INTENT.search(blob):
                continue

            jobs.append({
                "company": name,
                "job_id": _post_id(url),
                "title": title[:120] or "LinkedIn post",
                "location": "LinkedIn",
                "description": snippet,
                "url": url,
            })

    log.info("[%s] LinkedIn search → %d matching post(s)", name, len(jobs))
    return jobs
