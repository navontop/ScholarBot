import os
import sys

# Ensure parent path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from uagents import Bureau
from agents.coordinator import coordinator_agent
from agents.matcher import matcher_agent
from agents.auditor import auditor_agent
from agents.tracker import tracker_agent

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("\n" + "="*70)
    print("SCHOLARBOT: AUTONOMOUS MULTI-AGENT SCHOLARSHIP ADVISORY SYSTEM")
    print("Fetch-A-Thon 3.0 / ASI:One Agent Challenge")
    print("="*70)
    print(f"1. Coordinator Agent (ASI:One & ACP Chat): {coordinator_agent.address}")
    print(f"   Port: 8001 | Protocols: ACP (0.3.0) + Payment Protocol (0.1.0)")
    print(f"2. Scheme Matching Engine Agent:           {matcher_agent.address}")
    print(f"   Port: 8002 | Protocol: SchemeMatchingProtocol (1.0.0)")
    print(f"3. Doc Compliance Advisory Agent:          {auditor_agent.address}")
    print(f"   Port: 8003 | Protocol: DocumentComplianceProtocol (1.0.0)")
    print(f"4. Deadline & Calendar Tracker Agent:       {tracker_agent.address}")
    print(f"   Port: 8004 | Protocol: DeadlineTrackerProtocol (1.0.0)")
    print("="*70)
    print("[DEPLOYMENT MODES]")
    print("A. Local Unified Bureau (Active): All 4 agents run in a single process with direct internal dispatch.")
    print("B. Separate Processes / Mailbox Mode: Run each agent individually:")
    print("   - Terminal 1: python agents/coordinator.py (uses AGENTVERSE_MAILBOX_KEY if set)")
    print("   - Terminal 2: python agents/matcher.py")
    print("   - Terminal 3: python agents/auditor.py")
    print("   - Terminal 4: python agents/tracker.py")
    print("C. Agentverse Hosted (Single-File): Deploy scholarship_agentverse_hosted.py directly on Agentverse Web IDE.")
    print("="*70)
    print("Starting Fetch.ai Bureau... Press Ctrl+C to stop.\n")

    bureau = Bureau(port=8000, endpoint=["http://127.0.0.1:8000/submit"])
    bureau.add(coordinator_agent)
    bureau.add(matcher_agent)
    bureau.add(auditor_agent)
    bureau.add(tracker_agent)
    bureau.run()

