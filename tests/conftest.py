import os
import tempfile
import pytest

_GLOBAL_TEMP_DIR = tempfile.TemporaryDirectory()

def pytest_configure(config):
    """Runs at pytest startup before any test module is imported or collected."""
    os.chdir(_GLOBAL_TEMP_DIR.name)
    os.environ["AGENT_SEEDS_PATH"] = os.path.join(_GLOBAL_TEMP_DIR.name, ".agent_seeds.json")

def pytest_unconfigure(config):
    """Runs at pytest shutdown."""
    try:
        _GLOBAL_TEMP_DIR.cleanup()
    except Exception:
        pass

@pytest.fixture(autouse=True)
def isolate_test_storage(tmp_path, monkeypatch):
    """Isolates each test function to its own tmp_path."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENT_SEEDS_PATH", str(tmp_path / ".agent_seeds.json"))
    yield
