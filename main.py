#!/usr/bin/env python3
"""
Hardware Job Monitor — main entry point.

Usage:
  python main.py          # Normal run (check + notify)
  python main.py --init   # Seed seen_jobs.json without sending notifications
  python main.py --test-notify  # Send a test WhatsApp message

GitHub Actions runs this via the job_monitor.yml workflow.
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pytz
import yaml

import filter as job_filter
import notifier
import state
from fetchers import FETCHER_MAP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------- Config loading ----------

def load_config() -> dict[str, Any]:
    cfg_path = Path(__file__).parent / "config.yaml"
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------- Quiet hours check ----------

def is_quiet_hours(cfg: dict) -> bool:
    qh = cfg.get("quiet_hours", {})
    tz_name = qh.get("timezone", "Asia/Jerusalem")
    start_str = qh.get("start", "00:00")
    end_str = qh.get("end", "07:00")

    tz = pytz.timezone(tz_name)
    now = datetime.now(tz)
    current = now.hour * 60 + now.minute

    start_h, start_m = map(int, start_str.split(":"))
    end_h, end_m = map(int, end_str.split(":"))
    start = start_h * 60 + start_m
    end = end_h * 60 + end_m

    if start <= end:
        return start <= current < end
    # Crosses midnight
    return current >= start or current < end


# ---------- Fetch all companies ----------

def fetch_all(companies: list[dict]) -> dict[str, list[dict]]:
    """Returns {company_name: [jobs]} for all enabled companies."""
    results: dict[str, list[dict]] = {}

    for company in companies:
        if not company.get("enabled", True):
            continue

        name = company["name"]
        ats = company.get("ats", "scraper")
        fetcher = FETCHER_MAP.get(ats)

        if fetcher is None:
            log.warning("[%s] Unknown ATS type '%s', skipping", name, ats)
            continue

        try:
            jobs = fetcher(company)
            results[name] = jobs
            log.info("[%s] Fetched %d total jobs", name, len(jobs))
        except Exception as exc:
            log.error("[%s] Fetch failed (%s): %s", name, ats, exc, exc_info=True)
            results[name] = []

    return results


# ---------- Main run ----------

def run(init_mode: bool = False) -> None:
    cfg = load_config()
    companies = cfg.get("companies", [])
    keywords = cfg.get("keywords", {})
    filter_mode = cfg.get("filter", {}).get("mode", "student_only")
    notif_cfg = cfg.get("notification", {})
    max_jobs_per_msg = notif_cfg.get("max_jobs_per_message", 20)

    seen = state.load_seen()
    pending = state.load_pending()

    log.info("=== Job Monitor run started — %d companies to check ===", len([c for c in companies if c.get("enabled", True)]))

    all_results = fetch_all(companies)

    new_relevant: list[dict] = []
    total_scanned = 0
    total_new = 0

    for company_name, jobs in all_results.items():
        total_scanned += len(jobs)
        company_new = 0

        for job in jobs:
            if state.is_seen(seen, job):
                continue

            # Mark seen regardless of relevance (avoids re-processing on every run)
            state.mark_seen(seen, job)
            total_new += 1
            company_new += 1

            if job_filter.is_relevant(job, keywords, mode=filter_mode):
                if not init_mode:
                    new_relevant.append(job)
                    log.info("[%s] NEW relevant job: %s | %s", company_name, job["title"], job["location"])

        if company_new:
            log.info("[%s] %d new job(s) found this run", company_name, company_new)

    log.info(
        "=== Run complete: scanned=%d total_new=%d relevant_new=%d ===",
        total_scanned, total_new, len(new_relevant)
    )

    # Save seen state (critical — do this before notification so state is safe)
    state.save_seen(seen)

    if init_mode:
        log.info("INIT mode: baseline established. %d jobs recorded. No notifications sent.", len(seen))
        return

    # ---------- Notification logic ----------
    quiet = is_quiet_hours(cfg)

    if quiet:
        # Queue new relevant jobs for the morning digest
        if new_relevant:
            pending.extend(new_relevant)
            state.save_pending(pending)
            log.info(
                "Quiet hours active — %d job(s) queued for morning digest (queue now has %d)",
                len(new_relevant), len(pending)
            )
        else:
            log.info("Quiet hours active — no new relevant jobs found, nothing queued")
    else:
        # Combine queued overnight jobs with new ones found now
        jobs_to_send = pending + new_relevant
        if jobs_to_send:
            if pending:
                log.info("Sending morning digest: %d queued + %d new = %d total", len(pending), len(new_relevant), len(jobs_to_send))
            success = notifier.send_whatsapp(jobs_to_send, max_jobs=max_jobs_per_msg)
            if success:
                state.clear_pending()
                log.info("Notifications sent and queue cleared")
            else:
                # Notification failed (e.g. WhatsApp credentials not yet configured).
                # Persist ALL undelivered jobs to the pending queue so nothing is lost —
                # they will be retried on the next run once notifications work.
                state.save_pending(jobs_to_send)
                log.error(
                    "Notification failed — %d job(s) saved to pending queue for retry next run "
                    "(check WhatsApp credentials)", len(jobs_to_send)
                )
        else:
            log.info("No new relevant jobs and no pending queue — nothing to send")


def test_notify() -> None:
    """Send a test message to verify WhatsApp integration."""
    test_job = {
        "company": "Test Company",
        "title": "Hardware Engineering Intern (TEST)",
        "location": "Tel Aviv, Israel",
        "url": "https://example.com/jobs/test",
    }
    log.info("Sending test WhatsApp notification...")
    success = notifier.send_whatsapp([test_job])
    if success:
        log.info("Test notification sent successfully!")
    else:
        log.error("Test notification failed — check your env vars")
        sys.exit(1)


# ---------- Entry point ----------

def main() -> None:
    parser = argparse.ArgumentParser(description="Hardware Job Monitor")
    parser.add_argument("--init", action="store_true", help="Seed baseline without sending notifications")
    parser.add_argument("--test-notify", action="store_true", help="Send a test WhatsApp message")
    args = parser.parse_args()

    if args.test_notify:
        test_notify()
    else:
        run(init_mode=args.init)


if __name__ == "__main__":
    main()
