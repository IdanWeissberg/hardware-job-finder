"""
Job relevance filter.

Two modes (set via config `filter.mode`):
  "student_only"        — a job passes if it is a student/intern role
                          (ANY student keyword). Default: the user wants every
                          student position at the monitored companies.
  "hardware_and_student"— stricter: must match a hardware keyword AND a
                          student keyword.

Matching is case-insensitive over title + description + location.
"""
from __future__ import annotations

import re
from typing import Any


def _matches_any(text: str, keywords: list[str]) -> bool:
    text_lower = text.lower()
    for kw in keywords:
        # Match whole words/phrases only, so "intern" doesn't match "internal"
        # and "soc" doesn't match "associate". \b works for the ASCII keywords;
        # Hebrew keywords fall back to substring (no false-positive risk there).
        pattern = r"\b" + re.escape(kw.lower()) + r"\b"
        if re.search(pattern, text_lower):
            return True
    return False


def is_relevant(
    job: dict[str, Any],
    keywords: dict[str, list[str]],
    mode: str = "student_only",
) -> bool:
    """Return True if the job is relevant under the given mode."""
    searchable = " ".join([
        job.get("title", ""),
        job.get("description", ""),
        job.get("location", ""),
    ])
    student_match = _matches_any(searchable, keywords.get("student", []))

    if mode == "hardware_and_student":
        hw_match = _matches_any(searchable, keywords.get("hardware", []))
        return hw_match and student_match

    # default: student_only — every student/intern role qualifies
    return student_match
