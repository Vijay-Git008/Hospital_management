import pytest
import json
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import Hospital, Resource, Patient, Incident, Allocation, AIConfiguration
from app.security.encryption import encrypt_val, decrypt_val
from app.negotiation.dependency_graph import ResourceDependencyGraph
from app.negotiation.scoring import calculate_priority_score
from app.negotiation.engine import NegotiationEngine

# Setup mock database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_encryption_decryption():
    secret = "sk-proj-test1234567890"
    encrypted = encrypt_val(secret)
    assert encrypted != secret
    decrypted = decrypt_val(encrypted)
    assert decrypted == secret

def test_scoring_logic():
    # Patient with Triage 1 (Critical) and 30m wait
    score_1 = calculate_priority_score(triage_level=1, waiting_time_minutes=30.0, suitability_score=90.0, downstream_impact_count=0)
    # Patient with Triage 2 and 5m wait
    score_2 = calculate_priority_score(triage_level=2, waiting_time_minutes=5.0, suitability_score=70.0, downstream_impact_count=2)
    
    assert score_1["total_score"] > score_2["total_score"]
    assert score_1["triage_score"] == 100.0
    assert score_2["impact_penalty"] == 40.0  # 2 * 20

def test_dependency_graph():
    resources = [
        {"id": "OR-1", "name": "OR 1", "type": "Operating Room", "status": "Occupied"},
        {"id": "OR-2", "name": "OR 2", "type": "Operating Room", "status": "Available"}
    ]
    allocs = [
        {"resource_id": "OR-1", "patient_id": "PT-1"}
    ]
    cases = [
        {"id": "PT-1", "name": "PT-1", "triage_level": 1, "status": "Allocated", "required_resource_types": ["Operating Room"]},
        {"id": "PT-2", "name": "PT-2", "triage_level": 2, "status": "Pending", "required_resource_types": ["Operating Room"]}
    ]

    graph = ResourceDependencyGraph()
    graph.update_topology(resources, allocs, cases)
    
    # Check DFS cascade: OR-1 is allocated to PT-1, PT-1 requires Operating Room (which includes OR-1 and OR-2)
    impact = graph.get_cascading_impacts("OR-1")
    # OR-1 is linked to PT-1
    impacted_ids = [node["id"] for node in impact]
    assert "PT-1" in impacted_ids

@pytest.mark.asyncio
async def test_negotiation_cycle(db_session):
    # Seed hospital
    h = Hospital(name="Test Hospital", latitude=0.0, longitude=0.0)
    db_session.add(h)
    db_session.flush()

    # Seed resources
    or1 = Resource(hospital_id=h.id, name="OR 1", type="Operating Room", status="Available", metadata_json="{}")
    dr1 = Resource(hospital_id=h.id, name="Dr. Sarah", type="Doctor", status="Available", metadata_json='{"specialty": "Trauma Surgeon"}')
    db_session.add(or1)
    db_session.add(dr1)

    # Seed Incident
    inc = Incident(title="Highway Accident", severity="Critical", status="Active")
    db_session.add(inc)
    db_session.flush()

    # Seed Patient Case
    p = Patient(
        name_encrypted="John Doe", 
        triage_level=1, 
        status="Pending", 
        clinical_data_json=json.dumps({"summary": "Severe Trauma", "required_resources": ["Operating Room", "Doctor"]})
    )
    db_session.add(p)
    db_session.commit()

    # Execute engine cycle
    engine = NegotiationEngine()
    await engine.run_negotiation_cycle(db_session, inc.id)

    # Verify allocation
    p_after = db_session.query(Patient).filter(Patient.id == p.id).first()
    assert p_after.status == "Allocated"

    allocs = db_session.query(Allocation).all()
    assert len(allocs) == 2
    assert allocs[0].checksum != ""
