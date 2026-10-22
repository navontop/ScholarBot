import pytest
from datetime import datetime, timezone
from core.doc_auditor import audit_document_compliance, parse_date_flexibly, mask_sensitive_identifiers
from core.models import DocumentAuditRequest, StudentProfile

def test_parse_date_flexibly_all_formats():
    assert parse_date_flexibly("14 August 2024") is not None
    assert parse_date_flexibly("14-Aug-24") is not None
    assert parse_date_flexibly("2024-08-14") is not None
    assert parse_date_flexibly("15/09/2026") is not None
    assert parse_date_flexibly("invalid-date-string") is None

def test_unparseable_date_reports_warn():
    doc_text = "Income Certificate\nApplicant: Rahul Sharma\nIncome: Rs 150000\nNo date mentioned"
    profile = StudentProfile(student_name="Rahul Sharma", state="Rajasthan")
    req = DocumentAuditRequest(
        session_id="test",
        scheme_id="nsp_central_sector",
        doc_type="income_certificate",
        doc_text=doc_text,
        profile=profile
    )
    res = audit_document_compliance(req, scheme_income_cap=450000.0)
    date_check = next((c for c in res.checks if "Date" in c.check_name or "Validity" in c.check_name), None)
    assert date_check is not None
    assert date_check.status == "WARN"
    assert date_check.status != "PASS"

def test_any_fail_causes_overall_fail():
    # Stale certificate (> 12 months for 12-month validity scheme)
    doc_text = "Income Certificate\nApplicant: Rahul Sharma\nIncome: Rs 150000\nDate: 01-Jan-2023"
    profile = StudentProfile(student_name="Rahul Sharma")
    req = DocumentAuditRequest(
        session_id="test",
        scheme_id="nsp_central_sector",
        doc_type="income_certificate",
        doc_text=doc_text,
        profile=profile
    )
    res = audit_document_compliance(req, scheme_income_cap=450000.0)
    assert any(c.status == "FAIL" for c in res.checks)
    assert res.overall_status == "FAIL"

def test_npci_and_name_skipped_are_info_not_pass():
    doc_text = "Income Certificate\nApplicant: Rahul Sharma\nIncome: Rs 150000\nDate: 15-Sep-2026"
    profile = StudentProfile(student_name="Student")  # default name, skipped check
    req = DocumentAuditRequest(
        session_id="test",
        scheme_id="nsp_central_sector",
        doc_type="income_certificate",
        doc_text=doc_text,
        profile=profile
    )
    res = audit_document_compliance(req, scheme_income_cap=450000.0)
    npci_check = next((c for c in res.checks if "NPCI" in c.check_name or "DBT" in c.check_name), None)
    assert npci_check is not None
    assert npci_check.status == "INFO"

def test_doc_type_marksheet_not_treated_as_income_cert():
    doc_text = "Class 12th Board Marksheet\nStudent: Priya Sharma\nMarks Obtained: 88%\nDate: 10-May-2026\nBoard Seal: Present"
    profile = StudentProfile(student_name="Priya Sharma", marks_percentage=88.0)
    req = DocumentAuditRequest(
        session_id="test",
        scheme_id="nsp_central_sector",
        doc_type="marksheet",
        doc_text=doc_text,
        profile=profile
    )
    res = audit_document_compliance(req, scheme_income_cap=450000.0)
    # Marksheet should not complain about missing income amount!
    income_check = next((c for c in res.checks if "Income Ceiling" in c.check_name), None)
    assert income_check is None
    assert res.overall_status == "PASS"

def test_aadhaar_masked_before_log():
    raw = "Applicant Aadhaar: 9876 5432 1098"
    masked = mask_sensitive_identifiers(raw)
    assert "9876 5432 1098" not in masked
    assert "XXXX-XXXX-1098" in masked
