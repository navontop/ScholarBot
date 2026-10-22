import pytest
import uuid
from agents.coordinator import handle_chat_message
from core.cards import (
    get_action_hub_card,
    get_intake_form_card,
    get_profile_review_card,
    get_carousel_card,
    get_scheme_detail_card,
    get_audit_result_card,
    get_deadlines_card
)
from core.models import StudentProfile, ScholarshipItem, DocumentAuditResponse, DeadlineItem
from uagents_core.types import DeliveryStatus

class FakeMsg:
    def __init__(self, content: str):
        self._content = content
        self.msg_id = uuid.uuid4()
    def text(self):
        return self._content
    @property
    def content(self):
        return []

class DummyStorage:
    def __init__(self):
        self._store = {}
    def get(self, k, default=None):
        return self._store.get(k, default)
    def set(self, k, v):
        self._store[k] = v
    def has(self, k):
        return k in self._store

class DummyContext:
    def __init__(self, logger):
        self.logger = logger
        self.storage = DummyStorage()
        self.sent_messages = []
    async def send(self, destination, message):
        self.sent_messages.append((destination, message))
        return DeliveryStatus.DELIVERED
    async def send_and_receive(self, destination, message, response_type=None, timeout=3.0):
        return None, DeliveryStatus.FAILED

@pytest.mark.asyncio
async def test_form_accepts_flat_and_nested_payloads():
    import logging
    logger = logging.getLogger("test_cards")
    ctx = DummyContext(logger)

    # 1. Flat payload (top-level keys)
    flat_payload = (
        '{"action": "submit_intake", "state": "Madhya Pradesh", "marks": "82", '
        '"family_income": 220000, "course": "B.Tech / B.E.", "category": "OBC"}'
    )
    msg1 = FakeMsg(flat_payload)
    await handle_chat_message(ctx, "student_flat", msg1)

    profile_flat = ctx.storage.get("profile:student_flat")
    assert profile_flat is not None
    assert profile_flat["state"] == "Madhya Pradesh"
    assert profile_flat["marks_percentage"] == 82.0
    assert profile_flat["family_income"] == 220000.0

    # 2. Nested payload (keys inside 'values')
    nested_payload = (
        '{"action": "submit_intake", "values": {"state": "Uttar Pradesh", "marks": 78, '
        '"family_income": "180000", "course": "MBBS / BDS / Medical", "category": "SC"}}'
    )
    msg2 = FakeMsg(nested_payload)
    await handle_chat_message(ctx, "student_nested", msg2)

    profile_nested = ctx.storage.get("profile:student_nested")
    assert profile_nested is not None
    assert profile_nested["state"] == "Uttar Pradesh"
    assert profile_nested["marks_percentage"] == 78.0
    assert profile_nested["family_income"] == 180000.0

@pytest.mark.asyncio
async def test_form_tolerates_malformed_inputs_without_crash():
    import logging
    logger = logging.getLogger("test_cards")
    ctx = DummyContext(logger)

    # Garbage numbers, missing keys, unexpected types
    corrupt_payload = '{"action": "submit_intake", "values": {"marks": "invalid_percent", "family_income": [1,2,3]}}'
    msg = FakeMsg(corrupt_payload)
    await handle_chat_message(ctx, "student_corrupt", msg)
    assert len(ctx.sent_messages) > 0

def test_every_user_facing_card_has_back_to_menu():
    profile = StudentProfile(student_name="Priyanshu")
    scheme = ScholarshipItem(
        id="nsp_central_sector",
        name="Central Sector",
        provider="Govt",
        portal="NSP",
        portal_url="https://scholarships.gov.in",
        amount="20000",
        match_score=95,
        deadline="2026-11-30",
        verified=False,
        match_reason="Eligible"
    )
    audit = DocumentAuditResponse(
        session_id="s1",
        scheme_id="nsp_central_sector",
        doc_type="income_certificate",
        overall_status="PASS",
        readiness_score=90,
        checks=[],
        extracted_fields={},
        action_plan=[],
        disclaimer="Advisory"
    )
    deadline = DeadlineItem(
        scheme_id="s1",
        scheme_name="Central Sector",
        deadline_date="2026-11-30",
        days_remaining=40,
        urgency_tier="OPEN",
        badge_label="Open",
        portal_url="https://scholarships.gov.in",
        ics_calendar_data="BEGIN:VCALENDAR\nEND:VCALENDAR"
    )

    cards = [
        ("intake_form", get_intake_form_card(profile)),
        ("profile_review", get_profile_review_card(profile)),
        ("carousel", get_carousel_card([scheme])),
        ("scheme_detail", get_scheme_detail_card(scheme, {})),
        ("audit_result", get_audit_result_card(audit)),
        ("deadlines", get_deadlines_card([deadline]))
    ]

    for name, card in cards:
        card_str = str(card).lower()
        has_back = "back_to_hub" in card_str or "back_to_menu" in card_str or "open_hub" in card_str
        assert has_back, f"Card '{name}' does not contain a 'back to menu' / 'back_to_hub' action: {card}"
