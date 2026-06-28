"""
Job relevance filter.
A job passes if it matches at least one hardware keyword AND
at least one student/intern keyword (title + description, case-insensitive).
"""
from __future__ import annotations

import re
from typing import Any


def _matches_any(text: str, keywords: list[str]) -> bool:
    text_lower = text.lower()
    for kw in keywords:
        pattern = re.escape(kw.lower())
        if re.search(pattern, text_lower):
            return True
    return False


def is_relevant(job: dict[str, Any], keywords: dict[str, list[str]]) -> bool:
    """Return True if job matches both keyword categories."""
    searchable = " ".join([
        job.get("title", ""),
        job.get("description", ""),
        job.get("location", ""),
    ])
    hw_match = _matches_any(searchable, keywords.get("hardware", []))
    student_match = _matches_any(searchable, keywords.get("student", []))
    return hw_match and student_match
