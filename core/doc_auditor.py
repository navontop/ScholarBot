import difflib
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from core.models import AuditCheckItem, DocumentAuditRequest, DocumentAuditResponse, StudentProfile

logger = logging.getLogger("DocAuditor")

DOC_RULES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "doc_rules.json")

def load_doc_rules() -> dict:
    try:
        with open(DOC_RULES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Error loading {DOC_RULES_PATH}: {e}")
        return {}

DOC_RULES_DB = load_doc_rules()

MONTH_NAMES = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9, "sept": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12
}

from core.privacy import mask_sensitive_identifiers

def parse_date_flexibly(date_str: str) -> Optional[datetime]:
    """
    Robust multi-format date parser supporting:
    - 14 August 2024 / 14 Aug 24 / 14-Aug-2024 / 14-Aug-24
    - 2024-08-14 / 2024/08/14
    - 14/08/2024 / 14-08-2024 / 14.08.2024
    """
    if not date_str or len(date_str.strip()) < 6:
        return None

    cleaned = date_str.strip().lower()

    # Format: 14 August 2024 or 14-Aug-24
    word_match = re.search(r'(\d{1,2})[\s/-]+([a-z]{3,9})[\s/-]+(\d{2,4})', cleaned)
    if word_match:
        day = int(word_match.group(1))
        m_str = word_match.group(2)
        yr = int(word_match.group(3))
        if yr < 100:
            yr += 2000
        month = MONTH_NAMES.get(m_str) or MONTH_NAMES.get(m_str[:3])
        if month and 1 <= day <= 31 and 1990 <= yr <= 2040:
            try:
                return datetime(yr, month, day, tzinfo=timezone.utc)
            except Exception:
                pass

    # Format: YYYY-MM-DD or YYYY/MM/DD
    iso_match = re.search(r'(\d{4})[\s/-](\d{1,2})[\s/-](\d{1,2})', cleaned)
    if iso_match:
        yr = int(iso_match.group(1))
        month = int(iso_match.group(2))
        day = int(iso_match.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31:
            try:
                return datetime(yr, month, day, tzinfo=timezone.utc)
            except Exception:
                pass

    # Format: DD/MM/YYYY or DD-MM-YYYY
    dmy_match = re.search(r'(\d{1,2})[\s/.-](\d{1,2})[\s/.-](\d{2,4})', cleaned)
    if dmy_match:
        day = int(dmy_match.group(1))
        month = int(dmy_match.group(2))
        yr = int(dmy_match.group(3))
        if yr < 100:
            yr += 2000
        if 1 <= month <= 12 and 1 <= day <= 31:
            try:
                return datetime(yr, month, day, tzinfo=timezone.utc)
            except Exception:
                pass

    return None

def parse_document_text(raw_text: str) -> Dict[str, str]:
    """Extracts structured fields from raw OCR/pasted document text."""
    cleaned = raw_text.strip()
    extracted: Dict[str, str] = {}

    # Extract Income Amount
    income_match = re.search(r'(?:annual\s*income|family\s*income|total\s*income|aay|aamdani|income)[\s:=₹rs.]*(\d[\d,]{4,8})', cleaned, re.IGNORECASE)
    if income_match:
        extracted["income_amount"] = income_match.group(1).replace(",", "")
    else:
        lakh_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lpa)', cleaned, re.IGNORECASE)
        if lakh_match:
            extracted["income_amount"] = str(int(float(lakh_match.group(1)) * 100000))

    # Extract Marks %
    marks_match = re.search(r'(?:marks|percentage|aggregate|score)[\s:=]*(\d{1,2}(?:\.\d+)?)\s*%', cleaned, re.IGNORECASE)
    if not marks_match:
        marks_match = re.search(r'(\d{1,2}(?:\.\d+)?)\s*%', cleaned)
    if marks_match:
        extracted["marks_percentage"] = marks_match.group(1)

    # Extract Date strings
    date_patterns = [
        r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,-]+\d{2,4})\b',
        r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
        r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',
        r'\b(\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*-\d{2,4})\b'
    ]
    for pat in date_patterns:
        m = re.search(pat, cleaned, re.IGNORECASE)
        if m:
            extracted["issue_date"] = m.group(1)
            break

    # Extract Certificate Number
    cert_m = re.search(r'(?:certificate\s*(?:no|number)|praman\s*patra\s*kramank|application\s*no|rd\s*no)[\s:=]*([A-Za-z0-9/-]{5,25})', cleaned, re.IGNORECASE)
    if cert_m:
        extracted["certificate_number"] = cert_m.group(1)

    # Extract Authority / Signatory
    auth_m = re.search(r'\b(tehsildar|tahsildar|sdm|sub\s*divisional\s*magistrate|revenue\s*officer|bdo|collector|circle\s*officer|cno|principal|headmaster|registrar|board|cbse|icse|state\s*board|university|council|controller\s*of\s*examinations|secretary)\b', cleaned, re.IGNORECASE)
    if auth_m:
        extracted["issuing_authority"] = auth_m.group(1).title()

    # Extract Caste / Category
    cat_m = re.search(r'\b(obc|sc|st|general|ews|backward\s*class|scheduled\s*caste|scheduled\s*tribe|minority)\b', cleaned, re.IGNORECASE)
    if cat_m:
        extracted["category"] = cat_m.group(1).upper()

    # Extract Student Name
    name_m = re.search(r'(?:student\s*name|applicant\s*name|name\s*of\s*applicant|name|shri|smt|kumari)[\s:=]*([A-Za-z\s]{3,30})(?:\n|,|father|s/o|d/o)', cleaned, re.IGNORECASE)
    if name_m:
        cand = name_m.group(1).strip()
        if len(cand) > 3 and not any(w in cand.lower() for w in ["income", "certificate", "government", "revenue", "marksheet"]):
            extracted["student_name"] = cand.title()

    # Verification Markers
    has_qr = bool(re.search(r'\b(qr|qr-code|barcode|digitally\s*signed|e-sign(?:ed)?|verification\s*(?:code|marker|seal)|net\s*verified|seal|stamp)\b', cleaned, re.IGNORECASE))
    extracted["verification_marker"] = "Appears Present (Digital QR / e-Sign detected)" if has_qr else "Not clearly visible in text"

    return extracted

def audit_document_compliance(req: DocumentAuditRequest, scheme_income_cap: float = 250000.0) -> DocumentAuditResponse:
    """
    Executes deterministic compliance checks on student document against published government scheme rules.
    - Uses real datetime.now(timezone.utc).
    - If any check fails, overall status is FAIL.
    - Informational checks (NPCI DBT, skipped name) have status 'INFO' and do not artificially inflate the score.
    """
    # CRITICAL: Mask sensitive identifiers before logging or processing
    raw_doc = mask_sensitive_identifiers(req.doc_text)
    logger.info(f"[DocAuditor] Auditing document (doc_type='{req.doc_type}', scheme='{req.scheme_id}', text_len={len(raw_doc)} chars)")

    extracted = parse_document_text(raw_doc)
    profile = req.profile

    checks: List[AuditCheckItem] = []
    action_plan: List[str] = []
    score = 100

    # Retrieve scheme-specific document rules from database
    rule = DOC_RULES_DB.get(req.scheme_id, DOC_RULES_DB.get("default", {}))
    validity_limit_months = rule.get("validity_months", 12)

    # 1. Document Text Presence
    if not raw_doc or len(raw_doc.strip()) < 15:
        return DocumentAuditResponse(
            session_id=req.session_id,
            scheme_id=req.scheme_id,
            doc_type=req.doc_type,
            overall_status="WARN",
            readiness_score=40,
            extracted_fields={},
            checks=[
                AuditCheckItem(
                    check_name="Document Text Analysis",
                    status="WARN",
                    details="No readable text or scan payload was provided.",
                    remedy="Paste the text from your certificate or upload a clear photo/PDF of your document."
                )
            ],
            action_plan=["Upload or paste your certificate details to run the automated pre-check."],
            disclaimer="Pre-check advisory based on published rules. Always confirm on official portal."
        )

    # 2. Issue Date & Validity Period (Real Current Date)
    now = datetime.now(timezone.utc)
    issue_date_str = extracted.get("issue_date")
    parsed_date = parse_date_flexibly(issue_date_str) if issue_date_str else None

    if parsed_date:
        diff_days = (now - parsed_date).days
        if diff_days < 0:
            score -= 40
            checks.append(AuditCheckItem(
                check_name="Certificate Validity Window",
                status="FAIL",
                details=f"Document issue date ({issue_date_str}) is in the future. Certificate dates must precede or equal today.",
                remedy="Check the date printed on your certificate; future-dated certificates will cause immediate application rejection."
            ))
            action_plan.append("Correct invalid future certificate issue date before submitting.")
        else:
            months_old = max(0, diff_days // 30)

            if months_old > validity_limit_months:
                score -= 40
                checks.append(AuditCheckItem(
                    check_name="Certificate Validity Window",
                    status="FAIL",
                    details=f"Document is dated ~{months_old} months ago ({issue_date_str}), exceeding the {validity_limit_months}-month validity rule for this scheme.",
                    remedy=f"Obtain a fresh certificate issued within the required {validity_limit_months}-month window before submitting."
                ))
                action_plan.append(f"Renew your certificate: exceeds {validity_limit_months}-month statutory limit.")
            elif months_old > 12 and validity_limit_months > 12:
                score -= 15
                checks.append(AuditCheckItem(
                    check_name="Certificate Validity Window",
                    status="WARN",
                    details=f"Certificate was issued in an earlier financial year ({issue_date_str}, ~{months_old} months old).",
                    remedy="Confirm on your college notice board whether your portal accepts previous FY certificates."
                ))
                action_plan.append("Verify current FY income certificate requirement with your college Nodal Officer.")
            else:
                checks.append(AuditCheckItem(
                    check_name="Certificate Validity Window",
                    status="PASS",
                    details=f"Document issue date ({issue_date_str}) is within the allowable {validity_limit_months}-month window.",
                    remedy="No action needed."
                ))
    else:
        # Date unparseable or missing -> Must report WARN, never PASS!
        score -= 20
        checks.append(AuditCheckItem(
            check_name="Certificate Validity Window",
            status="WARN",
            details="Could not detect or verify a valid issue date from the provided document text.",
            remedy="Ensure the certificate has a visible, clearly formatted issue date and dispatch number."
        ))
        action_plan.append("Ensure issue date is clearly legible on your certificate.")

    # 3. Handling based on doc_type
    doc_type_clean = req.doc_type.lower()

    if doc_type_clean in ["income_certificate", "general"]:
        extracted_income = extracted.get("income_amount")
        if extracted_income:
            try:
                val = float(extracted_income)
                if val > scheme_income_cap:
                    score -= 40
                    diff = val - scheme_income_cap
                    checks.append(AuditCheckItem(
                        check_name="Economic Criteria (Income Ceiling)",
                        status="FAIL",
                        details=f"Document shows annual income of ₹{val:,.0f}, which exceeds the scheme ceiling of ₹{scheme_income_cap:,.0f} by ₹{diff:,.0f}.",
                        remedy="This specific scheme will reject your application on financial eligibility. Consider applying for private CSR schemes with higher income caps (e.g. Reliance UG, Tata Trusts)."
                    ))
                    action_plan.append(f"Explore alternative schemes: income ₹{val:,.0f} exceeds ₹{scheme_income_cap:,.0f} cap.")
                else:
                    checks.append(AuditCheckItem(
                        check_name="Economic Criteria (Income Ceiling)",
                        status="PASS",
                        details=f"Stated income ₹{val:,.0f} satisfies scheme criteria (<= ₹{scheme_income_cap:,.0f}).",
                        remedy="Ensure exact same amount is entered on the official portal."
                    ))
            except Exception:
                pass
        else:
            score -= 15
            checks.append(AuditCheckItem(
                check_name="Economic Criteria (Income Ceiling)",
                status="WARN",
                details="No numerical family income figure detected in the document text.",
                remedy="Verify that your income certificate states the gross annual family income clearly."
            ))

    elif doc_type_clean == "marksheet":
        extracted_marks = extracted.get("marks_percentage")
        if extracted_marks:
            try:
                marks_val = float(extracted_marks)
                min_marks_req = 50.0
                if marks_val < min_marks_req:
                    score -= 30
                    checks.append(AuditCheckItem(
                        check_name="Academic Cutoff Verification",
                        status="FAIL",
                        details=f"Marksheet shows {marks_val:.1f}%, which is below the minimum requirement.",
                        remedy="Check other schemes that accept your academic tier."
                    ))
                else:
                    checks.append(AuditCheckItem(
                        check_name="Academic Cutoff Verification",
                        status="PASS",
                        details=f"Marks ({marks_val:.1f}%) satisfy academic eligibility.",
                        remedy="Keep original marksheet scan ready for upload."
                    ))
            except Exception:
                pass

    elif doc_type_clean == "caste_certificate":
        extracted_cat = extracted.get("category")
        if extracted_cat and profile.category and profile.category.upper() not in ["GENERAL", "ALL"]:
            if extracted_cat != profile.category.upper() and profile.category.upper() not in extracted_cat:
                score -= 35
                checks.append(AuditCheckItem(
                    check_name="Social Category Verification",
                    status="FAIL",
                    details=f"Certificate category ({extracted_cat}) does not match your profile category ({profile.category}).",
                    remedy="Ensure you upload your official caste certificate matching your applied category."
                ))

    # 4. Name Matching / Spelling Discrepancy
    doc_name = extracted.get("student_name")
    prof_name = profile.student_name.strip()
    if doc_name and prof_name and prof_name.lower() not in ["student", ""]:
        ratio = difflib.SequenceMatcher(None, doc_name.lower(), prof_name.lower()).ratio()
        if ratio < 0.6:
            score -= 30
            checks.append(AuditCheckItem(
                check_name="Applicant Name Verification",
                status="FAIL",
                details=f"Name on document ('{doc_name}') significantly differs from your registered profile name ('{prof_name}').",
                remedy="Use the exact legal name as printed on your Class 10th marksheet and Aadhaar card."
            ))
            action_plan.append("Resolve name mismatch across documents using an official name change affidavit if applicable.")
        elif ratio < 0.85:
            score -= 10
            checks.append(AuditCheckItem(
                check_name="Applicant Name Verification",
                status="WARN",
                details=f"Minor spelling variation between document ('{doc_name}') and profile ('{prof_name}').",
                remedy="Portals verify character-by-character against Aadhaar. Ensure zero spelling difference."
            ))
        else:
            checks.append(AuditCheckItem(
                check_name="Applicant Name Verification",
                status="PASS",
                details=f"Name matches ({doc_name}).",
                remedy="No action needed."
            ))
    else:
        # Advisory / INFO only - MUST NOT BE PASS, MUST NOT RAISE SCORE
        checks.append(AuditCheckItem(
            check_name="Applicant Name Verification",
            status="INFO",
            details="Name verification skipped (ensure name matches Aadhaar character-to-character).",
            remedy="Ensure Class 10th name matches bank account."
        ))

    # 5. Official Issuing Authority & Digital Verification
    auth = extracted.get("issuing_authority")
    marker = extracted.get("verification_marker")
    has_qr = bool(marker and "Appears Present" in marker)

    if auth and has_qr:
        checks.append(AuditCheckItem(
            check_name="Issuing Authority & Digital Stamp",
            status="PASS",
            details=f"Issued by designated officer ({auth}). Digital verification marker detected ({marker}).",
            remedy="Keep digital PDF copy handy."
        ))
    elif auth and not has_qr:
        score -= 15
        checks.append(AuditCheckItem(
            check_name="Issuing Authority & Digital Stamp",
            status="WARN",
            details=f"Issued by designated officer ({auth}), but digital verification stamp or QR code was not clearly detected in text ({marker}).",
            remedy="Ensure the certificate has a visible digital sign, QR code, or official revenue seal before uploading."
        ))
        action_plan.append("Confirm presence of QR code or official seal on certificate.")
    else:
        score -= 20
        checks.append(AuditCheckItem(
            check_name="Issuing Authority & Digital Stamp",
            status="WARN",
            details="Could not verify issuing officer signature or digital QR code.",
            remedy="Ensure the certificate has a visible digital sign or Tehsildar stamp."
        ))

    # 6. NPCI Direct Benefit Transfer (DBT) Mandatory Advisory (MUST BE INFO, NOT PASS)
    checks.append(AuditCheckItem(
        check_name="Bank Account NPCI DBT Mapping",
        status="INFO",
        details="Critical Advisory: Over 40% of scholarship rejections happen due to unmapped NPCI bank status.",
        remedy="Check active NPCI mapper status on myaadhaar.uidai.gov.in -> Bank Seeding Status."
    ))

    # Overall Status: Any FAIL => FAIL!
    has_fail = any(c.status == "FAIL" for c in checks)
    has_warn = any(c.status == "WARN" for c in checks)

    if has_fail:
        overall = "FAIL"
        score = min(score, 55)
    elif has_warn:
        overall = "WARN"
        score = min(score, 75)
    else:
        overall = "PASS"

    score = max(min(score, 100), 20)

    if not action_plan:
        action_plan = [
            "Your document passed primary pre-check criteria.",
            "Verify active NPCI Aadhaar bank seeding before final portal submission.",
            "Retain stamped fee receipts from your institute."
        ]

    return DocumentAuditResponse(
        session_id=req.session_id,
        scheme_id=req.scheme_id,
        doc_type=req.doc_type,
        overall_status=overall,
        readiness_score=score,
        extracted_fields=extracted,
        checks=checks,
        action_plan=action_plan,
        disclaimer="Pre-check advisory based on published rules. Always confirm on official portal."
    )
