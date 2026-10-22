"""
Build script to compile self-contained Agentverse hosted deployment bundles:
1. scholarship_agentverse_hosted.py (Self-contained standalone safe-mode bundle)
2. hosted_coordinator.py (Coordinator with Agent Chat Protocol & Payment Protocol)
3. hosted_matcher.py (Scheme Matching Specialist Agent)
4. hosted_auditor.py (Document Compliance Specialist Agent)
5. hosted_tracker.py (Deadline Tracker Specialist Agent)

Zero local imports (no core/ or data/ dependencies).
Ready to paste directly into Agentverse hosted agent editor.
"""

import os
import json
import re

def build():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    data_dir = os.path.join(root_dir, "data")
    core_dir = os.path.join(root_dir, "core")

    with open(os.path.join(data_dir, "scholarships.json"), "r", encoding="utf-8") as f:
        scholarships_raw = json.load(f)
    with open(os.path.join(data_dir, "doc_rules.json"), "r", encoding="utf-8") as f:
        doc_rules_raw = json.load(f)

    def read_core(mod_name):
        path = os.path.join(core_dir, f"{mod_name}.py")
        if not os.path.exists(path):
            return ""
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r'from\s+core\.[a-zA-Z_]+\s+import\s*\([\s\S]*?\)', '', content)
        content = re.sub(r'from\s+core\.[a-zA-Z_]+\s+import\s+[^\n]+', '', content)
        content = re.sub(r'import\s+core\.[^\n]+', '', content)
        return content

    models_code = read_core("models")
    privacy_code = read_core("privacy")
    matching_code = read_core("matching")
    doc_auditor_code = read_core("doc_auditor")
    deadlines_code = read_core("deadlines")
    llm_code = read_core("llm")
    cards_code = read_core("cards")
    payments_code = read_core("payments")
    portal_verifier_code = read_core("portal_verifier")

    # Replace file loaders with in-memory embedded datasets
    matching_clean = re.sub(
        r'_base_dir\s*=\s*[^\n]+\nDATA_PATH\s*=\s*[^\n]+|DATA_PATH\s*=\s*[^\n]+',
        'DATA_PATH = "data/scholarships.json"',
        matching_code
    )
    matching_clean = re.sub(
        r'def load_scholarships\(\) -> List\[dict\]:[\s\S]*?return \[\]',
        'def load_scholarships() -> List[dict]:\n    return EMBEDDED_SCHOLARSHIPS',
        matching_clean
    )
    doc_auditor_clean = re.sub(
        r'DOC_RULES_PATH = [\s\S]*?DOC_RULES_DB = load_doc_rules\(\)',
        'def load_doc_rules() -> dict:\n    return EMBEDDED_DOC_RULES\n\nDOC_RULES_DB = EMBEDDED_DOC_RULES',
        doc_auditor_code
    )
    portal_verifier_clean = re.sub(
        r'CACHE_FILE = [^\n]+',
        'CACHE_FILE = "/tmp/portal_cache.json"',
        portal_verifier_code
    )

    common_imports = '''import asyncio
import base64
from datetime import datetime, timezone, timedelta
import hashlib
import json
import logging
import os
import re
import secrets
import ssl
import sys
import time
from typing import Dict, List, Optional, Any, Tuple
import urllib.request
import urllib.error
from uuid import uuid4

try:
    import httpx
except ImportError:
    httpx = None

from pydantic.v1 import Field
from uagents import Agent, Context, Protocol, Model
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
logger = logging.getLogger("ScholarBotHosted")
'''

    embedded_datasets = f'''
# ==============================================================================
# EMBEDDED DATASETS (Zero local filesystem dependencies)
# ==============================================================================
EMBEDDED_SCHOLARSHIPS = json.loads({repr(json.dumps(scholarships_raw))})
EMBEDDED_DOC_RULES = json.loads({repr(json.dumps(doc_rules_raw))})
'''

    # Read existing agent logic from scholarship_agentverse_hosted.py
    with open(os.path.join(root_dir, "scholarship_agentverse_hosted.py"), "r", encoding="utf-8") as f:
        hosted_content = f.read()

    marker = "hosted_agent = Agent("
    idx = hosted_content.find(marker)
    agent_logic = hosted_content[idx:] if idx != -1 else ""
    end_main = agent_logic.find('if __name__ == "__main__":')
    if end_main != -1:
        agent_logic = agent_logic[:end_main]
    agent_logic_clean = re.sub(r'# Export agent reference for Agentverse[\s\S]*', '', agent_logic)
    agent_logic_clean = re.sub(r'agent\s*=\s*hosted_agent[\s\S]*', '', agent_logic_clean).strip()

    agent_setup = """
try:
    _loop = asyncio.get_event_loop()
except RuntimeError:
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)

def scheme_to_item(s: dict) -> ScholarshipItem:
    elig = s.get("eligibility", {})
    return ScholarshipItem(
        id=s.get("id", ""),
        name=s.get("name", ""),
        provider=s.get("provider", ""),
        portal=s.get("portal", ""),
        portal_url=s.get("portal_url", ""),
        source_url=s.get("source_url", ""),
        amount=s.get("amount", ""),
        amount_value=float(s.get("amount_value", 0.0)),
        category_list=elig.get("categories", []),
        min_marks=float(elig.get("min_marks", 0.0)),
        max_family_income=float(elig.get("max_family_income", 10000000.0)),
        applicable_states=elig.get("states", []),
        gender=elig.get("gender", "All"),
        deadline=s.get("deadline"),
        description=s.get("description", ""),
        match_score=85,
        match_status="eligible",
        match_reason="",
        apply_url=s.get("apply_url") or s.get("portal_url", "")
    )
"""

    # Orchestration methods for hosted_coordinator.py
    coordinator_orchestration = '''
# Specialist Agent Addresses (set in Agentverse Secrets/Environment)
SCHEME_AGENT_ADDRESS = os.getenv("SCHEME_AGENT_ADDRESS", "")
DOC_AGENT_ADDRESS = os.getenv("DOC_AGENT_ADDRESS", "")
TRACKER_AGENT_ADDRESS = os.getenv("TRACKER_AGENT_ADDRESS", "")

LAST_DISPATCH_ATTRIBUTION: Dict[str, str] = {}

async def request_scheme_matching(ctx: Context, profile: StudentProfile, session_id: str) -> Tuple[List[ScholarshipItem], List[ScholarshipItem]]:
    attribution = "⚠️ Specialist unavailable, used local engine."
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
                attribution = f"Matched by Scheme Matching Agent ({SCHEME_AGENT_ADDRESS})"
                LAST_DISPATCH_ATTRIBUTION[session_id] = attribution
                return resp.matches, resp.close_misses
            else:
                ctx.logger.warning(f"[Coordinator Fallback] Specialist at {SCHEME_AGENT_ADDRESS} returned status: {status}. Falling back to local engine.")
        except Exception as ex:
            ctx.logger.warning(f"[Coordinator Fallback] Error contacting {SCHEME_AGENT_ADDRESS}: {ex}. Falling back to local engine.")

    ctx.logger.info("[Coordinator Fallback] Executing local engine fallback for matching...")
    LAST_DISPATCH_ATTRIBUTION[session_id] = attribution
    return match_scholarships(profile)

async def request_document_audit(ctx: Context, audit_req: DocumentAuditRequest, income_cap: float) -> DocumentAuditResponse:
    session_id = audit_req.session_id or str(uuid4())
    attribution = "⚠️ Specialist unavailable, used local engine."
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
                attribution = f"Audited by Document Compliance Agent ({DOC_AGENT_ADDRESS})"
                LAST_DISPATCH_ATTRIBUTION[session_id] = attribution
                return resp
            else:
                ctx.logger.warning(f"[Coordinator Fallback] Subagent at {DOC_AGENT_ADDRESS} returned status: {status}. Falling back to local engine.")
        except Exception as ex:
            ctx.logger.warning(f"[Coordinator Fallback] Error contacting {DOC_AGENT_ADDRESS}: {ex}. Falling back to local engine.")

    ctx.logger.info("[Coordinator Fallback] Executing local engine fallback for document audit...")
    LAST_DISPATCH_ATTRIBUTION[session_id] = attribution
    return audit_document_compliance(audit_req, scheme_income_cap=income_cap)

async def request_deadlines(ctx: Context, scheme_ids: List[str], session_id: Optional[str] = None) -> List[DeadlineItem]:
    sess_id = session_id or str(uuid4())
    attribution = "⚠️ Specialist unavailable, used local engine."
    if TRACKER_AGENT_ADDRESS and hasattr(ctx, "send_and_receive"):
        ctx.logger.info(f"[Coordinator] Dispatching DeadlineRequest to DeadlineTrackerAgent at {TRACKER_AGENT_ADDRESS}...")
        try:
            resp, status = await ctx.send_and_receive(
                TRACKER_AGENT_ADDRESS,
                DeadlineRequest(session_id=sess_id, scheme_ids=scheme_ids),
                response_type=DeadlineResponse,
                timeout=5
            )
            if resp and isinstance(resp, DeadlineResponse):
                ctx.logger.info(f"[Coordinator] Received DeadlineResponse from {TRACKER_AGENT_ADDRESS}: {len(resp.items)} deadlines.")
                attribution = f"Tracked by Deadline Tracker Agent ({TRACKER_AGENT_ADDRESS})"
                LAST_DISPATCH_ATTRIBUTION[sess_id] = attribution
                return resp.items
            else:
                ctx.logger.warning(f"[Coordinator Fallback] Subagent at {TRACKER_AGENT_ADDRESS} returned status: {status}. Falling back to local engine.")
        except Exception as ex:
            ctx.logger.warning(f"[Coordinator Fallback] Error contacting {TRACKER_AGENT_ADDRESS}: {ex}. Falling back to local engine.")

    ctx.logger.info("[Coordinator Fallback] Executing local engine fallback for deadlines...")
    schemes = load_scholarships()
    selected_items = [s for s in schemes if not scheme_ids or s["id"] in scheme_ids]
    LAST_DISPATCH_ATTRIBUTION[sess_id] = attribution
    return build_deadline_items(selected_items)
'''

    # Construct coordinator_agent_logic by applying specialist dispatches to agent_logic_clean
    coordinator_agent_logic = agent_logic_clean.replace(
        "USER_PROFILES: Dict[str, StudentProfile] = {}",
        "USER_PROFILES: Dict[str, StudentProfile] = {}\n" + coordinator_orchestration
    )

    old_match_block = '''        eligible, close_misses = match_scholarships(profile)
        if not eligible:
            await ctx.send(sender, create_text_chat(
                f"No scholarships matched your profile based on published criteria, but {len(close_misses)} are near matches. "
                f"Type 'menu' to open the Action Hub."))
            return True
        await ctx.send(sender, create_card_message(
            f"🎉 Found {len(eligible)} scholarships that match your profile (based on published criteria - confirm on the official portal).\\n"
            f"📌 Your details: {profile_summary_line(profile)}\\n\\nSwipe the cards to see grants, deadlines and required documents:",
            "carousel", get_carousel_card(eligible, close_misses)))
        return True'''

    new_match_block = '''        match_sess_id = str(uuid4())
        eligible, close_misses = await request_scheme_matching(ctx, profile, match_sess_id)
        attribution_str = LAST_DISPATCH_ATTRIBUTION.get(match_sess_id, "")
        attr_line = f"\\n\\n_{attribution_str}_" if attribution_str else ""
        if not eligible:
            await ctx.send(sender, create_text_chat(
                f"No scholarships matched your profile based on published criteria, but {len(close_misses)} are near matches. "
                f"Type 'menu' to open the Action Hub.{attr_line}"))
            return True
        await ctx.send(sender, create_card_message(
            f"🎉 Found {len(eligible)} scholarships that match your profile (based on published criteria - confirm on the official portal).\\n"
            f"📌 Your details: {profile_summary_line(profile)}{attr_line}\\n\\nSwipe the cards to see grants, deadlines and required documents:",
            "carousel", get_carousel_card(eligible, close_misses)))
        return True'''

    coordinator_agent_logic = coordinator_agent_logic.replace(old_match_block, new_match_block)

    old_deadline_block = '''    if action == "view_deadlines":
        items = build_deadline_items(load_scholarships())
        await ctx.send(sender, create_card_message(
            "📅 **Scholarship deadlines (days counted from today).**\\nDates come from our unverified dataset, so confirm every date on the official portal:",
            "review", get_deadlines_card(items)))
        return True'''

    new_deadline_block = '''    if action == "view_deadlines":
        deadlines_sess_id = str(uuid4())
        items = await request_deadlines(ctx, [], deadlines_sess_id)
        attribution_str = LAST_DISPATCH_ATTRIBUTION.get(deadlines_sess_id, "")
        attr_line = f"\\n\\n_{attribution_str}_" if attribution_str else ""
        await ctx.send(sender, create_card_message(
            f"📅 **Scholarship deadlines (days counted from today).\\nDates come from our unverified dataset, so confirm every date on the official portal:{attr_line}**",
            "review", get_deadlines_card(items)))
        return True'''

    coordinator_agent_logic = coordinator_agent_logic.replace(old_deadline_block, new_deadline_block)

    old_audit_block = '''        if len(user_text) > 30 and any(k in user_text.lower() for k in doc_keywords):
            target = storage_get(ctx, f"active_audit_scheme:{sender}") or "nsp_central_sector"
            req = DocumentAuditRequest(session_id=str(uuid4()), scheme_id=target, doc_type="income_certificate",
                                       doc_text=user_text, profile=profile)
            res = audit_document_compliance(req, scheme_income_cap=get_scheme_income_cap(target) or 250000.0)
            await ctx.send(sender, create_card_message(
                f"📄 **Document pre-check complete: {res.overall_status} ({res.readiness_score}/100)**",
                "review", get_audit_result_card(res)))
            return'''

    new_audit_block = '''        if len(user_text) > 30 and any(k in user_text.lower() for k in doc_keywords):
            target = storage_get(ctx, f"active_audit_scheme:{sender}") or "nsp_central_sector"
            audit_sess_id = str(uuid4())
            req = DocumentAuditRequest(
                session_id=audit_sess_id,
                scheme_id=target,
                doc_type="income_certificate",
                doc_text=user_text,
                profile=profile
            )
            res = await request_document_audit(ctx, req, income_cap=get_scheme_income_cap(target) or 250000.0)
            attribution_str = LAST_DISPATCH_ATTRIBUTION.get(audit_sess_id, "")
            attr_line = f"\\n\\n_{attribution_str}_" if attribution_str else ""
            await ctx.send(sender, create_card_message(
                f"📄 **Document pre-check complete: {res.overall_status} ({res.readiness_score}/100)**{attr_line}",
                "review", get_audit_result_card(res)))
            return'''

    coordinator_agent_logic = coordinator_agent_logic.replace(old_audit_block, new_audit_block)

    # 1. BUILD scholarship_agentverse_hosted.py (Standalone Safe-Mode Bundle)
    standalone_header = '''"""
ScholarBot - Standalone Agentverse Hosted Agent Bundle
100% self-contained single-file agent with zero local imports.
Ready for direct paste into the Agentverse hosted web editor.
"""
'''
    standalone_content = (
        standalone_header
        + common_imports
        + embedded_datasets
        + "\n# ==================== CORE MODELS ====================\n"
        + models_code
        + "\n# ==================== PRIVACY REDACTION ====================\n"
        + privacy_code
        + "\n# ==================== MATCHING ENGINE ====================\n"
        + matching_clean
        + "\n# ==================== DOCUMENT AUDITOR ====================\n"
        + doc_auditor_clean
        + "\n# ==================== DEADLINES & CALENDAR ====================\n"
        + deadlines_code
        + "\n# ==================== LLM & INTENT PARSER ====================\n"
        + llm_code
        + "\n# ==================== INTERACTIVE CARDS ====================\n"
        + cards_code
        + "\n# ==================== PAYMENT PROTOCOL ====================\n"
        + payments_code
        + "\n# ==================== REAL-TIME PORTAL VERIFIER ====================\n"
        + portal_verifier_clean
        + "\n# ==================== HOSTED AGENT & PROTOCOLS ====================\n"
        + agent_setup
        + "\n"
        + agent_logic_clean
        + "\n\n# Export agent reference for Agentverse\nagent = hosted_agent\n\nif __name__ == '__main__':\n    hosted_agent.run()\n"
    )

    with open(os.path.join(root_dir, "scholarship_agentverse_hosted.py"), "w", encoding="utf-8") as f:
        f.write(standalone_content)
    print("Successfully built standalone scholarship_agentverse_hosted.py")

    # 2. BUILD hosted_coordinator.py (Coordinator with specialist routing)
    coordinator_header = '''"""
ScholarBot - Hosted Coordinator Agent
100% self-contained single-file agent with zero local imports.
Dispatches to specialist agents on Agentverse via ACP with local fallback.
Ready for direct paste into Agentverse hosted editor.
"""
'''
    coordinator_content = (
        coordinator_header
        + common_imports
        + embedded_datasets
        + "\n# Specialist Agent Addresses (set in Agentverse Secrets/Environment)\n"
        + 'SCHEME_AGENT_ADDRESS = os.getenv("SCHEME_AGENT_ADDRESS", "")\n'
        + 'DOC_AGENT_ADDRESS = os.getenv("DOC_AGENT_ADDRESS", "")\n'
        + 'TRACKER_AGENT_ADDRESS = os.getenv("TRACKER_AGENT_ADDRESS", "")\n'
        + "\n# ==================== CORE MODELS ====================\n"
        + models_code
        + "\n# ==================== PRIVACY REDACTION ====================\n"
        + privacy_code
        + "\n# ==================== MATCHING ENGINE (LOCAL FALLBACK) ====================\n"
        + matching_clean
        + "\n# ==================== DOCUMENT AUDITOR (LOCAL FALLBACK) ====================\n"
        + doc_auditor_clean
        + "\n# ==================== DEADLINES & CALENDAR ====================\n"
        + deadlines_code
        + "\n# ==================== LLM & INTENT PARSER ====================\n"
        + llm_code
        + "\n# ==================== INTERACTIVE CARDS ====================\n"
        + cards_code
        + "\n# ==================== PAYMENT PROTOCOL ====================\n"
        + payments_code
        + "\n# ==================== REAL-TIME PORTAL VERIFIER ====================\n"
        + portal_verifier_clean
        + "\n# ==================== HOSTED AGENT & PROTOCOLS ====================\n"
        + agent_setup
        + "\n"
        + coordinator_agent_logic
        + "\n\n# Export agent reference for Agentverse\nagent = hosted_agent\n\nif __name__ == '__main__':\n    hosted_agent.run()\n"
    )

    with open(os.path.join(root_dir, "hosted_coordinator.py"), "w", encoding="utf-8") as f:
        f.write(coordinator_content)
    print("Successfully built hosted_coordinator.py")

    # 3. BUILD hosted_matcher.py
    matcher_content = f'''"""
ScholarBot - Hosted Scheme Matching Specialist Agent
100% self-contained single-file agent with zero local imports.
Ready for direct paste into Agentverse hosted editor.
"""
{common_imports}
{embedded_datasets}

# ==================== CORE MODELS ====================
{models_code}

# ==================== MATCHING ENGINE ====================
{matching_clean}

# ==================== SPECIALIST AGENT DEFINITION ====================
MATCHER_SEED = os.getenv("MATCHER_SEED", "scholarbot_matcher_agentverse_v3")
agent = Agent(
    name="scheme_matching_agent",
    seed=MATCHER_SEED,
    description="Autonomous Scheme Matching Specialist Agent: Evaluates candidate profiles against published criteria for central, state, and private scholarships in India.",
    metadata={{
        "tags": ["scholarship", "India", "NSP", "matcher", "eligibility"],
        "category": "education"
    }}
)

matcher_proto = Protocol(name="SchemeMatchingProtocol", version="1.0.0")

@matcher_proto.on_message(model=SchemeMatchRequest, replies=SchemeMatchResponse)
async def handle_match_request(ctx: Context, sender: str, msg: SchemeMatchRequest):
    ctx.logger.info(f"[Matcher] Received match request for {{msg.profile.student_name}} from {{sender}}")
    eligible, close_misses = match_scholarships(msg.profile)
    ctx.logger.info(f"[Matcher] Found {{len(eligible)}} eligible schemes and {{len(close_misses)}} close misses.")
    response = SchemeMatchResponse(
        session_id=msg.session_id,
        total_found=len(eligible),
        matches=eligible,
        close_misses=close_misses
    )
    await ctx.send(sender, response)

agent.include(matcher_proto)

# Alias for compatibility
hosted_agent = agent
'''
    with open(os.path.join(root_dir, "hosted_matcher.py"), "w", encoding="utf-8") as f:
        f.write(matcher_content)
    print("Successfully built hosted_matcher.py")

    # 4. BUILD hosted_auditor.py
    auditor_content = f'''"""
ScholarBot - Hosted Document Compliance Specialist Agent
100% self-contained single-file agent with zero local imports.
Ready for direct paste into Agentverse hosted editor.
"""
{common_imports}
{embedded_datasets}

# ==================== CORE MODELS ====================
{models_code}

# ==================== PRIVACY REDACTION ====================
{privacy_code}

# ==================== DOCUMENT AUDITOR ====================
{doc_auditor_clean}

# ==================== SPECIALIST AGENT DEFINITION ====================
AUDITOR_SEED = os.getenv("AUDITOR_SEED", "scholarbot_auditor_agentverse_v3")
agent = Agent(
    name="doc_compliance_agent",
    seed=AUDITOR_SEED,
    description="Autonomous Document Compliance Specialist Agent: Pre-checks income certificates, caste certificates, and marksheets against anti-rejection rules.",
    metadata={{
        "tags": ["scholarship", "India", "audit", "document check", "compliance"],
        "category": "education"
    }}
)

auditor_proto = Protocol(name="DocumentComplianceProtocol", version="1.0.0")

@auditor_proto.on_message(model=DocumentAuditRequest, replies=DocumentAuditResponse)
async def handle_audit_request(ctx: Context, sender: str, msg: DocumentAuditRequest):
    ctx.logger.info(f"[Auditor] Received document audit request from {{sender}} for scheme: {{msg.scheme_id}}")
    rule = DOC_RULES_DB.get(msg.scheme_id, DOC_RULES_DB.get("default", {{}}))
    income_cap = float(rule.get("income_cap", 250000.0))
    res = audit_document_compliance(msg, scheme_income_cap=income_cap)
    await ctx.send(sender, res)

@auditor_proto.on_message(model=DocumentGuidanceRequest, replies=DocumentGuidanceResponse)
async def handle_guidance_request(ctx: Context, sender: str, msg: DocumentGuidanceRequest):
    rule = DOC_RULES_DB.get(msg.scheme_id, DOC_RULES_DB.get("default", {{}}))
    await ctx.send(sender, DocumentGuidanceResponse(
        session_id=msg.session_id,
        scheme_id=msg.scheme_id,
        scheme_name=msg.scheme_name,
        mandatory_docs=rule.get("mandatory", []),
        critical_warning=rule.get("warning", ""),
        rejection_prevention_tips=rule.get("tips", []),
        portal_url=rule.get("portal", "https://scholarships.gov.in"),
        step_by_step_process=rule.get("steps", [])
    ))

agent.include(auditor_proto)

# Alias for compatibility
hosted_agent = agent
'''
    with open(os.path.join(root_dir, "hosted_auditor.py"), "w", encoding="utf-8") as f:
        f.write(auditor_content)
    print("Successfully built hosted_auditor.py")

    # 5. BUILD hosted_tracker.py
    tracker_content = f'''"""
ScholarBot - Hosted Deadline Tracker Specialist Agent
100% self-contained single-file agent with zero local imports.
Ready for direct paste into Agentverse hosted editor.
"""
{common_imports}
{embedded_datasets}

# ==================== CORE MODELS ====================
{models_code}

# ==================== DEADLINES & CALENDAR ====================
{deadlines_code}

# ==================== SPECIALIST AGENT DEFINITION ====================
TRACKER_SEED = os.getenv("TRACKER_SEED", "scholarbot_tracker_agentverse_v3")
agent = Agent(
    name="deadline_tracker_agent",
    seed=TRACKER_SEED,
    description="Autonomous Deadline Tracking Specialist Agent: Tracks scholarship application closing dates, computes urgency tiers, and generates iCalendar files.",
    metadata={{
        "tags": ["scholarship", "India", "deadlines", "calendar", "reminders"],
        "category": "education"
    }}
)

tracker_proto = Protocol(name="DeadlineTrackerProtocol", version="1.0.0")

@tracker_proto.on_message(model=DeadlineRequest, replies=DeadlineResponse)
async def handle_deadline_request(ctx: Context, sender: str, msg: DeadlineRequest):
    ctx.logger.info(f"[Tracker] Received deadline request for {{len(msg.scheme_ids)}} schemes from {{sender}}")
    raw_schemes = EMBEDDED_SCHOLARSHIPS
    selected_items: list[ScholarshipItem] = []
    for s in raw_schemes:
        if not msg.scheme_ids or s["id"] in msg.scheme_ids:
            elig = s.get("eligibility", {{}})
            selected_items.append(ScholarshipItem(
                id=s["id"],
                name=s["name"],
                provider=s["provider"],
                portal=s["portal"],
                portal_url=s["portal_url"],
                source_url=s.get("source_url", ""),
                amount=s["amount"],
                category_list=elig.get("categories", []),
                min_marks=float(elig.get("min_marks", 0.0)),
                max_family_income=float(elig.get("max_family_income", 10000000.0)),
                applicable_states=elig.get("states", []),
                gender=elig.get("gender", "All"),
                deadline=s.get("deadline", "2026-12-31"),
                description=s.get("description", ""),
                match_score=85,
                match_status="eligible",
                match_reason="",
                apply_url=s.get("apply_url") or s.get("portal_url", "")
            ))
    deadline_items = build_deadline_items(selected_items)
    await ctx.send(sender, DeadlineResponse(session_id=msg.session_id, items=deadline_items))

@agent.on_interval(period=3600.0)
async def proactive_deadline_scan(ctx: Context):
    ctx.logger.info("[Tracker Heartbeat] Running scheduled scan for closing scholarships...")
    raw = EMBEDDED_SCHOLARSHIPS
    closing_soon = []
    for s in raw:
        deadline_str = s.get("deadline", "2026-12-31")
        try:
            parts = [int(p) for p in deadline_str.split("-")]
            dt = datetime(parts[0], parts[1], parts[2], 23, 59, 59, tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            days = (dt - now).days
            if 0 <= days <= 7:
                closing_soon.append((s["name"], days))
        except Exception:
            pass
    if closing_soon:
        ctx.logger.warning(f"[ALERT] {{len(closing_soon)}} schemes closing within 7 days: {{closing_soon}}")

agent.include(tracker_proto)

# Alias for compatibility
hosted_agent = agent
'''
    with open(os.path.join(root_dir, "hosted_tracker.py"), "w", encoding="utf-8") as f:
        f.write(tracker_content)
    print("Successfully built hosted_tracker.py")

if __name__ == "__main__":
    build()
