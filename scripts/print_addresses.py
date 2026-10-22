import asyncio
import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

# Ensure event loop for Python 3.12+ uAgents
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from agents.coordinator import coordinator_agent
from agents.matcher import matcher_agent
from agents.auditor import auditor_agent
from agents.tracker import tracker_agent

def generate_table() -> str:
    table = [
        "| Agent | Role | Seed Variable | Persistent Address |",
        "|-------|------|---------------|-------------------|",
        f"| **ScholarBot Coordinator** | Primary Chat & Payment Interface | `COORDINATOR_SEED` | `{coordinator_agent.address}` |",
        f"| **Scheme Matching Engine** | Filtering, Scoring & State Logic | `MATCHER_SEED` | `{matcher_agent.address}` |",
        f"| **Doc Compliance Auditor** | Statutory Document Pre-Checks | `AUDITOR_SEED` | `{auditor_agent.address}` |",
        f"| **Deadline Tracker** | Deadlines, Alarms & .ICS Engine | `TRACKER_SEED` | `{tracker_agent.address}` |"
    ]
    return "\n".join(table)

def main():
    table = generate_table()
    print("\n=== ScholarBot Dynamic Agent Address Table ===")
    print(table)
    print("\n==============================================\n")

    if "--update-readme" in sys.argv:
        readme_path = os.path.join(PROJECT_ROOT, "README.md")
        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()

            import re
            table_pattern = re.compile(
                r'\| Agent \| Role \| Seed Variable \| Persistent Address \|[\s\S]*?(?=\n\n|\Z)',
                re.MULTILINE
            )
            if table_pattern.search(content):
                new_content = table_pattern.sub(table, content)
                with open(readme_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"[OK] Successfully updated agent addresses table in {readme_path}")

if __name__ == "__main__":
    main()
