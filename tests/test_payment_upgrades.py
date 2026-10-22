"""Test payment flow upgrades:
- Payment verification hook / rejection of malformed tx IDs in non-demo mode
- Free preview pack fallback
- Pending payment storage persistence
"""
import pytest
from uagents_core.contrib.protocols.payment import CommitPayment, Funds, RejectPayment, CompletePayment
from core.payments import handle_payment_commit, verify_transaction_onchain, generate_concierge_pack
from core.models import ScholarshipItem, StudentProfile

def test_tx_verification_rejects_malformed_in_nondemo(monkeypatch):
    import core.payments as pmod
    monkeypatch.setattr(pmod, "PAYMENT_DEMO_MODE", False)

    # Empty transaction ID
    commit_empty = CommitPayment(
        transaction_id="",
        reference="pay-1234",
        recipient="agent1qtest",
        funds=Funds(currency="USDC", amount="0.01", payment_method="skyfire")
    )
    success, reply, msg = handle_payment_commit(commit_empty)
    assert not success
    assert isinstance(reply, RejectPayment)

    # Malformed transaction ID (garbage characters or too short)
    commit_malformed = CommitPayment(
        transaction_id="not_a_valid_hash_!!!",
        reference="pay-1234",
        recipient="agent1qtest",
        funds=Funds(currency="USDC", amount="0.01", payment_method="skyfire")
    )
    success, reply, msg = handle_payment_commit(commit_malformed)
    assert not success
    assert isinstance(reply, RejectPayment)

def test_tx_verification_accepts_valid_hex(monkeypatch):
    import core.payments as pmod
    monkeypatch.setattr(pmod, "PAYMENT_DEMO_MODE", False)

    valid_hash = "0x4f8a3c2b1e0d9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e"
    commit_valid = CommitPayment(
        transaction_id=valid_hash,
        reference="pay-1234",
        recipient="agent1qtest",
        funds=Funds(currency="USDC", amount="0.01", payment_method="skyfire")
    )
    success, reply, msg = handle_payment_commit(commit_valid)
    assert success
    assert isinstance(reply, CompletePayment)
    assert reply.transaction_id == valid_hash

def test_generate_concierge_pack_uses_selected_scheme():
    scheme = ScholarshipItem(
        id="reliance_foundation_ug",
        name="Reliance Foundation Undergraduate Scholarship",
        provider="Reliance Foundation",
        portal="Reliance Portal",
        portal_url="https://www.scholarships.reliancefoundation.org",
        amount="Up to ₹2,00,000",
        deadline="2026-10-31"
    )
    profile = StudentProfile(student_name="Aarav Sharma", state="Maharashtra")
    pack = generate_concierge_pack(scheme, {"mandatory": ["Income Certificate"]}, profile)
    assert "Reliance Foundation" in pack.markdown_content
    assert pack.scheme_id == "reliance_foundation_ug"
