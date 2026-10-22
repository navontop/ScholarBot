import os
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from core.models import DeadlineItem, DeadlineResponse, ScholarshipItem

CURRENT_YEAR = 2026

def calculate_deadline_metrics(deadline_iso_str: Optional[str]) -> tuple[int, str, str]:
    """
    Computes days remaining and urgency tier from real ISO date (YYYY-MM-DD).
    If deadline is not verified / null, returns 'Check official portal'.
    Current time is anchored to 2026.
    """
    if not deadline_iso_str or str(deadline_iso_str).strip() in ("", "None", "null"):
        return (9999, "OPEN", "Check official portal")

    try:
        parts = [int(p) for p in str(deadline_iso_str).split("-")]
        deadline_dt = datetime(parts[0], parts[1], parts[2], 23, 59, 59, tzinfo=timezone.utc)
    except Exception:
        return (9999, "OPEN", "Check official portal")

    now = datetime.now(timezone.utc)
    diff = deadline_dt - now
    days = diff.days

    if days < 0:
        return (days, "CLOSED", "Portal Closed for Current Session")
    elif days <= 7:
        return (days, "CRITICAL_UNDER_7_DAYS", f"Closing in {days} Days (Urgent Action Required)")
    elif days <= 15:
        return (days, "EXPIRING_UNDER_15_DAYS", f"Closing in {days} Days (Apply Soon)")
    else:
        return (days, "OPEN", f"{days} Days Remaining")

def generate_ics_calendar(scheme_name: str, deadline_iso_str: str, portal_url: str) -> str:
    """
    Generates standard RFC-5545 iCalendar (.ics) content with 7-day, 3-day, and 1-day reminders.
    Uses stable SHA256 UID.
    """
    import hashlib
    now = datetime.now(timezone.utc)
    if not deadline_iso_str or str(deadline_iso_str).strip() in ("", "None", "null"):
        dt_stamp = now.strftime("%Y%m%dT%H%M%SZ")
        dt_start = "20261231T090000Z"
        dt_end = "20261231T180000Z"
        clean_desc = f"Application tracking for {scheme_name}. Official deadline not yet verified for 2026-27 cycle. Check portal regularly at: {portal_url}".replace(",", "\\,").replace(";", "\\;")
    else:
        try:
            parts = [int(p) for p in str(deadline_iso_str).split("-")]
            dt_stamp = now.strftime("%Y%m%dT%H%M%SZ")
            dt_start = f"{parts[0]:04d}{parts[1]:02d}{parts[2]:02d}T090000Z"
            dt_end = f"{parts[0]:04d}{parts[1]:02d}{parts[2]:02d}T180000Z"
        except Exception:
            dt_stamp = now.strftime("%Y%m%dT%H%M%SZ")
            dt_start = "20261231T090000Z"
            dt_end = "20261231T180000Z"
        clean_desc = f"Official Application Deadline for {scheme_name}. Apply at: {portal_url}. Verify NPCI DBT bank linking before submitting.".replace(",", "\\,").replace(";", "\\;")

    stable_hash = hashlib.sha256(f"{scheme_name}-{deadline_iso_str}".encode()).hexdigest()[:16]
    clean_summary = scheme_name.replace(",", "\\,").replace(";", "\\;")

    ics_content = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//ScholarBot//Indian Scholarship Calendar v1.0//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:PUBLISH\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:scholarship-{stable_hash}@scholarbot.asi1.ai\r\n"
        f"DTSTAMP:{dt_stamp}\r\n"
        f"DTSTART:{dt_start}\r\n"
        f"DTEND:{dt_end}\r\n"
        f"SUMMARY:[DEADLINE] {clean_summary}\r\n"
        f"DESCRIPTION:{clean_desc}\r\n"
        f"URL:{portal_url}\r\n"
        "STATUS:CONFIRMED\r\n"
        # Alarm 7 days before
        "BEGIN:VALARM\r\n"
        "TRIGGER:-P7D\r\n"
        "ACTION:DISPLAY\r\n"
        f"DESCRIPTION:Scholarship Reminder: 7 days left to apply for {clean_summary}\r\n"
        "END:VALARM\r\n"
        # Alarm 3 days before
        "BEGIN:VALARM\r\n"
        "TRIGGER:-P3D\r\n"
        "ACTION:DISPLAY\r\n"
        f"DESCRIPTION:Urgent: 3 days remaining for {clean_summary}\r\n"
        "END:VALARM\r\n"
        # Alarm 1 day before
        "BEGIN:VALARM\r\n"
        "TRIGGER:-P1D\r\n"
        "ACTION:DISPLAY\r\n"
        f"DESCRIPTION:FINAL REMINDER: Tomorrow is last date for {clean_summary}!\r\n"
        "END:VALARM\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
    return ics_content

def get_calendar_data_uri(ics_content: str) -> str:
    """Encodes .ics content as a browser/client downloadable data URI."""
    encoded = urllib.parse.quote(ics_content)
    return f"data:text/calendar;charset=utf-8,{encoded}"

def build_deadline_items(schemes: List[Any]) -> List[DeadlineItem]:
    """Generates structured DeadlineItem list for schemes."""
    items: List[DeadlineItem] = []
    for s in schemes:
        sid = getattr(s, "id", None) or (s.get("id") if isinstance(s, dict) else "")
        sname = getattr(s, "name", None) or (s.get("name") if isinstance(s, dict) else "")
        purl = getattr(s, "portal_url", None) or (s.get("portal_url") if isinstance(s, dict) else "")
        dline = getattr(s, "deadline", None) if hasattr(s, "deadline") else (s.get("deadline") if isinstance(s, dict) else None)
        days, tier, badge = calculate_deadline_metrics(dline)
        ics_text = generate_ics_calendar(sname, dline, purl)
        items.append(DeadlineItem(
            scheme_id=sid,
            scheme_name=sname,
            portal_url=purl,
            deadline_date=dline if dline else "Check official portal",
            days_remaining=days,
            urgency_tier=tier,
            badge_label=badge,
            ics_calendar_data=ics_text
        ))
    # Sort: closing soonest first (excluding closed to bottom, unverified/portal to middle)
    items.sort(key=lambda x: (x.days_remaining < 0, x.days_remaining))
    return items
