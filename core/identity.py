import json
import logging
import os
import secrets
from typing import Optional

logger = logging.getLogger("Identity")
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_SEEDS_PATH = os.path.join(PROJECT_ROOT, "data", ".agent_seeds.json")

def get_or_create_seed(env_var_name: str, agent_name: str, seeds_file: Optional[str] = None) -> str:
    """
    Retrieves agent seed:
    1. Checks environment variable first.
    2. If not set, checks persistent gitignored seeds file.
    3. If not present in file, generates a secure 32-byte seed once, persists it,
       and logs a clear one-time backup notice without printing the seed itself.
    """
    env_seed = os.getenv(env_var_name)
    if env_seed and env_seed.strip():
        return env_seed.strip()

    path = seeds_file or os.getenv("AGENT_SEEDS_PATH") or DEFAULT_SEEDS_PATH
    seeds_db = {}

    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                seeds_db = json.load(f)
        except Exception:
            seeds_db = {}

    if agent_name in seeds_db and seeds_db[agent_name]:
        return seeds_db[agent_name]

    # Generate persistent seed once
    new_seed = secrets.token_hex(32)
    seeds_db[agent_name] = new_seed

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(seeds_db, f, indent=2)
        print(f"[Identity] Generated persistent seed for '{agent_name}' in {os.path.basename(path)}. Please back up {os.path.basename(path)} securely! Never commit it to git.")
    except Exception as e:
        logger.warning(f"Could not persist seed for {agent_name}: {e}")

    return new_seed
