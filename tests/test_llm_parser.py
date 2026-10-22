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
