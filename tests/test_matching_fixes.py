import pytest
from core.matching import (
    normalize_state,
    normalize_course,
    normalize_category,
    evaluate_scheme,
    match_scholarships
)
from core.models import StudentProfile, ScholarshipItem
from core.llm import extract_profile_with_regex, generate_grounded_explanation

def test_normalize_state_safe_matching():
    # "income up to 3 lakh, Bihar" -> Bihar (must NOT match 'up' to Uttar Pradesh)
    assert normalize_state("income up to 3 lakh, Bihar") == "Bihar"
    
    # "I am an OBC student" -> All / no state (must NOT match 'an' to Andaman)
    assert normalize_state("I am an OBC student") == "All"
    
    # Explicit "from UP" or "state: UP" -> Uttar Pradesh
    assert normalize_state("I am from UP") == "Uttar Pradesh"
    assert normalize_state("state: UP") == "Uttar Pradesh"
    assert normalize_state("domicile: bihar") == "Bihar"

def test_normalize_course_safe_matching():
    # "I want to be a doctor, MBBS" -> MBBS (must NOT match 'be' to B.Tech / B.E.)
    course = normalize_course("I want to be a doctor, MBBS")
    assert course == "MBBS / BDS / Medical"
    
    # "I am doing BE in computer science" -> B.Tech / B.E.
    assert normalize_course("doing BE in computer science") == "B.Tech / B.E."

def test_gender_from_relative_not_user_gender():
    # "my sister also needs help" must NOT set user gender to Female
    p1 = extract_profile_with_regex("My sister also needs help with engineering scholarships")
    assert p1.gender != "Female"
    assert p1.gender == "All"
    
    # Direct applicant gender
    p2 = extract_profile_with_regex("I am a girl studying B.Tech in Delhi")
    assert p2.gender == "Female"

def test_course_filtering():
    # Scheme requires B.Tech, student is Medical
    scheme = {
        "id": "aicte_pragati_girls",
        "name": "AICTE Pragati",
        "eligibility": {
            "categories": ["General", "OBC"],
            "courses": ["B.Tech / B.E.", "Diploma / Polytechnic"],
            "states": ["All"],
            "gender": "Female",
            "min_marks": 50.0,
            "max_family_income": 800000.0,
            "min_year_of_study": 1
        }
    }
    profile_med = StudentProfile(
        student_name="Ananya",
        course="MBBS / BDS / Medical",
        gender="Female",
        category="General",
        family_income=300000.0,
        marks_percentage=80.0,
        state="Delhi"
    )
    status, score, reason = evaluate_scheme(scheme, profile_med)
    assert status == "ineligible"
    assert "course" in reason.lower()

def test_min_year_of_study_filtering():
    scheme = {
        "id": "senior_research_grant",
        "name": "Senior Degree Grant",
        "eligibility": {
            "categories": ["General"],
            "courses": ["B.Tech / B.E."],
            "states": ["All"],
            "gender": "All",
            "min_marks": 50.0,
            "max_family_income": 800000.0,
            "min_year_of_study": 3
        }
    }
    profile_year1 = StudentProfile(
        course="B.Tech / B.E.",
        year_of_study=1,
        category="General",
        family_income=300000.0,
        marks_percentage=80.0
    )
    status, score, reason = evaluate_scheme(scheme, profile_year1)
    assert status == "ineligible"
    assert "year" in reason.lower()

def test_category_check_no_general_shortcut():
    # Scheme exclusively for SC/ST
    scheme = {
        "id": "post_matric_sc",
        "name": "Post-Matric SC",
        "eligibility": {
            "categories": ["SC", "ST"],
            "courses": ["B.Tech / B.E."],
            "states": ["All"],
            "gender": "All",
            "min_marks": 50.0,
            "max_family_income": 500000.0
        }
    }
    profile_gen = StudentProfile(
        category="General",
        course="B.Tech / B.E.",
        family_income=200000.0,
        marks_percentage=80.0
    )
    status, score, reason = evaluate_scheme(scheme, profile_gen)
    assert status == "ineligible"

def test_unknown_state_does_not_match_state_only_schemes():
    scheme = {
        "id": "raj_post_matric",
        "name": "Rajasthan Post-Matric",
        "eligibility": {
            "categories": ["General", "OBC"],
            "courses": ["B.Tech / B.E."],
            "states": ["rajasthan"],
            "gender": "All",
            "min_marks": 50.0,
            "max_family_income": 500000.0
        }
    }
    # User with unspecified/unknown state ("All") must NOT get state-restricted scheme
    profile_unknown_state = StudentProfile(
        state="All",
        course="B.Tech / B.E.",
        category="General",
        family_income=200000.0,
        marks_percentage=80.0
    )
    status, score, reason = evaluate_scheme(scheme, profile_unknown_state)
    assert status == "ineligible"

@pytest.mark.asyncio
async def test_detail_view_explanation_for_ineligible_scheme():
    scheme = ScholarshipItem(
        id="high_cutoff_merit",
        name="High Cutoff Merit",
        provider="Govt",
        portal="NSP",
        portal_url="https://scholarships.gov.in",
        amount="₹50,000",
        min_marks=85.0,
        max_family_income=250000.0,
        applicable_states=["All"],
        match_status="ineligible",
        match_reason="Academic marks 65.0% below minimum 85.0%."
    )
    profile = StudentProfile(
        marks_percentage=65.0,
        family_income=200000.0
    )
    explanation = await generate_grounded_explanation(scheme, profile)
    # Must NOT claim student qualifies!
    assert "qualifies" not in explanation.lower() or "not" in explanation.lower()
    assert "below minimum" in explanation.lower() or "ineligible" in explanation.lower() or "does not meet" in explanation.lower()
