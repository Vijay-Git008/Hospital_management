from pydantic import BaseModel
from typing import Dict, Any, Optional

class AgentMessage(BaseModel):
    sender_id: str
    recipient_id: str
    message_type: str  # CFP (Call for Proposal), BID, ACCEPT, REJECT, INFORM
    conversation_id: str
    payload: Dict[str, Any]

class BaseAgent:
    def __init__(self, agent_id: str, name: str, agent_type: str):
        self.agent_id = agent_id
        self.name = name
        self.agent_type = agent_type

    def __repr__(self):
        return f"<{self.agent_type} Agent: {self.name} ({self.agent_id})>"
