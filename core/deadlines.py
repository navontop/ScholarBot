import os
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, List, Optional
from core.models import DeadlineItem, DeadlineResponse, ScholarshipItem

CURRENT_YEAR = 2026

def calculate_deadline_metrics(deadline_iso_str: str) -> tuple[int, str, str]:
    """
    Computes days remaining and urgency tier from real ISO date (YYYY-MM-DD).
    Current time is anchored to 2026.
    """
    try:
        parts = [int(p) for p in deadline_iso_str.split("-")]
        deadline_dt = datetime(parts[0], parts[1], parts[2], 23, 59, 59, tzinfo=timezone.utc)
    except Exception:
        # Fallback to end of current year
        deadline_dt = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

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
    try:
        parts = [int(p) for p in deadline_iso_str.split("-")]
        dt_stamp = now.strftime("%Y%m%dT%H%M%SZ")
        dt_start = f"{parts[0]:04d}{parts[1]:02d}{parts[2]:02d}T090000Z"
        dt_end = f"{parts[0]:04d}{parts[1]:02d}{parts[2]:02d}T180000Z"
    except Exception:
        dt_stamp = now.strftime("%Y%m%dT%H%M%SZ")
        dt_start = "20261231T090000Z"
        dt_end = "20261231T180000Z"

    stable_hash = hashlib.sha256(f"{scheme_name}-{deadline_iso_str}".encode()).hexdigest()[:16]
    clean_summary = scheme_name.replace(",", "\\,").replace(";", "\\;")
    clean_desc = f"Official Application Deadline for {clean_summary}. Apply at: {portal_url}. Verify NPCI DBT bank linking before submitting.".replace(",", "\\,").replace(";", "\\;")

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

def build_deadline_items(schemes: List[ScholarshipItem]) -> List[DeadlineItem]:
    """Generates structured DeadlineItem list for schemes."""
    items: List[DeadlineItem] = []
    for s in schemes:
        days, tier, badge = calculate_deadline_metrics(s.deadline)
        ics_text = generate_ics_calendar(s.name, s.deadline, s.portal_url)
        items.append(DeadlineItem(
            scheme_id=s.id,
            scheme_name=s.name,
            portal_url=s.portal_url,
            deadline_date=s.deadline,
            days_remaining=days,
            urgency_tier=tier,
            badge_label=badge,
            ics_calendar_data=ics_text
        ))
    # Sort: closing soonest first (excluding closed to bottom)
    items.sort(key=lambda x: (x.days_remaining < 0, x.days_remaining))
    return items
