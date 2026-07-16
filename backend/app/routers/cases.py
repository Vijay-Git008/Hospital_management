from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import json
import uuid
import datetime
from ..db.database import get_db
from ..db.models import Patient, Incident, Resource, Allocation, AuditRecord
from ..db.seed import seed_db
from ..models.schemas import PatientOut, PatientCreate
from ..security.rbac import allow_coordinator
from ..negotiation.engine import NegotiationEngine
from ..ws.hub import manager

router = APIRouter(prefix="/api/cases", tags=["Cases & Operations"])

# Dynamic negotiation callback that broadcasts to WebSocket
async def ws_broadcast_callback(data: dict):
    await manager.broadcast(data)

engine_runner = NegotiationEngine(broadcast_callback=ws_broadcast_callback)

@router.get("", response_model=List[PatientOut])
def get_cases(db: Session = Depends(get_db)):
    return db.query(Patient).all()

@router.post("/ingest", response_model=PatientOut)
def ingest_case(
    payload: PatientCreate, 
    db: Session = Depends(get_db), 
    current_user = Depends(allow_coordinator)
):
    """Ingests a new emergency patient case into the queue."""
    # Write encrypted patient name or mask it
    masked_name = f"PT-{payload.name[:3].upper()}-{uuid.uuid4().hex[:4].upper()}"
    
    patient = Patient(
        name_encrypted=masked_name,
        triage_level=payload.triage_level,
        clinical_data_json=json.dumps(payload.clinical_data)
    )
    db.add(patient)
    db.flush()

    # Log audit event
    prev_audit = db.query(AuditRecord).order_by(AuditRecord.created_at.desc()).first()
    prev_checksum = prev_audit.checksum if prev_audit else ""

    audit = AuditRecord(
        user_id=current_user.id,
        action="IngestPatientCase",
        target_id=patient.id,
        payload_json=json.dumps({"triage": payload.triage_level}),
        ip_address="127.0.0.1",
        checksum=""
    )
    db.add(audit)
    db.flush()
    audit.checksum = audit.calculate_checksum(prev_checksum)
    db.commit()

    return patient

@router.post("/trigger-negotiation")
async def trigger_negotiation(incident_id: str, db: Session = Depends(get_db)):
    """Triggers the CNP cycle for pending cases under a specific incident."""
    await engine_runner.run_negotiation_cycle(db, incident_id)
    return {"message": "Negotiation cycle completed."}

@router.post("/scenario")
async def load_scenario(scenario_name: str, db: Session = Depends(get_db)):
    """Resets the system and loads one of three pre-built emergency scenarios."""
    # Reset inventory to ensure clean state
    seed_db()

    # Create incident
    incident_title = ""
    severity = ""
    patients_data = []

    if scenario_name == "mass_casualty":
        incident_title = "Highway Multi-Vehicle Collision"
        severity = "Critical"
        patients_data = [
            {
                "name": "Alex Mercer",
                "triage_level": 1,
                "clinical_data": {
                    "summary": "Internal bleeding, blunt force chest trauma. Immediate operation required.",
                    "required_resources": ["Operating Room", "Doctor", "Nurse"]
                }
            },
            {
                "name": "Sarah Connor",
                "triage_level": 1,
                "clinical_data": {
                    "summary": "Traumatic brain injury, skull fracture. Craniectomy required.",
                    "required_resources": ["Operating Room", "Doctor", "Nurse"]
                }
            },
            {
                "name": "Peter Parker",
                "triage_level": 2,
                "clinical_data": {
                    "summary": "Open compound femur fracture. Stabilization required.",
                    "required_resources": ["Operating Room", "Doctor", "Nurse"]
                }
            }
        ]
    elif scenario_name == "pandemic":
        incident_title = "Avian Flu Outbreak Surge"
        severity = "Critical"
        # Let's seed 4 patients to exceed ventilator capacity (only 3 ventilators exist)
        patients_data = [
            {
                "name": "Bruce Banner",
                "triage_level": 1,
                "clinical_data": {
                    "summary": "Severe respiratory distress. SPO2 at 78%. Intubation needed.",
                    "required_resources": ["ICU Bed", "Ventilator", "Nurse"]
                }
            },
            {
                "name": "Clark Kent",
                "triage_level": 1,
                "clinical_data": {
                    "summary": "Acute viral pneumonia. Intubation needed.",
                    "required_resources": ["ICU Bed", "Ventilator", "Nurse"]
                }
            },
            {
                "name": "Diana Prince",
                "triage_level": 1,
                "clinical_data": {
                    "summary": "Pneumothorax, respiratory failure. Ventilation needed.",
                    "required_resources": ["ICU Bed", "Ventilator", "Nurse"]
                }
            },
            {
                "name": "Barry Allen",
                "triage_level": 2,
                "clinical_data": {
                    "summary": "Severe asthma exacerbation, viral infection.",
                    "required_resources": ["ICU Bed", "Ventilator", "Nurse"]
                }
            }
        ]
    elif scenario_name == "cyber_attack":
        incident_title = "Hospital Core Network Offline"
        severity = "Major"
        
        # Simulate generator failure on two ICU Beds
        icu_beds = db.query(Resource).filter(Resource.type == "ICU Bed").limit(2).all()
        for bed in icu_beds:
            bed.status = "Maintenance"
            bed.metadata_json = json.dumps({"reason": "ICU Ward B backup power offline", "ventilator_attached": False})
        
        # Seed patients needing immediate critical transfer/ambulance support
        patients_data = [
            {
                "name": "Tony Stark",
                "triage_level": 1,
                "clinical_data": {
                    "summary": "Cardiac arrest post-generator failure. Requires ALS transport.",
                    "required_resources": ["Ambulance", "Doctor"]
                }
            },
            {
                "name": "Steve Rogers",
                "triage_level": 2,
                "clinical_data": {
                    "summary": "Stroke symptoms. Requires rapid imaging transfer.",
                    "required_resources": ["Ambulance", "Doctor"]
                }
            }
        ]
    else:
        raise HTTPException(status_code=400, detail="Invalid scenario name")

    # Save incident
    incident = Incident(
        title=incident_title,
        severity=severity,
        status="Active"
    )
    db.add(incident)
    db.flush()

    # Save patients
    created_patients = []
    for pd in patients_data:
        patient = Patient(
            name_encrypted=pd["name"],
            triage_level=pd["triage_level"],
            clinical_data_json=json.dumps(pd["clinical_data"]),
            status="Pending"
        )
        db.add(patient)
        created_patients.append(patient)
    db.flush()

    # Log audit event
    prev_audit = db.query(AuditRecord).order_by(AuditRecord.created_at.desc()).first()
    prev_checksum = prev_audit.checksum if prev_audit else ""
    
    audit = AuditRecord(
        user_id=None,
        action="LoadScenario",
        target_id=scenario_name,
        payload_json=f'{{"incident_title": "{incident_title}"}}',
        ip_address="127.0.0.1",
        checksum=""
    )
    db.add(audit)
    db.flush()
    audit.checksum = audit.calculate_checksum(prev_checksum)
    
    db.commit()

    # Immediately run negotiation cycle
    await engine_runner.run_negotiation_cycle(db, incident.id)

    return {"message": f"Scenario '{scenario_name}' loaded and negotiation executed.", "incident_id": incident.id}
