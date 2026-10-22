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
    assert len(data) >= 15, "Should have at least 15 verified scholarships"

    ids = set()
    for item in data:
        assert "id" in item
        assert item["id"] not in ids, f"Duplicate ID: {item['id']}"
        ids.add(item["id"])

        assert "name" in item and len(item["name"]) > 5
        assert "provider" in item
        assert "portal" in item
        assert "portal_url" in item and item["portal_url"].startswith("http")
        assert "amount" in item
        assert "eligibility" in item

        elig = item["eligibility"]
        assert "categories" in elig and len(elig["categories"]) > 0
        assert "min_marks" in elig and isinstance(elig["min_marks"], (int, float))
        assert "max_family_income" in elig and elig["max_family_income"] > 0
        assert "states" in elig and len(elig["states"]) > 0
        assert "gender" in elig

        # ISO date check (YYYY-MM-DD)
        assert "deadline" in item
        assert re.match(r'^\d{4}-\d{2}-\d{2}$', item["deadline"])
        assert "last_verified" in item
        if item.get("verified"):
            assert re.match(r'^\d{4}-\d{2}-\d{2}$', item["last_verified"])
        else:
            assert item["last_verified"] is None
        assert "verified" in item

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
