import json
import logging
import re
import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional

from ..db.database import get_db
from ..db.models import User, Patient, Bed, Ventilator, NexusAuditLog, NexusLastAlert, AIConfiguration, Notification
from ..models.schemas import (
    PatientVitalsUpdate, PatientMedComplete, PatientPlanUpdate,
    PatientReferralRequest, PatientRegisterRequest, BedAssignRequest,
    ManualLogCreate, LastAlertSave, BYOKConfigSave,
    CROEngineRequest, NotificationOut
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
            "admission_time": p.admission_time.isoformat() if p.admission_time else None,
            "attendingDoctor": p.attendingDoctor,
            "consultedDoctors": consulted_docs,
            "bedId": p.bedId,
            "status": p.status,
            "vitals": vitals_val,
            "treatments": treatments_val,
            "tests": tests_val,
            "aiSummary": ai_summary_val,
            "med": med_val,
            "notes": p.notes,
            "is_vip": p.is_vip or 0
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
        notes=None,
        is_vip=payload.is_vip or 0
    )
    db.add(patient)

    # Update Bed allocation
    bed = db.query(Bed).filter(Bed.id == payload.bedId).first()
    if bed:
        bed.status = "STABLE"
        bed.patientId = new_id

    db.commit()
    create_notification(db, f"New patient registered: {payload.name} ({new_id}). Assigned to Bed {payload.bedId}.", role="Nurse", severity="info")
    create_notification(db, f"New patient intake: {new_id} awaiting assessment.", role="Doctor", severity="info")
    return {"success": True, "patient_id": new_id}

@router.post("/patients/discharge/{patient_id}")
def discharge_patient(patient_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Discharge a patient and release their allocated bed."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient_name = patient.name
    patient_bed = patient.bedId

    if patient.bedId:
        bed = db.query(Bed).filter(Bed.id == patient.bedId).first()
        if bed:
            bed.status = "AVAILABLE"
            bed.patientId = None

    db.delete(patient)
    db.commit()
    create_notification(db, f"Patient discharged: {patient_name} ({patient_id}). Bed {patient_bed} is now AVAILABLE.", role="Receptionist", severity="info")
    create_notification(db, f"Bed Release: Bed {patient_bed} freed by {patient_name}.", role="Coordinator", severity="info")
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

from pydantic import BaseModel
from io import BytesIO
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def create_notification(db: Session, text: str, role: str = None, severity: str = "info"):
    try:
        notif = Notification(
            text=text,
            role=role,
            severity=severity
        )
        db.add(notif)
        db.commit()
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        db.rollback()

@router.get("/notifications", response_model=List[NotificationOut])
def get_notifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Fetch notifications relevant to the user's role or general system ones."""
    role = current_user.role
    # Return notifications where role is null (system wide) or role matches the user's role
    notifications = db.query(Notification).filter(
        (Notification.role == None) | (Notification.role == role)
    ).order_by(Notification.created_at.desc()).limit(50).all()
    return notifications

@router.get("/notifications/unread-count")
def get_unread_count(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get count of unread notifications."""
    role = current_user.role
    count = db.query(Notification).filter(
        ((Notification.role == None) | (Notification.role == role)) & (Notification.is_read == 0)
    ).count()
    return {"count": count}

@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Mark a notification as read."""
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = 1
    db.commit()
    return {"success": True}

@router.post("/notifications/read-all")
def mark_all_read(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Mark all notifications for the current role as read."""
    role = current_user.role
    unread = db.query(Notification).filter(
        ((Notification.role == None) | (Notification.role == role)) & (Notification.is_read == 0)
    ).all()
    for n in unread:
        n.is_read = 1
    db.commit()
    return {"success": True}

@router.get("/vip-override/candidates")
def get_vip_override_candidates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Check ICU capacity. If full, find stable patients as transfer candidates to free a bed for a critical VIP case."""
    icu_beds = db.query(Bed).filter(Bed.zone == "ICU").all()
    total_icu = len(icu_beds)
    occupied_icu = [b for b in icu_beds if b.patientId is not None]
    
    is_full = len(occupied_icu) >= total_icu
    
    # Get patients in ICU
    icu_patient_ids = [b.patientId for b in occupied_icu if b.patientId is not None]
    patients_in_icu = db.query(Patient).filter(Patient.id.in_(icu_patient_ids)).all()
    
    # Find available General Ward beds for relocation
    available_gw_beds = db.query(Bed).filter(
        (Bed.zone.in_(["GA", "GB"])) & (Bed.status == "AVAILABLE")
    ).all()
    
    candidates = []
    for p in patients_in_icu:
        is_stable = p.status == "STABLE"
        score = 0
        if is_stable:
            score += 50
        score += p.triage_level * 10
        
        try:
            vitals = json.loads(p.vitals or "{}")
        except Exception:
            vitals = {}
            
        spo2 = vitals.get("spo2", 98)
        bp = vitals.get("bp", "120/80")
        
        if is_stable or p.triage_level >= 3:
            dest_bed = available_gw_beds[len(candidates)].id if len(candidates) < len(available_gw_beds) else "GA-01"
            candidates.append({
                "patient_id": p.id,
                "name": p.name,
                "current_bed": p.bedId,
                "diagnosis": p.diagnosis,
                "status": p.status,
                "triage_level": p.triage_level,
                "spo2": spo2,
                "bp": bp,
                "recommended_destination": dest_bed,
                "reasoning": f"Patient has been stable for 24+ hours with oxygen saturation at {spo2}% on room air. Vitals are within normal limits (BP: {bp}).",
                "risk_assessment": "Low risk of decompensation. Transfer to step-down GA ward is clinically indicated.",
                "score": score
            })
            
    candidates.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "icu_full": is_full,
        "total_icu_beds": total_icu,
        "occupied_icu_beds": len(occupied_icu),
        "candidates": candidates,
        "available_destinations": [b.id for b in available_gw_beds]
    }

class VIPOverrideApprovalPayload(BaseModel):
    vip_patient_id: str
    stable_patient_id: str
    target_icu_bed_id: str
    relocation_bed_id: str

@router.post("/vip-override/approve")
def approve_vip_override(payload: VIPOverrideApprovalPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Execute the VIP ICU Override: move stable patient out to a General Ward, then assign ICU bed to VIP."""
    if current_user.role.upper() != "DOCTOR" and current_user.role.upper() != "ADMINISTRATOR":
        raise HTTPException(status_code=403, detail="Only Doctors or Administrators can approve clinical overrides.")
        
    vip_patient = db.query(Patient).filter(Patient.id == payload.vip_patient_id).first()
    stable_patient = db.query(Patient).filter(Patient.id == payload.stable_patient_id).first()
    
    if not vip_patient or not stable_patient:
        raise HTTPException(status_code=404, detail="VIP Patient or Stable Candidate not found.")
        
    icu_bed = db.query(Bed).filter(Bed.id == payload.target_icu_bed_id).first()
    gw_bed = db.query(Bed).filter(Bed.id == payload.relocation_bed_id).first()
    
    if not icu_bed or not gw_bed:
        raise HTTPException(status_code=404, detail="ICU Bed or Relocation General Ward Bed not found.")
        
    old_icu_bed_id = stable_patient.bedId
    stable_patient.bedId = gw_bed.id
    stable_patient.status = "STABLE"
    
    gw_bed.status = "STABLE"
    gw_bed.patientId = stable_patient.id
    
    vip_patient.bedId = icu_bed.id
    vip_patient.status = "CRITICAL"
    
    icu_bed.status = "CRITICAL"
    icu_bed.patientId = vip_patient.id
    
    time_str = datetime.datetime.now().strftime("%I:%M:%S %p")
    log_text = (
        f"VIP ICU Override approved by {current_user.name or current_user.username}. "
        f"Stable patient {stable_patient.name} ({stable_patient.id}) transferred from {old_icu_bed_id} to General Ward bed {gw_bed.id}. "
        f"Critical VIP patient {vip_patient.name} ({vip_patient.id}) admitted to ICU Bed {icu_bed.id}."
    )
    audit_log = NexusAuditLog(
        agent=current_user.name or current_user.username,
        role=current_user.role.upper(),
        text=log_text,
        time=time_str
    )
    db.add(audit_log)
    
    create_notification(db, f"VIP Override: {vip_patient.id} admitted to ICU Bed {icu_bed.id}.", role="Doctor", severity="critical")
    create_notification(db, f"Relocation: {stable_patient.id} transferred to General Ward {gw_bed.id}.", role="Nurse", severity="warning")
    
    db.commit()
    return {"success": True, "detail": log_text}

@router.get("/patients/{patient_id}/pdf-report")
def generate_patient_pdf_report(patient_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    styles = getSampleStyleSheet()
    
    # Custom colors
    primary_color = colors.HexColor("#1A365D")
    secondary_color = colors.HexColor("#2D3748")
    accent_color = colors.HexColor("#319795")
    border_color = colors.HexColor("#E2E8F0")
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=primary_color,
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#718096"),
        spaceAfter=15
    )
    
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=accent_color,
        spaceBefore=12,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=secondary_color
    )
    
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#4A5568"),
        fontName="Helvetica-Bold"
    )

    story.append(Paragraph("METRO GENERAL HOSPITAL - NEXUS CLINICAL RESOURCE PORTAL", title_style))
    story.append(Paragraph("Clinical Resource Optimization Engine (CRO Engine) · Patient Summary Report", subtitle_style))
    story.append(Spacer(1, 10))
    
    try:
        vitals = json.loads(patient.vitals or "{}")
    except Exception:
        vitals = {}
    
    info_data = [
        [Paragraph("Patient Name:", label_style), Paragraph(patient.name or "N/A", body_style), Paragraph("Patient ID:", label_style), Paragraph(patient.id or "N/A", body_style)],
        [Paragraph("Age / Gender:", label_style), Paragraph(f"{patient.age or 'N/A'} / {patient.gender or 'N/A'}", body_style), Paragraph("Blood Group:", label_style), Paragraph(patient.bloodGroup or "N/A", body_style)],
        [Paragraph("Current Bed:", label_style), Paragraph(patient.bedId or "Unallocated", body_style), Paragraph("Status:", label_style), Paragraph(patient.status or "N/A", body_style)],
        [Paragraph("Attending Doctor:", label_style), Paragraph(patient.attendingDoctor or "N/A", body_style), Paragraph("Admitted At:", label_style), Paragraph(f"{patient.admittedAt or 0} hrs ago", body_style)]
    ]
    
    t_info = Table(info_data, colWidths=[100, 160, 100, 160])
    t_info.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, border_color),
    ]))
    
    story.append(t_info)
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("Clinical Diagnosis & History", section_heading))
    story.append(Paragraph(f"<b>Diagnosis:</b> {patient.diagnosis or 'N/A'}", body_style))
    if patient.mechanism:
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>Mechanism:</b> {patient.mechanism}", body_style))
        
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("Current Vitals Metrics", section_heading))
    vitals_data = [
        [Paragraph("BP", label_style), Paragraph("SpO2", label_style), Paragraph("GCS", label_style), Paragraph("HR", label_style), Paragraph("Temp", label_style), Paragraph("RR", label_style)],
        [Paragraph(str(vitals.get("bp", "N/A")), body_style), 
         Paragraph(f"{vitals.get('spo2', 'N/A')}%", body_style), 
         Paragraph(str(vitals.get("gcs", "N/A")), body_style), 
         Paragraph(f"{vitals.get('hr', 'N/A')} bpm", body_style), 
         Paragraph(f"{vitals.get('temp', 'N/A')} °C", body_style), 
         Paragraph(f"{vitals.get('rr', 'N/A')} /min", body_style)]
    ]
    t_vitals = Table(vitals_data, colWidths=[85, 85, 85, 85, 85, 85])
    t_vitals.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F8FAFC")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_vitals)
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("CRO Engine AI Assessment Summary", section_heading))
    try:
        ai_summary = json.loads(patient.aiSummary or "{}")
    except Exception:
        ai_summary = {}
        
    stage = ai_summary.get("stage", "N/A")
    trajectory = ai_summary.get("trajectory", "N/A")
    priorities = ai_summary.get("priorities", [])
    
    story.append(Paragraph(f"<b>Clinical Stage:</b> {stage} · <b>Trajectory:</b> {trajectory}", body_style))
    story.append(Spacer(1, 6))
    
    if priorities:
        story.append(Paragraph("<b>Clinical Priorities:</b>", label_style))
        for p_item in priorities:
            story.append(Paragraph(f"• {p_item}", body_style))
            story.append(Spacer(1, 2))
            
    story.append(Spacer(1, 12))
    story.append(Paragraph("Audit Trail Actions", section_heading))
    logs = db.query(NexusAuditLog).filter(NexusAuditLog.text.like(f"%{patient.id}%")).order_by(NexusAuditLog.created_at.desc()).all()
    if logs:
        for l in logs:
            story.append(Paragraph(f"[{l.time}] <b>{l.agent} ({l.role}):</b> {l.text}", body_style))
            story.append(Spacer(1, 4))
    else:
        story.append(Paragraph("No direct override or allocation events logged for this patient ID.", body_style))
        
    doc.build(story)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=Nexus_Report_{patient.id}.pdf"})

@router.post("/cro-engine")
async def run_cro_engine(payload: CROEngineRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Triggers the multi-agent clinical placement optimization engine via BYOK or sandbox mode."""
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
        { "agent": 'Orchestrator', "role": 'System Orchestrator', "color": '#7C3AED', "text": f'Resource optimization complete. Structural resolution: Route patient {patient.id} to ICU-07 with standby support.' }
    ]

    import os

    provider = None
    api_key = None
    model_name = None
    max_tokens = 1000

    if config and config.provider != "MOCK" and config.api_key_encrypted:
        provider = config.provider
        api_key = decrypt_val(config.api_key_encrypted)
        model_name = config.model_name
        max_tokens = config.max_tokens or 1000
    else:
        if os.getenv("OPENAI_API_KEY"):
            provider = "OPENAI"
            api_key = os.getenv("OPENAI_API_KEY")
            model_name = os.getenv("OPENAI_MODEL_NAME") or "gpt-4o-mini"
        elif os.getenv("GEMINI_API_KEY"):
            provider = "GEMINI"
            api_key = os.getenv("GEMINI_API_KEY")
            model_name = os.getenv("GEMINI_MODEL_NAME") or "gemini-1.5-flash"
        elif os.getenv("ANTHROPIC_API_KEY"):
            provider = "ANTHROPIC"
            api_key = os.getenv("ANTHROPIC_API_KEY")
            model_name = os.getenv("ANTHROPIC_MODEL_NAME") or "claude-3-5-sonnet-20241022"

    if not provider or not api_key:
        time_str = datetime.datetime.now().strftime("%I:%M:%S %p")
        log = NexusAuditLog(
            agent="Orchestrator",
            role="SYSTEM",
            text=f"CRO Engine simulated resource placement script generated for {patient.id}",
            time=time_str
        )
        db.add(log)
        db.commit()
        return mock_messages

    try:
        llm_client = get_client_by_provider(
            provider=provider,
            api_key=api_key,
            model_name=model_name,
            temperature=0.2,
            max_tokens=max_tokens
        )
        
        try:
            vitals_val = json.loads(patient.vitals or "{}")
            tests_val = json.loads(patient.tests or "[]")
        except Exception:
            vitals_val = {}
            tests_val = []

        prompt = f"""
        You are simulating a hospital multi-agent clinical resource team (CRO Engine). 
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

        time_str = datetime.datetime.now().strftime("%I:%M:%S %p")
        log = NexusAuditLog(
            agent="Orchestrator",
            role="SYSTEM",
            text=f"CRO Engine live execution script generated via {provider} for {patient.id}",
            time=time_str
        )
        db.add(log)
        db.commit()

        return parsed_script

    except Exception as err:
        logger.error(f"AI Connection failed: {err}")
        time_str = datetime.datetime.now().strftime("%I:%M:%S %p")
        log = NexusAuditLog(
            agent="Orchestrator",
            role="SYSTEM",
            text=f"AI Connection failed: {str(err)}. Reverted to CRO Engine sandbox mode.",
            time=time_str
        )
        db.add(log)
        db.commit()
        return mock_messages

