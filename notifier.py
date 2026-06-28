"""
WhatsApp notification module.

Providers supported:
  1. CallMeBot (default, free for personal use)
     Register once: https://www.callmebot.com/blog/free-api-whatsapp-messages/
     Required env vars:
       CALLMEBOT_PHONE   — your WhatsApp number in international format (e.g. +972501234567)
       CALLMEBOT_API_KEY — key received from the CallMeBot bot

  2. Twilio WhatsApp API (more robust alternative)
     Required env vars:
       TWILIO_ACCOUNT_SID
       TWILIO_AUTH_TOKEN
       TWILIO_FROM        — Twilio sandbox number (e.g. whatsapp:+14155238886)
       TWILIO_TO          — your WhatsApp number  (e.g. whatsapp:+972501234567)

Set WHATSAPP_PROVIDER=twilio to switch (default: callmebot).
"""
from __future__ import annotations

import logging
import os
import urllib.parse

import requests

log = logging.getLogger(__name__)

MAX_WHATSAPP_CHARS = 1600  # safe limit below WhatsApp's 4096


def _format_jobs(jobs: list[dict], max_jobs: int = 20) -> str:
    lines = []
    shown = jobs[:max_jobs]
    for j in shown:
        lines.append(
            f"🔧 *{j['company']}* — {j['title']}\n"
            f"   📍 {j['location']}\n"
            f"   🔗 {j['url']}"
        )
    msg = "\n\n".join(lines)
    if len(jobs) > max_jobs:
        msg += f"\n\n...ועוד {len(jobs) - max_jobs} משרות נוספות"
    return msg


def _send_callmebot(text: str) -> bool:
    phone = os.environ.get("CALLMEBOT_PHONE", "")
    api_key = os.environ.get("CALLMEBOT_API_KEY", "")

    if not phone or not api_key:
        log.error("CALLMEBOT_PHONE or CALLMEBOT_API_KEY env vars not set")
        return False

    # CallMeBot free API
    url = "https://api.callmebot.com/whatsapp.php"
    params = {
        "phone": phone,
        "text": text,
        "apikey": api_key,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200 and "Message Sent" in resp.text:
            log.info("CallMeBot: message sent successfully")
            return True
        log.warning("CallMeBot returned: %s — %s", resp.status_code, resp.text[:200])
        return False
    except Exception as exc:
        log.error("CallMeBot request failed: %s", exc)
        return False


def _send_twilio(text: str) -> bool:
    try:
        from twilio.rest import Client  # type: ignore[import]
    except ImportError:
        log.error("twilio package not installed. Run: pip install twilio")
        return False

    sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    from_num = os.environ.get("TWILIO_FROM", "")
    to_num = os.environ.get("TWILIO_TO", "")

    if not all([sid, token, from_num, to_num]):
        log.error("One or more Twilio env vars missing (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM, TWILIO_TO)")
        return False

    try:
        client = Client(sid, token)
        msg = client.messages.create(body=text, from_=from_num, to=to_num)
        log.info("Twilio: message sent, SID=%s", msg.sid)
        return True
    except Exception as exc:
        log.error("Twilio request failed: %s", exc)
        return False


def send_whatsapp(jobs: list[dict], max_jobs: int = 20) -> bool:
    """Send a consolidated WhatsApp message for a list of jobs."""
    if not jobs:
        return True

    provider = os.environ.get("WHATSAPP_PROVIDER", "callmebot").lower()

    header = f"🚨 {len(jobs)} משרה{'ות' if len(jobs) > 1 else ''} חומרה חדשה{'ות' if len(jobs) > 1 else ''} נמצא{'ו' if len(jobs) > 1 else ''}!\n\n"
    body = _format_jobs(jobs, max_jobs)
    full_text = header + body

    # Truncate to WhatsApp limit
    if len(full_text) > MAX_WHATSAPP_CHARS:
        full_text = full_text[:MAX_WHATSAPP_CHARS - 50] + "\n...(קוצר)"

    log.info("Sending WhatsApp via %s: %d job(s)", provider, len(jobs))

    if provider == "twilio":
        return _send_twilio(full_text)
    return _send_callmebot(full_text)
