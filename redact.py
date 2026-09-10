"""Strip credentials out of text before it reaches a log.

The repo is public, which means GitHub Actions logs are public too. Exception
messages from `requests` usually embed the full URL — and our URLs can carry a
Telegram bot token, a Google API key, or a Comeet token. GitHub masks registered
secrets in logs, but that is a safety net, not a guarantee (it only matches the
exact stored string). Redacting at the source is the reliable fix.
"""
from __future__ import annotations

import re

# api.telegram.org/bot<digits>:<token>/...
_BOT = re.compile(r"(bot\d{6,12}:)[A-Za-z0-9_-]+", re.IGNORECASE)
# ?key=... &token=... &apikey=... &api_key=... &cx=...
_QUERY = re.compile(r"\b(api[_-]?key|apikey|key|token|access_token|cx)=([^&\s\"'>]+)", re.IGNORECASE)


def redact(value: object) -> str:
    """Return str(value) with any embedded credential replaced by ***."""
    s = str(value)
    s = _BOT.sub(r"\1***", s)
    s = _QUERY.sub(r"\1=***", s)
    return s
