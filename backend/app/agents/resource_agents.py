from typing import Optional
from .base import BaseAgent, AgentMessage
import json

class ResourceAgent(BaseAgent):
    def __init__(self, resource_id: str, name: str, resource_type: str, status: str, metadata: dict):
        super().__init__(resource_id, name, "Resource")
        self.resource_type = resource_type
        self.status = status
        self.metadata = metadata

    def calculate_bid(self, cfp_message: AgentMessage) -> Optional[AgentMessage]:
        """
        Receives a Call for Proposals (CFP). Evaluates availability and suitability.
        Returns a BID message if suitable, or None if unavailable/unsuitable.
        """
        if self.status != "Available":
            return None

        payload = cfp_message.payload
        patient_triage = payload.get("triage_level", 5)
        required_types = payload.get("required_resource_types", [])

        # Check if this resource's type is required
        if self.resource_type not in required_types:
            return None

        # Compute suitability score based on resource characteristics
        # Range: 0 to 100
        suitability_score = 70.0  # Base line suitability

        # Refine based on metadata constraints
        if self.resource_type == "ICU Bed":
            # If patient is triage 1 or 2, they likely need ventilator
            needs_vent = patient_triage <= 2
            has_vent = self.metadata.get("ventilator_attached", False)
            if needs_vent and has_vent:
                suitability_score += 30.0  # Highly suitable
            elif needs_vent and not has_vent:
                suitability_score -= 20.0  # Less suitable (no ventilator)

        elif self.resource_type == "Doctor":
            # Match specialty
            specialty = self.metadata.get("specialty", "")
            summary = payload.get("clinical_summary", "").lower()
            if "trauma" in summary and "trauma" in specialty.lower():
                suitability_score += 30.0
            elif "cardiac" in summary and "cardio" in specialty.lower():
                suitability_score += 30.0
            elif "respiratory" in summary and "pulmon" in specialty.lower():
                suitability_score += 30.0

        elif self.resource_type == "Ventilator":
            # Check calibration
            suitability_score += 10.0

        # Construct bid response
        bid_payload = {
            "resource_id": self.agent_id,
            "resource_name": self.name,
            "resource_type": self.resource_type,
            "suitability_score": suitability_score,
            "status": self.status,
            "metadata": self.metadata
        }

        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=cfp_message.sender_id,
            message_type="BID",
            conversation_id=cfp_message.conversation_id,
            payload=bid_payload
        )
