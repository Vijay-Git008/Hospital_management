import datetime
import uuid
import hashlib
import json
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base, SessionLocal

class Hospital(Base):
    __tablename__ = "hospitals"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(255), nullable=True)
    contact_number = Column(String(50), nullable=True)
    specialties = Column(Text, default="[]")  # JSON list
    bed_count = Column(Integer, default=0)
    available_beds = Column(Integer, default=0)
    icu_beds = Column(Integer, default=0)
    available_icu_beds = Column(Integer, default=0)
    ambulances_total = Column(Integer, default=0)
    ambulances_available = Column(Integer, default=0)
    ambulances_busy = Column(Integer, default=0)
    ambulances_maintenance = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    users = relationship("User", back_populates="hospital")
    resources = relationship("Resource", back_populates="hospital")

class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # Admin, Coordinator, Doctor, Nurse, Manager, Observer
    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # NEXUS specific properties
    name = Column(String(100), nullable=True)
    specialty = Column(String(100), nullable=True)
    dept = Column(String(100), nullable=True)
    ward = Column(String(100), nullable=True)
    initial = Column(String(5), nullable=True)

    hospital = relationship("Hospital", back_populates="users")
    audit_records = relationship("AuditRecord", back_populates="user")

class Resource(Base):
    __tablename__ = "resources"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # ICU, Doctor, Nurse, Ventilator, OR, Ambulance, Blood, Equipment
    status = Column(String(50), default="Available")  # Available, Occupied, Maintenance
    metadata_json = Column(Text, default="{}")  # Extra details (e.g. specialty, model)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    hospital = relationship("Hospital", back_populates="resources")
    allocations = relationship("Allocation", back_populates="resource")

class Patient(Base):
    __tablename__ = "patients"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name_encrypted = Column(String(255), nullable=False)
    triage_level = Column(Integer, nullable=False)  # 1 = critical, 5 = non-urgent
    admission_time = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String(50), default="Pending")  # Pending, Allocated, Discharged
    clinical_data_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_vip = Column(Integer, default=0)

    # NEXUS specific fields (nullable for backward compatibility with tests/existing seeds)
    name = Column(String(100), nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String(10), nullable=True)
    bloodGroup = Column(String(10), nullable=True)
    diagnosis = Column(String(255), nullable=True)
    mechanism = Column(String(255), nullable=True)
    admittedAt = Column(Integer, nullable=True)  # Elapsed hours
    attendingDoctor = Column(String(50), nullable=True)
    consultedDoctors = Column(Text, default="[]")  # JSON list
    bedId = Column(String(50), nullable=True)
    vitals = Column(Text, default="{}")  # JSON vitals
    treatments = Column(Text, default="[]")  # JSON list
    tests = Column(Text, default="[]")  # JSON list
    aiSummary = Column(Text, default="{}")  # JSON object
    med = Column(Text, default="[]")  # JSON list
    notes = Column(Text, nullable=True)  # Doctor plan notes

    negotiations = relationship("Negotiation", back_populates="patient")
    allocations = relationship("Allocation", back_populates="patient")

class Incident(Base):
    __tablename__ = "incidents"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(100), nullable=False)
    severity = Column(String(50), nullable=False)  # Critical, Major, Minor
    status = Column(String(50), default="Active")  # Active, Resolved
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    negotiations = relationship("Negotiation", back_populates="incident")

class Negotiation(Base):
    __tablename__ = "negotiations"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), default="Initiated")  # Initiated, Bidding, Awarded, Failed
    reasoning_tree_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    incident = relationship("Incident", back_populates="negotiations")
    patient = relationship("Patient", back_populates="negotiations")
    steps = relationship("NegotiationStep", back_populates="negotiation")
    allocations = relationship("Allocation", back_populates="negotiation")

class NegotiationStep(Base):
    __tablename__ = "negotiation_steps"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    negotiation_id = Column(String(36), ForeignKey("negotiations.id", ondelete="CASCADE"), nullable=False)
    step_type = Column(String(50), nullable=False)  # CFP, BID, AWARD, REJECT
    agent_id = Column(String(100), nullable=False)
    content_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    negotiation = relationship("Negotiation", back_populates="steps")

class Allocation(Base):
    __tablename__ = "allocations"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    negotiation_id = Column(String(36), ForeignKey("negotiations.id", ondelete="SET NULL"), nullable=True)
    resource_id = Column(String(36), ForeignKey("resources.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    allocated_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="Active")  # Active, Released, Overridden
    checksum = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    negotiation = relationship("Negotiation", back_populates="allocations")
    resource = relationship("Resource", back_populates="allocations")
    patient = relationship("Patient", back_populates="allocations")

    def calculate_checksum(self, prev_checksum: str = "") -> str:
        """Calculates a SHA-256 block checksum chained to the previous block."""
        data = f"{self.id}|{self.negotiation_id}|{self.resource_id}|{self.patient_id}|{self.status}|{self.created_at}"
        hasher = hashlib.sha256()
        hasher.update((data + prev_checksum).encode("utf-8"))
        return hasher.hexdigest()

class AuditRecord(Base):
    __tablename__ = "audit_records"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)  # Login, ManualOverride, ConfigChange, TestAPIConnection
    target_id = Column(String(100), nullable=True)
    payload_json = Column(Text, default="{}")
    ip_address = Column(String(45), nullable=True)
    checksum = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="audit_records")

    def calculate_checksum(self, prev_checksum: str = "") -> str:
        """Calculates a SHA-256 block checksum chained to the previous block."""
        data = f"{self.id}|{self.user_id}|{self.action}|{self.target_id}|{self.payload_json}|{self.created_at}"
        hasher = hashlib.sha256()
        hasher.update((data + prev_checksum).encode("utf-8"))
        return hasher.hexdigest()

class AIConfiguration(Base):
    __tablename__ = "ai_configurations"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String(50), nullable=False)  # openai, gemini, anthropic
    model_name = Column(String(100), nullable=False)
    api_key_encrypted = Column(Text, nullable=False)
    temperature = Column(Float, default=0.2)
    max_tokens = Column(Integer, default=1000)
    vip_weight = Column(Float, default=15.0)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class Bed(Base):
    __tablename__ = "beds"
    id = Column(String(50), primary_key=True)
    zone = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)  # AVAILABLE, CRITICAL, STABLE, TRANSFERRING
    patientId = Column(String(50), nullable=True)

class Ventilator(Base):
    __tablename__ = "ventilators"
    id = Column(String(50), primary_key=True)
    status = Column(String(50), nullable=False)  # AVAILABLE, OCCUPIED
    assignedTo = Column(String(50), nullable=True)
    location = Column(String(100), nullable=False)

class NexusAuditLog(Base):
    __tablename__ = "nexus_audit_logs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False)
    text = Column(Text, nullable=False)
    time = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class NexusLastAlert(Base):
    __tablename__ = "nexus_last_alerts"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hospital = Column(String(255), nullable=False)
    time = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    role = Column(String(50), nullable=True)  # e.g., Doctor, Nurse, Receptionist, Administrator
    text = Column(Text, nullable=False)
    severity = Column(String(20), default="info")  # critical, warning, info
    is_read = Column(Integer, default=0)  # 0 for unread, 1 for read
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

