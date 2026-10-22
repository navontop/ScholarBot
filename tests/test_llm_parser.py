import pytest
from core.llm import (
    classify_intent_with_regex,
    extract_profile_with_regex,
    is_hindi_or_hinglish,
    parse_student_profile,
)

def test_free_text_profile_extraction():
    text = "I'm from Rajasthan, OBC, doing B.Tech, family income 3 lakh, 82% in 12th, my name is Rahul"
    profile = extract_profile_with_regex(text)
    assert profile.state == "Rajasthan"
    assert profile.category == "OBC"
    assert profile.course == "B.Tech / B.E."
    assert profile.family_income == 300000.0
    assert profile.marks_percentage == 82.0
    assert profile.student_name == "Rahul"

def test_missing_fields_detection():
    # User only states state and marks
    text = "I scored 78% marks and I live in UP"
    profile = extract_profile_with_regex(text)
    assert profile.state == "Uttar Pradesh"
    assert profile.marks_percentage == 78.0
    assert "family_income" in profile.missing_fields
    assert "social_category" in profile.missing_fields

def test_intent_classification():
    assert classify_intent_with_regex("check my income certificate") == "audit_document"
    assert classify_intent_with_regex("verify document for rejection") == "audit_document"
    assert classify_intent_with_regex("when is the deadline?") == "deadlines"
    assert classify_intent_with_regex("show calendar alarms") == "deadlines"
    assert classify_intent_with_regex("what if my income was 2 lakh?") == "what_if"
    assert classify_intent_with_regex("give me the concierge pack with SOP essay") == "concierge_pack"
    assert classify_intent_with_regex("namaste kaise ho") == "small_talk"
    assert classify_intent_with_regex("find scholarships for me") == "find_scholarships"

def test_hindi_hinglish_detection():
    assert is_hindi_or_hinglish("kya mujhe scholarship milegi?") is True
    assert is_hindi_or_hinglish("mera income certificate check karo") is True
    assert is_hindi_or_hinglish("नमस्ते मुझे छात्रवृत्ति चाहिए") is True
    assert is_hindi_or_hinglish("Hello, please find scholarships for me") is False

@pytest.mark.asyncio
async def test_asi1_primary_profile_extraction_success():
    from unittest.mock import patch
    import json
    from core.llm import parse_student_profile

    fake_llm_response = json.dumps({
        "student_name": "Aman Verma",
        "state": "Rajasthan",
        "category": "OBC",
        "family_income": 300000.0,
        "course": "B.Tech / B.E.",
        "marks_percentage": 84.5,
        "gender": "Male",
        "disability": False,
        "minority": False,
        "year_of_study": 2,
        "missing_fields": []
    })

    with patch("core.llm.call_asi1_chat", return_value=fake_llm_response):
        profile = await parse_student_profile("main Rajasthan se hu, OBC, income 3 lakh, B.Tech, 84.5% marks, mera naam Aman Verma hai")
        assert profile.student_name == "Aman Verma"
        assert profile.state == "Rajasthan"
        assert profile.category == "OBC"
        assert profile.family_income == 300000.0
        assert profile.marks_percentage == 84.5

@pytest.mark.asyncio
async def test_asi1_primary_intent_classification_success():
    from unittest.mock import patch
    from core.llm import classify_intent

    with patch("core.llm.call_asi1_chat", return_value="deadlines"):
        intent = await classify_intent("kab tak form bhar sakte hain?")
        assert intent == "deadlines"

@pytest.mark.asyncio
async def test_asi1_failure_fallback_to_regex():
    from unittest.mock import patch
    from core.llm import parse_student_profile, classify_intent

    # Test when LLM returns None / network error
    with patch("core.llm.call_asi1_chat", return_value=None):
        profile = await parse_student_profile("I am from Rajasthan, OBC, doing B.Tech, family income 2.5 lakh, 80% marks")
        assert profile.state == "Rajasthan"
        assert profile.category == "OBC"
        assert profile.family_income == 250000.0

        intent = await classify_intent("check my income certificate")
        assert intent == "audit_document"

@pytest.mark.asyncio
async def test_grounded_explanation_blocks_invented_rupees():
    from unittest.mock import patch
    from core.llm import generate_grounded_explanation
    from core.models import ScholarshipItem, StudentProfile

    scheme = ScholarshipItem(
        id="test_sc",
        name="Test Merit Scholarship",
        provider="Govt of India",
        portal="NSP",
        portal_url="https://scholarships.gov.in",
        amount="₹50,000 per year",
        amount_value=50000.0,
        category_list=["All"],
        min_marks=75.0,
        max_family_income=250000.0,
        applicable_states=["All"],
        gender="All",
        deadline="2026-11-30",
        match_status="eligible",
        match_score=95
    )
    profile = StudentProfile(
        student_name="Pooja",
        state="Rajasthan",
        category="General",
        family_income=200000.0,
        marks_percentage=85.0
    )

    # LLM hallucinates an ungrounded ₹99,999 amount not in scheme or profile
    hallucinated_text = "Congratulations Pooja! You qualify for a special bonus grant of ₹99,999 under this scheme."
    with patch("core.llm.call_asi1_chat", return_value=hallucinated_text):
        explanation = await generate_grounded_explanation(scheme, profile, lang_hindi=False)
        # Hallucinated amount must be rejected, triggering safe fallback
        assert "₹99,999" not in explanation
        assert "₹200,000" in explanation or "₹250,000" in explanation
