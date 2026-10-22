import os
import re
import pytest

def test_no_unverified_claims_in_user_facing_code():
    """
    Asserts that no user-facing strings in coordinator.py, cards.py, payments.py,
    README.md, or DEMO_SCRIPT.md make false claims like 'verified scholarships',
    '20+ verified', '100% matched', or 'guarantee'.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    files_to_check = [
        os.path.join(base_dir, "agents", "coordinator.py"),
        os.path.join(base_dir, "core", "cards.py"),
        os.path.join(base_dir, "core", "payments.py"),
        os.path.join(base_dir, "README.md"),
        os.path.join(base_dir, "DEMO_SCRIPT.md")
    ]
    
    forbidden_patterns = [
        re.compile(r'20\+\s*verified', re.IGNORECASE),
        re.compile(r'verified\s*central', re.IGNORECASE),
        re.compile(r'verified\s*scholarships?', re.IGNORECASE),
        re.compile(r'100%\s*matched', re.IGNORECASE),
        re.compile(r'Verified\s*Document\s*Checklist', re.IGNORECASE),
        re.compile(r'Verified\s*Complete\s*Package', re.IGNORECASE),
        re.compile(r'\bguarantee\b', re.IGNORECASE),
    ]
    
    violations = []
    
    for file_path in files_to_check:
        if not os.path.exists(file_path):
            continue
        with open(file_path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, 1):
                # Skip comments or code logic matching scheme.verified == True
                stripped = line.strip()
                if stripped.startswith("#") or "scheme.verified" in line or "verified=False" in line or "verified == true" in line:
                    continue
                for pattern in forbidden_patterns:
                    if pattern.search(line):
                        violations.append(f"{os.path.basename(file_path)}:L{idx}: {line.strip()}")
                        
    assert not violations, "Found dishonest/unverified claims in user-facing files:\n" + "\n".join(violations)
