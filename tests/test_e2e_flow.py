import asyncio
import json
import os
import sys
from uuid import uuid4
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from uagents_core.contrib.protocols.chat import ChatMessage, TextContent
from agents.coordinator import (
    coordinator_agent,
    handle_chat_message,
    get_or_create_profile,
    USER_PROFILES,
)

class MockContext:
    def __init__(self):
        self.sent_messages = []
        self.logger = coordinator_agent._logger

    async def send(self, destination: str, message):
        self.sent_messages.append((destination, message))

@pytest.mark.asyncio
async def test_e2e_conversation_flow():
    ctx = MockContext()
    user_address = "agent1q_test_student_user_123456789"

    # Step 1: User says greeting
    msg1 = ChatMessage(content=[TextContent(type="text", text="Hi, I need help finding scholarships")])
    await handle_chat_message(ctx, user_address, msg1)
    assert len(ctx.sent_messages) >= 2 # ACK + Response
    _, resp1 = ctx.sent_messages[-1]
    assert resp1.content[1].metadata["card_kind"] == "carousel"
    print("[E2E Step 1 Passed] Greeting triggered Action Hub carousel.")

    # Step 2: User provides free-text profile
    ctx.sent_messages.clear()
    msg2 = ChatMessage(content=[TextContent(
        type="text",
        text="I am from Rajasthan, OBC category, doing B.Tech, family income 2.2 lakh, 84% marks, my name is Priya"
    )])
    await handle_chat_message(ctx, user_address, msg2)
    _, resp2 = ctx.sent_messages[-1]
    assert resp2.content[1].metadata["card_kind"] == "review"
    saved_profile = USER_PROFILES[user_address]
    assert saved_profile.state == "Rajasthan"
    assert saved_profile.family_income == 220000.0
    assert saved_profile.marks_percentage == 84.0
    print("[E2E Step 2 Passed] Free text extracted into StudentProfile and Review Card rendered.")

    # Step 3: User confirms profile to match scholarships
    ctx.sent_messages.clear()
    msg3 = ChatMessage(content=[TextContent(type="text", text=json.dumps({"action": "confirm_and_match"}))])
    await handle_chat_message(ctx, user_address, msg3)
    _, resp3 = ctx.sent_messages[-1]
    assert resp3.content[1].metadata["card_kind"] == "carousel"
    payload = json.loads(resp3.content[1].metadata["card_payload"])
    assert len(payload["items"]) >= 2
    print(f"[E2E Step 3 Passed] Matched {len(payload['items'])} scholarships in interactive carousel.")

    # Step 4: User runs document pre-check
    ctx.sent_messages.clear()
    doc_payload = """
    Rajasthan Revenue Department Income Certificate Form I
    Applicant: Priya Sharma
    Annual Income: Rs 220000
    Issue Date: 12/09/2026
    Tehsildar Jaipur e-Signed
    """
    msg4 = ChatMessage(content=[TextContent(type="text", text=doc_payload)])
    await handle_chat_message(ctx, user_address, msg4)
    _, resp4 = ctx.sent_messages[-1]
    assert resp4.content[1].metadata["card_kind"] == "review"
    audit_data = json.loads(resp4.content[1].metadata["card_payload"])
    assert "Document Pre-Check Audit: PASS" in audit_data["title"]
    print("[E2E Step 4 Passed] Deterministic document pre-check returned PASS with readiness score.")

    # Step 5: User triggers Concierge Pack
    ctx.sent_messages.clear()
    msg5 = ChatMessage(content=[TextContent(type="text", text=json.dumps({"action": "request_concierge_pack", "scheme_id": "raj_postmatric_sje"}))])
    await handle_chat_message(ctx, user_address, msg5)
    _, resp5 = ctx.sent_messages[-1]
    assert resp5.content[1].metadata["card_kind"] == "detail"
    print("[E2E Step 5 Passed] Payment Protocol Concierge Pack request sent.")

    # Step 6: User commits payment via Payment Protocol (handle_payment_commit_msg)
    from uagents_core.contrib.protocols.payment import CommitPayment, Funds
    from agents.coordinator import handle_payment_commit_msg
    
    pay_req = next((msg for _, msg in ctx.sent_messages if hasattr(msg, "reference")), None)
    ref = pay_req.reference if pay_req else "pay-demo-ref"
    
    ctx.sent_messages.clear()
    commit_msg = CommitPayment(
        funds=Funds(currency="USDC", amount="0.01", payment_method="skyfire"),
        recipient=coordinator_agent.address,
        transaction_id="demo-tx-priya-12345",
        reference=ref,
        description="Payment for concierge pack",
        metadata={"scheme_id": "raj_postmatric_sje"}
    )
    await handle_payment_commit_msg(ctx, user_address, commit_msg)
    
    # Check that CompletePayment and text with Concierge Pack were sent
    _, resp6 = ctx.sent_messages[-1]
    assert "Payment verified!" in resp6.text()
    assert "Applicant Pre-Filled Dossier" in resp6.text()
    assert "Statement of Purpose" in resp6.text()
    print("[E2E Step 6 Passed] Payment completed and Concierge Pack delivered with custom SOP!")
