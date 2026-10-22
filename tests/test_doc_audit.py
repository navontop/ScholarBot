import pytest
from core.doc_auditor import audit_document_compliance, mask_sensitive_identifiers, parse_document_text
from core.models import DocumentAuditRequest, StudentProfile

def test_aadhaar_masking():
    raw = "My Aadhaar is 1234 5678 9012 and PAN is ABCDE1234F"
    masked = mask_sensitive_identifiers(raw)
    assert "1234 5678 9012" not in masked
    assert "XXXX-XXXX-9012" in masked
    assert "ABCDE1234F" not in masked

def test_valid_document_pass():
    doc_text = """
    GOVERNMENT OF RAJASTHAN - REVENUE DEPARTMENT
    Income Certificate (Form I)
    Certificate No: RJ-INC-2026-98124
    Applicant Name: Rahul Sharma
    Father Name: Mohan Sharma
    Total Annual Household Income: Rs 180,000
    Date of Issue: 15/09/2026
    Digitally Signed by Tehsildar (Jaipur)
    Verification QR Code: Present
    """
    profile = StudentProfile(student_name="Rahul Sharma", state="Rajasthan", family_income=180000.0)
    req = DocumentAuditRequest(
        session_id="test-session",
        scheme_id="raj_postmatric_sje",
        doc_type="income_certificate",
        doc_text=doc_text,
        profile=profile
    )
    result = audit_document_compliance(req, scheme_income_cap=250000.0)
    assert result.overall_status == "PASS"
    assert result.readiness_score >= 80

def test_expired_document_fail():
    # Certificate dated 14 months ago for Rajasthan SJE (mandates <= 6 months)
    doc_text = """
    Income Certificate
    Applicant Name: Rahul Sharma
    Total Annual Income: Rs 200,000
    Date of Issue: 10/08/2025
    Tehsildar Signed
    """
    profile = StudentProfile(student_name="Rahul Sharma", state="Rajasthan", family_income=200000.0)
    req = DocumentAuditRequest(
        session_id="test-session",
        scheme_id="raj_postmatric_sje",
        doc_type="income_certificate",
        doc_text=doc_text,
        profile=profile
    )
    result = audit_document_compliance(req, scheme_income_cap=250000.0)
    # Must flag the validity problem
    val_check = next((c for c in result.checks if "Validity" in c.check_name), None)
    assert val_check is not None
    assert val_check.status == "FAIL"

def test_income_exceed_fail():
    doc_text = """
    Income Certificate
    Applicant Name: Rahul Sharma
    Total Annual Income: Rs 350,000
    Date of Issue: 10/09/2026
    Tehsildar Signed
    """
    profile = StudentProfile(student_name="Rahul Sharma", state="Rajasthan", family_income=350000.0)
    req = DocumentAuditRequest(
        session_id="test-session",
        scheme_id="raj_postmatric_sje",
        doc_type="income_certificate",
        doc_text=doc_text,
        profile=profile
    )
    result = audit_document_compliance(req, scheme_income_cap=250000.0)
    inc_check = next((c for c in result.checks if "Income" in c.check_name), None)
    assert inc_check is not None
    assert inc_check.status == "FAIL"
