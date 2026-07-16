from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..db.database import get_db
from ..db.models import Resource, Allocation, AuditRecord
from ..models.schemas import ResourceOut
from ..security.rbac import allow_coordinator, allow_clinical

router = APIRouter(prefix="/api/resources", tags=["Resources"])

@router.get("", response_model=List[ResourceOut])
def list_resources(db: Session = Depends(get_db)):
    return db.query(Resource).all()

@router.post("/{resource_id}/override")
def override_resource(
    resource_id: str,
    action: str,  # "release" or "occupy"
    patient_id: str = None,  # required for occupy
    db: Session = Depends(get_db),
    current_user = Depends(allow_coordinator)
):
    """Coordinator override to manually re-route or free resources during operational blockages."""
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    prev_audit = db.query(AuditRecord).order_by(AuditRecord.created_at.desc()).first()
    prev_checksum = prev_audit.checksum if prev_audit else ""

    if action == "release":
        resource.status = "Available"
        # Release any active allocation for this resource
        active_allocs = db.query(Allocation).filter(
            Allocation.resource_id == resource_id,
            Allocation.status == "Active"
        ).all()
        for a in active_allocs:
            a.status = "Overridden"

        audit = AuditRecord(
            user_id=current_user.id,
            action="ManualRelease",
            target_id=resource_id,
            payload_json=f'{{"resource_name": "{resource.name}", "resource_type": "{resource.type}"}}',
            ip_address="127.0.0.1",
            checksum=""
        )
        db.add(audit)
        db.flush()
        audit.checksum = audit.calculate_checksum(prev_checksum)

    elif action == "occupy":
        if not patient_id:
            raise HTTPException(status_code=400, detail="patient_id is required to manually allocate resource")
        resource.status = "Occupied"

        # Checksum chain for allocation
        prev_alloc = db.query(Allocation).filter(Allocation.status == "Active").order_by(Allocation.created_at.desc()).first()
        prev_checksum_alloc = prev_alloc.checksum if prev_alloc else ""

        alloc = Allocation(
            resource_id=resource_id,
            patient_id=patient_id,
            status="Active",
            checksum=""
        )
        db.add(alloc)
        db.flush()
        alloc.checksum = alloc.calculate_checksum(prev_checksum_alloc)

        audit = AuditRecord(
            user_id=current_user.id,
            action="ManualAllocation",
            target_id=resource_id,
            payload_json=f'{{"patient_id": "{patient_id}", "resource_name": "{resource.name}"}}',
            ip_address="127.0.0.1",
            checksum=""
        )
        db.add(audit)
        db.flush()
        audit.checksum = audit.calculate_checksum(prev_checksum)

    else:
        raise HTTPException(status_code=400, detail="Invalid action. Must be 'release' or 'occupy'")

    db.commit()
    return {"message": f"Resource {resource.name} status updated to {resource.status}"}
