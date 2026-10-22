# Backward compatibility wrapper for agents.doc_agent
from agents.auditor import (
    auditor_agent,
    doc_agent,
    SCHEME_DOC_RULES,
)

__all__ = [
    "auditor_agent",
    "doc_agent",
    "SCHEME_DOC_RULES",
]
