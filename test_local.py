import asyncio
import json
import os
import sys

# Support UTF-8 output on Windows terminal
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from core.models import StudentProfile, DocumentAuditRequest
from core.matching import match_scholarships
from core.doc_auditor import audit_document_compliance
from core.deadlines import build_deadline_items
from core.cards import get_carousel_card, get_scheme_detail_card, get_profile_review_card
from core.payments import generate_concierge_pack
from core.doc_auditor import DOC_RULES_DB

def run_local_verification():
    print("="*70)
    print("🎓 SCHOLARBOT: LOCAL MULTI-AGENT VERIFICATION PIPELINE")
    print("   Validating Engines: Matching + Document Audit + Deadlines + Payments")
    print("="*70)

    # 1. Profile Setup
    test_profile = StudentProfile(
        student_name="Priyanshu Verma",
        state="Rajasthan",
        category="OBC",
        family_income=220000.0,
        course="B.Tech / B.E.",
        marks_percentage=82.0,
        gender="All",
        disability=False
    )
    print(f"\n[1] Student Profile:")
    print(f"  * Name: {test_profile.student_name}")
    print(f"  * Domicile: {test_profile.state} | Category: {test_profile.category}")
    print(f"  * Course: {test_profile.course} | Marks: {test_profile.marks_percentage}%")
    print(f"  * Annual Family Income: ₹{test_profile.family_income:,.0f}")

    # 2. Scheme Matching Engine
    print("\n[2] Scheme Matching Engine:")
    eligible, close_misses = match_scholarships(test_profile)
    print(f"  [OK] Found {len(eligible)} eligible verified scholarships!")
    for idx, s in enumerate(eligible[:4], 1):
        print(f"    {idx}. {s.name} ({s.amount})")
        print(f"       Score: {s.match_score}% | Portal: {s.portal} | Reason: {s.match_reason}")
    if close_misses:
        print(f"  [OK] Found {len(close_misses)} close-miss opportunities:")
        for cm in close_misses[:2]:
            print(f"    - {cm.name}: {cm.match_reason}")

    assert len(eligible) >= 2, "Matching engine failed to find eligible schemes."

    # 3. Interactive Cards
    print("\n[3] ASI:One Interactive Cards Generation:")
    carousel = get_carousel_card(eligible)
    print(f"  [OK] Rendered Carousel with {len(carousel['items'])} cards for ASI:One.")
    review = get_profile_review_card(test_profile)
    print(f"  [OK] Rendered Review Card: {review['title']}.")

    # 4. Anti-Rejection Document Audit Engine
    print("\n[4] Document Compliance & Anti-Rejection Audit Engine:")
    # Scenario A: Valid current certificate
    valid_doc = """
    Revenue Dept Govt of Rajasthan - Form I Income Certificate
    Applicant: Priyanshu Verma
    Annual Household Income: Rs 220000
    Date: 14/09/2026
    Tehsildar Signed with digital QR
    """
    req_a = DocumentAuditRequest(
        session_id="local-test",
        scheme_id="raj_postmatric_sje",
        doc_type="income_certificate",
        doc_text=valid_doc,
        profile=test_profile
    )
    res_a = audit_document_compliance(req_a, scheme_income_cap=250000.0)
    print(f"  * Scenario A (Valid Certificate): Status={res_a.overall_status} (Score: {res_a.readiness_score}/100)")
    assert res_a.overall_status == "PASS"

    # Scenario B: Stale certificate (dated 14 months ago)
    stale_doc = """
    Income Certificate
    Applicant: Priyanshu Verma
    Annual Income: Rs 220000
    Date: 10/08/2025
    Tehsildar Signed
    """
    req_b = DocumentAuditRequest(
        session_id="local-test",
        scheme_id="raj_postmatric_sje",
        doc_type="income_certificate",
        doc_text=stale_doc,
        profile=test_profile
    )
    res_b = audit_document_compliance(req_b, scheme_income_cap=250000.0)
    print(f"  * Scenario B (Stale Certificate): Status={res_b.overall_status} (Score: {res_b.readiness_score}/100)")
    print(f"    Flagged Remedy: {res_b.checks[0].remedy}")
    assert res_b.overall_status in ["FAIL", "WARN"]

    # 5. Dynamic Deadline Tracker & Calendar
    print("\n[5] Dynamic Deadline Tracker & .ics Calendar Alarms:")
    deadlines = build_deadline_items(eligible[:3])
    for d in deadlines:
        print(f"  * {d.scheme_name[:35]}... -> {d.badge_label} (Cutoff: {d.deadline_date})")
    assert len(deadlines[0].ics_calendar_data) > 100

    # 6. Payment Protocol Concierge Pack
    print("\n[6] Payment Protocol & Application Concierge Pack:")
    doc_rule = DOC_RULES_DB.get(eligible[0].id, DOC_RULES_DB["default"])
    pack = generate_concierge_pack(eligible[0], doc_rule, test_profile)
    print(f"  [OK] Generated Pack: '{pack.pack_title}'")
    print(f"  [OK] Custom SOP Length: {len(pack.sop_essay)} chars")
    assert len(pack.sop_essay) > 100

    print("\n" + "="*70)
    print("🏆 ALL 6 MULTI-AGENT ENGINES VERIFIED SUCCESSFULLY WITH 100% PASS RATE!")
    print("="*70)

if __name__ == "__main__":
    run_local_verification()
