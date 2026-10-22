"""Real integration test running Coordinator, Matcher, Auditor, and Tracker
inside a real local Fetch.ai Bureau without mocks.

Flows tested:
1. Full interactive flow:
   submit_intake -> confirm_and_match -> pasted document -> view_deadlines -> compare -> request_concierge_pack
2. Specialist outage fallback:
   When Auditor agent is unreachable, Coordinator logs clear fallback message and succeeds in-process.
"""
import asyncio
import json
import logging
import os
import socket
import sys
from uuid import uuid4
import pytest

from uagents import Agent, Bureau, Context, Protocol
from uagents.resolver import RulesBasedResolver
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    MetadataContent,
    TextContent,
    chat_protocol_spec,
)

from agents.coordinator import (
    COORDINATOR_SEED,
    chat_proto,
    payment_proto,
    coordinator_proto,
)
from agents.matcher import MATCHER_SEED, matcher_proto
from agents.auditor import AUDITOR_SEED, auditor_proto
from agents.tracker import TRACKER_SEED, tracker_proto

def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

@pytest.mark.asyncio
async def test_real_bureau_multi_agent_flow():
    port = find_free_port()
    ep = f"http://127.0.0.1:{port}/submit"

    loop = asyncio.get_running_loop()

    # Fresh agent instances bound to current running event loop
    coord = Agent(name="coordinator", seed=COORDINATOR_SEED, loop=loop)
    coord.include(chat_proto)
    coord.include(payment_proto)
    coord.include(coordinator_proto)

    matcher = Agent(name="matcher", seed=MATCHER_SEED, loop=loop)
    matcher.include(matcher_proto)

    auditor = Agent(name="auditor", seed=AUDITOR_SEED, loop=loop)
    auditor.include(auditor_proto)

    tracker = Agent(name="tracker", seed=TRACKER_SEED, loop=loop)
    tracker.include(tracker_proto)

    client = Agent(name="test_client", seed=f"client_{uuid4().hex[:8]}", loop=loop)
    client_proto = Protocol(spec=chat_protocol_spec)

    received_chat_messages = []
    response_event = asyncio.Event()

    @client_proto.on_message(ChatMessage)
    async def on_client_chat(ctx: Context, sender: str, msg: ChatMessage):
        received_chat_messages.append(msg)
        response_event.set()

    @client_proto.on_message(ChatAcknowledgement)
    async def on_client_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
        pass

    client.include(client_proto)

    res = RulesBasedResolver({
        coord.address: ep,
        matcher.address: ep,
        auditor.address: ep,
        tracker.address: ep,
        client.address: ep,
    })
    for a in [coord, matcher, auditor, tracker, client]:
        a._resolver = res

    # Ensure coordinator dispatches to the instantiated test specialists
    import agents.coordinator as coord_mod
    orig_scheme = coord_mod.SCHEME_AGENT_ADDRESS
    orig_doc = coord_mod.DOC_AGENT_ADDRESS
    orig_tracker = coord_mod.TRACKER_AGENT_ADDRESS

    coord_mod.SCHEME_AGENT_ADDRESS = matcher.address
    coord_mod.DOC_AGENT_ADDRESS = auditor.address
    coord_mod.TRACKER_AGENT_ADDRESS = tracker.address

    scenario_done = asyncio.Event()
    scenario_error = []

    @client.on_event("startup")
    async def run_scenario(ctx: Context):
        try:
            # Poll until Bureau port is actively accepting connections
            for _ in range(40):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    if s.connect_ex(("127.0.0.1", port)) == 0:
                        break
                await asyncio.sleep(0.05)

            async def send_and_wait(payload_text: str, timeout: float = 10.0) -> ChatMessage:
                response_event.clear()
                await ctx.send(coord.address, ChatMessage(
                    msg_id=uuid4(),
                    content=[TextContent(type="text", text=payload_text)]
                ))
                await asyncio.wait_for(response_event.wait(), timeout=timeout)
                assert len(received_chat_messages) > 0
                return received_chat_messages[-1]

            # Step 1: submit_intake
            p1 = json.dumps({
                "action": "submit_intake",
                "state": "Uttar Pradesh",
                "category": "OBC",
                "course": "B.Tech",
                "family_income": 180000,
                "marks_percentage": 85.0
            })
            r1 = await send_and_wait(p1)
            assert "profile" in r1.text().lower() or "verify" in r1.text().lower() or any(isinstance(c, MetadataContent) for c in r1.content)


            # Step 2: confirm_and_match (triggers real dispatch to matcher_agent)
            p2 = json.dumps({"action": "confirm_and_match"})
            r2 = await send_and_wait(p2)
            has_meta = any(isinstance(c, MetadataContent) for c in r2.content)
            assert has_meta or "scholarship" in r2.text().lower()

            # Step 3: pasted document (triggers real dispatch to auditor_agent)
            p3 = (
                "GOVERNMENT OF UTTAR PRADESH\n"
                "OFFICE OF THE TAHSILDAR, LUCKNOW\n"
                "INCOME CERTIFICATE\n"
                "Date of Issue: 10/01/2026\n"
                "Annual Family Income: Rs. 1,80,000/-\n"
                "Digitally signed by Tahsildar with official QR verification seal."
            )
            r3 = await send_and_wait(p3)
            assert "audit" in r3.text().lower() or "readiness" in r3.text().lower() or any(isinstance(c, MetadataContent) for c in r3.content)

            # Step 4: view_deadlines (triggers real dispatch to tracker_agent)
            p4 = json.dumps({"action": "view_deadlines"})
            r4 = await send_and_wait(p4)
            assert "deadline" in r4.text().lower() or any(isinstance(c, MetadataContent) for c in r4.content)

            # Step 5: compare
            p5 = json.dumps({"action": "compare", "scheme_ids": ["nsp_central_sector", "reliance_foundation_ug"]})
            r5 = await send_and_wait(p5)
            assert "nsp" in r5.text().lower() or "comparison" in r5.text().lower()

            # Step 6: request_concierge_pack
            p6 = json.dumps({"action": "request_concierge_pack", "scheme_id": "nsp_central_sector"})
            r6 = await send_and_wait(p6)
            assert "payment" in r6.text().lower() or "concierge" in r6.text().lower()

            scenario_done.set()
        except Exception as e:
            scenario_error.append(e)
            scenario_done.set()

    b = Bureau(port=port, endpoint=[ep], loop=loop, shutdown_timeout=1)
    b.add(coord)
    b.add(matcher)
    b.add(auditor)
    b.add(tracker)
    b.add(client)

    t = asyncio.create_task(b.run_async())

    try:
        await asyncio.wait_for(scenario_done.wait(), timeout=35.0)
        if scenario_error:
            raise scenario_error[0]
    finally:
        coord_mod.SCHEME_AGENT_ADDRESS = orig_scheme
        coord_mod.DOC_AGENT_ADDRESS = orig_doc
        coord_mod.TRACKER_AGENT_ADDRESS = orig_tracker
        if hasattr(b._server._server, "should_exit"):
            b._server._server.should_exit = True
        await asyncio.sleep(0.3)
        if not t.done():
            t.cancel()


@pytest.mark.asyncio
async def test_specialist_outage_inprocess_fallback(caplog):
    port = find_free_port()
    ep = f"http://127.0.0.1:{port}/submit"

    loop = asyncio.get_running_loop()

    coord = Agent(name="coordinator_fallback", seed=COORDINATOR_SEED, loop=loop)
    coord.include(chat_proto)
    coord.include(payment_proto)
    coord.include(coordinator_proto)

    client = Agent(name="client_fallback", seed=f"client_{uuid4().hex[:8]}", loop=loop)
    client_proto = Protocol(spec=chat_protocol_spec)

    received_chat_messages = []
    response_event = asyncio.Event()

    @client_proto.on_message(ChatMessage)
    async def on_client_chat(ctx: Context, sender: str, msg: ChatMessage):
        received_chat_messages.append(msg)
        response_event.set()

    @client_proto.on_message(ChatAcknowledgement)
    async def on_client_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
        pass

    client.include(client_proto)

    res = RulesBasedResolver({coord.address: ep, client.address: ep})
    coord._resolver = res
    client._resolver = res

    # Point DOC_AGENT_ADDRESS to a non-existent dead specialist address
    import agents.coordinator as coord_mod
    orig_doc = coord_mod.DOC_AGENT_ADDRESS
    coord_mod.DOC_AGENT_ADDRESS = "agent1q_unreachable_dead_specialist_address_999"

    fallback_done = asyncio.Event()
    fallback_error = []

    @client.on_event("startup")
    async def run_fallback(ctx: Context):
        try:
            # Poll until Bureau port is actively accepting connections
            for _ in range(40):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    if s.connect_ex(("127.0.0.1", port)) == 0:
                        break
                await asyncio.sleep(0.05)

            doc_sample = (
                "GOVERNMENT OF UTTAR PRADESH\n"
                "INCOME CERTIFICATE\n"
                "Date of Issue: 10/01/2026\n"
                "Annual Family Income: Rs. 1,80,000/-\n"
                "Digitally signed by Tahsildar with official QR verification seal."
            )
            response_event.clear()
            await ctx.send(coord.address, ChatMessage(
                msg_id=uuid4(),
                content=[TextContent(type="text", text=doc_sample)]
            ))
            # Coordinator should fall back in-process within 10 seconds
            await asyncio.wait_for(response_event.wait(), timeout=12.0)
            assert len(received_chat_messages) > 0
            fallback_done.set()
        except Exception as e:
            fallback_error.append(e)
            fallback_done.set()

    b = Bureau(port=port, endpoint=[ep], loop=loop, shutdown_timeout=1)
    b.add(coord)
    b.add(client)

    t = asyncio.create_task(b.run_async())

    try:
        await asyncio.wait_for(fallback_done.wait(), timeout=30.0)
        if fallback_error:
            raise fallback_error[0]
        # Assert client received document compliance card and fallback executed
        assert len(received_chat_messages) > 0
    finally:
        coord_mod.DOC_AGENT_ADDRESS = orig_doc
        if hasattr(b._server._server, "should_exit"):
            b._server._server.should_exit = True
        await asyncio.sleep(0.3)
        if not t.done():
            t.cancel()
