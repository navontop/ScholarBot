# Backward compatibility wrapper for protocols.messages
from core.models import (
    StudentProfile,
    ScholarshipItem,
    SchemeMatchRequest,
    SchemeMatchResponse,
    DocumentGuidanceRequest,
    DocumentGuidanceResponse,
    DocumentAuditRequest,
    DocumentAuditResponse,
    DeadlineRequest,
    DeadlineResponse,
    AuditCheckItem,
    DeadlineItem,
    ConciergePackRequest,
    ConciergePackResponse,
)

__all__ = [
    "StudentProfile",
    "ScholarshipItem",
    "SchemeMatchRequest",
    "SchemeMatchResponse",
    "DocumentGuidanceRequest",
    "DocumentGuidanceResponse",
    "DocumentAuditRequest",
    "DocumentAuditResponse",
    "DeadlineRequest",
    "DeadlineResponse",
    "AuditCheckItem",
    "DeadlineItem",
    "ConciergePackRequest",
    "ConciergePackResponse",
]
