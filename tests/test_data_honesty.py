import pytest
import json
import os
from core.matching import load_scholarships
from core.cards import get_scheme_detail_card
from core.models import ScholarshipItem

def test_all_scholarships_data_unverified():
    schemes = load_scholarships()
    assert len(schemes) >= 15
    for s in schemes:
        assert s.get("verified") is False, f"Scheme {s['id']} should have verified=False"
        assert s.get("last_verified") is None, f"Scheme {s['id']} should have last_verified=None"

def test_card_shows_unverified_warning_for_unverified_schemes():
    scheme = ScholarshipItem(
        id="test_scheme",
        name="Test Scheme",
        provider="Ministry of Education",
        portal="NSP",
        portal_url="https://scholarships.gov.in",
        amount="₹20,000",
        deadline="2026-11-30",
        verified=False,
        last_verified=None
    )
    card = get_scheme_detail_card(scheme, {"mandatory": ["Income Certificate"]})
    rows = card.get("summary_rows", [])
    verif_row = next((r for r in rows if r["label"] == "Verification Status"), None)
    assert verif_row is not None
    assert verif_row["value"] == "Unverified, confirm on official portal"
