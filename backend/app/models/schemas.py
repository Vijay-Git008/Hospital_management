from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Auth Schemas ---
class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: str
    username: str
    role: str
    hospital_id: Optional[str] = None
    created_at: datetime
    
    # NEXUS specific properties
    name: Optional[str] = None
    specialty: Optional[str] = None
    dept: Optional[str] = None
    ward: Optional[str] = None
    initial: Optional[str] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

# --- Resource Schemas ---
class ResourceOut(BaseModel):
    id: str
    hospital_id: str
    name: str
    type: str
    status: str
    metadata_json: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- Patient / Case Schemas ---
class PatientCreate(BaseModel):
    name: str
    triage_level: int = Field(..., ge=1, le=5)
    clinical_data: Dict[str, Any] = Field(default_factory=dict)

class PatientOut(BaseModel):
    id: str
    triage_level: int
    admission_time: datetime
    status: str
    clinical_data_json: str
    created_at: datetime
    is_vip: Optional[int] = 0

    class Config:
        from_attributes = True

# --- Incident Schemas ---
class IncidentCreate(BaseModel):
    title: str
    severity: str  # Critical, Major, Minor
    patients: List[PatientCreate]

class IncidentOut(BaseModel):
    id: str
    title: str
    severity: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- AI Configuration Schemas ---
class AIConfigCreate(BaseModel):
    provider: str  # openai, gemini, anthropic
    model_name: str
    api_key: str
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=10, le=8000)
    vip_weight: Optional[float] = 15.0

class AIConfigOut(BaseModel):
    provider: str
    model_name: str
    temperature: float
    max_tokens: int
    vip_weight: Optional[float] = 15.0
    updated_at: datetime

    class Config:
        from_attributes = True

class AITestRequest(BaseModel):
    provider: str
    model_name: str
    api_key: str
    temperature: float = 0.2

# --- Negotiation & Allocation Schemas ---
class NegotiationStepOut(BaseModel):
    id: str
    negotiation_id: str
    step_type: str
    agent_id: str
    content_json: str
    created_at: datetime

    class Config:
        from_attributes = True

class NegotiationOut(BaseModel):
    id: str
    incident_id: str
    patient_id: str
    status: str
    reasoning_tree_json: str
    created_at: datetime
    steps: List[NegotiationStepOut] = []

    class Config:
        from_attributes = True

class AllocationOut(BaseModel):
    id: str
    negotiation_id: Optional[str] = None
    resource_id: str
    patient_id: str
    allocated_at: datetime
    expires_at: Optional[datetime] = None
    status: str
    checksum: str
    created_at: datetime

    class Config:
        from_attributes = True

class AuditRecordOut(BaseModel):
    id: str
    user_id: Optional[str] = None
    action: str
    target_id: Optional[str] = None
    payload_json: str
    ip_address: Optional[str] = None
    checksum: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- NEXUS Specific Schemas ---

class PatientVitalsUpdate(BaseModel):
    patient_id: str
    bp: Optional[str] = None
    spo2: Optional[int] = None
    gcs: Optional[int] = None
    hr: Optional[int] = None

class PatientMedComplete(BaseModel):
    patient_id: str
    med_index: int

class PatientPlanUpdate(BaseModel):
    patient_id: str
    notes: str

class PatientReferralRequest(BaseModel):
    patient_id: str
    specialist_id: str

class PatientRegisterRequest(BaseModel):
    name: str
    age: int
    gender: str
    bloodGroup: str
    diagnosis: str
    bedId: str
    is_vip: Optional[int] = 0

class BedAssignRequest(BaseModel):
    bed_id: str
    patient_id: str

class ManualLogCreate(BaseModel):
    text: str

class LastAlertSave(BaseModel):
    hospital: str

class BYOKConfigSave(BaseModel):
    provider: str
    apiKey: str
    model: str
    endpoint: Optional[str] = None

class CROEngineRequest(BaseModel):
    patient_id: str

class NotificationOut(BaseModel):
    id: str
    role: Optional[str] = None
    text: str
    severity: str
    is_read: int
    created_at: datetime

    class Config:
        from_attributes = True

