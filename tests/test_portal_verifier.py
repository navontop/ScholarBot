import time
from unittest.mock import MagicMock, patch
from core.portal_verifier import format_time_ago, verify_portal_url, _MEMORY_CACHE

def test_format_time_ago():
    now = time.time()
    assert format_time_ago(now - 10) == "Checked just now"
    assert format_time_ago(now - 300) == "Checked 5 minutes ago"
    assert format_time_ago(now - 7200) == "Checked 2 hours ago"
    assert format_time_ago(now - 90000) == "Checked 1 day ago"

def test_verify_portal_cache_hit():
    scheme_id = "test_scheme_cache"
    now = time.time()
    _MEMORY_CACHE[scheme_id] = {
        "status": "Verified today",
        "checked_at": now - 3600,
        "checked_ago_str": "Checked 1 hour ago",
        "http_code": 200,
        "message": "Gateway verified",
        "cached": False
    }

    res = verify_portal_url(scheme_id, "https://example.com/test", force_refresh=False)
    assert res["status"] == "Verified today"
    assert res["cached"] is True
    assert "hour" in res["checked_ago_str"]

def test_verify_portal_unreachable_fallback():
    # Attempting to fetch non-existent scheme or invalid target
    res = verify_portal_url("non_existent_fake", "https://invalid.domain.fetch.local/test", timeout_secs=0.5, force_refresh=True)
    assert res["status"] == "Could not verify"
    assert "offline repository" in res["message"] or "gateway unreachable" in res["message"]
    assert res["cached"] is False

def test_verify_portal_mock_success():
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b"National Scholarship Portal 2026-27 Application Open"
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = verify_portal_url("nsp_mock", "https://scholarships.gov.in", force_refresh=True)
        assert res["status"] == "Verified today"
        assert res["http_code"] == 200
        assert "Gateway verified" in res["message"]
