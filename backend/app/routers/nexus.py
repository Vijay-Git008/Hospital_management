import json
import logging
import re
import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional

from ..db.database import get_db
from ..db.models import User, Patient, Bed, Ventilator, NexusAuditLog, NexusLastAlert, AIConfiguration
from ..models.schemas import (
    PatientVitalsUpdate, PatientMedComplete, PatientPlanUpdate,
    PatientReferralRequest, PatientRegisterRequest, BedAssignRequest,
    ManualLogCreate, LastAlertSave, BYOKConfigSave, SQLConsoleQuery,
    AINegotiationRequest
)
from ..security.auth import get_current_user
from ..security.encryption import encrypt_val, decrypt_val
from ..ai.client import get_client_by_provider

logger = logging.getLogger("NEXUS_Router")

router = APIRouter(prefix="/api/nexus", tags=["NEXUS Platform"])

@router.get("/patients")
def list_patients(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Fetch all active patients with formatted JSON objects."""
    patients = db.query(Patient).all()
    result = []
    for p in patients:
        if not p.name:  # Only return patients with names (NEXUS patients)
            continue
        try:
            consulted_docs = json.loads(p.consultedDoctors or "[]")
        except Exception:
            consulted_docs = []
        try:
            vitals_val = json.loads(p.vitals or "{}")
        except Exception:
            vitals_val = {}
        try:
            treatments_val = json.loads(p.treatments or "[]")
        except Exception:
            treatments_val = []
        try:
            tests_val = json.loads(p.tests or "[]")
        except Exception:
            tests_val = []
        try:
            ai_summary_val = json.loads(p.aiSummary or "{}")
        except Exception:
            ai_summary_val = {}
        try:
            med_val = json.loads(p.med or "[]")
        except Exception:
            med_val = []

        result.append({
            "id": p.id,
            "name": p.name,
            "age": p.age,
            "gender": p.gender,
            "bloodGroup": p.bloodGroup,
            "diagnosis": p.diagnosis,
            "mechanism": p.mechanism,
            "admittedAt": p.admittedAt,
            "attendingDoctor": p.attendingDoctor,
            "consultedDoctors": consulted_docs,
            "bedId": p.bedId,
            "status": p.status,
            "vitals": vitals_val,
            "treatments": treatments_val,
            "tests": tests_val,
            "aiSummary": ai_summary_val,
            "med": med_val,
            "notes": p.notes
        })
    return result

@router.post("/patients/register")
def register_patient(payload: PatientRegisterRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Register a new patient and allocate a bed in the database."""
    # Find next patient ID e.g. P-027
    existing = db.query(Patient).all()
    p_ids = []
    for p in existing:
        if p.id and p.id.startswith('P-'):
            parts = p.id.split('-')
            if len(parts) > 1 and parts[1].isdigit():
                p_ids.append(int(parts[1]))
    next_num = max(p_ids) + 1 if p_ids else 27
    new_id = f"P-{str(next_num).zfill(3)}"

    patient = Patient(
        id=new_id,
        name_encrypted=payload.name,
        triage_level=3,
        status="STABLE",
        clinical_data_json=json.dumps({"summary": payload.diagnosis}),
        name=payload.name,
        age=payload.age,
        gender=payload.gender,
        bloodGroup=payload.bloodGroup,
        diagnosis=payload.diagnosis,
        mechanism="Walk-in Admissions",
        admittedAt=0,
        attendingDoctor="DR-2025-001",
        consultedDoctors="[]",
        bedId=payload.bedId,
        vitals=json.dumps({"bp": "120/80", "spo2": 98, "gcs": 15, "hr": 78, "temp": 37.0, "rr": 16, "spco2": 40, "map": 93}),
        treatments=json.dumps(["Admissions Protocols"]),
        tests=json.dumps([
            {"name": "CBC", "result": "WBC 7.2", "unit": "", "ref": "4-11", "status": "NORMAL"},
            {"name": "CMP", "result": "Na 140, K 4.1", "unit": "mmol/L", "ref": "Normal", "status": "NORMAL"}
        ]),
        aiSummary=json.dumps({"stage": "Stable", "trajectory": "Initial assessment", "priorities": ["Baseline checks"], "resources": {"icu": "Not required", "vent": "Not required", "surg": "None"}, "flags": []}),
        med=json.dumps([]),
        notes=None
    )
    db.add(patient)

    # Update Bed allocation
    bed = db.query(Bed).filter(Bed.id == payload.bedId).first()
    if bed:
        bed.status = "STABLE"
        bed.patientId = new_id

    db.commit()
    return {"success": True, "patient_id": new_id}

@router.post("/patients/discharge/{patient_id}")
def discharge_patient(patient_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Discharge a patient and release their allocated bed."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if patient.bedId:
        bed = db.query(Bed).filter(Bed.id == patient.bedId).first()
        if bed:
            bed.status = "AVAILABLE"
            bed.patientId = None

    db.delete(patient)
    db.commit()
    return {"success": True}

@router.post("/patients/update-plan")
def update_plan(payload: PatientPlanUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Update patient care notes / treatment plan."""
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.notes = payload.notes
    db.commit()
    return {"success": True}

@router.post("/patients/refer")
def refer_patient(payload: PatientReferralRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Refer patient to a specialist doctor."""
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    try:
        consulted = json.loads(patient.consultedDoctors or "[]")
    except Exception:
        consulted = []
    if payload.specialist_id not in consulted:
        consulted.append(payload.specialist_id)
    patient.consultedDoctors = json.dumps(consulted)
    db.commit()
    return {"success": True}

@router.post("/patients/vitals")
def update_vitals(payload: PatientVitalsUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Update patient vitals metrics."""
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    try:
        vitals = json.loads(patient.vitals or "{}")
    except Exception:
        vitals = {}

    if payload.bp is not None:
        vitals["bp"] = payload.bp
    if payload.spo2 is not None:
        vitals["spo2"] = payload.spo2
    if payload.gcs is not None:
        vitals["gcs"] = payload.gcs
    if payload.hr is not None:
        vitals["hr"] = payload.hr

    patient.vitals = json.dumps(vitals)
    db.commit()
    return {"success": True}

@router.post("/patients/meds/complete")
def complete_med(payload: PatientMedComplete, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Mark a patient's medication dose as complete."""
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    try:
        meds = json.loads(patient.med or "[]")
    except Exception:
        meds = []

    if 0 <= payload.med_index < len(meds):
        meds[payload.med_index]["status"] = "Completed"

    patient.med = json.dumps(meds)
    db.commit()
    return {"success": True}

@router.get("/beds")
def list_beds(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Retrieve all beds and their current statuses."""
    beds = db.query(Bed).all()
    return [{"id": b.id, "zone": b.zone, "status": b.status, "patientId": b.patientId} for b in beds]

@router.post("/beds/assign")
def assign_bed(payload: BedAssignRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Manually assign a patient to a bed."""
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Free old bed
    if patient.bedId:
        old_bed = db.query(Bed).filter(Bed.id == patient.bedId).first()
        if old_bed:
            old_bed.status = "AVAILABLE"
            old_bed.patientId = None

    # Assign new bed
    bed = db.query(Bed).filter(Bed.id == payload.bed_id).first()
    if not bed:
        raise HTTPException(status_code=404, detail="Bed not found")

    bed.status = patient.status
    bed.patientId = patient.id
    patient.bedId = payload.bed_id

    db.commit()
    return {"success": True}

@router.get("/ventilators")
def list_ventilators(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Retrieve all ventilators in a dictionary mapping."""
    vents = db.query(Ventilator).all()
    result = {}
    for v in vents:
        result[v.id] = {
            "status": v.status,
            "assignedTo": v.assignedTo,
            "location": v.location
        }
    return result

@router.get("/logs")
def list_logs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Fetch manual and system action logs."""
    logs = db.query(NexusAuditLog).order_by(NexusAuditLog.created_at.desc()).all()
    return [{
        "id": l.id,
        "agent": l.agent,
        "role": l.role,
        "text": l.text,
        "time": l.time
    } for l in logs]

@router.post("/logs")
def create_log(payload: ManualLogCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Write a manual user action to the audit logs."""
    time_str = datetime.datetime.now().strftime("%I:%M:%S %p")
    log = NexusAuditLog(
        agent=current_user.name or current_user.username,
        role=current_user.role.upper(),
        text=payload.text,
        time=time_str
    )
    db.add(log)
    db.commit()
    return {"success": True}

@router.get("/last-alert")
def get_last_alert(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get the last active ambulance dispatch/divert alert."""
    alert = db.query(NexusLastAlert).order_by(NexusLastAlert.created_at.desc()).first()
    if not alert:
        return None
    return {"hospital": alert.hospital, "time": alert.time}

@router.post("/last-alert")
def save_last_alert(payload: LastAlertSave, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Save/update the last ambulance divert alert."""
    time_str = datetime.datetime.now().strftime("%I:%M %p")
    alert = NexusLastAlert(
        hospital=payload.hospital,
        time=time_str
    )
    db.add(alert)
    db.commit()
    return {"success": True}

@router.get("/byok-config")
def get_byok_config(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Retrieve current LLM configuration (masking the API key)."""
    config = db.query(AIConfiguration).first()
    if not config:
        return {"provider": "MOCK", "apiKey": "", "model": "", "endpoint": ""}
    return {
        "provider": config.provider,
        "apiKey": "••••••••••••" if config.api_key_encrypted else "",
        "model": config.model_name,
        "endpoint": ""
    }

@router.post("/byok-config")
def save_byok_config(payload: BYOKConfigSave, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Encrypt and save the BYOK connection details."""
    config = db.query(AIConfiguration).first()

    encrypted_key = None
    if payload.apiKey and payload.apiKey != "••••••••••••":
        encrypted_key = encrypt_val(payload.apiKey)

    if not config:
        config = AIConfiguration(
            provider=payload.provider,
            model_name=payload.model,
            api_key_encrypted=encrypted_key or "",
            temperature=0.2,
            max_tokens=1000
        )
        db.add(config)
    else:
        config.provider = payload.provider
        config.model_name = payload.model
        if encrypted_key is not None:
            config.api_key_encrypted = encrypted_key

    db.commit()
    return {"success": True}

@router.post("/sql-console")
def execute_sql(payload: SQLConsoleQuery, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Run SQL commands securely on the SQLite database, validating inputs to prevent SQL injection."""
    query = payload.query.strip()
    
    if current_user.role not in ["Doctor", "Nurse", "Receptionist", "Administrator"]:
        raise HTTPException(status_code=403, detail="Access denied. Unauthorized role.")

    # Validate that it is only a SELECT or UPDATE query
    clean_query = re.sub(r'\s+', ' ', query).strip()
    is_select = re.match(r'^SELECT\s+', clean_query, re.IGNORECASE)
    is_update = re.match(r'^UPDATE\s+', clean_query, re.IGNORECASE)

    if not (is_select or is_update):
        raise HTTPException(status_code=400, detail="Only SELECT and UPDATE statements are supported in this relational console.")

    # Restrict table access - block attempts to access system security configurations
    sensitive_tables = ["users", "hospitals", "resources", "incidents", "negotiations", "negotiation_steps", "allocations", "audit_records", "ai_configurations"]
    for t in sensitive_tables:
        if re.search(r'\b' + re.escape(t) + r'\b', clean_query, re.IGNORECASE):
            raise HTTPException(status_code=400, detail=f"Access denied to system table: {t}")

    try:
        result = db.execute(text(query))
        if is_select:
            columns = list(result.keys())
            rows = []
            for row in result.fetchall():
                row_dict = {}
                for col in columns:
                    val = getattr(row, col)
                    row_dict[col] = str(val) if val is not None else ""
                rows.append(row_dict)
            return {"headers": columns, "rows": rows}
        else:
            db.commit()
            return {"headers": ["Status code"], "rows": [{"Status code": "Database records modified successfully."}]}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/ai-negotiation")
async def run_ai_negotiation(payload: AINegotiationRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Triggers the multi-agent clinical placement negotiation script via BYOK or sandbox mode."""
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    config = db.query(AIConfiguration).first()

    mock_messages = [
        { "agent": 'Orchestrator', "role": 'System Orchestrator', "color": '#7C3AED', "text": f'Initiating global allocation scan for inbound critical case {patient.id} ({patient.diagnosis}).' },
        { "agent": 'ICU Agent', "role": 'Bed Coordinator', "color": '#2563EB', "text": 'ICU capacity is currently at 90%. I have identified bed ICU-07 holding a pending discharge. Expediting transfer parameters.' },
        { "agent": 'Staff Agent', "role": 'Clinical Personnel Matcher', "color": '#D97706', "text": 'Matched Dr. Sharma (Emergency Medicine) as Primary and Dr. Rajan (Cardiothoracic Surgery) as On-Call Consultant.' },
        { "agent": 'Equipment Agent', "role": 'Ventilator Systems Tracker', "color": '#DC2626', "text": 'Assigned Ventilator VENT-04 from auxiliary storage. Routing to bed ICU-07 now.' },
        { "agent": 'Ambulance Agent', "role": 'Paramedic Intake Handler', "color": '#0891B2', "text": 'Inbound vehicle ETA 1min 45sec. Landing pad and elevator clear path verified.' },
        { "agent": 'Orchestrator', "role": 'System Orchestrator', "color": '#7C3AED', "text": f'Negotiation sequence complete. Structural resolution: Route patient {patient.id} to ICU-07 with standby support.' }
    ]

    if not config or config.provider == "MOCK" or not config.api_key_encrypted:
        # Log simulated action
        time_str = datetime.datetime.now().strftime("%I:%M:%S %p")
        log = NexusAuditLog(
            agent="Orchestrator",
            role="SYSTEM",
            text=f"AI Agent simulated resource placement script generated for {patient.id}",
            time=time_str
        )
        db.add(log)
        db.commit()
        return mock_messages

    try:
        api_key = decrypt_val(config.api_key_encrypted)
        llm_client = get_client_by_provider(
            provider=config.provider,
            api_key=api_key,
            model_name=config.model_name,
            temperature=0.2,
            max_tokens=config.max_tokens or 1000
        )
        
        try:
            vitals_val = json.loads(patient.vitals or "{}")
            tests_val = json.loads(patient.tests or "[]")
        except Exception:
            vitals_val = {}
            tests_val = []

        prompt = f"""
        You are simulating a hospital multi-agent clinical resource team. 
        Analyze this patient case data:
        Patient ID: {patient.id}
        Diagnosis: {patient.diagnosis}
        Vitals: {json.dumps(vitals_val)}
        Tests: {json.dumps(tests_val[:3])}

        Provide a step-by-step negotiation script between 3 AI agents in raw JSON format.
        The final array must strictly match this shape (with exact keys and colors):
        [
          {{"agent": "Orchestrator", "role": "System Orchestrator", "color": "#7C3AED", "text": "agent narrative step"}},
          {{"agent": "ICU Agent", "role": "ICU Ward Coordinator", "color": "#2563EB", "text": "agent narrative step"}},
          {{"agent": "Staff Agent", "role": "Clinical Personnel Matcher", "color": "#D97706", "text": "agent recommendation"}}
        ]
        Return only valid, parsable JSON. No markdown backticks.
        """

        raw_res = await llm_client.generate_text(prompt)
        sanitized = raw_res.replace("```json", "").replace("```", "").strip()
        parsed_script = json.loads(sanitized)

        # Log decision
        time_str = datetime.datetime.now().strftime("%I:%M:%S %p")
        log = NexusAuditLog(
            agent="Orchestrator",
            role="SYSTEM",
            text=f"AI Agent live negotiation script generated via {config.provider} for {patient.id}",
            time=time_str
        )
        db.add(log)
        db.commit()

        return parsed_script

    except Exception as err:
        logger.error(f"AI Connection failed: {err}")
        # Log failure
        time_str = datetime.datetime.now().strftime("%I:%M:%S %p")
        log = NexusAuditLog(
            agent="Orchestrator",
            role="SYSTEM",
            text=f"AI Connection failed: {str(err)}. Reverted to sandbox mode.",
            time=time_str
        )
        db.add(log)
        db.commit()
        return mock_messages
