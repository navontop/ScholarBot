import os
import json
import re

def build():
    with open("data/scholarships.json", "r", encoding="utf-8") as f:
        scholarships_raw = json.load(f)
    with open("data/doc_rules.json", "r", encoding="utf-8") as f:
        doc_rules_raw = json.load(f)

    # Read each core module
    def read_core(mod_name):
        path = os.path.join("core", f"{mod_name}.py")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        # strip multi-line and single-line imports from core.*
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

    # Read existing agent logic from scholarship_agentverse_hosted.py (from line ~80 onwards)
    with open("scholarship_agentverse_hosted.py", "r", encoding="utf-8") as f:
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
"""

    header = '''"""
ScholarBot - Standalone Agentverse Hosted Agent Bundle
100% self-contained single-file agent with zero local imports.
Ready for direct paste into the Agentverse hosted web editor.
"""
import asyncio
import base64
from datetime import datetime, timezone, timedelta
import hashlib
import json
import logging
import os
import re
import secrets
import sys
from typing import Dict, List, Optional, Any, Tuple
import urllib.request
from uuid import uuid4

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

# ==============================================================================
# EMBEDDED DATASETS
# ==============================================================================
EMBEDDED_SCHOLARSHIPS = json.loads(''' + repr(json.dumps(scholarships_raw)) + ''')

EMBEDDED_DOC_RULES = json.loads(''' + repr(json.dumps(doc_rules_raw)) + ''')


'''

    # Replace file loaders with in-memory embedded versions
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

    agent_logic = re.sub(r'# Export agent reference for Agentverse\s+agent = hosted_agent', '', agent_logic).strip()

    full_content = (
        header
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
        + "\n# ==================== HOSTED AGENT & PROTOCOLS ====================\n"
        + agent_setup
        + "\n"
        + agent_logic
        + "\n\n# Export agent reference for Agentverse\nagent = hosted_agent\n"
    )

    with open("scholarship_agentverse_hosted.py", "w", encoding="utf-8") as f:
        f.write(full_content)
    print("Successfully built standalone scholarship_agentverse_hosted.py")

if __name__ == "__main__":
    build()
