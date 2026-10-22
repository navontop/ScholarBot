import os
import sys

# Ensure parent directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from uagents import Agent, Context, Protocol
from core.deadlines import build_deadline_items
from core.matching import load_scholarships
from core.models import (
    DeadlineItem,
    DeadlineRequest,
    DeadlineResponse,
    ScholarshipItem,
)

from core.identity import get_or_create_seed

TRACKER_SEED = get_or_create_seed("TRACKER_SEED", "tracker")
TRACKER_PORT = int(os.getenv("TRACKER_PORT", "8004"))

tracker_agent = Agent(
    name="deadline_tracker_agent",
    seed=TRACKER_SEED,
    port=TRACKER_PORT,
    endpoint=[f"http://127.0.0.1:{TRACKER_PORT}/submit"],
    description="Autonomous Deadline Tracking Specialist Agent: Tracks scholarship application closing dates, computes urgency tiers, and generates iCalendar files.",
    metadata={
        "tags": ["scholarship", "India", "NSP", "document check", "deadlines", "eligibility"],
        "category": "education"
    }
)

print(f"[*] [Tracker] Address: {tracker_agent.address}")

tracker_proto = Protocol(name="DeadlineTrackerProtocol", version="1.0.0")

@tracker_proto.on_message(model=DeadlineRequest, replies=DeadlineResponse)
async def handle_deadline_request(ctx: Context, sender: str, msg: DeadlineRequest):
    ctx.logger.info(f"[Tracker] Received deadline calculation request for {len(msg.scheme_ids)} schemes from {sender}")
    raw_schemes = load_scholarships()
    
    selected_items: list[ScholarshipItem] = []
    for s in raw_schemes:
        if not msg.scheme_ids or s["id"] in msg.scheme_ids:
            elig = s.get("eligibility", {})
            selected_items.append(ScholarshipItem(
                id=s["id"],
                name=s["name"],
                provider=s["provider"],
                portal=s["portal"],
                portal_url=s["portal_url"],
                source_url=s.get("source_url", ""),
                amount=s["amount"],
                category_list=elig.get("categories", []),
                min_marks=float(elig.get("min_marks", 0.0)),
                max_family_income=float(elig.get("max_family_income", 10000000.0)),
                applicable_states=elig.get("states", []),
                gender=elig.get("gender", "All"),
                deadline=s.get("deadline", "2026-12-31"),
                description=s.get("description", ""),
                match_score=85,
                match_status="eligible",
                match_reason="",
                apply_url=s.get("apply_url") or s.get("portal_url", "")
            ))

    deadline_items = build_deadline_items(selected_items)
    ctx.logger.info(f"[Tracker] Computed {len(deadline_items)} deadline records with .ics calendar alarms.")
    await ctx.send(sender, DeadlineResponse(session_id=msg.session_id, items=deadline_items))

@tracker_agent.on_interval(period=3600.0)
async def proactive_deadline_scan(ctx: Context):
    """Hourly background scan to log approaching scholarship cutoffs and notify subscribers."""
    ctx.logger.info("[Tracker Heartbeat] Running automated scan for scholarships closing within 7 days...")
    raw = load_scholarships()
    closing_soon = []
    for s in raw:
        deadline_str = s.get("deadline", "2026-12-31")
        try:
            parts = [int(p) for p in deadline_str.split("-")]
            from datetime import datetime, timezone
            dt = datetime(parts[0], parts[1], parts[2], 23, 59, 59, tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            days = (dt - now).days
            if 0 <= days <= 7:
                closing_soon.append((s["name"], days))
        except Exception:
            pass
    if closing_soon:
        ctx.logger.warning(f"[ALERT] [URGENT DEADLINES] {len(closing_soon)} schemes closing in <= 7 days: {closing_soon}")
    else:
        ctx.logger.info("[OK] All major scholarship deadlines are healthy.")


tracker_agent.include(tracker_proto)

if __name__ == "__main__":
    print(f"Starting Deadline Tracker Agent on port {TRACKER_PORT} with address: {tracker_agent.address}")
    tracker_agent.run()
