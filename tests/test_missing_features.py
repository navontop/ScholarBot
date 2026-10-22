import pytest
from core.matching import load_scholarships
from core.deadlines import generate_ics_calendar
from core.models import ScholarshipItem, StudentProfile

def test_ics_has_stable_hash_uid():
    ics1 = generate_ics_calendar("AICTE Pragati", "2026-12-31", "https://scholarships.gov.in")
    ics2 = generate_ics_calendar("AICTE Pragati", "2026-12-31", "https://scholarships.gov.in")
    # Same input produces identical UID (stable SHA256 hash)
    uid1 = [line for line in ics1.splitlines() if line.startswith("UID:")][0]
    uid2 = [line for line in ics2.splitlines() if line.startswith("UID:")][0]
    assert uid1 == uid2
    assert "@scholarbot" in uid1

def test_compare_schemes_logic():
    schemes = load_scholarships()
    s1 = schemes[0] # Central Sector
    s2 = schemes[1] # AICTE Pragati
    
    # Comparison table generation logic
    comp_md = (
        f"| Feature | {s1['name'][:25]} | {s2['name'][:25]} |\n"
        f"|---|---|---|\n"
        f"| **Amount** | {s1['amount']} | {s2['amount']} |\n"
        f"| **Income Ceiling** | ₹{s1['eligibility']['max_family_income']:,} | ₹{s2['eligibility']['max_family_income']:,} |\n"
        f"| **Min Marks** | {s1['eligibility']['min_marks']}% | {s2['eligibility']['min_marks']}% |\n"
        f"| **Gender** | {s1['eligibility']['gender']} | {s2['eligibility']['gender']} |\n"
        f"| **Portal** | {s1['portal']} | {s2['portal']} |\n"
    )
    assert s1['name'][:20] in comp_md
    assert s2['name'][:20] in comp_md
    assert "Income Ceiling" in comp_md

def test_explain_scheme_logic():
    schemes = load_scholarships()
    pragati = next(s for s in schemes if "pragati" in s["id"])
    assert pragati is not None
    assert "₹50,000" in pragati["amount"]
    assert pragati["eligibility"]["gender"] == "Female"
