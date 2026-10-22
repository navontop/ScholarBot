# Backward compatibility wrapper for agents.scheme_agent
from agents.matcher import (
    matcher_agent,
    scheme_agent,
    filter_scholarships,
    match_scholarships,
)

__all__ = [
    "matcher_agent",
    "scheme_agent",
    "filter_scholarships",
    "match_scholarships",
]
