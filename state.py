"""
State management for seen jobs and pending notification queue.

seen_jobs.json       — set of "company|job_id" strings already processed
pending_notifications.json — list of job dicts queued for next digest
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

SEEN_PATH = Path("seen_jobs.json")
PENDING_PATH = Path("pending_notifications.json")


# ---------- seen_jobs ----------

def load_seen() -> set[str]:
    if not SEEN_PATH.exists():
        return set()
    try:
        data = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
        return set(data)
    except Exception as exc:
        log.warning("Could not read %s: %s", SEEN_PATH, exc)
        return set()


def save_seen(seen: set[str]) -> None:
    SEEN_PATH.write_text(
        json.dumps(sorted(seen), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def job_key(job: dict[str, Any]) -> str:
    return f"{job['company']}|{job['job_id']}"


def mark_seen(seen: set[str], job: dict[str, Any]) -> None:
    seen.add(job_key(job))


def is_seen(seen: set[str], job: dict[str, Any]) -> bool:
    return job_key(job) in seen


# ---------- pending notifications ----------

def load_pending() -> list[dict]:
    if not PENDING_PATH.exists():
        return []
    try:
        data = json.loads(PENDING_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as exc:
        log.warning("Could not read %s: %s", PENDING_PATH, exc)
        return []


def save_pending(queue: list[dict]) -> None:
    PENDING_PATH.write_text(
        json.dumps(queue, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def clear_pending() -> None:
    save_pending([])
