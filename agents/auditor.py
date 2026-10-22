import os
import sys

# Ensure parent directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from uagents import Agent, Context, Protocol
from core.doc_auditor import DOC_RULES_DB, audit_document_compliance
from core.matching import get_scheme_income_cap
from core.models import (
    DocumentAuditRequest,
    DocumentAuditResponse,
    DocumentGuidanceRequest,
    DocumentGuidanceResponse,
)

from core.identity import get_or_create_seed

AUDITOR_SEED = get_or_create_seed("AUDITOR_SEED", "auditor")
AUDITOR_PORT = int(os.getenv("AUDITOR_PORT", "8003"))

auditor_agent = Agent(
    name="doc_compliance_agent",
    seed=AUDITOR_SEED,
    port=AUDITOR_PORT,
    endpoint=[f"http://127.0.0.1:{AUDITOR_PORT}/submit"],
    description="Autonomous Document Compliance Specialist Agent: Audits certificates, income caps, validity dates, and issuing authorities to prevent application rejections.",
    metadata={
        "tags": ["scholarship", "India", "NSP", "document check", "deadlines", "eligibility"],
        "category": "education"
    }
)

print(f"[*] [Auditor] Address: {auditor_agent.address}")

auditor_proto = Protocol(name="DocumentComplianceProtocol", version="1.0.0")

@auditor_proto.on_message(model=DocumentAuditRequest, replies=DocumentAuditResponse)
async def handle_document_audit(ctx: Context, sender: str, msg: DocumentAuditRequest):
    ctx.logger.info(f"[Auditor] Received document audit request for scheme {msg.scheme_id} from {sender}")
    ctx.logger.info(f"  Doc Type: {msg.doc_type}, Text Length: {len(msg.doc_text)} chars")

    # Read income ceiling dynamically from data/scholarships.json
    income_cap = get_scheme_income_cap(msg.scheme_id)
    if income_cap is None:
        rule = DOC_RULES_DB.get(msg.scheme_id, DOC_RULES_DB.get("default", {}))
        income_cap = float(rule.get("income_cap", 250000.0))

    result = audit_document_compliance(msg, scheme_income_cap=income_cap)
    ctx.logger.info(f"[Auditor] Audit complete: Status={result.overall_status}, Score={result.readiness_score}/100, Checks={len(result.checks)}")
    await ctx.send(sender, result)

@auditor_proto.on_message(model=DocumentGuidanceRequest, replies=DocumentGuidanceResponse)
async def handle_doc_guidance(ctx: Context, sender: str, msg: DocumentGuidanceRequest):
    ctx.logger.info(f"[Auditor] Generating anti-rejection guidance for scheme: {msg.scheme_name} ({msg.scheme_id})")
    rule = DOC_RULES_DB.get(msg.scheme_id, DOC_RULES_DB.get("default", {}))

    response = DocumentGuidanceResponse(
        session_id=msg.session_id,
        scheme_id=msg.scheme_id,
        scheme_name=msg.scheme_name,
        mandatory_docs=rule.get("mandatory", []),
        critical_warning=rule.get("warning", ""),
        rejection_prevention_tips=rule.get("tips", []),
        portal_url=rule.get("portal", "https://scholarships.gov.in"),
        step_by_step_process=rule.get("steps", [])
    )
    await ctx.send(sender, response)

auditor_agent.include(auditor_proto)

# Backward compatibility aliases
doc_agent = auditor_agent
SCHEME_DOC_RULES = DOC_RULES_DB

if __name__ == "__main__":
    print(f"Starting Doc Compliance Auditor Agent on port {AUDITOR_PORT} with address: {auditor_agent.address}")
    auditor_agent.run()
