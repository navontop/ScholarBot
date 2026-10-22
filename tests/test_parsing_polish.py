import pytest
from core.matching import normalize_state, match_scholarships, evaluate_scheme, load_scholarships
from core.llm import extract_profile_with_regex
from core.models import StudentProfile

def test_hinglish_and_short_state_codes():
    # 1. "main UP se hu, OBC, btech, 2 lakh income, 80%"
    text1 = "main UP se hu, OBC, btech, 2 lakh income, 80%"
    assert normalize_state(text1) == "Uttar Pradesh"
    prof1 = extract_profile_with_regex(text1)
    assert prof1.state == "Uttar Pradesh"
    assert prof1.category == "OBC"
    assert prof1.course == "B.Tech / B.E."
    assert prof1.family_income == 200000.0
    assert prof1.marks_percentage == 80.0

    # 2. "I am from MP"
    text2 = "I am from MP"
    assert normalize_state(text2) == "Madhya Pradesh"
    prof2 = extract_profile_with_regex(text2)
    assert prof2.state == "Madhya Pradesh"

    # 3. Bare words must NEVER match state codes
    assert normalize_state("woke up early morning to study") == "All"
    assert normalize_state("speed up the application process") == "All"

def test_unknown_gender_does_not_silently_mark_girls_schemes_eligible():
    schemes = load_scholarships()
    pragati = next(s for s in schemes if s["id"] == "aicte_pragati_girls")
    
    # Profile with unknown gender (gender="All")
    prof = StudentProfile(
        student_name="Student",
        state="Uttar Pradesh",
        category="General",
        course="B.Tech / B.E.",
        family_income=200000.0,
        marks_percentage=85.0,
        gender="All"  # Unknown
    )
    status, score, reason = evaluate_scheme(pragati, prof)
    # Must NOT be eligible
    assert status != "eligible", f"Unknown gender should not be marked eligible for girls-only scheme, got status={status}"
    assert "maybe" in reason.lower() or "confirm gender" in reason.lower() or "girls only" in reason.lower()
