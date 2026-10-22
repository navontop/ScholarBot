import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4
from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    MetadataContent,
    TextContent,
)
from core.models import (
    DeadlineItem,
    DocumentAuditResponse,
    ScholarshipItem,
    StudentProfile,
)

def create_text_chat(text: str) -> ChatMessage:
    """Creates a basic plain-text chat message."""
    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=text)],
    )

def create_card_message(narration: str, card_kind: str, payload: dict, is_terminal: bool = False) -> ChatMessage:
    """Wraps card payload into official ASI:One wire protocol."""
    metadata = {
        "card_protocol_version": "1",
        "requires_card_interaction": "true" if not is_terminal else "false",
        "card_kind": card_kind,
        "card_payload": json.dumps(payload),
        "preferred_drawer_width_px": "420",
    }
    if is_terminal:
        metadata["is_terminal"] = "true"

    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[
            TextContent(type="text", text=narration),
            MetadataContent(type="metadata", metadata=metadata),
        ],
    )

def get_action_hub_card() -> dict:
    """Fast Action Hub card providing 1-click entry to all features with compact images."""
    items = [
        {
            "id": "action_find",
            "image": "https://images.unsplash.com/photo-1523240795612-9a054b0db644?w=260&h=130&fit=crop&auto=format&q=80",
            "title": "🔍 Find Matching Scholarships",
            "subtitle": "Discover 20+ central, state, and CSR scholarships tailored to you",
            "secondary_text": "Complete eligibility intake form",
            "badges": [{"label": "Smart Matching", "variant": "success"}],
            "primary_cta": {
                "label": "Open Intake Form",
                "selection": {"action": "open_intake_form"}
            }
        },
        {
            "id": "action_audit",
            "image": "https://images.unsplash.com/photo-1450133064473-71024230f91b?w=260&h=130&fit=crop&auto=format&q=80",
            "title": "📄 Anti-Rejection Document Audit",
            "subtitle": "Pre-check income certificate, caste certificate, marksheet, and NPCI DBT",
            "secondary_text": "Deterministic compliance pre-check",
            "badges": [{"label": "Rejection Shield", "variant": "warning"}],
            "primary_cta": {
                "label": "Audit Document",
                "selection": {"action": "open_doc_audit"}
            }
        },
        {
            "id": "action_deadlines",
            "image": "https://images.unsplash.com/photo-1506784365847-bbad939e9335?w=260&h=130&fit=crop&auto=format&q=80",
            "title": "📅 Deadlines & Calendar Tracker",
            "subtitle": "Real-time urgency tracker with downloadable .ics calendar alarms (7, 3, 1 day)",
            "secondary_text": "Never miss a portal cutoff",
            "badges": [{"label": "Live Dates", "variant": "info"}],
            "primary_cta": {
                "label": "View Deadlines",
                "selection": {"action": "view_deadlines"}
            }
        },
        {
            "id": "action_whatif",
            "image": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=260&h=130&fit=crop&auto=format&q=80",
            "title": "🔮 'What-If' Eligibility Simulator",
            "subtitle": "Simulate what happens if your family income or marks change",
            "secondary_text": "Instant re-matching",
            "badges": [{"label": "Personal AI", "variant": "info"}],
            "primary_cta": {
                "label": "Run Simulation",
                "selection": {"action": "simulate_what_if"}
            }
        },
        {
            "id": "action_concierge",
            "image": "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=260&h=130&fit=crop&auto=format&q=80",
            "title": "⚡ Application Concierge Pack",
            "subtitle": "Get a complete application pack: document checklist, portal guide, and SOP essay",
            "secondary_text": "Fetch.ai Payment Protocol enabled",
            "badges": [{"label": "0.01 USDC / 0.05 FET", "variant": "success"}],
            "primary_cta": {
                "label": "Get Concierge Pack",
                "selection": {"action": "request_concierge_pack"}
            }
        },
        {
            "id": "action_profile",
            "image": "https://images.unsplash.com/photo-1434030216411-0b793f4b4173?w=260&h=130&fit=crop&auto=format&q=80",
            "title": "👤 My Profile & Shortlist",
            "subtitle": "View or update your saved profile, saved scholarships, and active reminders",
            "secondary_text": "Zero-typing persistence",
            "badges": [{"label": "Saved Memory", "variant": "info"}],
            "primary_cta": {
                "label": "Manage Profile",
                "selection": {"action": "view_profile"}
            }
        }
    ]

    return {
        "title": "ScholarBot Action Hub",
        "subtitle": "Choose an action or swipe through features to get started",
        "items": items
    }

def get_intake_form_card(prefill: Optional[StudentProfile] = None) -> dict:
    """Returns ASI:One Form Card schema for student intake with full fields."""
    return {
        "title": "Scholarship Eligibility Intake Form",
        "fields": [
            {
                "name": "state",
                "kind": "select",
                "label": "1. Home State / Domicile (All 28 States & 8 UTs)",
                "required": True,
                "options": [
                    {"value": "Andaman and Nicobar Islands", "label": "Andaman & Nicobar Islands (UT)"},
                    {"value": "Andhra Pradesh", "label": "Andhra Pradesh"},
                    {"value": "Arunachal Pradesh", "label": "Arunachal Pradesh"},
                    {"value": "Assam", "label": "Assam"},
                    {"value": "Bihar", "label": "Bihar"},
                    {"value": "Chandigarh", "label": "Chandigarh (UT)"},
                    {"value": "Chhattisgarh", "label": "Chhattisgarh"},
                    {"value": "Dadra and Nagar Haveli and Daman and Diu", "label": "Dadra & Nagar Haveli and Daman & Diu (UT)"},
                    {"value": "Delhi", "label": "Delhi (NCT / National Capital)"},
                    {"value": "Goa", "label": "Goa"},
                    {"value": "Gujarat", "label": "Gujarat"},
                    {"value": "Haryana", "label": "Haryana"},
                    {"value": "Himachal Pradesh", "label": "Himachal Pradesh"},
                    {"value": "Jammu and Kashmir", "label": "Jammu & Kashmir (UT)"},
                    {"value": "Jharkhand", "label": "Jharkhand"},
                    {"value": "Karnataka", "label": "Karnataka"},
                    {"value": "Kerala", "label": "Kerala"},
                    {"value": "Ladakh", "label": "Ladakh (UT)"},
                    {"value": "Lakshadweep", "label": "Lakshadweep (UT)"},
                    {"value": "Madhya Pradesh", "label": "Madhya Pradesh"},
                    {"value": "Maharashtra", "label": "Maharashtra"},
                    {"value": "Manipur", "label": "Manipur"},
                    {"value": "Meghalaya", "label": "Meghalaya"},
                    {"value": "Mizoram", "label": "Mizoram"},
                    {"value": "Nagaland", "label": "Nagaland"},
                    {"value": "Odisha", "label": "Odisha"},
                    {"value": "Puducherry", "label": "Puducherry (UT)"},
                    {"value": "Punjab", "label": "Punjab"},
                    {"value": "Rajasthan", "label": "Rajasthan"},
                    {"value": "Sikkim", "label": "Sikkim"},
                    {"value": "Tamil Nadu", "label": "Tamil Nadu"},
                    {"value": "Telangana", "label": "Telangana"},
                    {"value": "Tripura", "label": "Tripura"},
                    {"value": "Uttar Pradesh", "label": "Uttar Pradesh"},
                    {"value": "Uttarakhand", "label": "Uttarakhand"},
                    {"value": "West Bengal", "label": "West Bengal"},
                    {"value": "All", "label": "All India / Pan-India Central Scheme"}
                ]
            },
            {
                "name": "course",
                "kind": "select",
                "label": "2. Current Education Level & Program",
                "required": True,
                "options": [
                    {"value": "B.Tech / B.E.", "label": "College: Engineering (B.Tech / B.E.)"},
                    {"value": "MBBS / BDS / Medical", "label": "College: Medical / Healthcare (MBBS / BDS / Nursing / B.Pharm)"},
                    {"value": "B.Sc / BCA / B.Com / BA", "label": "College: General Undergrad (B.Sc / BCA / B.Com / BA / BBA)"},
                    {"value": "MBA / M.Tech / M.Sc", "label": "University: Postgraduate (MBA / M.Tech / M.Sc / MCA / MA)"},
                    {"value": "Diploma / Polytechnic", "label": "Diploma / Polytechnic / ITI"},
                    {"value": "Class 11th - 12th", "label": "School: Higher Secondary (Class 11th - 12th)"},
                    {"value": "Class 10th", "label": "School: Secondary (Class 9th - 10th Matric)"},
                    {"value": "Law (LLB / LLM)", "label": "Law Degree (BA LLB / BBA LLB / LLB / LLM)"},
                    {"value": "PhD / Doctorate", "label": "Doctorate: PhD / Research Scholar"}
                ]
            },
            {
                "name": "category",
                "kind": "select",
                "label": "3. Social Category",
                "required": True,
                "options": [
                    {"value": "General", "label": "General / Open"},
                    {"value": "EWS", "label": "EWS (Economically Weaker Section)"},
                    {"value": "OBC", "label": "OBC (Other Backward Class)"},
                    {"value": "SC", "label": "SC (Scheduled Caste)"},
                    {"value": "ST", "label": "ST (Scheduled Tribe)"},
                    {"value": "Minority", "label": "Minority (Muslim/Sikh/Christian/Jain/Buddhist/Parsi)"}
                ]
            },
            {
                "name": "family_income",
                "kind": "select",
                "label": "4. Annual Family Income (INR)",
                "required": True,
                "options": [
                    {"value": "90000", "label": "Below ₹1.0 Lakh / year (BPL / Highest Need Priority)"},
                    {"value": "150000", "label": "₹1.0 Lakh - ₹1.5 Lakhs / year"},
                    {"value": "250000", "label": "₹1.5 Lakhs - ₹2.5 Lakhs / year (Govt Cap for Post-Matric)"},
                    {"value": "450000", "label": "₹2.5 Lakhs - ₹4.5 Lakhs / year (Central Sector Limit)"},
                    {"value": "800000", "label": "₹4.5 Lakhs - ₹8.0 Lakhs / year (AICTE Pragati / Saksham Limit)"},
                    {"value": "1500000", "label": "Above ₹8.0 Lakhs / year (Private CSR Eligible)"}
                ]
            },
            {
                "name": "marks",
                "kind": "select",
                "label": "5. Last Qualifying Exam Score (Marks % or CGPA equivalent)",
                "required": True,
                "options": [
                    {"value": "85", "label": "85% and Above / 8.5+ CGPA (Top Percentile / Distinction)"},
                    {"value": "75", "label": "75% - 84% / 7.5 - 8.4 CGPA (First Class with Distinction)"},
                    {"value": "65", "label": "60% - 74% / 6.0 - 7.4 CGPA (First Class)"},
                    {"value": "52", "label": "50% - 59% / 5.0 - 5.9 CGPA (Second Class / Minimum Pass)"},
                    {"value": "45", "label": "Below 50% / Below 5.0 CGPA"}
                ]
            },
            {
                "name": "gender",
                "kind": "select",
                "label": "6. Gender",
                "required": True,
                "options": [
                    {"value": "Female", "label": "Female (Unlocks AICTE Pragati & Kotak Kanya)"},
                    {"value": "Male", "label": "Male"},
                    {"value": "Transgender", "label": "Transgender / Third Gender"},
                    {"value": "All", "label": "Prefer not to say / Any"}
                ]
            },
            {
                "name": "disability",
                "kind": "select",
                "label": "7. Specially Abled / PwD Status",
                "required": True,
                "options": [
                    {"value": "no", "label": "No (Not Specially Abled)"},
                    {"value": "yes", "label": "Yes (>= 40% Benchmark Disability - Unlocks Saksham)"}
                ]
            }
        ],
        "submit_cta": {
            "label": "Review & Match Scholarships",
            "selection": {"action": "submit_intake", "fallback": "back_to_hub"}
        }
    }

def get_profile_review_card(profile: StudentProfile) -> dict:
    """Review screen to verify extracted details before running matcher."""
    summary_rows = [
        {"label": "Student Name", "value": profile.student_name},
        {"label": "Home State", "value": profile.state},
        {"label": "Social Category", "value": profile.category},
        {"label": "Annual Income", "value": f"₹{profile.family_income:,.0f}"},
        {"label": "Course", "value": profile.course},
        {"label": "Academic Score", "value": f"{profile.marks_percentage:.1f}%"},
        {"label": "Gender", "value": profile.gender},
        {"label": "Disability (PwD)", "value": "Yes (>= 40%)" if profile.disability else "No"}
    ]

    return {
        "title": "Review Student Profile",
        "summary_rows": summary_rows,
        "approve_cta": {
            "label": "✅ Confirm & Find Scholarships",
            "selection": {"action": "confirm_and_match"},
            "primary": True
        },
        "reject_cta": {
            "label": "🏠 Back to Menu",
            "selection": {"action": "back_to_hub"}
        }
    }

SCHEME_THUMBNAILS = {
    "nsp_central_sector": "https://images.unsplash.com/photo-1523050854058-8df90110c9f1?w=260&h=130&fit=crop&auto=format&q=80",
    "aicte_pragati": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=260&h=130&fit=crop&auto=format&q=80",
    "aicte_saksham": "https://images.unsplash.com/photo-1576765608535-5f04d1e3f289?w=260&h=130&fit=crop&auto=format&q=80",
    "post_matric_sc": "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=260&h=130&fit=crop&auto=format&q=80",
    "post_matric_st": "https://images.unsplash.com/photo-1427504494785-3a9ca7044f45?w=260&h=130&fit=crop&auto=format&q=80",
    "post_matric_obc": "https://images.unsplash.com/photo-1509062522246-3755977927d7?w=260&h=130&fit=crop&auto=format&q=80",
    "begum_hazrat_mahal": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=260&h=130&fit=crop&auto=format&q=80",
    "pre_matric_minority": "https://images.unsplash.com/photo-1580582932707-520aed937b7b?w=260&h=130&fit=crop&auto=format&q=80",
    "post_matric_minority": "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=260&h=130&fit=crop&auto=format&q=80",
    "reliance_foundation": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=260&h=130&fit=crop&auto=format&q=80",
    "hdfc_badhte_kadam": "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=260&h=130&fit=crop&auto=format&q=80",
    "kotak_kanya": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=260&h=130&fit=crop&auto=format&q=80",
    "tata_trusts_medical": "https://images.unsplash.com/photo-1532938911079-1b06ac7ceec7?w=260&h=130&fit=crop&auto=format&q=80",
    "sitaram_jindal": "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=260&h=130&fit=crop&auto=format&q=80",
    "lic_hfl_vidyadhan": "https://images.unsplash.com/photo-1434030216411-0b793f4b4173?w=260&h=130&fit=crop&auto=format&q=80",
    "santoor_scholarship": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=260&h=130&fit=crop&auto=format&q=80",
    "rajasthan_cm_higher_ed": "https://images.unsplash.com/photo-1523050854058-8df90110c9f1?w=260&h=130&fit=crop&auto=format&q=80",
    "up_scholarship_postmatric": "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=260&h=130&fit=crop&auto=format&q=80",
    "maha_dbt_postmatric": "https://images.unsplash.com/photo-1509062522246-3755977927d7?w=260&h=130&fit=crop&auto=format&q=80",
    "delhi_higher_ed": "https://images.unsplash.com/photo-1523240795612-9a054b0db644?w=260&h=130&fit=crop&auto=format&q=80"
}

def get_carousel_card(matched_schemes: List[ScholarshipItem], close_misses: List[ScholarshipItem] = None) -> dict:
    """Builds a horizontal carousel card for matched scholarships with distinct badges and CTAs."""
    items = []
    default_img = "https://images.unsplash.com/photo-1523050854058-8df90110c9f1?w=260&h=130&fit=crop&auto=format&q=80"
    for s in matched_schemes:
        badges = [
            {"label": f"{s.match_score}% Match", "variant": "success"},
            {"label": s.deadline, "variant": "info"}
        ]
        scheme_img = SCHEME_THUMBNAILS.get(s.id, default_img)
        items.append({
            "id": s.id,
            "image": scheme_img,
            "title": s.name[:45] + ("..." if len(s.name) > 45 else ""),
            "subtitle": f"{s.provider[:35]} · {s.portal[:25]}",
            "secondary_text": s.amount,
            "badges": badges,
            "primary_cta": {
                "label": "View Guide & Checklist",
                "selection": {
                    "action": "view_scheme_details",
                    "scheme_id": s.id,
                    "scheme_name": s.name
                }
            }
        })

    # Add close misses if available
    if close_misses:
        for cm in close_misses[:2]:
            items.append({
                "id": cm.id,
                "image": "https://images.unsplash.com/photo-1532619675605-1ede6c2ed2b0?w=260&h=130&fit=crop&auto=format&q=80",
                "title": f"[Close Miss] {cm.name[:35]}...",
                "subtitle": f"{cm.portal}",
                "secondary_text": cm.match_reason[:45] + "...",
                "badges": [{"label": "Near Match", "variant": "warning"}],
                "primary_cta": {
                    "label": "See What You Need",
                    "selection": {
                        "action": "view_scheme_details",
                        "scheme_id": cm.id,
                        "scheme_name": cm.name
                    }
                }
            })

    # Add return to menu card
    items.append({
        "id": "hub_return",
        "image": "https://images.unsplash.com/photo-1498243691581-b145c3f54a5a?w=260&h=130&fit=crop&auto=format&q=80",
        "title": "Return to Action Hub",
        "subtitle": "Explore other advisory tools, deadlines, or document audits",
        "secondary_text": "ScholarBot Main Menu",
        "badges": [{"label": "Menu", "variant": "info"}],
        "primary_cta": {
            "label": "🏠 Back to Menu",
            "selection": {"action": "back_to_hub"}
        }
    })

    return {
        "title": f"Found {len(matched_schemes)} Eligible Scholarships",
        "subtitle": "Swipe through available central, state, and foundation opportunities",
        "items": items
    }

def get_scheme_detail_card(scheme: ScholarshipItem, doc_guidance: dict) -> dict:
    """Generates detailed view card with documentation, direct portal link, and actions."""
    summary_rows = [
        {"label": "Scholarship Grant", "value": scheme.amount},
        {"label": "Funding Body", "value": scheme.provider},
        {"label": "Official Portal", "value": scheme.portal},
        {"label": "Application Deadline", "value": scheme.deadline},
        {"label": "Direct Portal URL", "value": scheme.portal_url},
        {"label": "Verification Status", "value": f"Verified (Last checked: {scheme.last_verified})" if scheme.verified else "Unverified, confirm on official portal"}
    ]

    checklist_preview = " • " + " • ".join(doc_guidance.get("mandatory", [])[:4])
    summary_rows.append({"label": "Mandatory Docs", "value": checklist_preview})

    return {
        "title": f"Guide: {scheme.name[:50]}",
        "hero_image": "https://images.unsplash.com/photo-1523240795612-9a054b0db644?w=450&h=200&fit=crop&auto=format&q=80",
        "summary_rows": summary_rows,
        "ctas": [
            {
                "label": "📄 Run Pre-Check Document Audit",
                "primary": True,
                "selection": {
                    "action": "audit_for_scheme",
                    "scheme_id": scheme.id,
                    "scheme_name": scheme.name
                }
            },
            {
                "label": "🏠 Back to Menu",
                "selection": {"action": "back_to_hub"}
            }
        ]
    }

def get_audit_result_card(audit: DocumentAuditResponse) -> dict:
    """Renders document audit readiness card."""
    summary_rows = [
        {"label": "Overall Audit Status", "value": f"{audit.overall_status} (Readiness: {audit.readiness_score}/100)"},
        {"label": "Document Type", "value": audit.doc_type.replace("_", " ").title()}
    ]

    for check in audit.checks:
        icon = "✅" if check.status == "PASS" else ("⚠️" if check.status == "WARN" else "❌")
        summary_rows.append({
            "label": f"{icon} {check.check_name}",
            "value": f"{check.details} Remedy: {check.remedy}" if check.remedy else check.details
        })

    return {
        "title": f"Document Pre-Check Audit: {audit.overall_status}",
        "summary_rows": summary_rows,
        "approve_cta": {
            "label": "⚡ Get Full Concierge Pack & SOP",
            "selection": {
                "action": "request_concierge_pack",
                "scheme_id": audit.scheme_id
            },
            "primary": True
        },
        "reject_cta": {
            "label": "🏠 Back to Action Hub",
            "selection": {"action": "back_to_hub"}
        }
    }

def get_deadlines_card(items: List[DeadlineItem]) -> dict:
    """Renders deadline urgency list card."""
    summary_rows = []
    for d in items[:6]:
        summary_rows.append({
            "label": d.scheme_name[:35] + ("..." if len(d.scheme_name) > 35 else ""),
            "value": f"{d.badge_label} | Deadline: {d.deadline_date}"
        })

    return {
        "title": "Scholarship Deadlines & Calendar",
        "summary_rows": summary_rows,
        "approve_cta": {
            "label": "🔔 Set Proactive Reminders",
            "selection": {"action": "save_reminders"},
            "primary": True
        },
        "reject_cta": {
            "label": "🏠 Back to Action Hub",
            "selection": {"action": "back_to_hub"}
        }
    }
