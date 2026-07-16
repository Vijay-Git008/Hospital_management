from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..db.database import get_db
from ..db.models import AIConfiguration, AuditRecord
from ..models.schemas import AIConfigCreate, AITestRequest, AIConfigOut
from ..security.encryption import encrypt_val, decrypt_val
from ..security.rbac import allow_admin
from ..ai.client import test_llm_connection

router = APIRouter(prefix="/api/ai", tags=["AI Configuration"])

@router.post("/config", response_model=AIConfigOut)
def save_ai_config(
    payload: AIConfigCreate, 
    db: Session = Depends(get_db), 
    current_user = Depends(allow_admin)
):
    """Encrypts and stores the dynamic BYOK API configuration in the database."""
    # Encrypt API Key
    encrypted_key = encrypt_val(payload.api_key)

    # Check if there is an existing config
    config = db.query(AIConfiguration).first()
    if not config:
        config = AIConfiguration(
            provider=payload.provider,
            model_name=payload.model_name,
            api_key_encrypted=encrypted_key,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens
        )
        db.add(config)
    else:
        config.provider = payload.provider
        config.model_name = payload.model_name
        config.api_key_encrypted = encrypted_key
        config.temperature = payload.temperature
        config.max_tokens = payload.max_tokens

    # Write audit log
    prev_audit = db.query(AuditRecord).order_by(AuditRecord.created_at.desc()).first()
    prev_checksum = prev_audit.checksum if prev_audit else ""
    
    audit = AuditRecord(
        user_id=current_user.id,
        action="SaveAIConfig",
        target_id=config.id,
        payload_json=f'{{"provider": "{payload.provider}", "model": "{payload.model_name}"}}',
        ip_address="127.0.0.1",
        checksum=""
    )
    db.add(audit)
    db.flush()
    audit.checksum = audit.calculate_checksum(prev_checksum)
    
    db.commit()
    db.refresh(config)
    return config

@router.get("/config")
def get_ai_config(db: Session = Depends(get_db)):
    """Returns the current active AI configuration (omits the secret API key)."""
    config = db.query(AIConfiguration).first()
    if not config:
        return {"configured": False}
    return {
        "configured": True,
        "provider": config.provider,
        "model_name": config.model_name,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "updated_at": config.updated_at
    }

@router.post("/test")
async def test_api_connection(
    payload: AITestRequest, 
    db: Session = Depends(get_db)
):
    """Tests the API connection dynamically using the credentials provided in the request."""
    success = await test_llm_connection(
        provider=payload.provider,
        api_key=payload.api_key,
        model_name=payload.model_name,
        temperature=payload.temperature
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API Key validation failed. Please check your credentials and network settings."
        )

    # Log audit event
    prev_audit = db.query(AuditRecord).order_by(AuditRecord.created_at.desc()).first()
    prev_checksum = prev_audit.checksum if prev_audit else ""

    audit = AuditRecord(
        user_id=None,  # can be called unauthenticated before setup
        action="TestAIConnection",
        target_id=payload.provider,
        payload_json=f'{{"provider": "{payload.provider}", "model": "{payload.model_name}"}}',
        ip_address="127.0.0.1",
        checksum=""
    )
    db.add(audit)
    db.flush()
    audit.checksum = audit.calculate_checksum(prev_checksum)
    db.commit()

    return {"success": True, "message": "Connection verification succeeded."}
