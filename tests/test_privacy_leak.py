import pytest
import io
import logging
from uagents import Context
from core.models import StudentProfile
from agents.coordinator import handle_chat_message
from uagents_core.types import DeliveryStatus

import uuid

class FakeMsg:
    def __init__(self, content: str):
        self._content = content
        self.msg_id = uuid.uuid4()
    def text(self):
        return self._content
    @property
    def content(self):
        return []

class DummyStorage:
    def __init__(self):
        self._store = {}
    def get(self, k, default=None):
        return self._store.get(k, default)
    def set(self, k, v):
        self._store[k] = v
    def has(self, k):
        return k in self._store

class DummyContext:
    def __init__(self, logger):
        self.logger = logger
        self.storage = DummyStorage()
        self.sent_messages = []
    async def send(self, destination, message):
        self.sent_messages.append((destination, message))
        return DeliveryStatus.DELIVERED
    async def send_and_receive(self, destination, message, response_type=None, timeout=3.0):
        return None, DeliveryStatus.FAILED

@pytest.mark.asyncio
async def test_privacy_no_leak_in_logs():
    # Set up log capture
    log_capture_string = io.StringIO()
    handler = logging.StreamHandler(log_capture_string)
    handler.setLevel(logging.DEBUG)
    
    # Attach to root and uagents loggers
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)
    
    test_logger = logging.getLogger("uagents.coordinator")
    test_logger.setLevel(logging.DEBUG)
    test_logger.addHandler(handler)
    
    ctx = DummyContext(test_logger)
    
    # Message with sensitive identifiers: Aadhaar, PAN, Phone, Account
    sensitive_aadhaar = "1234 5678 9012"
    sensitive_pan = "ABCDE1234F"
    phone = "9876543210"
    account = "9876543210123"
    
    user_input = f"My Aadhaar is {sensitive_aadhaar}, PAN is {sensitive_pan}, phone {phone}, account {account}, finding engineering scholarships in UP income 2 lakh"
    msg = FakeMsg(user_input)
    
    try:
        await handle_chat_message(ctx, "agent1_test_user", msg)
    finally:
        root_logger.removeHandler(handler)
        test_logger.removeHandler(handler)
        
    captured_logs = log_capture_string.getvalue()
    
    # Assert neither Aadhaar nor PAN nor phone nor account appears in any captured logs
    assert sensitive_aadhaar not in captured_logs, f"Aadhaar leaked in logs: {captured_logs}"
    assert sensitive_pan not in captured_logs, f"PAN leaked in logs: {captured_logs}"
    assert phone not in captured_logs, f"Phone leaked in logs: {captured_logs}"
    assert account not in captured_logs, f"Account leaked in logs: {captured_logs}"

    # Also assert that the stored profile does NOT contain the raw Aadhaar, PAN, phone, or account
    stored_profile_raw = ctx.storage.get("profile:agent1_test_user")
    assert stored_profile_raw is not None
    stored_str = str(stored_profile_raw)
    assert sensitive_aadhaar not in stored_str
    assert sensitive_pan not in stored_str
    assert phone not in stored_str
    assert account not in stored_str
