import asyncio
import os
import sys
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.models import StudentProfile, SchemeMatchRequest, SchemeMatchResponse, DocumentAuditRequest
from agents.matcher import matcher_agent
from agents.auditor import auditor_agent
from agents.tracker import tracker_agent
from agents.coordinator import (
    coordinator_agent,
    request_scheme_matching,
    request_document_audit,
    request_deadlines,
    SCHEME_AGENT_ADDRESS,
    DOC_AGENT_ADDRESS,
    TRACKER_AGENT_ADDRESS,
)

class MockOrchestrationContext:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.logger = coordinator_agent._logger

    async def send_and_receive(self, destination: str, message, response_type, sync=False, timeout=5):
        if self.should_fail:
            return None, "TIMEOUT"
        if isinstance(message, SchemeMatchRequest):
            from core.matching import match_scholarships
            el, cm = match_scholarships(message.profile)
            return SchemeMatchResponse(session_id=message.session_id, total_found=len(el), matches=el, close_misses=cm), "DELIVERED"
        return None, "UNSUPPORTED"

@pytest.mark.asyncio
async def test_multi_agent_real_dispatch():
    """Tests that coordinator dispatches to specialist agent when reachable."""
    ctx = MockOrchestrationContext(should_fail=False)
    profile = StudentProfile(state="Rajasthan", category="OBC", family_income=200000.0, marks_percentage=80.0)
    matches, close_misses = await request_scheme_matching(ctx, profile, "sess-1")
    assert len(matches) > 0
    assert any(s.id == "raj_postmatric_sje" for s in matches)

@pytest.mark.asyncio
async def test_multi_agent_fallback_on_failure():
    """Tests that coordinator falls back to in-process logic when subagent fails/times out."""
    ctx = MockOrchestrationContext(should_fail=True)
    profile = StudentProfile(state="Rajasthan", category="OBC", family_income=200000.0, marks_percentage=80.0)
    matches, close_misses = await request_scheme_matching(ctx, profile, "sess-2")
    # Must still return matches via in-process fallback
    assert len(matches) > 0
    assert any(s.id == "raj_postmatric_sje" for s in matches)

def test_derived_addresses_not_made_up():
    """Verifies that addresses match the real agent instances, not fake static strings."""
    assert SCHEME_AGENT_ADDRESS == matcher_agent.address
    assert DOC_AGENT_ADDRESS == auditor_agent.address
    assert TRACKER_AGENT_ADDRESS == tracker_agent.address
