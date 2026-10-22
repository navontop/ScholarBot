import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

# Ensure parent directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    MetadataContent,
    ResourceContent,
    StartSessionContent,
    TextContent,
    chat_protocol_spec,
)
from uagents_core.contrib.protocols.payment import (
    CancelPayment,
    CommitPayment,
    CompletePayment,
    RejectPayment,
    RequestPayment,
    payment_protocol_spec,
)

from core.cards import (
    create_card_message,
    create_text_chat,
    get_action_hub_card,
    get_audit_result_card,
    get_carousel_card,
    get_deadlines_card,
    get_intake_form_card,
    get_profile_review_card,
    get_scheme_detail_card,
)
from core.deadlines import build_deadline_items, calculate_deadline_metrics, get_calendar_data_uri
from core.doc_auditor import DOC_RULES_DB, audit_document_compliance
from core.llm import (
    check_asi1_api_health,
    classify_intent,
    generate_grounded_explanation,
    is_hindi_or_hinglish,
    parse_student_profile,
)
from core.privacy import mask_sensitive_identifiers
from core.matching import load_scholarships, match_scholarships
from core.models import (
    DeadlineItem,
    DeadlineRequest,
    DeadlineResponse,
    DocumentAuditRequest,
    DocumentAuditResponse,
    DocumentGuidanceRequest,
    DocumentGuidanceResponse,
    ScholarshipItem,
    SchemeMatchRequest,
    SchemeMatchResponse,
    StudentProfile,
)
from core.payments import (
    create_concierge_payment_request,
    generate_concierge_pack,
    handle_payment_commit,
)

import secrets

# Logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
logger = logging.getLogger("ScholarCoordinator")

from core.identity import get_or_create_seed

COORDINATOR_SEED = get_or_create_seed("COORDINATOR_SEED", "coordinator")
COORDINATOR_PORT = int(os.getenv("COORDINATOR_PORT", "8001"))
AGENTVERSE_MAILBOX_KEY = os.getenv("AGENTVERSE_MAILBOX_KEY", "")

from agents.matcher import matcher_agent
from agents.auditor import auditor_agent
from agents.tracker import tracker_agent

SCHEME_AGENT_ADDRESS = os.getenv("SCHEME_AGENT_ADDRESS") or getattr(matcher_agent, "address", "")
DOC_AGENT_ADDRESS = os.getenv("DOC_AGENT_ADDRESS") or getattr(auditor_agent, "address", "")
TRACKER_AGENT_ADDRESS = os.getenv("TRACKER_AGENT_ADDRESS") or getattr(tracker_agent, "address", "")

# Initialize Coordinator Agent with Agentverse discoverability metadata
agent_kwargs = {
    "name": "scholarbot_coordinator",
    "seed": COORDINATOR_SEED,
    "port": COORDINATOR_PORT,
    "description": "ScholarBot Autonomous India Scholarship Advisory Agent: Match central, state, and CSR schemes, pre-check eligibility documents, and track deadlines.",
    "metadata": {
        "tags": ["scholarship", "India", "NSP", "document check", "deadlines", "eligibility"],
        "category": "education",
        "author": "Fetch-A-Thon 3.0 ScholarBot Team"
    }
}

# If mailbox is enabled, DO NOT configure endpoint (endpoint configuration overrides mailbox in uagents)
if AGENTVERSE_MAILBOX_KEY and len(AGENTVERSE_MAILBOX_KEY) > 20:
    agent_kwargs["mailbox"] = True
else:
    agent_kwargs["endpoint"] = [f"http://127.0.0.1:{COORDINATOR_PORT}/submit"]

coordinator_agent = Agent(**agent_kwargs)
print(f"[*] [Coordinator] Address: {coordinator_agent.address}")

# Run startup self-check for ASI1 API health without printing secrets
_asi1_ok, _asi1_msg = check_asi1_api_health()
logger.info(f"[Coordinator Startup Self-Check] {_asi1_msg}")


# Official Protocol Specifications
chat_proto = Protocol(spec=chat_protocol_spec)
payment_proto = Protocol(spec=payment_protocol_spec, role="seller")
coordinator_proto = Protocol(name="ScholarCoordinatorInternal", version="1.0.0")

# In-memory session tracking & profile store
USER_PROFILES: Dict[str, StudentProfile] = {}
LAST_MATCHES: Dict[str, List[ScholarshipItem]] = {}
SAVED_SHORTLIST: Dict[str, List[str]] = {}
SAVED_REMINDERS: Dict[str, List[str]] = {}
PENDING_PAYMENTS: Dict[str, dict] = {}
PENDING_PAYMENTS_BY_SENDER: Dict[str, dict] = {}

def get_or_create_profile(user_address: str, ctx: Optional[Context] = None) -> StudentProfile:
    if ctx and hasattr(ctx, "storage"):
        try:
            stored = ctx.storage.get(f"profile:{user_address}")
            if stored and isinstance(stored, dict):
                USER_PROFILES[user_address] = StudentProfile(**stored)
                return USER_PROFILES[user_address]
        except Exception:
            pass
    if user_address not in USER_PROFILES:
        USER_PROFILES[user_address] = StudentProfile()
    return USER_PROFILES[user_address]

def persist_profile(user_address: str, profile: StudentProfile, ctx: Optional[Context] = None):
    USER_PROFILES[user_address] = profile
    if ctx and hasattr(ctx, "storage"):
        try:
            ctx.storage.set(f"profile:{user_address}", profile.model_dump())
        except Exception:
            pass

# ==============================================================================
# MULTI-AGENT INTER-AGENT ORCHESTRATION WITH RESILIENT FALLBACK
# ==============================================================================
async def request_scheme_matching(ctx: Context, profile: StudentProfile, session_id: str) -> tuple[List[ScholarshipItem], List[ScholarshipItem]]:
    if SCHEME_AGENT_ADDRESS and hasattr(ctx, "send_and_receive"):
        ctx.logger.info(f"[Coordinator] Dispatching SchemeMatchRequest to SchemeMatchingAgent at {SCHEME_AGENT_ADDRESS}...")
        try:
            resp, status = await ctx.send_and_receive(
                SCHEME_AGENT_ADDRESS,
                SchemeMatchRequest(session_id=session_id, profile=profile),
                response_type=SchemeMatchResponse,
                timeout=5
            )
            if resp and isinstance(resp, SchemeMatchResponse):
                ctx.logger.info(f"[Coordinator] Received SchemeMatchResponse from {SCHEME_AGENT_ADDRESS}: {resp.total_found} matches found.")
                return resp.matches, resp.close_misses
            else:
                ctx.logger.warning(f"[Coordinator Fallback] Specialist at {SCHEME_AGENT_ADDRESS} returned status: {status}. Falling back to in-process engine.")
        except Exception as ex:
            ctx.logger.warning(f"[Coordinator Fallback] Error contacting {SCHEME_AGENT_ADDRESS}: {ex}. Falling back to in-process engine.")

    ctx.logger.info("[Coordinator In-Process] Executing local matching engine fallback...")
    return match_scholarships(profile)

async def request_document_audit(ctx: Context, audit_req: DocumentAuditRequest, income_cap: float) -> DocumentAuditResponse:
    if DOC_AGENT_ADDRESS and hasattr(ctx, "send_and_receive"):
        ctx.logger.info(f"[Coordinator] Dispatching DocumentAuditRequest to DocComplianceAgent at {DOC_AGENT_ADDRESS}...")
        try:
            resp, status = await ctx.send_and_receive(
                DOC_AGENT_ADDRESS,
                audit_req,
                response_type=DocumentAuditResponse,
                timeout=5
            )
            if resp and isinstance(resp, DocumentAuditResponse):
                ctx.logger.info(f"[Coordinator] Received DocumentAuditResponse from {DOC_AGENT_ADDRESS}: status={resp.overall_status}")
                return resp
            else:
                ctx.logger.warning(f"[Coordinator Fallback] Subagent at {DOC_AGENT_ADDRESS} returned status: {status}. Falling back to in-process engine.")
        except Exception as ex:
            ctx.logger.warning(f"[Coordinator Fallback] Error contacting {DOC_AGENT_ADDRESS}: {ex}. Falling back to in-process engine.")

    ctx.logger.info("[Coordinator In-Process] Executing local document compliance audit fallback...")
    return audit_document_compliance(audit_req, scheme_income_cap=income_cap)

async def request_deadlines(ctx: Context, scheme_ids: List[str]) -> List[DeadlineItem]:
    if TRACKER_AGENT_ADDRESS and hasattr(ctx, "send_and_receive"):
        ctx.logger.info(f"[Coordinator] Dispatching DeadlineRequest to DeadlineTrackerAgent at {TRACKER_AGENT_ADDRESS}...")
        try:
            resp, status = await ctx.send_and_receive(
                TRACKER_AGENT_ADDRESS,
                DeadlineRequest(session_id=str(uuid4()), scheme_ids=scheme_ids),
                response_type=DeadlineResponse,
                timeout=5
            )
            if resp and isinstance(resp, DeadlineResponse):
                ctx.logger.info(f"[Coordinator] Received DeadlineResponse from {TRACKER_AGENT_ADDRESS}: {len(resp.items)} deadlines.")
                return resp.items
            else:
                ctx.logger.warning(f"[Coordinator Fallback] Subagent at {TRACKER_AGENT_ADDRESS} returned status: {status}. Falling back to in-process engine.")
        except Exception as ex:
            ctx.logger.warning(f"[Coordinator Fallback] Error contacting {TRACKER_AGENT_ADDRESS}: {ex}. Falling back to in-process engine.")

    schemes = load_scholarships()
    selected_items = [
        ScholarshipItem(
            id=s["id"],
            name=s["name"],
            provider=s["provider"],
            portal=s["portal"],
            portal_url=s["portal_url"],
            amount=s["amount"],
            deadline=s.get("deadline", "2026-12-31"),
            description=s.get("description", "")
        )
        for s in schemes if not scheme_ids or s["id"] in scheme_ids
    ]
    return build_deadline_items(selected_items)

# ==============================================================================
# AGENT CHAT PROTOCOL HANDLER
# ==============================================================================
@chat_proto.on_message(ChatMessage)
async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
    # 1. Immediate ACK
    await ctx.send(sender, ChatAcknowledgement(acknowledged_msg_id=msg.msg_id))

    try:
        await _process_chat_message_safely(ctx, sender, msg)
    except Exception as e:
        ctx.logger.error(f"[Coordinator Guard] Handled unexpected error in chat processing: {e}", exc_info=True)
        hub_card = get_action_hub_card()
        friendly_msg = "I encountered an unexpected issue processing your request. Don't worry! Please use the Action Hub below to continue:"
        await ctx.send(sender, create_card_message(friendly_msg, "carousel", hub_card))

async def _process_chat_message_safely(ctx: Context, sender: str, msg: ChatMessage):
    # Check for StartSessionContent, EndSessionContent, and ResourceContent

    has_start_session = False
    has_end_session = False
    resource_payload: Optional[str] = None

    for item in msg.content:
        if isinstance(item, StartSessionContent):
            has_start_session = True
        elif isinstance(item, EndSessionContent):
            has_end_session = True
        elif isinstance(item, ResourceContent):
            res = item.resource
            res_list = res if isinstance(res, list) else [res]
            uris = [r.uri for r in res_list if hasattr(r, "uri")]
            if uris:
                resource_payload = uris[0]

    if has_end_session:
        ctx.logger.info(f"[Coordinator] EndSessionContent received from {sender}")
        await ctx.send(sender, create_text_chat("Session ended. Thank you for using ScholarBot! You can restart anytime by typing 'Hi' or 'Start'."))
        return

    user_text = msg.text().strip()

    if has_start_session and not user_text:
        ctx.logger.info(f"[Coordinator] StartSessionContent received from {sender}")
        hub_card = get_action_hub_card()
        narration = "Welcome to ScholarBot! 🎓 Your autonomous scholarship & document advisory agent. Explore the Action Hub below:"
        await ctx.send(sender, create_card_message(narration, "carousel", hub_card))
        return

    if resource_payload and not user_text:
        user_text = f"Uploaded document: {resource_payload}"

    # Never log raw user text or sensitive identifiers - log metadata only
    ctx.logger.info(f"[Coordinator] Message from {sender}: type=chat, length={len(user_text)}")

    # Mask sensitive identifiers (Aadhaar, PAN, phone, account) BEFORE stored profile, LLM prompt, or specialist message
    user_text = mask_sensitive_identifiers(user_text)

    lang_hindi = is_hindi_or_hinglish(user_text)
    profile = get_or_create_profile(sender, ctx)

    # 2. Check for Card Action Selections (from JSON or raw command string)
    action_data: Optional[dict] = None
    if user_text.startswith("{") and user_text.endswith("}"):
        try:
            action_data = json.loads(user_text)
        except Exception:
            pass

    action_type = action_data.get("action") if action_data else None

    # Handle quick keyword actions and short prompts (e.g. 'a', 'b', 'hi')
    if not action_type:
        low = user_text.lower().strip()
        is_greeting = bool(re.search(r'^(hi+|hello+|hey+|namaste|pranam|kya haal|good morning|start|restart|menu|hub|help|home)(\b|[^\w]|$)', low))
        is_short_prompt = len(low) <= 3 or low in ["hub", "menu", "start", "restart", "help", "home", "back_to_hub", "back_to_menu", "new_search", "options", "shuru", "dikhao"]
        if is_greeting or is_short_prompt:
            action_type = "open_hub"
        elif low in ["done", "exit", "bye", "thank you", "thanks"]:
            action_type = "done"

    # ==========================================================================
    # ACTION DISPATCHER
    # ==========================================================================
    if action_type == "open_hub":
        hub_card = get_action_hub_card()
        narration = (
            "Namaste! 🙏 Main hoon **ScholarBot** - aapka autonomous scholarship advisor. "
            "Aap niche Action Hub se koi bhi action select kar sakte hain ya direct apni profile likh sakte hain:"
            if lang_hindi else
            "Welcome! 🎓 I am **ScholarBot**, your autonomous scholarship & document advisory agent. "
            "Swipe through the Action Hub below to explore features, or type your query directly:"
        )
        await ctx.send(sender, create_card_message(narration, "carousel", hub_card))
        return

    if action_type == "open_intake_form":
        form_card = get_intake_form_card(profile)
        narration = (
            "Kripya apni eligibility details bharein. Ham published criteria ke aadhar par central, state aur CSR schemes match karenge:"
            if lang_hindi else
            "Please fill in your academic, financial, and category details below for matching based on published criteria:"
        )
        await ctx.send(sender, create_card_message(narration, "form", form_card))
        return

    if action_type == "submit_intake":
        # Accept BOTH nested action_data.get("values", {}) AND flat action_data, tolerating numbers/strings
        form_vals = {}
        if isinstance(action_data, dict):
            if "values" in action_data and isinstance(action_data["values"], dict):
                form_vals = dict(action_data["values"])
            else:
                form_vals = dict(action_data)

        if "state" in form_vals and form_vals["state"]:
            profile.state = str(form_vals["state"]).strip()
        if "course" in form_vals and form_vals["course"]:
            profile.course = str(form_vals["course"]).strip()
        if "category" in form_vals and form_vals["category"]:
            profile.category = str(form_vals["category"]).strip()
        if "family_income" in form_vals and form_vals["family_income"] is not None:
            try:
                clean_inc = str(form_vals["family_income"]).replace(",", "").replace("₹", "").replace("Rs", "").strip()
                profile.family_income = float(clean_inc)
            except Exception:
                pass
        if "marks" in form_vals and form_vals["marks"] is not None:
            try:
                clean_marks = str(form_vals["marks"]).replace("%", "").strip()
                profile.marks_percentage = float(clean_marks)
            except Exception:
                pass
        if "gender" in form_vals and form_vals["gender"]:
            profile.gender = str(form_vals["gender"]).strip()
        if "disability" in form_vals:
            profile.disability = (str(form_vals["disability"]).lower() in ["yes", "true", "1"])

        persist_profile(sender, profile, ctx)

        # Show Review Screen
        review_card = get_profile_review_card(profile)
        narration = (
            "Aapki details note kar li gayi hain! Kripya review karein aur 'Confirm & Match' par tap karein:"
            if lang_hindi else
            "Profile extracted successfully! Please verify your information below before matching:"
        )
        await ctx.send(sender, create_card_message(narration, "review", review_card))
        return

    if action_type == "confirm_and_match":
        # If state is unknown, ask for it before matching (do not show Pan-India only results)
        if not profile.state or profile.state in ["All", "unknown", ""]:
            form_card = get_intake_form_card(profile)
            narration = (
                "Kripya apna home state batayein taaki ham aapke state ki specific scholarships aur central schemes dono match kar sakein:"
                if lang_hindi else
                "Please specify your home state before matching, so we can find state-specific scholarships alongside central schemes:"
            )
            await ctx.send(sender, create_card_message(narration, "form", form_card))
            return

        # Run matching engine (dispatches SchemeMatchRequest to SchemeMatchingAgent with resilient fallback)
        ctx.logger.info(f"[Coordinator] Orchestrating scheme match for {profile.student_name}...")
        eligible, close_misses = await request_scheme_matching(ctx, profile, str(uuid4()))
        LAST_MATCHES[sender] = eligible

        if not eligible:
            msg_text = (
                f"Aapke profile ke mutabiq filhal koi matching scheme nahi mili. "
                f"Lekin hamne {len(close_misses)} close-miss opportunities dekhi hain."
                if lang_hindi else
                f"No matching scholarships were found for your current profile based on published criteria. "
                f"However, we identified {len(close_misses)} near-match opportunities."
            )
            await ctx.send(sender, create_text_chat(msg_text))
            return

        carousel_card = get_carousel_card(eligible, close_misses)
        narration = (
            f"🎉 Badhai ho! Hamne aapke liye **{len(eligible)} matching scholarships** dhundhi hain (published criteria par based; official portal par confirm karein)! "
            f"Cards ko swipe karke eligibility aur document rules check karein:"
            if lang_hindi else
            f"🎉 Found **{len(eligible)} scholarships** matching your profile based on published criteria (confirm on the official portal)! "
            f"Swipe through the cards below to inspect grant amounts, deadlines, and required documents:"
        )
        await ctx.send(sender, create_card_message(narration, "carousel", carousel_card))
        return

    if action_type == "view_scheme_details":
        scheme_id = action_data.get("scheme_id")
        schemes = load_scholarships()
        selected = next((s for s in schemes if s["id"] == scheme_id), None)
        if selected:
            elig = selected.get("eligibility", {})
            status, score, reason = evaluate_scheme(selected, profile)
            sc_item = ScholarshipItem(
                id=selected["id"],
                name=selected["name"],
                provider=selected["provider"],
                portal=selected["portal"],
                portal_url=selected["portal_url"],
                source_url=selected.get("source_url", ""),
                amount=selected["amount"],
                category_list=elig.get("categories", []),
                min_marks=float(elig.get("min_marks", 0.0)),
                max_family_income=float(elig.get("max_family_income", 10000000.0)),
                applicable_states=elig.get("states", []),
                gender=elig.get("gender", "All"),
                deadline=selected.get("deadline", "2026-12-31"),
                description=selected.get("description", ""),
                match_score=score,
                match_status=status,
                match_reason=reason,
                last_verified=selected.get("last_verified", "2026-10-15"),
                verified=selected.get("verified", True)
            )

            doc_rule = DOC_RULES_DB.get(scheme_id, DOC_RULES_DB.get("default", {}))
            detail_card = get_scheme_detail_card(sc_item, doc_rule)
            explanation = await generate_grounded_explanation(sc_item, profile, lang_hindi)

            narration = (
                f"📋 **{sc_item.name}** ki details:\n\n{explanation}\n\n"
                f"Aap official portal par apply karne se pehle documents pre-check audit run kar sakte hain."
                if lang_hindi else
                f"📋 Details for **{sc_item.name}**:\n\n{explanation}\n\n"
                f"Ensure you complete the document pre-check before submitting on the official portal."
            )
            await ctx.send(sender, create_card_message(narration, "detail", detail_card))
            return

    if action_type in ["open_doc_audit", "audit_for_scheme"]:
        scheme_id = action_data.get("scheme_id", "nsp_central_sector") if action_data else "nsp_central_sector"
        narration = (
            "📄 **Document Compliance & Anti-Rejection Pre-Check**\n\n"
            "Apne certificate ka text yahan paste karein (jaise: Income Certificate, Caste Certificate, ya Marksheet). "
            "Ham check karenge:\n"
            "- 📅 Issue Date & Validity (6 mahine / financial year)\n"
            "- 💰 Annual Income Limit vs Scheme Cap\n"
            "- 👤 Name & Category Matching\n"
            "- 🏦 NPCI Aadhaar DBT Bank Readiness\n\n"
            "*Privacy Note: We never log or store full Aadhaar numbers; all numbers are masked automatically.*"
            if lang_hindi else
            "📄 **Anti-Rejection Document Pre-Check Audit**\n\n"
            "Paste the text of your income certificate, caste certificate, or marksheet below to run an instant compliance check.\n\n"
            "Our deterministic engine verifies:\n"
            "1. 📅 Date of issuance & validity (6-month rule / current financial year)\n"
            "2. 💰 Stated family income against scheme maximum ceiling\n"
            "3. 👤 Character-by-character applicant name matching\n"
            "4. 🏦 Mandatory NPCI Aadhaar DBT bank account mapping\n\n"
            "*Privacy Protection: All sensitive identification numbers (Aadhaar, PAN) are automatically masked.*"
        )
        await ctx.send(sender, create_text_chat(narration))
        return

    if action_type == "view_deadlines":
        deadline_items = await request_deadlines(ctx, [])
        deadlines_card = get_deadlines_card(deadline_items)
        narration = (
            "📅 **Current Academic Session Deadlines & Calendar:**\n"
            "Ye scholarships closing dates hain. Kisi bhi scheme ka `.ics` calendar event generate kar sakte hain."
            if lang_hindi else
            "📅 **Scholarship Application Deadlines (Academic Year 2026-27):**\n"
            "Real-time countdowns computed from published cutoffs. Tap below to save reminders:"
        )
        await ctx.send(sender, create_card_message(narration, "review", deadlines_card))
        return

    if action_type == "save_reminders":
        scheme_id = action_data.get("scheme_id") if action_data else None
        if not scheme_id and sender in SAVED_SHORTLIST and SAVED_SHORTLIST[sender]:
            scheme_id = SAVED_SHORTLIST[sender][-1]
        elif not scheme_id and sender in LAST_MATCHES and LAST_MATCHES[sender]:
            scheme_id = LAST_MATCHES[sender][0].id
        if not scheme_id:
            scheme_id = "nsp_central_sector"

        schemes = load_scholarships()
        selected = next((s for s in schemes if s["id"] == scheme_id), schemes[0])

        user_rem = SAVED_REMINDERS.setdefault(sender, [])
        if selected["id"] not in user_rem:
            user_rem.append(selected["id"])

        if hasattr(ctx, "storage"):
            try:
                ctx.storage.set(f"reminders:{sender}", user_rem)
                subs = ctx.storage.get("subscribers") or []
                if sender not in subs:
                    subs.append(sender)
                    ctx.storage.set("subscribers", subs)
            except Exception:
                pass

        ics_text = generate_ics_calendar(selected["name"], selected.get("deadline", "2026-12-31"), selected.get("portal_url", "https://scholarships.gov.in"))

        narration = (
            f"✅ **Reminders saved for {selected['name']}!**\n\n"
            "Proactive notifications will trigger 7 days, 3 days, and 1 day before cutoff.\n\n"
            "📅 **Copyable Calendar Event (.ics)**:\n"
            "```text\n"
            f"{ics_text}\n"
            "```\n"
            f"💡 *Tip: Copy the text block above to save as a `.ics` calendar file.*"
        )
        await ctx.send(sender, create_text_chat(narration))
        return

    if action_type == "request_concierge_pack":
        scheme_id = action_data.get("scheme_id") if action_data else None
        if not scheme_id and sender in SAVED_SHORTLIST and SAVED_SHORTLIST[sender]:
            scheme_id = SAVED_SHORTLIST[sender][-1]
        elif not scheme_id and sender in LAST_MATCHES and LAST_MATCHES[sender]:
            scheme_id = LAST_MATCHES[sender][0].id
        if not scheme_id:
            scheme_id = "nsp_central_sector"

        schemes = load_scholarships()
        selected = next((s for s in schemes if s["id"] == scheme_id), schemes[0])

        import time
        # Send official Payment Protocol RequestPayment
        payment_req = create_concierge_payment_request(
            coordinator_agent.address,
            selected["name"],
            str(uuid4()),
            scheme_id=selected["id"]
        )
        PENDING_PAYMENTS[payment_req.reference] = {
            "scheme_id": selected["id"],
            "sender": sender,
            "timestamp": time.time()
        }
        PENDING_PAYMENTS_BY_SENDER[sender] = {
            "reference": payment_req.reference,
            "scheme_id": selected["id"],
            "timestamp": time.time()
        }
        if hasattr(ctx, "storage"):
            try:
                ctx.storage.set(f"payment:{payment_req.reference}", PENDING_PAYMENTS[payment_req.reference])
                ctx.storage.set(f"payment_sender:{sender}", PENDING_PAYMENTS_BY_SENDER[sender])
            except Exception:
                pass

        ctx.logger.info(f"[Coordinator] Dispatched official RequestPayment (ref={payment_req.reference}) for '{selected['name']}' to {sender}")
        await ctx.send(sender, payment_req)

        # Send user-facing interactive card explaining the payment request
        narration = (
            f"⚡ **Application Concierge Pack for {selected['name']}**\n\n"
            "An official **Fetch.ai Payment Protocol Request** has been dispatched to your wallet / client:\n\n"
            f"- **Scheme:** {selected['name']}\n"
            f"- **Accepted Funds:** 0.01 USDC (Skyfire) / 0.05 FET (Direct)\n"
            f"- **Payment Reference:** `{payment_req.reference}`\n"
            f"- **Operational Mode:** DEMO / TESTNET Enabled\n"
            f"- **Validity:** 300 seconds\n\n"
            "Submit `CommitPayment` with your transaction hash via your uAgents client to unlock the complete concierge dossier.\n\n"
            "*Alternatively, you can preview the first section of the dossier for free below.*"
        )
        summary_rows = [
            {"label": "Product", "value": f"Concierge Pack: {selected['name'][:35]}"},
            {"label": "Protocol", "value": "Fetch.ai Agent Payment Protocol (uagents_core)"},
            {"label": "Accepted Funds", "value": "0.01 USDC (Skyfire) / 0.05 FET (Direct)"},
            {"label": "Mode", "value": "DEMO / TESTNET Active"}
        ]
        pay_card = {
            "title": "Payment Protocol Request Active",
            "summary_rows": summary_rows,
            "actions": [
                {
                    "label": "👁️ Preview pack (first section only, free)",
                    "selection": {"action": "preview_concierge_pack", "scheme_id": selected["id"]}
                },
                {
                    "label": "🔙 Back to menu",
                    "selection": {"action": "back_to_hub"}
                }
            ],
            "reject_cta": {
                "label": "Cancel Payment",
                "selection": {"action": "reject_payment", "reference": payment_req.reference}
            }
        }
        await ctx.send(sender, create_card_message(narration, "detail", pay_card))
        return

    if action_type == "preview_concierge_pack":
        scheme_id = action_data.get("scheme_id") if action_data else "nsp_central_sector"
        schemes = load_scholarships()
        selected = next((s for s in schemes if s["id"] == scheme_id), schemes[0])
        preview_text = (
            f"🎓 **ScholarBot Application Concierge Pack [FREE PREVIEW]**\n\n"
            f"**Scheme:** {selected['name']}\n"
            f"**Funding Body:** {selected['provider']}\n"
            f"**Official Portal:** [{selected['portal']}]({selected['portal_url']})\n"
            f"**Application Deadline:** {selected.get('deadline', '2026-12-31')}\n\n"
            f"---\n\n"
            f"### 👤 1. Applicant Pre-Filled Dossier (Preview Section)\n"
            f"- **Student Name:** {profile.student_name}\n"
            f"- **Domicile State:** {profile.state}\n"
            f"- **Category:** {profile.category}\n"
            f"- **Course:** {profile.course}\n"
            f"- **Academic Score:** {profile.marks_percentage}%\n"
            f"- **Annual Family Income:** ₹{profile.family_income:,.0f}\n"
            f"- **Aadhaar-Seeded Bank Account:** Required (NPCI DBT active)\n\n"
            f"---\n"
            f"*Preview Note: Full Concierge Pack (Sections 2-5: Document Checklist, Portal Workflow, Anti-Rejection Tips, and Tailored Statement of Purpose) is unlocked via Fetch.ai Payment Protocol commit.*\n\n"
            f"Use the Action Hub to explore other scholarships or audit documents:"
        )
        hub_card = get_action_hub_card()
        await ctx.send(sender, create_card_message(preview_text, "carousel", hub_card))
        return

    if action_type == "reject_payment":
        ref = action_data.get("reference") if action_data else None
        if ref and ref in PENDING_PAYMENTS:
            del PENDING_PAYMENTS[ref]
        PENDING_PAYMENTS_BY_SENDER.pop(sender, None)
        await ctx.send(sender, create_text_chat("Payment request was cancelled. All free scholarship discovery, eligibility matching, and checklists remain active!"))
        return


    if action_type == "simulate_what_if":
        # Simulate income at ₹2,40,000 and ₹4,00,000
        sim_profile = StudentProfile(**profile.model_dump())
        sim_profile.family_income = 240000.0
        m_24, _ = match_scholarships(sim_profile)

        sim_profile.family_income = 450000.0
        m_45, _ = match_scholarships(sim_profile)

        narration = (
            f"🔮 **'What-If' Simulation for {profile.student_name}:**\n\n"
            f"- **Scenario A (Family Income = ₹2.4 Lakhs / yr):**\n"
            f"  Eligible for **{len(m_24)} schemes** (Unlocks 100% tuition waivers: Rajasthan SJE, UP Dashmottar, ONGC).\n\n"
            f"- **Scenario B (Family Income = ₹4.5 Lakhs / yr):**\n"
            f"  Eligible for **{len(m_45)} schemes** (NSP Central Sector, Tata Trusts, Sitaram Jindal).\n\n"
            f"💡 *Advice: State quota fee waivers strictly require income <= ₹2.5 Lakhs. Keep your Tehsildar certificate accurate!*"
            if lang_hindi else
            f"🔮 **'What-If' Economic Simulation for {profile.student_name}:**\n\n"
            f"• **If Income is ₹2.4 Lakhs/yr:** You qualify for **{len(m_24)} scholarships**, unlocking complete tuition waivers.\n"
            f"• **If Income is ₹4.5 Lakhs/yr:** You qualify for **{len(m_45)} scholarships** (Central Sector, Tata, Jindal).\n\n"
            f"💡 *Takeaway: A certificate under ₹2.5L is the key threshold for state government fee waivers.*"
        )
        await ctx.send(sender, create_text_chat(narration))
        return

    if action_type == "view_profile":
        narration = (
            f"👤 **Saved Profile for {sender[:12]}...**\n"
            f"- Name: {profile.student_name}\n"
            f"- State: {profile.state}\n"
            f"- Course: {profile.course}\n"
            f"- Category: {profile.category}\n"
            f"- Income: ₹{profile.family_income:,.0f}\n"
            f"- Marks: {profile.marks_percentage}%\n\n"
            "Tap 'Edit Profile' to change, or 'Delete My Data' to remove all records."
        )
        review_card = get_profile_review_card(profile)
        await ctx.send(sender, create_card_message(narration, "review", review_card))
        return

    if action_type == "back_to_list":
        if sender in LAST_MATCHES and LAST_MATCHES[sender]:
            carousel_card = get_carousel_card(LAST_MATCHES[sender])
            await ctx.send(sender, create_card_message("Back to your scholarship results:", "carousel", carousel_card))
            return
        else:
            action_type = "open_hub"

    if action_type in ["back_to_hub", "new_search"]:
        hub_card = get_action_hub_card()
        await ctx.send(sender, create_card_message("Action Hub:", "carousel", hub_card))
        return

    if action_type == "done":
        farewell = (
            "Aapka swagat hai! Kisi bhi samay dubara query karne ke liye 'Hi' ya 'Menu' type karein. Shubhkaamnayein!"
            if lang_hindi else
            "Best of luck with your scholarship applications! Type 'Hi' anytime to reopen ScholarBot."
        )
        await ctx.send(sender, create_text_chat(farewell))
        return

    # ==========================================================================
    # 3. NATURAL LANGUAGE UNDERSTANDING & INTENT ROUTING
    # ==========================================================================
    # Check if text looks like a pasted document (Income, Caste, Marksheet)
    doc_keywords = ["certificate", "tehsildar", "annual income", "praman patra", "revenue", "validity", "marksheet", "father", "son of", "bonafide"]
    if any(k in user_text.lower() for k in doc_keywords) and len(user_text) > 30:
        ctx.logger.info(f"[Coordinator] Detected document text payload from {sender}. Running compliance audit...")
        audit_req = DocumentAuditRequest(
            session_id=str(uuid4()),
            scheme_id="nsp_central_sector",
            doc_type="income_certificate",
            doc_text=user_text,
            profile=profile
        )
        audit_res = await request_document_audit(ctx, audit_req, income_cap=profile.family_income or 250000.0)
        card = get_audit_result_card(audit_res)
        narration = (
            f"📄 **Document Pre-Check Audit Complete: Status {audit_res.overall_status} ({audit_res.readiness_score}/100)**\n\n"
            f"Hamne aapke document ka automated rule check kiya hai:"
            if lang_hindi else
            f"📄 **Document Compliance Audit Complete: {audit_res.overall_status} ({audit_res.readiness_score}/100 Readiness)**\n\n"
            f"Detailed pre-check findings against published government scholarship criteria:"
        )
        await ctx.send(sender, create_card_message(narration, "review", card))
        return

    # Intent Classification
    intent = await classify_intent(user_text)
    ctx.logger.info(f"[Coordinator] Detected intent: '{intent}'")

    if intent == "small_talk":
        hub_card = get_action_hub_card()
        greet = (
            "Namaste! 🙏 Main **ScholarBot** hoon. Main aapko 20+ government & private scholarships published criteria ke mutabiq match karta hoon, "
            "rejection-prevention document audit karta hoon, aur application guidance provide karta hoon (kripya official portal par confirm karein). "
            "Aap shuru karne ke liye niche Action Hub use karein ya apni details batayein:"
            if lang_hindi else
            "Hello! 🎓 I am **ScholarBot**, your autonomous scholarship advisor. "
            "I match central, state, and foundation scholarships based on published criteria (confirm on the official portal), run anti-rejection document checks, and track deadlines. "
            "How can I help you today? Check the Action Hub below or describe your situation:"
        )
        await ctx.send(sender, create_card_message(greet, "carousel", hub_card))
        return

    if intent == "audit_document":
        narration = (
            "Apne certificate ka text yahan paste karein ya upload karein (jaise Income Certificate ya Marksheet). "
            "Ham validity date, income limit, aur NPCI DBT status ka instant deterministic audit karenge."
            if lang_hindi else
            "Please paste the text of your certificate (Income, Caste, or Marksheet) here. "
            "I will run a deterministic compliance audit checking validity, income ceiling, and NPCI DBT readiness."
        )
        await ctx.send(sender, create_text_chat(narration))
        return

    if intent == "compare":
        schemes = load_scholarships()
        s1 = schemes[0]
        s2 = schemes[1]
        low = user_text.lower()
        matched = [s for s in schemes if any(w in low for w in s["name"].lower().split() if len(w) > 3)]
        if len(matched) >= 2:
            s1, s2 = matched[0], matched[1]
        elif len(matched) == 1:
            s1 = matched[0]
            s2 = schemes[1] if schemes[1]["id"] != s1["id"] else schemes[2]

        comp_table = (
            f"⚖️ **Side-by-Side Scholarship Comparison**\n\n"
            f"| Criteria | **{s1['name'][:28]}** | **{s2['name'][:28]}** |\n"
            f"|---|---|---|\n"
            f"| 💰 **Financial Aid** | {s1['amount']} | {s2['amount']} |\n"
            f"| 🏛️ **Provider** | {s1['provider']} | {s2['provider']} |\n"
            f"| 📉 **Income Ceiling** | ₹{s1['eligibility']['max_family_income']:,} | ₹{s2['eligibility']['max_family_income']:,} |\n"
            f"| 📊 **Min Marks** | {s1['eligibility']['min_marks']}% | {s2['eligibility']['min_marks']}% |\n"
            f"| 🎓 **Course** | {', '.join(s1['eligibility'].get('courses', ['All']))[:25]} | {', '.join(s2['eligibility'].get('courses', ['All']))[:25]} |\n"
            f"| 🚻 **Gender** | {s1['eligibility']['gender']} | {s2['eligibility']['gender']} |\n"
            f"| 📅 **Deadline** | {s1.get('deadline', '2026-12-31')} | {s2.get('deadline', '2026-12-31')} |\n"
            f"| 🌐 **Portal** | [{s1['portal']}]({s1['portal_url']}) | [{s2['portal']}]({s2['portal_url']}) |\n"
        )
        await ctx.send(sender, create_text_chat(comp_table))
        return

    if intent == "explain_scheme":
        schemes = load_scholarships()
        low = user_text.lower()
        selected = next((s for s in schemes if any(w in low for w in s["name"].lower().split() if len(w) > 3)), schemes[0])
        status, score, reason = evaluate_scheme(selected, profile)
        sc_item = ScholarshipItem(
            id=selected["id"],
            name=selected["name"],
            provider=selected["provider"],
            portal=selected["portal"],
            portal_url=selected["portal_url"],
            amount=selected["amount"],
            deadline=selected.get("deadline", "2026-12-31"),
            category_list=selected["eligibility"].get("categories", []),
            min_marks=float(selected["eligibility"].get("min_marks", 0.0)),
            max_family_income=float(selected["eligibility"].get("max_family_income", 10000000.0)),
            applicable_states=selected["eligibility"].get("states", []),
            gender=selected["eligibility"].get("gender", "All"),
            description=selected.get("description", ""),
            match_score=score,
            match_status=status,
            match_reason=reason,
            verified=selected.get("verified", False)
        )
        doc_rule = DOC_RULES_DB.get(selected["id"], DOC_RULES_DB.get("default", {}))
        detail_card = get_scheme_detail_card(sc_item, doc_rule)
        explanation = await generate_grounded_explanation(sc_item, profile, lang_hindi)
        narration = f"📖 **Scheme Dossier: {sc_item.name}**\n\n{explanation}\n\nApply at official portal: {sc_item.portal_url}"
        await ctx.send(sender, create_card_message(narration, "detail", detail_card))
        return

    if intent == "what_if":
        await handle_chat_message(ctx, sender, ChatMessage(content=[TextContent(type="text", text=json.dumps({"action": "simulate_what_if"}))]))
        return

    if intent == "concierge_pack":
        await handle_chat_message(ctx, sender, ChatMessage(content=[TextContent(type="text", text=json.dumps({"action": "request_concierge_pack"}))]))
        return

    if intent == "my_profile":
        await handle_chat_message(ctx, sender, ChatMessage(content=[TextContent(type="text", text=json.dumps({"action": "view_profile"}))]))
        return

    # Default / find_scholarships: Parse Free-Text Profile using LLM + Regex
    extracted_profile = await parse_student_profile(user_text)
    # Update profile fields
    if extracted_profile.state != "All":
        profile.state = extracted_profile.state
    if extracted_profile.category != "General" or "category" not in profile.missing_fields:
        profile.category = extracted_profile.category
    if extracted_profile.family_income != 250000.0 or "family_income" not in profile.missing_fields:
        profile.family_income = extracted_profile.family_income
    if extracted_profile.marks_percentage != 75.0 or "academic_marks" not in profile.missing_fields:
        profile.marks_percentage = extracted_profile.marks_percentage
    if extracted_profile.course != "Engineering":
        profile.course = extracted_profile.course
    if extracted_profile.gender != "All":
        profile.gender = extracted_profile.gender
    if extracted_profile.disability:
        profile.disability = True
    if extracted_profile.student_name != "Student":
        profile.student_name = extracted_profile.student_name

    persist_profile(sender, profile, ctx)

    # If state is unknown, or income/marks/course missing, show prefilled intake form
    state_unknown = (not profile.state or profile.state in ["All", "unknown", ""])
    income_missing = ("family_income" in extracted_profile.missing_fields)
    marks_missing = ("academic_marks" in extracted_profile.missing_fields)
    course_missing = ("course" in extracted_profile.missing_fields or not profile.course)

    if state_unknown or income_missing or marks_missing or course_missing or len(extracted_profile.missing_fields) >= 1:
        missing_names = ", ".join(extracted_profile.missing_fields or ["state"])
        form_card = get_intake_form_card(profile)
        narration = (
            f"Maine aapki kuch details note ki hain. Kripya baki details ({missing_names}) confirm karein:"
            if lang_hindi else
            f"I extracted some of your details! Please complete the remaining fields below to get matching scholarships based on published criteria:"
        )
        await ctx.send(sender, create_card_message(narration, "form", form_card))
        return

    # All key fields present: Show Review Card!
    review_card = get_profile_review_card(profile)
    narration = (
        f"Aapki profile extract ho gayi hai! Kripya details check karein aur 'Confirm & Match' par tap karein:"
        if lang_hindi else
        f"Great! I understood your profile: **{profile.state} | {profile.course} | {profile.category} | ₹{profile.family_income:,.0f} | {profile.marks_percentage:.1f}%**. "
        f"Please verify below and confirm to view matching scholarships:"
    )
    await ctx.send(sender, create_card_message(narration, "review", review_card))

# ==============================================================================
# PAYMENT PROTOCOL HANDLER
# ==============================================================================
@payment_proto.on_message(CommitPayment)
async def handle_payment_commit_msg(ctx: Context, sender: str, msg: CommitPayment):
    ctx.logger.info(f"[Coordinator Payment] Received CommitPayment from {sender} for transaction {msg.transaction_id}")
    pending = PENDING_PAYMENTS.get(msg.reference) or PENDING_PAYMENTS_BY_SENDER.get(sender)
    if not pending and hasattr(ctx, "storage"):
        try:
            pending = ctx.storage.get(f"payment:{msg.reference}") or ctx.storage.get(f"payment_sender:{sender}")
        except Exception:
            pass
    created_ts = pending.get("timestamp") if pending else None
    
    success, reply, text_msg = handle_payment_commit(msg, created_timestamp=created_ts)
    await ctx.send(sender, reply)

    
    if success:
        # Deliver pack for the scheme in payment metadata or pending record (NEVER hardcoded schemes[0])
        scheme_id = None
        if msg.metadata and isinstance(msg.metadata, dict):
            scheme_id = msg.metadata.get("scheme_id")
        if not scheme_id and pending:
            scheme_id = pending.get("scheme_id")
        if not scheme_id:
            scheme_id = "nsp_central_sector"

        profile = get_or_create_profile(sender)
        schemes = load_scholarships()
        selected = next((s for s in schemes if s["id"] == scheme_id), schemes[0])
        elig = selected.get("eligibility", {})
        sc_item = ScholarshipItem(
            id=selected["id"],
            name=selected["name"],
            provider=selected["provider"],
            portal=selected["portal"],
            portal_url=selected["portal_url"],
            amount=selected["amount"],
            deadline=selected.get("deadline", "2026-12-31"),
            category_list=elig.get("categories", []),
            min_marks=float(elig.get("min_marks", 0.0)),
            max_family_income=float(elig.get("max_family_income", 10000000.0)),
            applicable_states=elig.get("states", []),
            gender=elig.get("gender", "All"),
            description=selected.get("description", "")
        )
        doc_rule = DOC_RULES_DB.get(selected["id"], DOC_RULES_DB.get("default", {}))
        pack = generate_concierge_pack(sc_item, doc_rule, profile)
        await ctx.send(sender, create_text_chat(f"{text_msg}\n\n{pack.markdown_content}"))

        # Clean up pending record
        if msg.reference in PENDING_PAYMENTS:
            del PENDING_PAYMENTS[msg.reference]
        PENDING_PAYMENTS_BY_SENDER.pop(sender, None)

@payment_proto.on_message(RejectPayment)
async def handle_payment_reject(ctx: Context, sender: str, msg: RejectPayment):
    ctx.logger.info(f"[Coordinator Payment] Payment rejected by {sender}: {msg.reason}")
    PENDING_PAYMENTS_BY_SENDER.pop(sender, None)
    await ctx.send(sender, create_text_chat(f"Payment was cancelled or rejected ({msg.reason}). Free scholarship search and checklists remain fully available!"))

# ==============================================================================
# SUBAGENT REPLIES (Multi-Agent Bureau / Inter-Agent Communication)
# ==============================================================================
@coordinator_proto.on_message(SchemeMatchResponse)
async def handle_scheme_reply(ctx: Context, sender: str, msg: SchemeMatchResponse):
    ctx.logger.info(f"[Coordinator] Received SchemeMatchResponse from {sender} with {msg.total_found} matches.")

@coordinator_proto.on_message(DocumentAuditResponse)
async def handle_audit_reply(ctx: Context, sender: str, msg: DocumentAuditResponse):
    ctx.logger.info(f"[Coordinator] Received DocumentAuditResponse from {sender}: {msg.overall_status}")

@coordinator_proto.on_message(DeadlineResponse)
async def handle_deadline_reply(ctx: Context, sender: str, msg: DeadlineResponse):
    ctx.logger.info(f"[Coordinator] Received DeadlineResponse from {sender} with {len(msg.items)} deadlines.")

@chat_proto.on_message(ChatAcknowledgement)
async def handle_chat_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.debug(f"[Coordinator] Received ACK from {sender} for message {msg.acknowledged_msg_id}")

@coordinator_agent.on_interval(period=3600.0)
async def check_and_send_deadline_reminders(ctx: Context):
    """Proactively notifies subscribed students when their saved scholarship deadline is approaching (deduped across 7/3/1 tiers)."""
    ctx.logger.info("[Coordinator Interval] Scanning registered scholarship reminders for approaching deadlines...")
    schemes = {s["id"]: s for s in load_scholarships()}
    
    subscribers = set()
    if hasattr(ctx, "storage"):
        try:
            stored_subs = ctx.storage.get("subscribers") or []
            subscribers.update(stored_subs)
        except Exception:
            pass
    subscribers.update(SAVED_REMINDERS.keys())

    for user_address in subscribers:
        user_schemes = list(SAVED_REMINDERS.get(user_address, []))
        if hasattr(ctx, "storage"):
            try:
                stored = ctx.storage.get(f"reminders:{user_address}")
                if stored and isinstance(stored, list):
                    user_schemes = list(set(user_schemes + stored))
            except Exception:
                pass

        for sid in user_schemes:
            if sid in schemes:
                scheme = schemes[sid]
                days, tier, badge = calculate_deadline_metrics(scheme.get("deadline", "2026-12-31"))

                active_tier = None
                if 0 <= days <= 1:
                    active_tier = "tier_1"
                elif 0 <= days <= 3:
                    active_tier = "tier_3"
                elif 0 <= days <= 7:
                    active_tier = "tier_7"

                if active_tier:
                    dedup_key = f"reminder_sent:{user_address}:{sid}:{active_tier}"
                    already_sent = False
                    if hasattr(ctx, "storage"):
                        try:
                            already_sent = bool(ctx.storage.get(dedup_key))
                        except Exception:
                            pass

                    if not already_sent:
                        alert_msg = f"⏰ [Proactive Deadline Alert] Only {days} day(s) left to submit your application for **{scheme['name']}**! Official portal: {scheme['portal_url']}"
                        try:
                            await ctx.send(user_address, create_text_chat(alert_msg))
                            ctx.logger.info(f"[Coordinator Reminder] Sent proactive reminder for {sid} ({active_tier}) to {user_address}")
                            if hasattr(ctx, "storage"):
                                try:
                                    ctx.storage.set(dedup_key, True)
                                except Exception:
                                    pass
                        except Exception as e:
                            ctx.logger.warning(f"[Coordinator Reminder] Failed to dispatch reminder to {user_address}: {e}")


# Include protocols with manifest publishing for Agentverse discovery
coordinator_agent.include(chat_proto, publish_manifest=True)
coordinator_agent.include(payment_proto, publish_manifest=True)
coordinator_agent.include(coordinator_proto)

# Backward compatibility alias
agent = coordinator_agent

if __name__ == "__main__":
    print(f"Starting ScholarBot Coordinator on port {COORDINATOR_PORT} with address: {coordinator_agent.address}")
    coordinator_agent.run()
