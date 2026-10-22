"""Test reliability features:
- ASI1 API health check without key leakage
- Proactive reminder deduplication across 7/3/1 tiers in ctx.storage
- Global exception guard in coordinator
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from core.llm import check_asi1_api_health
from agents.coordinator import check_and_send_deadline_reminders, handle_chat_message
from uagents_core.contrib.protocols.chat import ChatMessage, TextContent

def test_asi1_health_check_no_leakage(monkeypatch):
    import core.llm as llm
    fake_secret = "secret_asi1_key_99999"
    monkeypatch.setattr(llm, "ASI1_API_KEY", fake_secret)
    ok, msg = check_asi1_api_health()
    # The message must NOT contain the raw secret key
    assert fake_secret not in msg
    assert "length=" in msg or "chars" in msg

@pytest.mark.asyncio
async def test_reminder_dedup_tiers():
    # Mock Context with storage
    storage = {}
    ctx = MagicMock()
    ctx.storage.get.side_effect = lambda k: storage.get(k)
    ctx.storage.set.side_effect = lambda k, v: storage.update({k: v})
    ctx.send = AsyncMock()

    # Configure user with a registered reminder
    storage["subscribers"] = ["agent1user_test"]
    storage["reminders:agent1user_test"] = ["nsp_central_sector"]

    # First call - sends tier 7 (or current tier)
    await check_and_send_deadline_reminders(ctx)
    initial_send_count = ctx.send.call_count

    # Second call right after - should be deduplicated (not sent again)
    await check_and_send_deadline_reminders(ctx)
    assert ctx.send.call_count == initial_send_count

@pytest.mark.asyncio
async def test_global_exception_guard(monkeypatch):
    import agents.coordinator as coord
    # Force an unhandled error inside _process_chat_message_safely
    async def broken_process(ctx, sender, msg):
        raise ValueError("Simulated unexpected handler explosion")

    monkeypatch.setattr(coord, "_process_chat_message_safely", broken_process)

    ctx = MagicMock()
    ctx.send = AsyncMock()
    msg = ChatMessage(content=[TextContent(type="text", text="Hello")])

    # Should not raise exception
    await handle_chat_message(ctx, "agent1sender_test", msg)

    # Should have sent ACK and friendly error card with Action Hub
    assert ctx.send.call_count == 2
    sent_card_msg = ctx.send.call_args[0][1]
    assert isinstance(sent_card_msg, ChatMessage)
    text = sent_card_msg.text()
    assert "unexpected issue" in text.lower() or "action hub" in text.lower()

