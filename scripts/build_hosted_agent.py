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
        deadline=s.get("deadline", "2026-12-31"),
        description=s.get("description", ""),
        match_score=85,
        match_status="eligible",
        match_reason="",
        apply_url=s.get("apply_url") or s.get("portal_url", "")
    )
"""

    agent_logic_clean = re.sub(r'# Export agent reference for Agentverse\s+agent = hosted_agent', '', agent_logic).strip()

    # 1. BUILD scholarship_agentverse_hosted.py (Standalone Safe-Mode Bundle)
    standalone_content = (
        '"""\nScholarBot - Standalone Agentverse Hosted Agent Bundle\n'
        '100% self-contained single-file agent with zero local imports.\n'
        'Ready for direct paste into the Agentverse hosted web editor.\n"""\n'
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
        + "\n\n# Export agent reference for Agentverse\nagent = hosted_agent\n"
    )

    with open(os.path.join(root_dir, "scholarship_agentverse_hosted.py"), "w", encoding="utf-8") as f:
        f.write(standalone_content)
    print("Successfully built standalone scholarship_agentverse_hosted.py")

    # 2. BUILD hosted_coordinator.py (Coordinator with specialist routing)
    coordinator_content = (
        '"""\nScholarBot - Hosted Coordinator Agent\n'
        '100% self-contained single-file agent with zero local imports.\n'
        'Dispatches to specialist agents on Agentverse via ACP with local fallback.\n'
        'Ready for direct paste into Agentverse hosted editor.\n"""\n'
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
        + agent_logic_clean
        + "\n\n# Export agent reference for Agentverse\nagent = hosted_agent\n"
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

auditor_proto = Protocol(name="DocumentAuditProtocol", version="1.0.0")

@auditor_proto.on_message(model=DocumentAuditRequest, replies=DocumentAuditResponse)
async def handle_audit_request(ctx: Context, sender: str, msg: DocumentAuditRequest):
    ctx.logger.info(f"[Auditor] Received document audit request from {{sender}} for scheme: {{msg.scheme_id}}")
    res = audit_document_compliance(msg)
    await ctx.send(sender, res)

@auditor_proto.on_message(model=DocumentGuidanceRequest, replies=DocumentGuidanceResponse)
async def handle_guidance_request(ctx: Context, sender: str, msg: DocumentGuidanceRequest):
    guidance = get_document_guidance(msg.scheme_id)
    await ctx.send(sender, DocumentGuidanceResponse(
        session_id=msg.session_id,
        scheme_id=msg.scheme_id,
        mandatory=guidance.get("mandatory", []),
        optional=guidance.get("optional", []),
        issuing_authority=guidance.get("issuing_authority", "Authorized Competent Authority")
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
