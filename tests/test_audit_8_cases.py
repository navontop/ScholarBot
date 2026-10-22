import pytest
from datetime import datetime, timezone, timedelta
from core.doc_auditor import audit_document_compliance
from core.models import DocumentAuditRequest, StudentProfile
from core.matching import load_scholarships

def get_income_cap_for_scheme(scheme_id: str) -> float:
    for s in load_scholarships():
        sid = s.get("id", "")
        if sid == scheme_id or sid.lower() == scheme_id.lower():
            elig = s.get("eligibility", {})
            if "max_family_income" in elig and elig["max_family_income"] is not None:
                return float(elig["max_family_income"])
    return 250000.0

def test_audit_case_1_fresh():
    # Fresh document dated 2 months ago with valid authority & QR code
    now = datetime.now(timezone.utc)
    fresh_date = (now - timedelta(days=60)).strftime("%d/%m/%Y")
    doc_text = f"""
    Government of Uttar Pradesh - Revenue Department
    Income Certificate
    Applicant: Rahul Sharma
    Total Family Income: Rs 200,000
    Date of Issue: {fresh_date}
    Issuing Authority: Tehsildar
    Verification: Digitally Signed QR Code Verified
    """
    req = DocumentAuditRequest(
        session_id="case1",
        scheme_id="nsp_central_sector",
        doc_type="income_certificate",
        doc_text=doc_text,
        profile=StudentProfile(student_name="Rahul Sharma", state="Uttar Pradesh", family_income=200000.0)
    )
    res = audit_document_compliance(req, scheme_income_cap=get_income_cap_for_scheme("nsp_central_sector"))
    val_check = next((c for c in res.checks if "Validity" in c.check_name), None)
    assert val_check is not None
    assert val_check.status == "PASS"
    stamp_check = next((c for c in res.checks if "Authority" in c.check_name or "Stamp" in c.check_name), None)
    assert stamp_check is not None
    assert stamp_check.status == "PASS"
    assert res.overall_status == "PASS"

def test_audit_case_2_14_months_old():
    # Dated 14 months ago (~425 days ago)
    now = datetime.now(timezone.utc)
    date_14m = (now - timedelta(days=425)).strftime("%d/%m/%Y")
    doc_text = f"""
    Income Certificate
    Applicant: Rahul Sharma
    Total Income: Rs 200,000
    Date of Issue: {date_14m}
    Issuing Authority: Tehsildar
    Verification: QR Code Present
    """
    req = DocumentAuditRequest(
        session_id="case2",
        scheme_id="nsp_central_sector",
        doc_type="income_certificate",
        doc_text=doc_text,
        profile=StudentProfile(student_name="Rahul Sharma")
    )
    res = audit_document_compliance(req, scheme_income_cap=get_income_cap_for_scheme("nsp_central_sector"))
    val_check = next((c for c in res.checks if "Validity" in c.check_name), None)
    assert val_check is not None
    # 14 months exceeds standard 12-month validity window
    assert val_check.status in ["FAIL", "WARN"]

def test_audit_case_3_26_months_old_august_format():
    # 26 months old with "14 August 2024" format (today is Oct 2026 => ~26 months old)
    doc_text = """
    Revenue Department
    Income Certificate
    Applicant: Rahul Sharma
    Annual Income: Rs 200,000
    Date of Issue: 14 August 2024
    Issuing Authority: Tehsildar
    Verification: Digitally Signed QR
    """
    req = DocumentAuditRequest(
        session_id="case3",
        scheme_id="nsp_central_sector",
        doc_type="income_certificate",
        doc_text=doc_text,
        profile=StudentProfile(student_name="Rahul Sharma")
    )
    res = audit_document_compliance(req, scheme_income_cap=get_income_cap_for_scheme("nsp_central_sector"))
    val_check = next((c for c in res.checks if "Validity" in c.check_name), None)
    assert val_check is not None
    assert val_check.status == "FAIL"

def test_audit_case_4_50_months_old():
    # Dated 50 months ago (~1500 days ago)
    doc_text = """
    Income Certificate
    Applicant: Rahul Sharma
    Income: Rs 200,000
    Date of Issue: 01/01/2022
    Issuing Authority: Tehsildar
    Verification: QR Code
    """
    req = DocumentAuditRequest(
        session_id="case4",
        scheme_id="nsp_central_sector",
        doc_type="income_certificate",
        doc_text=doc_text,
        profile=StudentProfile(student_name="Rahul Sharma")
    )
    res = audit_document_compliance(req, scheme_income_cap=get_income_cap_for_scheme("nsp_central_sector"))
    val_check = next((c for c in res.checks if "Validity" in c.check_name), None)
    assert val_check is not None
    assert val_check.status == "FAIL"

def test_audit_case_5_future_date():
    # Future dated certificate e.g. 15/12/2027
    doc_text = """
    Revenue Department
    Income Certificate
    Applicant: Rahul Sharma
    Annual Family Income: Rs 200,000
    Date of Issue: 15/12/2027
    Issuing Authority: Tehsildar
    Verification: QR Code
    """
    req = DocumentAuditRequest(
        session_id="case5",
        scheme_id="nsp_central_sector",
        doc_type="income_certificate",
        doc_text=doc_text,
        profile=StudentProfile(student_name="Rahul Sharma")
    )
    res = audit_document_compliance(req, scheme_income_cap=get_income_cap_for_scheme("nsp_central_sector"))
    val_check = next((c for c in res.checks if "Validity" in c.check_name), None)
    assert val_check is not None
    # Must fail or warn for future date, never PASS
    assert val_check.status in ["FAIL", "WARN"]
    assert val_check.status != "PASS"

def test_audit_case_6_garbage_date():
    # Unparseable / garbage date
    doc_text = """
    Income Certificate
    Applicant: Rahul Sharma
    Annual Income: Rs 200,000
    Date of Issue: not_a_real_date_xyz
    Issuing Authority: Tehsildar
    Verification: QR Code
    """
    req = DocumentAuditRequest(
        session_id="case6",
        scheme_id="nsp_central_sector",
        doc_type="income_certificate",
        doc_text=doc_text,
        profile=StudentProfile(student_name="Rahul Sharma")
    )
    res = audit_document_compliance(req, scheme_income_cap=get_income_cap_for_scheme("nsp_central_sector"))
    val_check = next((c for c in res.checks if "Validity" in c.check_name), None)
    assert val_check is not None
    assert val_check.status == "WARN"

def test_audit_case_7_income_over_cap():
    # Income ₹6,00,000 for NSP Central Sector (cap is ₹4,50,000 in scholarships.json)
    now = datetime.now(timezone.utc)
    fresh_date = (now - timedelta(days=30)).strftime("%d/%m/%Y")
    doc_text = f"""
    Income Certificate
    Applicant: Rahul Sharma
    Total Annual Income: Rs 600,000
    Date of Issue: {fresh_date}
    Issuing Authority: Tehsildar
    Verification: Digitally Signed QR
    """
    req = DocumentAuditRequest(
        session_id="case7",
        scheme_id="nsp_central_sector",
        doc_type="income_certificate",
        doc_text=doc_text,
        profile=StudentProfile(student_name="Rahul Sharma")
    )
    income_cap = get_income_cap_for_scheme("nsp_central_sector")
    assert income_cap == 450000.0, f"Expected 450000 for nsp_central_sector, got {income_cap}"
    res = audit_document_compliance(req, scheme_income_cap=income_cap)
    income_check = next((c for c in res.checks if "Income" in c.check_name or "Economic" in c.check_name), None)
    assert income_check is not None
    assert income_check.status == "FAIL"
    assert res.overall_status == "FAIL"

def test_audit_case_8_missing_stamp():
    # Authority present (Tehsildar), but no QR / stamp / barcode
    now = datetime.now(timezone.utc)
    fresh_date = (now - timedelta(days=30)).strftime("%d/%m/%Y")
    doc_text = f"""
    Income Certificate
    Applicant: Rahul Sharma
    Total Annual Income: Rs 200,000
    Date of Issue: {fresh_date}
    Issuing Authority: Tehsildar
    """
    req = DocumentAuditRequest(
        session_id="case8",
        scheme_id="nsp_central_sector",
        doc_type="income_certificate",
        doc_text=doc_text,
        profile=StudentProfile(student_name="Rahul Sharma")
    )
    res = audit_document_compliance(req, scheme_income_cap=get_income_cap_for_scheme("nsp_central_sector"))
    stamp_check = next((c for c in res.checks if "Authority" in c.check_name or "Stamp" in c.check_name), None)
    assert stamp_check is not None
    # Must WARN when stamp/QR is missing, PASS only if both authority and verification marker found
    assert stamp_check.status == "WARN"
    assert stamp_check.status != "PASS"
