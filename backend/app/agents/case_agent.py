from .base import BaseAgent, AgentMessage
import uuid

class CaseAgent(BaseAgent):
    def __init__(self, patient_id: str, name: str, triage_level: int, required_resource_types: list, clinical_summary: str):
        super().__init__(patient_id, name, "PatientCase")
        self.triage_level = triage_level
        self.required_resource_types = required_resource_types
        self.clinical_summary = clinical_summary
        self.conversation_id = str(uuid.uuid4())

    def generate_cfp(self) -> AgentMessage:
        """Constructs a Call For Proposals (CFP) to send to the resource coordinator."""
        payload = {
            "patient_id": self.agent_id,
            "patient_name": self.name,
            "triage_level": self.triage_level,
            "required_resource_types": self.required_resource_types,
            "clinical_summary": self.clinical_summary,
            "timestamp": uuid.uuid4().hex  # pseudo-timestamp
        }
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id="coordinator",
            message_type="CFP",
            conversation_id=self.conversation_id,
            payload=payload
        )
