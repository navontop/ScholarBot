import os
import json
import pytest
import tempfile
from core.identity import get_or_create_seed

def test_seed_persistence_reuses_seed():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, ".test_seeds.json")
        
        # 1. First call: generates and persists
        seed1 = get_or_create_seed("TEST_SEED_ENV", "test_agent_1", seeds_file=test_file)
        assert seed1 is not None
        assert len(seed1) >= 16
        assert os.path.exists(test_file)
        
        # 2. Second call: reuses persisted seed
        seed2 = get_or_create_seed("TEST_SEED_ENV", "test_agent_1", seeds_file=test_file)
        assert seed1 == seed2, "Seed must be reused across calls, not randomly generated each time"

def test_gitignore_contains_required_entries():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    gitignore_path = os.path.join(base_dir, ".gitignore")
    assert os.path.exists(gitignore_path)
    
    with open(gitignore_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    for entry in ["private_keys.json", ".agent_seeds.json", "*.db", ".env", "*_data.json", "agent1q*_data.json"]:
        assert entry in content, f"Missing {entry} in .gitignore"

def test_no_secrets_or_storage_in_project_root():
    import glob
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    for pat in ["private_keys.json", ".agent_seeds.json", "*_data.json", "agent1q*_data.json"]:
        matches = glob.glob(os.path.join(base_dir, pat))
        assert len(matches) == 0, f"Found unexpected file in project root: {matches}"
