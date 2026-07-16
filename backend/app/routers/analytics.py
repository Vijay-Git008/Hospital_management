from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..db.database import get_db
from ..db.models import Allocation, AuditRecord, Patient, Resource
from ..models.schemas import AuditRecordOut
from ..security.rbac import allow_manager

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Security Audit"])

@router.get("/dashboard")
def get_dashboard_metrics(db: Session = Depends(get_db)):
    """Computes summary statistics for the Emergency Operations center."""
    total_patients = db.query(Patient).count()
    allocated_patients = db.query(Patient).filter(Patient.status == "Allocated").count()
    pending_patients = db.query(Patient).filter(Patient.status == "Pending").count()

    total_resources = db.query(Resource).count()
    occupied_resources = db.query(Resource).filter(Resource.status == "Occupied").count()
    maint_resources = db.query(Resource).filter(Resource.status == "Maintenance").count()

    utilization_rate = (occupied_resources / total_resources * 100.0) if total_resources > 0 else 0.0

    return {
        "patients": {
            "total": total_patients,
            "allocated": allocated_patients,
            "pending": pending_patients
        },
        "resources": {
            "total": total_resources,
            "occupied": occupied_resources,
            "maintenance": maint_resources,
            "utilization_rate": round(utilization_rate, 1)
        },
        "system_status": "Operational" if maint_resources < 3 else "Degraded"
    }

@router.get("/audit-records", response_model=List[AuditRecordOut])
def get_audit_records(db: Session = Depends(get_db)):
    return db.query(AuditRecord).order_by(AuditRecord.created_at.desc()).all()

@router.get("/validate-chain")
def validate_cryptographic_chain(db: Session = Depends(get_db)):
    """
    Validates the SHA-256 block chain integrity for allocations and audit logs.
    Detects if any malicious database manipulation occurred.
    """
    # 1. Validate Allocations Chain
    allocations = db.query(Allocation).order_by(Allocation.created_at.asc()).all()
    prev_alloc_checksum = ""
    tampered_allocations = []

    for idx, alloc in enumerate(allocations):
        calculated = alloc.calculate_checksum(prev_alloc_checksum)
        if alloc.checksum != calculated:
            tampered_allocations.append({
                "id": alloc.id,
                "recorded_checksum": alloc.checksum,
                "calculated_checksum": calculated,
                "index": idx
            })
        prev_alloc_checksum = alloc.checksum

    # 2. Validate Audit Records Chain
    audits = db.query(AuditRecord).order_by(AuditRecord.created_at.asc()).all()
    prev_audit_checksum = ""
    tampered_audits = []

    for idx, audit in enumerate(audits):
        calculated = audit.calculate_checksum(prev_audit_checksum)
        if audit.checksum != calculated:
            tampered_audits.append({
                "id": audit.id,
                "action": audit.action,
                "recorded_checksum": audit.checksum,
                "calculated_checksum": calculated,
                "index": idx
            })
        prev_audit_checksum = audit.checksum

    is_valid = len(tampered_allocations) == 0 and len(tampered_audits) == 0

    return {
        "chain_valid": is_valid,
        "tampered_allocations": tampered_allocations,
        "tampered_audits": tampered_audits
    }
