from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import bcrypt
from ..db.database import get_db
from ..db.models import User, AuditRecord
from ..models.schemas import Token, UserOut
from ..security.auth import create_access_token, get_current_user

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Log login audit record
    prev_audit = db.query(AuditRecord).order_by(AuditRecord.created_at.desc()).first()
    prev_checksum = prev_audit.checksum if prev_audit else ""

    audit = AuditRecord(
        user_id=user.id,
        action="LoginSuccess",
        target_id=user.id,
        payload_json="{}",
        ip_address="127.0.0.1",
        checksum=""
    )
    db.add(audit)
    db.flush()
    audit.checksum = audit.calculate_checksum(prev_checksum)
    db.commit()

    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
