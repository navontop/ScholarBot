import pytest
from core.deadlines import calculate_deadline_metrics, generate_ics_calendar

from datetime import datetime, timezone, timedelta

def test_deadline_calculation_open():
    future_date = (datetime.now(timezone.utc) + timedelta(days=20)).strftime("%Y-%m-%d")
    days, tier, badge = calculate_deadline_metrics(future_date)
    assert days > 15
    assert tier == "OPEN"

def test_deadline_calculation_critical():
    critical_date = (datetime.now(timezone.utc) + timedelta(days=4)).strftime("%Y-%m-%d")
    days, tier, badge = calculate_deadline_metrics(critical_date)
    assert 0 <= days <= 7
    assert tier == "CRITICAL_UNDER_7_DAYS"

def test_ics_generation():
    ics_text = generate_ics_calendar("NSP Central Sector Scheme", "2026-11-30", "https://scholarships.gov.in")
    assert "BEGIN:VCALENDAR" in ics_text
    assert "END:VCALENDAR" in ics_text
    assert "SUMMARY:[DEADLINE] NSP Central Sector Scheme" in ics_text
    assert "BEGIN:VALARM" in ics_text
    assert "TRIGGER:-P7D" in ics_text
    assert "TRIGGER:-P3D" in ics_text
    assert "TRIGGER:-P1D" in ics_text
