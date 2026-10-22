# Backward compatibility wrapper for coordinator_agent
from agents.coordinator import (
    coordinator_agent,
    agent,
    chat_proto,
    payment_proto,
    COORDINATOR_SEED,
    COORDINATOR_PORT,
    SCHEME_AGENT_ADDRESS,
    DOC_AGENT_ADDRESS,
    TRACKER_AGENT_ADDRESS,
)

__all__ = [
    "coordinator_agent",
    "agent",
    "chat_proto",
    "payment_proto",
    "COORDINATOR_SEED",
    "COORDINATOR_PORT",
    "SCHEME_AGENT_ADDRESS",
    "DOC_AGENT_ADDRESS",
    "TRACKER_AGENT_ADDRESS",
]

if __name__ == "__main__":
    coordinator_agent.run()
