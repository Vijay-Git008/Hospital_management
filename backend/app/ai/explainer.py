from sqlalchemy.orm import Session
from ..db.models import AIConfiguration
from ..security.encryption import decrypt_val
from .client import get_client_by_provider
import json

def get_active_llm_client(db: Session):
    """Loads the active AI configuration from the DB, decrypts the key, and returns an LLMClient."""
    config = db.query(AIConfiguration).order_by(AIConfiguration.updated_at.desc()).first()
    if not config or not config.api_key_encrypted:
        return None
    try:
        api_key = decrypt_val(config.api_key_encrypted)
        if not api_key:
            return None
        return get_client_by_provider(
            provider=config.provider,
            api_key=api_key,
            model_name=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )
    except Exception as e:
        print(f"Error initializing LLM client: {e}")
        return None

async def explain_allocation(db: Session, patient_info: dict, allocation_info: dict, scoring_details: dict, downstream_impacts: list) -> str:
    """Invokes the dynamic LLM to explain the priority allocation decision in plain language."""
    client = get_active_llm_client(db)
    if not client:
        return "AI explanation unavailable – Configure a valid API key in Settings."

    prompt = f"""
You are an AI Clinical Operations Assistant at a major hospital command center.
Please provide a concise, professional, and clear natural-language explanation of a resource allocation decision.
The explanation must be structured for review by doctors, nurse managers, and hospital administrators.

[Patient Data]
- Triage Level: {patient_info.get('triage_level')} (1 = most critical, 5 = minor)
- Symptoms/Summary: {patient_info.get('summary')}
- Waiting Duration: {patient_info.get('waiting_time_minutes')} minutes

[Allocated Resources]
{json.dumps(allocation_info, indent=2)}

[Scoring Details & Bid Breakdown]
{json.dumps(scoring_details, indent=2)}

[Downstream Cascading Impacts (NetworkX Graph Analysis)]
{json.dumps(downstream_impacts, indent=2)}

Explain:
1. Why this patient was prioritized over others (referencing severity, waiting duration, and scoring).
2. The clinical reasoning for allocating these specific resources.
3. The downstream impact (if any) and how it is managed.

Keep your response under 250 words, using clear bullet points. Avoid filler text.
"""
    try:
        return await client.generate_text(prompt)
    except Exception as e:
        return f"AI explanation failed: {str(e)}"

async def summarize_incident(db: Session, incident_title: str, severity: str, cases: list, allocations: list) -> str:
    """Generates an executive summary of an ongoing incident."""
    client = get_active_llm_client(db)
    if not client:
        return "AI summary unavailable – Configure a valid API key in Settings."

    prompt = f"""
You are an emergency operations coordinator. Write an executive incident summary for:
Incident: {incident_title}
Severity Level: {severity}

[Active Cases Ingested]
{json.dumps(cases, indent=2)}

[Resource Allocations Executed]
{json.dumps(allocations, indent=2)}

Provide a 3-sentence summary describing the emergency, the speed of multi-agent mediation, and any remaining bottlenecks.
"""
    try:
        return await client.generate_text(prompt)
    except Exception as e:
        return f"AI summary failed: {str(e)}"
