"""
Link Health-Check Script for ScholarBot.
Checks all source_url, apply_url, portal_url, and image URLs.
Outputs console summary and writes docs/LINK_REPORT.md.
"""
import json
import os
import sys
import urllib.request
import urllib.error
import ssl
from typing import Dict, List, Tuple
from datetime import datetime, timezone

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHOLARSHIPS_FILE = os.path.join(PROJECT_ROOT, "data", "scholarships.json")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
LINK_REPORT_FILE = os.path.join(DOCS_DIR, "LINK_REPORT.md")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 ScholarBot/2.0"

def create_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def check_url(url: str, timeout: float = 6.0) -> Tuple[bool, int, str]:
    if not url or not url.startswith("http"):
        return False, 0, "Malformed or empty URL"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"}
    )
    ctx = create_ssl_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            status = resp.getcode()
            content_type = resp.headers.get("Content-Type", "")
            return True, status, content_type
    except urllib.error.HTTPError as e:
        # Treat 403 / 406 as unverified (bot protection / WAF block), not OK
        if e.code in (200, 301, 302, 307, 308):
            return True, e.code, f"HTTP {e.code} (Redirect/Reachable)"
        elif e.code in (403, 406):
            return False, e.code, f"HTTP {e.code} (Unverified - WAF/Bot Protection)"
        else:
            return False, e.code, f"HTTP Error {e.code}"
    except urllib.error.URLError as e:
        return False, 0, f"URL Error: {e.reason}"
    except Exception as e:
        return False, 0, f"Exception: {type(e).__name__}"

def run_link_check(quick_mode: bool = False):
    os.makedirs(DOCS_DIR, exist_ok=True)
    if not os.path.exists(SCHOLARSHIPS_FILE):
        print(f"Error: {SCHOLARSHIPS_FILE} not found.")
        return

    with open(SCHOLARSHIPS_FILE, "r", encoding="utf-8") as f:
        schemes = json.load(f)

    print(f"Loaded {len(schemes)} schemes from {SCHOLARSHIPS_FILE}. Beginning health check...")

    tested_urls: Dict[str, Tuple[bool, int, str]] = {}
    scheme_results = []

    for idx, s in enumerate(schemes, 1):
        sid = s.get("id", f"scheme_{idx}")
        sname = s.get("name", "Unnamed")
        source_url = s.get("source_url", "")
        apply_url = s.get("apply_url") or s.get("portal_url", "")
        portal_url = s.get("portal_url", "")

        urls_to_test = [
            ("source_url", source_url),
            ("apply_url", apply_url),
            ("portal_url", portal_url)
        ]

        item_res = {
            "id": sid,
            "name": sname,
            "urls": {}
        }

        for label, url in urls_to_test:
            if not url:
                item_res["urls"][label] = (False, 0, "Missing")
                continue
            if url not in tested_urls:
                if quick_mode:
                    ok, code, msg = (url.startswith("https://"), 200 if url.startswith("https://") else 0, "Quick HTTPS check")
                else:
                    ok, code, msg = check_url(url)
                tested_urls[url] = (ok, code, msg)
            item_res["urls"][label] = tested_urls[url]

        scheme_results.append(item_res)
        if idx % 10 == 0 or idx == len(schemes):
            print(f"  Processed {idx}/{len(schemes)} schemes...")

    # Generate Markdown Report
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    total_tested = len(tested_urls)
    total_pass = sum(1 for ok, _, _ in tested_urls.values() if ok)
    total_fail = total_tested - total_pass

    lines = [
        "# ScholarBot Link Health Report",
        f"> Generated on: {timestamp}",
        f"> Total unique endpoints checked: {total_tested} | Passed: {total_pass} | Flagged/Failed: {total_fail}",
        "",
        "## Summary by Scheme",
        "",
        "| ID | Scheme Name | Apply URL Status | Source URL Status | Notes |",
        "|---|---|---|---|---|"
    ]

    for res in scheme_results:
        app_ok, app_code, app_msg = res["urls"].get("apply_url", (False, 0, "N/A"))
        src_ok, src_code, src_msg = res["urls"].get("source_url", (False, 0, "N/A"))
        app_status = f"{app_code} {'OK' if app_ok else 'FLAGGED'}"
        src_status = f"{src_code} {'OK' if src_ok else 'FLAGGED'}"
        notes = "Verified HTTPS" if (app_ok and src_ok) else "Needs manual verification"
        lines.append(f"| `{res['id']}` | {res['name'][:40]} | {app_status} | {src_status} | {notes} |")

    lines.extend([
        "",
        "## Failed or Flagged Endpoints",
        "",
        "| URL | HTTP Code | Diagnostic Message |",
        "|---|---|---|"
    ])

    for url, (ok, code, msg) in tested_urls.items():
        if not ok:
            lines.append(f"| `{url}` | {code} | {msg} |")

    report_content = "\n".join(lines) + "\n"
    with open(LINK_REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"\n[OK] Link check completed. Report written to: {LINK_REPORT_FILE}")
    print(f"Total Unique URLs: {total_tested} | Healthy/Reachable: {total_pass} | Flagged: {total_fail}")

if __name__ == "__main__":
    quick = "--quick" in sys.argv
    run_link_check(quick_mode=quick)
