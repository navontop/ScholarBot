import pytest
import time
from uuid import uuid4
from uagents_core.contrib.protocols.payment import (
    CommitPayment,
    CompletePayment,
    Funds,
    RejectPayment,
    RequestPayment
)
from core.payments import (
    create_concierge_payment_request,
    handle_payment_commit,
    generate_concierge_pack
)
from core.models import ScholarshipItem, StudentProfile

def test_payment_request_contains_scheme_and_demo_labels():
    req = create_concierge_payment_request(
        recipient_address="agent1q_test",
        scheme_name="Rajasthan Post-Matric Scholarship",
        scheme_id="raj_post_matric_sje",
        session_id="session-123"
    )
    assert isinstance(req, RequestPayment)
    assert req.metadata.get("scheme_id") == "raj_post_matric_sje"
    assert "DEMO" in req.metadata.get("mode", "") or "TESTNET" in req.metadata.get("mode", "")
    assert req.deadline_seconds == 300

def test_payment_commit_validates_transaction_id():
    # Empty transaction ID must be rejected
    commit_empty = CommitPayment(
        funds=Funds(currency="USDC", amount="0.01", payment_method="skyfire"),
        recipient="agent1q_test",
        transaction_id="",
        reference="pay-ref-1",
        description="test",
        metadata={"scheme_id": "raj_post_matric_sje"}
    )
    ok, reply, msg = handle_payment_commit(commit_empty)
    assert not ok
    assert isinstance(reply, RejectPayment)

def test_payment_commit_uses_real_transaction_id_not_fake_hardcoded():
    real_tx = f"demo-tx-hash-{uuid4().hex[:12]}"
    commit = CommitPayment(
        funds=Funds(currency="USDC", amount="0.01", payment_method="skyfire"),
        recipient="agent1q_test",
        transaction_id=real_tx,
        reference="pay-ref-2",
        description="test",
        metadata={"scheme_id": "raj_post_matric_sje"}
    )
    ok, reply, msg = handle_payment_commit(commit)
    assert ok
    assert isinstance(reply, CompletePayment)
    assert reply.transaction_id == real_tx
    # Must NOT be fake static id
    assert reply.transaction_id != "tx-skyfire-demo-verified"
    assert "DEMO" in msg or "TESTNET" in msg

def test_concierge_pack_delivered_for_requested_scheme_not_default():
    scheme = ScholarshipItem(
        id="raj_post_matric_sje",
        name="Rajasthan Post-Matric Scholarship for SC/ST/SBC",
        provider="Social Justice Department Rajasthan",
        portal="SJMS Portal",
        portal_url="https://sjmsnew.rajasthan.gov.in",
        amount="100% Tuition Fee Reimbursement",
        applicable_states=["Rajasthan"],
        deadline="2026-11-30",
        description="Fee reimbursement scheme"
    )
    profile = StudentProfile(student_name="Rahul Meena", state="Rajasthan")
    pack = generate_concierge_pack(scheme, {"mandatory": ["Caste Certificate", "Fee Receipt"]}, profile)
    
    assert pack.scheme_id == "raj_post_matric_sje"
    assert "Rajasthan Post-Matric" in pack.markdown_content
    # Must not be NSP Central Sector
    assert "nsp_central_sector" != pack.scheme_id
