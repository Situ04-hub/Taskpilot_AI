"""
gmail_loader.py
----------------
Real, READ-ONLY Gmail ingestion source for TaskPilot AI.

SECURITY: Credentials are NEVER hardcoded here. Set them as environment
variables (or in a local .env file loaded by main.py) before running:

    GMAIL_USER=you@gmail.com
    GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

Generate an App Password at: https://myaccount.google.com/apppasswords
(Requires 2FA enabled on the Google account. Never use your real password.)

If credentials are missing or the connection fails for any reason
(no network, wrong password, IMAP disabled), this module fails SAFE —
it returns an empty list, so the rest of the pipeline (mock sources)
keeps working without crashing the demo. The *reason* for failure is
always recorded in get_last_gmail_status() so the dashboard can show it.
"""

import os
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from typing import List

from models import Task, SourceEnum, SeverityEnum

URGENT_KEYWORDS = ["urgent", "critical", "asap", "production", "down", "outage", "p1", "sev1"]

# Tracks the outcome of the most recent fetch attempt, so app.py can
# show *why* real Gmail isn't showing up instead of failing silently.
_last_status = {"ok": False, "message": "Not attempted yet.", "count": 0}


def get_last_gmail_status() -> dict:
    return _last_status


def _decode(value) -> str:
    if value is None:
        return ""
    decoded, charset = decode_header(value)[0]
    if isinstance(decoded, bytes):
        return decoded.decode(charset or "utf-8", errors="ignore")
    return decoded


def fetch_real_gmail_tasks(max_emails: int = 5) -> List[Task]:
    """Connects to Gmail read-only, pulls latest emails, converts to Tasks.
    Returns [] on any failure — never raises, so it never breaks the demo.
    Tries UNSEEN (unread) first; if there are none, falls back to the
    most recent emails in the inbox overall, so a fully-read inbox still
    demos something real."""

    global _last_status

    # Read env vars at call time (not import time) so a .env loaded
    # later, or set right before clicking "Refresh", is picked up.
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not gmail_user or not gmail_password:
        msg = "GMAIL_USER / GMAIL_APP_PASSWORD not set. Create a .env file (see .env.example) with real values."
        print(f"[gmail_loader] {msg}")
        _last_status = {"ok": False, "message": msg, "count": 0}
        return []

    tasks: List[Task] = []

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(gmail_user, gmail_password)
        mail.select("inbox")

        # 1. Try unread first
        status, messages = mail.search(None, "UNSEEN")
        email_ids = messages[0].split() if status == "OK" else []
        used_fallback = False

        # 2. Fall back to most recent mail overall if no unread mail exists
        if not email_ids:
            status, messages = mail.search(None, "ALL")
            email_ids = messages[0].split() if status == "OK" else []
            used_fallback = True

        email_ids = email_ids[-max_emails:]

        if not email_ids:
            mail.logout()
            msg = "Connected to Gmail successfully, but the inbox appears to be empty."
            print(f"[gmail_loader] {msg}")
            _last_status = {"ok": True, "message": msg, "count": 0}
            return []

        for idx, e_id in enumerate(reversed(email_ids)):
            res, msg_data = mail.fetch(e_id, "(RFC822)")
            if res != "OK":
                continue

            msg = email.message_from_bytes(msg_data[0][1])
            subject = _decode(msg["Subject"]) or "No subject"
            sender = _decode(msg["From"]) or "Unknown sender"

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                        try:
                            body = part.get_payload(decode=True).decode(errors="ignore")
                        except Exception:
                            pass
                        break
            else:
                try:
                    body = msg.get_payload(decode=True).decode(errors="ignore")
                except Exception:
                    body = ""

            combined_text = f"{subject} {body}".lower()
            is_urgent = any(kw in combined_text for kw in URGENT_KEYWORDS)
            severity = SeverityEnum.P1 if is_urgent else SeverityEnum.P3

            tasks.append(
                Task(
                    id=f"GMAIL-REAL-{idx+1}",
                    title=subject[:80],
                    description=f"From: {sender}. {body[:300].strip()}",
                    source=SourceEnum.EMAIL,
                    severity=severity,
                    deadline=datetime.now() + timedelta(hours=24 if is_urgent else 72),
                    dependencies=[],
                    business_impact=8 if is_urgent else 4,
                    transparency_reason="Ingested live from your real Gmail inbox" + (" (no unread mail, showing recent)." if used_fallback else " (unread, read-only access).")
                )
            )

        mail.logout()
        msg = f"Pulled {len(tasks)} real email(s) from Gmail" + (" (fell back to recent mail — no unread found)." if used_fallback else " (unread).")
        print(f"[gmail_loader] {msg}")
        _last_status = {"ok": True, "message": msg, "count": len(tasks)}

    except imaplib.IMAP4.error as e:
        msg = f"Gmail rejected login. Check GMAIL_USER and that GMAIL_APP_PASSWORD is a 16-char App Password (not your real password). Detail: {e}"
        print(f"[gmail_loader] {msg}")
        _last_status = {"ok": False, "message": msg, "count": 0}
        return []
    except Exception as e:
        msg = f"Could not reach Gmail (network/DNS/firewall?). Detail: {e}"
        print(f"[gmail_loader] {msg}")
        _last_status = {"ok": False, "message": msg, "count": 0}
        return []

    return tasks