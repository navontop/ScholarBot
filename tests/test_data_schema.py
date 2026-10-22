import json
import os
import re
import pytest

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SCHOLARSHIPS_FILE = os.path.join(DATA_DIR, "scholarships.json")
DOC_RULES_FILE = os.path.join(DATA_DIR, "doc_rules.json")

def test_scholarships_schema():
    with open(SCHOLARSHIPS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) >= 80, f"Should have at least 80 verified scholarships, found {len(data)}"

    ids = set()
    for item in data:
        assert "id" in item
        assert item["id"] not in ids, f"Duplicate ID: {item['id']}"
        ids.add(item["id"])

        assert "name" in item and len(item["name"]) > 5
        assert "provider" in item
        assert "portal" in item
        assert "portal_url" in item and item["portal_url"].startswith("https://"), f"Non-https portal_url in {item['id']}"
        assert "apply_url" in item and item["apply_url"].startswith("https://"), f"Non-https apply_url in {item['id']}"
        assert "source_url" in item and item["source_url"].startswith("https://"), f"Non-https source_url in {item['id']}"
        assert "amount" in item
        assert "eligibility" in item

        elig = item["eligibility"]
        assert "categories" in elig and len(elig["categories"]) > 0
        assert "min_marks" in elig and isinstance(elig["min_marks"], (int, float))
        assert "max_family_income" in elig and elig["max_family_income"] > 0
        assert "states" in elig and len(elig["states"]) > 0
        assert "gender" in elig

        # ISO date check (YYYY-MM-DD or null if unverified for 2026-27 cycle)
        assert "deadline" in item
        if item["deadline"] is not None:
            assert re.match(r'^\d{4}-\d{2}-\d{2}$', item["deadline"])
        assert "last_verified" in item
        if item.get("verified"):
            assert re.match(r'^\d{4}-\d{2}-\d{2}$', item["last_verified"])
        else:
            assert item["last_verified"] is None
        assert "verified" in item

def test_girls_and_pwd_minimum_counts():
    with open(SCHOLARSHIPS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    girls_schemes = [
        s for s in data 
        if s.get("gender") == "Female" or s.get("eligibility", {}).get("gender", "").lower() == "female"
    ]
    pwd_schemes = [
        s for s in data 
        if s.get("disability_required") or s.get("eligibility", {}).get("disability_required")
    ]

    assert len(girls_schemes) >= 10, f"Expected at least 10 girls schemes, got {len(girls_schemes)}"
    assert len(pwd_schemes) >= 8, f"Expected at least 8 PwD schemes, got {len(pwd_schemes)}"

def test_all_28_states_and_8_uts_have_coverage():
    from core.matching import match_scholarships
    from core.models import StudentProfile

    all_28_states = [
        "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
        "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
        "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
        "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
        "Uttar Pradesh", "Uttarakhand", "West Bengal"
    ]
    all_8_uts = [
        "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
        "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry"
    ]

    for state in all_28_states + all_8_uts:
        profile = StudentProfile(
            student_name=f"Student of {state}",
            state=state,
            category="OBC",
            family_income=200000.0,
            course="B.Tech / B.E.",
            marks_percentage=75.0,
            gender="All"
        )
        eligible, _ = match_scholarships(profile)
        assert len(eligible) > 0, f"State/UT '{state}' has no eligible scholarships for typical profile"

def test_past_deadlines_show_as_closed():
    from core.deadlines import calculate_deadline_metrics

    # Test past date (before Oct 22, 2026)
    days, tier, badge = calculate_deadline_metrics("2026-05-31")
    assert days < 0
    assert tier == "CLOSED"
    assert "Closed" in badge

def test_doc_rules_schema():
    with open(DOC_RULES_FILE, "r", encoding="utf-8") as f:
        rules = json.load(f)

    assert "default" in rules
    for scheme_id, rule in rules.items():
        assert "mandatory" in rule and len(rule["mandatory"]) > 0
        assert "warning" in rule
        assert "tips" in rule and len(rule["tips"]) > 0
        assert "steps" in rule and len(rule["steps"]) > 0
        assert "portal" in rule and rule["portal"].startswith("http")
