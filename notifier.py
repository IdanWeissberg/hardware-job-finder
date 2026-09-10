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

  3. Telegram Bot API (free, instant, very reliable)
     Create a bot via @BotFather, then required env vars:
       TELEGRAM_BOT_TOKEN — token from BotFather (e.g. 8123456789:AAH...)
       TELEGRAM_CHAT_ID   — your chat id (auto-discoverable from getUpdates)

Set WHATSAPP_PROVIDER to "callmebot", "twilio", or "telegram" (default: callmebot).
"""
from __future__ import annotations

import logging
import os
import urllib.parse

import requests

from redact import redact

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
        log.error("CallMeBot request failed: %s", redact(exc))
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
        log.error("Twilio request failed: %s", redact(exc))
        return False


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _format_jobs_telegram(jobs: list[dict], max_jobs: int = 20) -> str:
    """Telegram HTML-formatted job list (company in bold, title linked)."""
    lines = []
    for j in jobs[:max_jobs]:
        company = _escape_html(j["company"])
        title = _escape_html(j["title"])
        location = _escape_html(j["location"])
        url = _escape_html(j["url"])
        lines.append(
            f'🔧 <b>{company}</b> — <a href="{url}">{title}</a>\n'
            f"   📍 {location}"
        )
    msg = "\n\n".join(lines)
    if len(jobs) > max_jobs:
        msg += f"\n\n…ועוד {len(jobs) - max_jobs} משרות נוספות"
    return msg


TELEGRAM_BATCH = 15  # jobs per message, keeps each well under the 4096-char limit


def _post_telegram(token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200 and resp.json().get("ok"):
            return True
        log.warning("Telegram returned: %s — %s", resp.status_code, redact(resp.text[:200]))
        return False
    except Exception as exc:
        log.error("Telegram request failed: %s", redact(exc))
        return False


def _send_telegram(jobs: list[dict], max_jobs: int = 20) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    # TELEGRAM_CHAT_ID may be a single id or a comma-separated list, so the same
    # alerts can go to several people (each must have messaged the bot once).
    # Example: "111111111,222222222".
    chat_ids = [c.strip() for c in os.environ.get("TELEGRAM_CHAT_ID", "").split(",") if c.strip()]

    if not token or not chat_ids:
        log.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID env vars not set")
        return False

    total = len(jobs)
    # Split into batches so a large digest is never truncated / lost.
    batches = [jobs[i:i + TELEGRAM_BATCH] for i in range(0, total, TELEGRAM_BATCH)]
    all_ok = True
    for idx, batch in enumerate(batches, 1):
        part = f" ({idx}/{len(batches)})" if len(batches) > 1 else ""
        header = (
            f"🚨 <b>{total} משרת סטודנט/התמחות חדשה{'ות' if total > 1 else ''}"
            f"{part}</b>\n\n"
        )
        text = header + _format_jobs_telegram(batch, max_jobs=TELEGRAM_BATCH)
        for cid in chat_ids:
            # One recipient failing must not stop delivery to the others.
            if not _post_telegram(token, cid, text):
                all_ok = False

    if all_ok:
        log.info("Telegram: sent %d job(s) in %d message(s) to %d recipient(s)",
                 total, len(batches), len(chat_ids))
    return all_ok


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

    log.info("Sending notification via %s: %d job(s)", provider, len(jobs))

    if provider == "telegram":
        return _send_telegram(jobs, max_jobs)
    if provider == "twilio":
        return _send_twilio(full_text)
    return _send_callmebot(full_text)
