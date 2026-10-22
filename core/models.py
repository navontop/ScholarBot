from typing import Dict, List, Optional
from pydantic.v1 import Field
from uagents import Model

class StudentProfile(Model):
    student_name: str = "Student"
    state: str = "All"
    category: str = "General"  # General, EWS, OBC, SC, ST, Minority
    family_income: float = 250000.0  # Annual income in INR
    course: str = "Engineering"
    marks_percentage: float = 75.0
    gender: str = "All"  # All, Male, Female
    disability: bool = False
    minority: bool = False
    year_of_study: int = 1
    missing_fields: List[str] = Field(default_factory=list)
    raw_text: str = ""
    family_income_min: Optional[float] = None
    family_income_max: Optional[float] = None
    marks_min: Optional[float] = None
    marks_max: Optional[float] = None

class ScholarshipItem(Model):
    id: str
    name: str
    provider: str
    portal: str
    portal_url: str
    source_url: str = ""
    amount: str
    amount_value: float = 0.0
    category_list: List[str] = Field(default_factory=list)
    min_marks: float = 0.0
    max_family_income: float = 10000000.0
    applicable_states: List[str] = Field(default_factory=list)
    gender: str = "All"
    disability_required: bool = False
    minority_required: bool = False
    deadline: str = "2026-12-31"
    description: str = ""
    match_score: int = 80
    match_status: str = "eligible"  # eligible, maybe, close_miss, ineligible
    match_reason: str = ""
    last_verified: Optional[str] = None
    verified: bool = False
    apply_url: str = ""
    apply_steps_hint: str = ""
    portal_name: str = ""
    portal_home_url: str = ""
    level: str = "UG"
    scheme_type: str = "central"
    renewable: bool = True
    docs_required: List[str] = Field(default_factory=list)
    notes: str = ""
    application_window: Optional[Dict[str, Optional[str]]] = None

class SchemeMatchRequest(Model):
    session_id: str
    profile: StudentProfile

class SchemeMatchResponse(Model):
    session_id: str
    total_found: int
    matches: List[ScholarshipItem]
    close_misses: List[ScholarshipItem] = Field(default_factory=list)

class AuditCheckItem(Model):
    check_name: str
    status: str  # PASS, WARN, FAIL
    details: str
    remedy: str = ""

class DocumentAuditRequest(Model):
    session_id: str
    scheme_id: str
    doc_type: str = "income_certificate"  # income_certificate, caste_certificate, marksheet, bonafide, bank_passbook, general
    doc_text: str = ""
    image_uri: Optional[str] = None
    profile: StudentProfile

class DocumentAuditResponse(Model):
    session_id: str
    scheme_id: str
    doc_type: str
    overall_status: str  # PASS, WARN, FAIL
    readiness_score: int  # 0 to 100
    extracted_fields: Dict[str, str] = Field(default_factory=dict)
    checks: List[AuditCheckItem] = Field(default_factory=list)
    action_plan: List[str] = Field(default_factory=list)
    disclaimer: str = "Pre-check advisory based on published rules. Always verify on official portal."

class DeadlineItem(Model):
    scheme_id: str
    scheme_name: str
    portal_url: str
    deadline_date: str
    days_remaining: int
    urgency_tier: str  # CLOSED, CRITICAL_UNDER_7_DAYS, EXPIRING_UNDER_15_DAYS, OPEN
    badge_label: str
    ics_calendar_data: str

class DeadlineRequest(Model):
    session_id: str
    scheme_ids: List[str]

class DeadlineResponse(Model):
    session_id: str
    items: List[DeadlineItem]

class DocumentGuidanceRequest(Model):
    session_id: str
    scheme_id: str
    scheme_name: str
    state: str = "All"
    category: str = "General"

class DocumentGuidanceResponse(Model):
    session_id: str
    scheme_id: str
    scheme_name: str
    mandatory_docs: List[str]
    critical_warning: str
    rejection_prevention_tips: List[str]
    portal_url: str
    step_by_step_process: List[str]

class ConciergePackRequest(Model):
    session_id: str
    scheme_id: str
    profile: StudentProfile
    include_sop: bool = True

class ConciergePackResponse(Model):
    session_id: str
    scheme_id: str
    scheme_name: str
    pack_title: str
    markdown_content: str
    sop_essay: str = ""
    ics_data: str = ""
