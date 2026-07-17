import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import bcrypt
import json

from app.main import app
from app.db.database import Base, get_db
from app.db.models import User, Patient, Bed, Ventilator, AIConfiguration
from app.security.encryption import encrypt_val, decrypt_val

# In-memory test database with StaticPool to share connection across sessions
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

@pytest.fixture(scope="function")
def db_session(monkeypatch):
    import app.db.database as db_module
    
    # Override SessionLocal with our test session factory
    monkeypatch.setattr(db_module, "SessionLocal", TestingSessionLocal)
    
    # Create the tables in the test engine
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        # Seed test user
        test_user = User(
            id="DR-2025-001",
            username="DR-2025-001",
            password_hash=get_password_hash("Anjali@123"),
            role="Doctor",
            name="Anjali Sharma",
            initial="A"
        )
        db.add(test_user)
        
        # Seed test beds
        bed1 = Bed(id="ICU-01", zone="ICU", status="AVAILABLE", patientId=None)
        bed2 = Bed(id="EM-01", zone="EM", status="AVAILABLE", patientId=None)
        db.add(bed1)
        db.add(bed2)
        
        # Seed test patient
        patient = Patient(
            id="P-024",
            name_encrypted="John Doe",
            triage_level=1,
            status="CRITICAL",
            clinical_data_json="{}",
            name="John Doe",
            age=45,
            gender="M",
            bloodGroup="O+",
            diagnosis="Tension Pneumothorax",
            attendingDoctor="DR-2025-001",
            consultedDoctors="[]",
            bedId="EM-01",
            vitals="{}",
            treatments="[]",
            tests="[]",
            aiSummary="{}",
            med="[]"
        )
        db.add(patient)
        
        db.commit()
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    # Set FastAPI dependency override to use overridden get_db
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
            
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_login_auth(client):
    response = client.post("/api/auth/login", data={"username": "DR-2025-001", "password": "Anjali@123"})
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

def test_get_patients_and_beds(client):
    login_res = client.post("/api/auth/login", data={"username": "DR-2025-001", "password": "Anjali@123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    res = client.get("/api/nexus/patients", headers=headers)
    assert res.status_code == 200
    pats = res.json()
    assert len(pats) == 1
    assert pats[0]["id"] == "P-024"
    assert pats[0]["name"] == "John Doe"
    
    res = client.get("/api/nexus/beds", headers=headers)
    assert res.status_code == 200
    beds = res.json()
    assert len(beds) == 2

def test_patient_crud_operations(client):
    login_res = client.post("/api/auth/login", data={"username": "DR-2025-001", "password": "Anjali@123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Register Patient
    reg_data = {
        "name": "Jane Miller",
        "age": 30,
        "gender": "F",
        "bloodGroup": "A-",
        "diagnosis": "Appendicitis",
        "bedId": "ICU-01"
    }
    res = client.post("/api/nexus/patients/register", json=reg_data, headers=headers)
    assert res.status_code == 200
    assert res.json()["success"] is True
    new_id = res.json()["patient_id"]
    
    # Check registration details
    res = client.get("/api/nexus/patients", headers=headers)
    pats = res.json()
    jane = next(p for p in pats if p["id"] == new_id)
    assert jane["name"] == "Jane Miller"
    assert jane["bedId"] == "ICU-01"
    
    # Check Bed status is now STABLE
    res = client.get("/api/nexus/beds", headers=headers)
    beds = res.json()
    icu_bed = next(b for b in beds if b["id"] == "ICU-01")
    assert icu_bed["status"] == "STABLE"
    assert icu_bed["patientId"] == new_id
    
    # 2. Update Plan Notes
    res = client.post("/api/nexus/patients/update-plan", json={"patient_id": new_id, "notes": "Prepare for surgery"}, headers=headers)
    assert res.status_code == 200
    
    # Check notes saved
    res = client.get("/api/nexus/patients", headers=headers)
    jane = next(p for p in res.json() if p["id"] == new_id)
    assert jane["notes"] == "Prepare for surgery"
    
    # 3. Discharge Patient
    res = client.post(f"/api/nexus/patients/discharge/{jane['id']}", headers=headers)
    assert res.status_code == 200
    
    # Check bed is released
    res = client.get("/api/nexus/beds", headers=headers)
    icu_bed = next(b for b in res.json() if b["id"] == "ICU-01")
    assert icu_bed["status"] == "AVAILABLE"
    assert icu_bed["patientId"] is None

def test_notifications_api(client):
    login_res = client.post("/api/auth/login", data={"username": "DR-2025-001", "password": "Anjali@123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Fetch notifications
    res = client.get("/api/nexus/notifications", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    
    # 2. Get unread count
    res = client.get("/api/nexus/notifications/unread-count", headers=headers)
    assert res.status_code == 200
    count_data = res.json()
    assert "count" in count_data


def test_byok_api_key_encryption_decryption(db_session):
    secret_key = "sk-proj-super-secret-key-12345"
    
    # Encrypt
    encrypted = encrypt_val(secret_key)
    assert encrypted != secret_key
    
    # Decrypt
    decrypted = decrypt_val(encrypted)
    assert decrypted == secret_key
