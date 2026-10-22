import os
import sys

# Ensure parent directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from uagents import Agent, Context, Protocol
from core.identity import get_or_create_seed
from core.matching import match_scholarships
from core.models import (
    SchemeMatchRequest,
    SchemeMatchResponse,
    ScholarshipItem,
    StudentProfile,
)

MATCHER_SEED = get_or_create_seed("MATCHER_SEED", "matcher")
MATCHER_PORT = int(os.getenv("MATCHER_PORT", "8002"))

matcher_agent = Agent(
    name="scheme_matching_agent",
    seed=MATCHER_SEED,
    port=MATCHER_PORT,
    endpoint=[f"http://127.0.0.1:{MATCHER_PORT}/submit"],
    description="Autonomous Scheme Matching Specialist Agent: Evaluates candidate profiles against published criteria for central, state, and private scholarships in India.",
    metadata={
        "tags": ["scholarship", "India", "NSP", "document check", "deadlines", "eligibility"],
        "category": "education"
    }
)

print(f"[*] [Matcher] Address: {matcher_agent.address}")

matcher_proto = Protocol(name="SchemeMatchingProtocol", version="1.0.0")

@matcher_proto.on_message(model=SchemeMatchRequest, replies=SchemeMatchResponse)
async def handle_match_request(ctx: Context, sender: str, msg: SchemeMatchRequest):
    ctx.logger.info(f"[Matcher] Received match request for {msg.profile.student_name} from {sender}")
    ctx.logger.info(f"  Profile: State={msg.profile.state}, Category={msg.profile.category}, Income=Rs. {msg.profile.family_income:,.0f}, Marks={msg.profile.marks_percentage}%")


    eligible, close_misses = match_scholarships(msg.profile)
    ctx.logger.info(f"[Matcher] Evaluation complete: {len(eligible)} eligible schemes, {len(close_misses)} close misses.")

    response = SchemeMatchResponse(
        session_id=msg.session_id,
        total_found=len(eligible),
        matches=eligible,
        close_misses=close_misses
    )
    await ctx.send(sender, response)

matcher_agent.include(matcher_proto)

# Backward compatibility alias
scheme_agent = matcher_agent
filter_scholarships = lambda profile: match_scholarships(profile)[0]

if __name__ == "__main__":
    print(f"Starting Scheme Matching Agent on port {MATCHER_PORT} with address: {matcher_agent.address}")
    matcher_agent.run()
