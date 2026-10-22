import pytest
import asyncio
import inspect
from core.llm import (
    call_asi1_chat,
    classify_intent,
    classify_intent_with_regex,
    parse_student_profile,
    extract_profile_with_regex,
    generate_grounded_explanation
)
from core.models import ScholarshipItem, StudentProfile

def test_llm_functions_are_async():
    assert inspect.iscoroutinefunction(call_asi1_chat)
    assert inspect.iscoroutinefunction(classify_intent)
    assert inspect.iscoroutinefunction(parse_student_profile)
    assert inspect.iscoroutinefunction(generate_grounded_explanation)

@pytest.mark.asyncio
async def test_fast_intent_classification_bypasses_network():
    # Obvious intents should resolve instantaneously without network
    intent = await classify_intent("check my income certificate")
    assert intent == "audit_document"
    
    intent_deadlines = await classify_intent("what is the application deadline?")
    assert intent_deadlines == "deadlines"

@pytest.mark.asyncio
async def test_fast_profile_parsing_bypasses_network_when_complete():
    # Fully specified profile resolves via regex without network
    text = "I am from Bihar, OBC, B.Tech student, annual income 2.5 lakh, marks 80%"
    profile = await parse_student_profile(text)
    assert profile.state == "Bihar"
    assert profile.category == "OBC"
    assert profile.course == "B.Tech / B.E."
    assert profile.family_income == 250000.0
    assert profile.marks_percentage == 80.0

@pytest.mark.asyncio
async def test_grounded_explanation_handles_ineligible_async():
    scheme = ScholarshipItem(
        id="sample_scheme",
        name="Sample Merit Scholarship",
        provider="Govt",
        portal="NSP",
        portal_url="https://scholarships.gov.in",
        amount="₹20,000",
        match_status="ineligible",
        match_reason="Income ₹500,000 exceeds ceiling of ₹250,000."
    )
    profile = StudentProfile(family_income=500000.0)
    exp = await generate_grounded_explanation(scheme, profile)
    assert "ineligible" in exp.lower() or "exceeds" in exp.lower()
