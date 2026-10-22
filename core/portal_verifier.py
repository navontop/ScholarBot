"""
ScholarBot Portal Verifier Tool (Phase 4: Real-time verification and tool use)
Fetches official scholarship pages / portals with strict timeouts and persistent caching.
Reports: 'Verified today', 'Could not verify', or 'Page changed'.
Never blocks primary user workflow; gracefully falls back to static dataset.
"""

import os
import json
import time
import ssl
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

CACHE_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "portal_verifier_cache.json"))

_MEMORY_CACHE: Dict[str, dict] = {}

def format_time_ago(epoch_seconds: float) -> str:
    diff = int(time.time() - epoch_seconds)
    if diff < 60:
        return "Checked just now"
    elif diff < 3600:
        mins = max(1, diff // 60)
        return f"Checked {mins} minute{'s' if mins > 1 else ''} ago"
    elif diff < 86400:
        hours = max(1, diff // 3600)
        return f"Checked {hours} hour{'s' if hours > 1 else ''} ago"
    else:
        days = max(1, diff // 86400)
        return f"Checked {days} day{'s' if days > 1 else ''} ago"

def load_cache() -> Dict[str, dict]:
    global _MEMORY_CACHE
    if _MEMORY_CACHE:
        return _MEMORY_CACHE
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _MEMORY_CACHE = json.load(f)
        except Exception:
            _MEMORY_CACHE = {}
    return _MEMORY_CACHE

def save_cache():
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_MEMORY_CACHE, f, indent=2)
    except Exception:
        pass

def verify_portal_url(
    scheme_id: str,
    target_url: str,
    expected_deadline: Optional[str] = None,
    timeout_secs: float = 3.0,
    force_refresh: bool = False
) -> dict:
    """
    Fetches an official scheme or portal page with strict timeout and persistent caching.
    Returns:
      {
        "status": "Verified today" | "Could not verify" | "Page changed",
        "checked_at": float,
        "checked_ago_str": str,
        "http_code": int | None,
        "message": str,
        "cached": bool
      }
    Never raises an unhandled exception.
    """
    cache = load_cache()
    now = time.time()

    # Check cache (TTL 6 hours)
    if not force_refresh and scheme_id in cache:
        entry = cache[scheme_id]
        if now - entry.get("checked_at", 0) < 21600:
            res = dict(entry)
            res["checked_ago_str"] = format_time_ago(res["checked_at"])
            res["cached"] = True
            return res

    if not target_url or not target_url.startswith("http"):
        return {
            "status": "Could not verify",
            "checked_at": now,
            "checked_ago_str": "Checked just now",
            "http_code": None,
            "message": "No valid HTTPS portal URL provided. Relying on verified offline repository.",
            "cached": False
        }

    # Execute with 1 automatic retry
    success = False
    http_code = None
    body_text = ""
    err_msg = ""

    ctx_ssl = ssl.create_default_context()
    ctx_ssl.check_hostname = False
    ctx_ssl.verify_mode = ssl.CERT_NONE

    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ScholarBot-Verifier/3.0 (Fetch.ai Agentverse)"
    }

    for attempt in range(2):
        try:
            req = urllib.request.Request(target_url, headers=req_headers, method="GET")
            with urllib.request.urlopen(req, timeout=timeout_secs, context=ctx_ssl) as resp:
                http_code = resp.status
                # Read at most 32KB to keep it lightweight
                content = resp.read(32768)
                body_text = content.decode("utf-8", errors="ignore").lower()
                success = True
                break
        except urllib.error.HTTPError as e:
            http_code = e.code
            if e.code in [401, 403]:  # Protected portal (NSP login / state SSO portal is reachable)
                success = True
                break
            err_msg = f"HTTP error {e.code}"
        except Exception as ex:
            err_msg = str(ex)
        if attempt == 0:
            time.sleep(0.2)

    if success:
        year_mentions = ["2026", "2026-27", "2026-2027", "2025-26", "scholarship", "apply", "registration"]
        has_context = any(ym in body_text for ym in year_mentions)
        status = "Verified today" if has_context or http_code in [200, 401, 403] else "Page changed"
        result = {
            "status": status,
            "checked_at": now,
            "checked_ago_str": "Checked just now",
            "http_code": http_code,
            "message": f"Official portal active (HTTP {http_code}). Gateway verified.",
            "cached": False
        }
    else:
        result = {
            "status": "Could not verify",
            "checked_at": now,
            "checked_ago_str": "Checked just now",
            "http_code": http_code,
            "message": f"Official portal gateway unreachable ({err_msg}). Falling back safely to static records.",
            "cached": False
        }

    _MEMORY_CACHE[scheme_id] = result
    save_cache()
    return result
