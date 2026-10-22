import pytest
from core.matching import match_scholarships, normalize_category, normalize_course, normalize_state
from core.models import StudentProfile

def test_state_normalization():
    assert normalize_state("UP") == "Uttar Pradesh"
    assert normalize_state("i live in rajasthan") == "Rajasthan"
    assert normalize_state("dilli") == "Delhi"
    assert normalize_state("j&k") == "Jammu and Kashmir"
    assert normalize_state("chandigarh") == "Chandigarh"
    assert normalize_state("unknown land") == "All"

def test_category_normalization():
    assert normalize_category("obc") == "OBC"
    assert normalize_category("open") == "General"
    assert normalize_category("scheduled caste") == "SC"
    assert normalize_category("muslim") == "Minority"

def test_rajasthan_obc_student():
    profile = StudentProfile(
        student_name="Rahul Sharma",
        state="Rajasthan",
        category="OBC",
        family_income=200000.0,
        course="B.Tech / B.E.",
        marks_percentage=80.0,
        gender="Male"
    )
    eligible, close_misses = match_scholarships(profile)
    assert len(eligible) > 0
    ids = [s.id for s in eligible]
    # Must include Rajasthan Post-Matric SJE and NSP Central Sector
    assert "raj_postmatric_sje" in ids
    assert "nsp_central_sector" in ids
    # Must NOT include female-only Pragati or disability-only Saksham
    assert "aicte_pragati_girls" not in ids
    assert "aicte_saksham" not in ids

def test_min_marks_enforcement():
    # Student with 62% marks should not qualify for NSP Central Sector (requires 75%)
    profile = StudentProfile(
        state="Rajasthan",
        category="General",
        family_income=300000.0,
        course="B.Tech / B.E.",
        marks_percentage=62.0,
        gender="Male"
    )
    eligible, close_misses = match_scholarships(profile)
    eligible_ids = [s.id for s in eligible]
    assert "nsp_central_sector" not in eligible_ids

def test_disability_filter():
    # Non-disabled student must not see AICTE Saksham
    p1 = StudentProfile(course="B.Tech / B.E.", disability=False)
    m1, _ = match_scholarships(p1)
    assert "aicte_saksham" not in [s.id for s in m1]

    # Disabled student must see AICTE Saksham
    p2 = StudentProfile(course="B.Tech / B.E.", disability=True, marks_percentage=65.0, family_income=300000.0)
    m2, _ = match_scholarships(p2)
    assert "aicte_saksham" in [s.id for s in m2]

def test_gender_filter():
    # Male student must not see Pragati
    male_p = StudentProfile(course="B.Tech / B.E.", gender="Male", family_income=300000.0)
    male_m, _ = match_scholarships(male_p)
    assert "aicte_pragati_girls" not in [s.id for s in male_m]

    # Female student must see Pragati
    female_p = StudentProfile(course="B.Tech / B.E.", gender="Female", family_income=300000.0, marks_percentage=70.0)
    female_m, _ = match_scholarships(female_p)
    assert "aicte_pragati_girls" in [s.id for s in female_m]

def test_close_miss_detection():
    # Student with income ₹2,70,000 on Rajasthan SJE (cap ₹2,50,000)
    profile = StudentProfile(
        state="Rajasthan",
        category="OBC",
        family_income=270000.0,
        course="B.Tech / B.E.",
        marks_percentage=75.0,
        gender="Male"
    )
    eligible, close_misses = match_scholarships(profile)
    cm_ids = [s.id for s in close_misses]
    assert "raj_postmatric_sje" in cm_ids

def test_income_range_could_qualify():
    # Student whose income range straddles cap (2.0L - 2.8L on a 2.5L cap)
    profile = StudentProfile(
        state="Rajasthan",
        category="OBC",
        family_income=260000.0,
        family_income_min=200000.0,
        family_income_max=280000.0,
        course="B.Tech / B.E.",
        marks_percentage=75.0,
        gender="Male"
    )
    eligible, _ = match_scholarships(profile)
    raj_s = next((s for s in eligible if s.id == "raj_postmatric_sje"), None)
    assert raj_s is not None
    assert "confirm your income certificate" in raj_s.match_reason

def test_explainability_ineligible_and_close_miss():
    # Check that reasons contain actionable guidance ("What would make you eligible")
    from core.matching import evaluate_scheme, load_scholarships
    data = load_scholarships()
    sje = next(s for s in data if s["id"] == "raj_postmatric_sje")
    
    # Profile with high income
    p_high = StudentProfile(
        state="Rajasthan",
        category="OBC",
        family_income=600000.0,
        course="B.Tech / B.E.",
        marks_percentage=75.0,
        gender="Male"
    )
    status, _, reason = evaluate_scheme(sje, p_high)
    assert status == "ineligible"
    assert "What would make you eligible" in reason

def test_stacking_calculator():
    from core.matching import calculate_stacking_benefit
    profile = StudentProfile(
        student_name="Pooja Rao",
        state="Karnataka",
        category="OBC",
        family_income=200000.0,
        course="B.Tech / B.E.",
        marks_percentage=85.0,
        gender="Female"
    )
    eligible, _ = match_scholarships(profile)
    assert len(eligible) > 0
    stack = calculate_stacking_benefit(eligible)
    assert stack["total_potential_annual"] > 0
    assert len(stack["recommended_stack"]) >= 1
    assert "Smart Stacking Model" in stack["combination_notes"]
    assert len(stack["stack_breakdown"]) >= 1

def test_transgender_gender_handling():
    profile = StudentProfile(
        state="Rajasthan",
        category="SC",
        family_income=150000.0,
        course="B.Tech / B.E.",
        marks_percentage=75.0,
        gender="Transgender"
    )
    eligible, _ = match_scholarships(profile)
    # Transgender candidate should match central and state SC schemes
    ids = [s.id for s in eligible]
    assert "raj_postmatric_sje" in ids
