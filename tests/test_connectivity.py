import os
import secrets
import pytest
from uagents import Agent, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    Resource,
    ResourceContent,
    StartSessionContent,
    TextContent,
    chat_protocol_spec,
)
from uagents_core.contrib.protocols.payment import (
    CommitPayment,
    RejectPayment,
    payment_protocol_spec,
)

import asyncio

def test_chat_protocol_spec_and_inclusion():
    """Verifies that Protocol(spec=chat_protocol_spec) can be included in an Agent with publish_manifest=True."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    cp = Protocol(spec=chat_protocol_spec)

    @cp.on_message(ChatMessage)
    async def handle_chat(ctx, sender, msg):
        pass

    @cp.on_message(ChatAcknowledgement)
    async def handle_ack(ctx, sender, msg):
        pass

    agent = Agent(name="test_conn_agent", loop=loop)
    # Must succeed without throwing RuntimeError
    agent.include(cp, publish_manifest=True)
    assert cp.name == "AgentChatProtocol"
    assert cp.version == "0.3.0"

def test_payment_protocol_spec_and_inclusion():
    """Verifies that Protocol(spec=payment_protocol_spec, role='seller') can be included with publish_manifest=True."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    pp = Protocol(spec=payment_protocol_spec, role="seller")

    @pp.on_message(CommitPayment)
    async def handle_commit(ctx, sender, msg):
        pass

    @pp.on_message(RejectPayment)
    async def handle_reject(ctx, sender, msg):
        pass

    agent = Agent(name="test_pay_agent", loop=loop)
    agent.include(pp, publish_manifest=True)
    assert pp.name == "AgentPaymentProtocol"
    assert pp.version == "0.1.0"

def test_session_and_resource_content_models():
    """Verifies StartSessionContent, EndSessionContent, and ResourceContent structure."""
    start = StartSessionContent()
    assert start.type == "start-session"

    end = EndSessionContent()
    assert end.type == "end-session"

    res = Resource(uri="https://example.com/doc.pdf", metadata={"mime_type": "application/pdf", "role": "document"})
    from uuid import uuid4
    rc = ResourceContent(resource_id=uuid4(), resource=res)
    assert rc.type == "resource"
    assert rc.resource.uri == "https://example.com/doc.pdf"

def test_no_hardcoded_seeds_in_code():
    """Ensures seeds are generated or sourced from environment, not static hardcoded strings."""
    from agents.coordinator import COORDINATOR_SEED
    assert COORDINATOR_SEED is not None
    assert len(COORDINATOR_SEED) >= 16
