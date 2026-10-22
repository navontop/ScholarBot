"""Test for scholarship_agentverse_hosted.py to verify it is 100% self-contained
with zero local imports (no core/ or data/ folder dependencies), loads cleanly,
exports the agent, uses chat_protocol_spec, and processes core logic.
"""
import importlib.util
import os
import shutil
import sys
import tempfile
import pytest

@pytest.fixture(scope="module")
def standalone_hosted_module():
    """
    Copies scholarship_agentverse_hosted.py into an isolated temporary directory
    that has NO core/ or data/ folder, strips project_root from sys.path,
    and dynamically imports it.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    src_file = os.path.join(project_root, "scholarship_agentverse_hosted.py")
    assert os.path.exists(src_file), "scholarship_agentverse_hosted.py must exist"

    with tempfile.TemporaryDirectory() as tmp_dir:
        dest_file = os.path.join(tmp_dir, "hosted_agent_isolated.py")
        shutil.copy2(src_file, dest_file)

        # Assert no core/ folder exists in this temporary directory
        assert not os.path.exists(os.path.join(tmp_dir, "core")), "Must not have core/ folder in temp dir"
        assert not os.path.exists(os.path.join(tmp_dir, "data")), "Must not have data/ folder in temp dir"

        old_path = list(sys.path)
        sys.path = [p for p in sys.path if os.path.abspath(p) != project_root]

        try:
            spec = importlib.util.spec_from_file_location("hosted_agent_isolated", dest_file)
            mod = importlib.util.module_from_spec(spec)
            sys.modules["hosted_agent_isolated"] = mod
            spec.loader.exec_module(mod)
            yield mod
        finally:
            sys.path = old_path
            sys.modules.pop("hosted_agent_isolated", None)

def test_hosted_agent_imports_and_structure(standalone_hosted_module):
    hosted = standalone_hosted_module
    assert hasattr(hosted, "agent"), "Must export agent"
    assert "scholarbot" in hosted.agent.name.lower()
    protocols = list(hosted.agent.protocols.keys())
    assert len(protocols) > 0, "Must register protocols"
    assert hasattr(hosted, "chat_proto")
    assert hasattr(hosted, "payment_proto")

def test_hosted_agent_audit_logic(standalone_hosted_module):
    hosted = standalone_hosted_module
    sample_text = """
    GOVERNMENT OF UTTAR PRADESH
    OFFICE OF THE TAHSILDAR, LUCKNOW
    INCOME CERTIFICATE
    Date of Issue: 10/01/2026
    Annual Family Income: Rs. 1,80,000/-
    Digitally signed by Tahsildar with official QR verification seal.
    """
    req = hosted.DocumentAuditRequest(
        session_id="test_hosted",
        scheme_id="nsp_central_sector",
        profile=hosted.StudentProfile(family_income=180000.0),
        doc_type="income_certificate",
        doc_text=sample_text
    )
    res = hosted.audit_document_compliance(req, scheme_income_cap=200000.0)
    assert res.overall_status in ("PASS", "WARN")
    assert res.readiness_score > 70

def test_hosted_agent_matching_logic(standalone_hosted_module):
    hosted = standalone_hosted_module
    profile = hosted.StudentProfile(
        category="OBC",
        family_income=180000,
        marks_percentage=85.0,
        gender="Female",
        state="Uttar Pradesh",
        course="B.Tech"
    )
    eligible, close = hosted.match_scholarships(profile)
    assert len(eligible) > 0
    top = eligible[0]
    assert hasattr(top, "id")
    assert hasattr(top, "portal")
