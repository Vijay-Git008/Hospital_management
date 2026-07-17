import datetime
import json
import bcrypt
from .database import Base, engine, SessionLocal
from .models import Hospital, User, Resource, Patient, Incident, Allocation, AuditRecord, Bed, Ventilator, NexusAuditLog, NexusLastAlert, Notification

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def seed_db():
    # Recreate tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Seed Hospital
        hospital = Hospital(
            name="Metro General Hospital Center",
            latitude=40.7128,
            longitude=-74.0060
        )
        db.add(hospital)
        db.flush()  # Generates UUIDs

        # 2. Seed Users for each RBAC Role
        roles_passwords = {
            "admin": ("admin_user", "Administrator"),
            "coord": ("coordinator_user", "Emergency Coordinator"),
            "doctor": ("doctor_user", "Doctor"),
            "nurse": ("nurse_user", "Nurse"),
            "manager": ("manager_user", "Hospital Manager"),
            "observer": ("observer_user", "Observer")
        }

        for username, (password, role) in roles_passwords.items():
            user = User(
                username=username,
                password_hash=get_password_hash(password),
                role=role,
                hospital_id=hospital.id
            )
            db.add(user)
        db.flush()

        # 3. Seed Resources
        # ICU Beds
        for i in range(1, 6):
            res = Resource(
                hospital_id=hospital.id,
                name=f"ICU Bed {i}",
                type="ICU Bed",
                status="Available",
                metadata_json=json.dumps({"ventilator_attached": i <= 2, "ward": "Critical Care A"})
            )
            db.add(res)

        # Operating Rooms (OR)
        for i in range(1, 3):
            res = Resource(
                hospital_id=hospital.id,
                name=f"Operating Room {i}",
                type="Operating Room",
                status="Available",
                metadata_json=json.dumps({"equipment": ["Anesthesia Machine", "Surgical Lights", "Cardiac Monitor"]})
            )
            db.add(res)

        # Doctors
        doctors = [
            ("Dr. Sarah Jenkins", "Trauma Surgeon"),
            ("Dr. Robert Chen", "Anesthesiologist"),
            ("Dr. Emily Ross", "Pulmonologist"),
            ("Dr. Marcus Vance", "Cardiologist")
        ]
        for name, specialty in doctors:
            res = Resource(
                hospital_id=hospital.id,
                name=name,
                type="Doctor",
                status="Available",
                metadata_json=json.dumps({"specialty": specialty, "shift": "Day", "pager": "555-010" + str(len(specialty)%10)})
            )
            db.add(res)

        # Nurses
        nurses = [
            ("Nurse Elena Rostova", "ICU Charge"),
            ("Nurse John Davis", "Trauma Nurse"),
            ("Nurse Maya Patel", "Surgical Nurse")
        ]
        for name, specialty in nurses:
            res = Resource(
                hospital_id=hospital.id,
                name=name,
                type="Nurse",
                status="Available",
                metadata_json=json.dumps({"specialty": specialty, "shift": "Day"})
            )
            db.add(res)

        # Ventilators
        for i in range(1, 4):
            res = Resource(
                hospital_id=hospital.id,
                name=f"Ventilator model-X9 {i}",
                type="Ventilator",
                status="Available",
                metadata_json=json.dumps({"type": "Invasive", "calibration_date": "2026-05-12"})
            )
            db.add(res)

        # Ambulances
        for i in range(1, 3):
            res = Resource(
                hospital_id=hospital.id,
                name=f"Ambulance Unit {i}",
                type="Ambulance",
                status="Available",
                metadata_json=json.dumps({"level": "Advanced Life Support", "crew": 2})
            )
            db.add(res)

        # Blood Units
        blood_types = ["O-Negative", "O-Positive", "A-Positive", "B-Positive"]
        for bt in blood_types:
            res = Resource(
                hospital_id=hospital.id,
                name=f"Blood Pack {bt} (Batch A)",
                type="Blood Unit",
                status="Available",
                metadata_json=json.dumps({"blood_type": bt, "expiry": "2026-08-20"})
            )
            db.add(res)

        # Medical Equipment
        equipment = ["Defibrillator Pro", "Portable Ultrasound", "Rapid Infuser"]
        for eq in equipment:
            res = Resource(
                hospital_id=hospital.id,
                name=eq,
                type="Medical Equipment",
                status="Available",
                metadata_json=json.dumps({"battery_charge": "95%", "location": "ED Storage"})
            )
            db.add(res)

        # 4. Seed NEXUS Staff Users
        USERS_NEXUS = [
            { "id": 'DR-2025-001', "pass": 'Anjali@123', "name": 'Anjali Sharma', "role": 'DOCTOR', "specialty": 'Emergency Medicine', "dept": 'Emergency Medicine', "initial": 'A' },
            { "id": 'DR-2025-002', "pass": 'Priya@123', "name": 'Priya Nair', "role": 'DOCTOR', "specialty": 'Intensive Care Unit', "dept": 'Intensive Care Unit', "initial": 'P' },
            { "id": 'DR-2025-003', "pass": 'Rajan@123', "name": 'S. Rajan', "role": 'DOCTOR', "specialty": 'Cardiothoracic Surgery', "dept": 'Operating Theatre', "initial": 'S' },
            { "id": 'DR-2025-004', "pass": 'Anand@123', "name": 'A. Anand', "role": 'DOCTOR', "specialty": 'Neurosurgery', "dept": 'Operating Theatre', "initial": 'A' },
            { "id": 'DR-2025-005', "pass": 'Meera@123', "name": 'Meera Krishnan', "role": 'DOCTOR', "specialty": 'General Surgery', "dept": 'General Ward', "initial": 'M' },
            { "id": 'DR-2025-006', "pass": 'Vivek@123', "name": 'Vivek Iyer', "role": 'DOCTOR', "specialty": 'Internal Medicine', "dept": 'General Ward', "initial": 'V' },
            { "id": 'DR-2025-007', "pass": 'Kumar@123', "name": 'R. Kumar', "role": 'DOCTOR', "specialty": 'Orthopedics', "dept": 'General Ward', "initial": 'K' },
            { "id": 'DR-2025-008', "pass": 'Devi@123', "name": 'S. Devi', "role": 'DOCTOR', "specialty": 'Pulmonology', "dept": 'General Ward', "initial": 'D' },
            { "id": 'DR-2025-009', "pass": 'Arjun@123', "name": 'Arjun Rao', "role": 'DOCTOR', "specialty": 'Nephrology', "dept": 'Intensive Care Unit', "initial": 'A' },
            { "id": 'DR-2025-010', "pass": 'Latha@123', "name": 'Latha Menon', "role": 'DOCTOR', "specialty": 'Gastroenterology', "dept": 'General Ward', "initial": 'L' },
            { "id": 'NR-2025-001', "pass": 'Nurse1@123', "name": 'Kavitha', "role": 'NURSE', "ward": 'ICU Wing', "initial": 'K' },
            { "id": 'NR-2025-002', "pass": 'Nurse2@123', "name": 'Deepa', "role": 'NURSE', "ward": 'Emergency Bay', "initial": 'D' },
            { "id": 'NR-2025-003', "pass": 'Nurse3@123', "name": 'Ramya', "role": 'NURSE', "ward": 'General Ward A', "initial": 'R' },
            { "id": 'NR-2025-004', "pass": 'Nurse4@123', "name": 'Suba', "role": 'NURSE', "ward": 'General Ward B', "initial": 'S' },
            { "id": 'NR-2025-005', "pass": 'Nurse5@123', "name": 'Anitha', "role": 'NURSE', "ward": 'Operating Theatre', "initial": 'A' },
            { "id": 'RC-2025-001', "pass": 'Recep1@123', "name": 'Preethi', "role": 'RECEPTIONIST', "initial": 'P' },
            { "id": 'RC-2025-002', "pass": 'Ravi@123', "name": 'Ravi', "role": 'RECEPTIONIST', "initial": 'R' },
            { "id": 'RC-2025-003', "pass": 'Recep3@123', "name": 'Suma', "role": 'RECEPTIONIST', "initial": 'S' },
            { "id": 'AM-2025-001', "pass": 'Ambu@123', "name": 'Ramesh (Paramedic)', "role": 'AMBULANCE', "initial": 'R' }
        ]

        for u in USERS_NEXUS:
            role_map = {
                "DOCTOR": "Doctor",
                "NURSE": "Nurse",
                "RECEPTIONIST": "Receptionist",
                "AMBULANCE": "Ambulance"
            }
            db_user = User(
                id=u["id"],
                username=u["id"],
                password_hash=get_password_hash(u["pass"]),
                role=role_map.get(u["role"], u["role"]),
                hospital_id=hospital.id,
                name=u["name"],
                specialty=u.get("specialty"),
                dept=u.get("dept"),
                ward=u.get("ward"),
                initial=u["initial"]
            )
            db.add(db_user)
        db.flush()

        # 5. Seed NEXUS Patients
        nexus_patients_data = [
            {
                "id": "P-024", "name": "John Doe", "age": 45, "gender": "M", "bloodGroup": "O+", 
                "diagnosis": "Tension Pneumothorax", "mechanism": "RTA", "admittedAt": 1, 
                "attendingDoctor": "DR-2025-001", "consultedDoctors": ["DR-2025-003"], "bedId": "EM-01", 
                "status": "CRITICAL", 
                "vitals": {"bp": "88/55", "spo2": 78, "gcs": 14, "hr": 134, "temp": 37.1, "rr": 32, "spco2": 52, "map": 66}, 
                "treatments": ["Decompression", "O2 Therapy"], 
                "tests": [
                    {"name": "CXR", "result": "Mediastinal shift", "unit": "", "ref": "Normal", "status": "ABNORMAL"},
                    {"name": "SpO2 trend", "result": "78%", "unit": "", "ref": ">94%", "status": "ABNORMAL"},
                    {"name": "ABG", "result": "pH 7.22, pCO2 52", "unit": "", "ref": "Normal", "status": "ABNORMAL"},
                    {"name": "ECG", "result": "Sinus tachy 134", "unit": "", "ref": "60-100", "status": "ABNORMAL"},
                    {"name": "BP", "result": "88/55", "unit": "mmHg", "ref": "120/80", "status": "ABNORMAL"}
                ],
                "aiSummary": {
                    "stage": "Critical", "trajectory": "Deteriorating quickly. Severe hypoxia and hypotension.", 
                    "priorities": ["Immediate needle decompression", "ICU admission", "Chest tube insertion"], 
                    "resources": {"icu": "Required", "vent": "Likely", "surg": "Urgent"}, 
                    "flags": ["Cardiac arrest risk"]
                },
                "med": [{"name": "Morphine", "route": "IV", "dose": "2mg", "freq": "PRN", "status": "Active"}]
            },
            { 
                "id": "P-025", "name": "Arjun Mehta", "age": 38, "gender": "M", "bloodGroup": "B+", 
                "diagnosis": "Cardiac Arrest", "mechanism": "Sudden collapse", "admittedAt": 1, 
                "attendingDoctor": "DR-2025-001", "consultedDoctors": ["DR-2025-003"], "bedId": "EM-03", 
                "status": "CRITICAL", 
                "vitals": {"bp": "70/40", "spo2": 72, "gcs": 6, "hr": 145, "temp": 37.4, "rr": 36, "spco2": 58, "map": 50}, 
                "treatments": ["CPR", "Defibrillation", "Adrenaline IV"], 
                "tests": [
                    {"name": "ECG", "result": "ST-elevation II,III,aVF", "unit": "", "ref": "Normal sinus", "status": "ABNORMAL"},
                    {"name": "Troponin I", "result": "8.4", "unit": "ng/mL", "ref": "0-0.04", "status": "ABNORMAL"},
                    {"name": "CK-MB", "result": "62", "unit": "U/L", "ref": "0-25", "status": "ABNORMAL"}
                ],
                "aiSummary": {
                    "stage": "Critical", "trajectory": "Actively resuscitating. Risk of brain death within minutes.", 
                    "priorities": ["Immediate defibrillation", "ICU transfer", "Cardiothoracic consult"], 
                    "resources": {"icu": "Required", "vent": "Required", "surg": "Urgent"}, 
                    "flags": ["Cardiac arrest", "Code Blue"]
                }, 
                "med": [{"name": "Adrenaline", "route": "IV", "dose": "1mg", "freq": "Every 3-5 min", "status": "Active"}] 
            },
            { 
                "id": "P-026", "name": "Kavya Reddy", "age": 52, "gender": "F", "bloodGroup": "O-", 
                "diagnosis": "Severe Septic Shock", "mechanism": "Post-surgical infection", "admittedAt": 2, 
                "attendingDoctor": "DR-2025-001", "consultedDoctors": ["DR-2025-002"], "bedId": "EM-04", 
                "status": "CRITICAL", 
                "vitals": {"bp": "68/42", "spo2": 82, "gcs": 9, "hr": 138, "temp": 40.1, "rr": 34, "spco2": 28, "map": 50}, 
                "treatments": ["Broad-spectrum Abx", "Vasopressors", "Fluid resus"], 
                "tests": [
                    {"name": "Blood Culture", "result": "Gram-neg rods", "unit": "", "ref": "Negative", "status": "ABNORMAL"},
                    {"name": "Lactate", "result": "4.8", "unit": "mmol/L", "ref": "<2.0", "status": "ABNORMAL"},
                    {"name": "Procalcitonin", "result": "42", "unit": "ng/mL", "ref": "<0.1", "status": "ABNORMAL"}
                ], 
                "aiSummary": { 
                    "stage": "Critical", "trajectory": "Haemodynamically unstable. Multi-organ failure risk high.", 
                    "priorities": ["Vasopressor escalation", "ICU transfer", "Source control surgery"], 
                    "resources": {"icu": "Required", "vent": "Likely", "surg": "Urgent"}, 
                    "flags": ["Multi-organ failure risk", "Septic shock"] 
                }, 
                "med": [{"name": "Norepinephrine", "route": "IV", "dose": "0.2mcg/kg/min", "freq": "Continuous", "status": "Active"}] 
            },
            { 
                "id": "P-021", "name": "Sarah Smith", "age": 32, "gender": "F", "bloodGroup": "A-", 
                "diagnosis": "Polytrauma MVA", "mechanism": "Car crash", "admittedAt": 2, 
                "attendingDoctor": "DR-2025-001", "consultedDoctors": ["DR-2025-003"], "bedId": "ICU-02", 
                "status": "CRITICAL", 
                "vitals": {"bp": "92/60", "spo2": 92, "gcs": 10, "hr": 115, "temp": 36.5, "rr": 24, "spco2": 40, "map": 70}, 
                "treatments": ["Blood Transfusion", "Pain Mgmt"], 
                "tests": [
                    {"name": "FAST US", "result": "Free fluid abd", "unit": "", "ref": "Negative", "status": "ABNORMAL"},
                    {"name": "Hgb", "result": "7.2", "unit": "g/dL", "ref": "13-17", "status": "ABNORMAL"}
                ], 
                "aiSummary": { 
                    "stage": "Critical", "trajectory": "Unstable. High risk of hypovolemic shock.", 
                    "priorities": ["Control bleeding", "Volume resuscitation", "Surgical review"], 
                    "resources": {"icu": "Required", "vent": "Not required", "surg": "Urgent"}, 
                    "flags": ["Hemorrhage"] 
                }, 
                "med": [{"name": "TXA", "route": "IV", "dose": "1g", "freq": "STAT", "status": "Active"}] 
            },
            { 
                "id": "P-023", "name": "Robert Johnson", "age": 58, "gender": "M", "bloodGroup": "B+", 
                "diagnosis": "Post-op Internal Bleeding", "mechanism": "Post-surg complication", "admittedAt": 4, 
                "attendingDoctor": "DR-2025-001", "consultedDoctors": ["DR-2025-005"], "bedId": "GB-08", 
                "status": "CRITICAL", 
                "vitals": {"bp": "74/48", "spo2": 94, "gcs": 13, "hr": 122, "temp": 37.0, "rr": 22, "spco2": 38, "map": 56}, 
                "treatments": ["Fluid Resuscitation"], 
                "tests": [
                    {"name": "Hgb", "result": "5.8", "unit": "g/dL", "ref": "13-17", "status": "ABNORMAL"},
                    {"name": "CT Abdomen", "result": "Active arterial blush", "unit": "", "ref": "Normal", "status": "ABNORMAL"}
                ], 
                "aiSummary": { 
                    "stage": "Critical", "trajectory": "Rapidly deteriorating BP.", 
                    "priorities": ["Transfusion", "Return to OT", "ICU transfer"], 
                    "resources": {"icu": "Required", "vent": "Not required", "surg": "Urgent"}, 
                    "flags": ["Shock"] 
                }, 
                "med": [{"name": "Packed RBCs", "route": "IV", "dose": "2 units", "freq": "STAT", "status": "Active"}] 
            },
            { 
                "id": "P-019", "name": "Emily Davis", "age": 65, "gender": "F", "bloodGroup": "O-", 
                "diagnosis": "Septic Shock", "mechanism": "UTI progression", "admittedAt": 12, 
                "attendingDoctor": "DR-2025-002", "consultedDoctors": [], "bedId": "ICU-01", 
                "status": "CRITICAL", 
                "vitals": {"bp": "85/50", "spo2": 90, "gcs": 11, "hr": 110, "temp": 39.2, "rr": 26, "spco2": 32, "map": 61}, 
                "treatments": ["Broad-spectrum Abx", "Vasopressors"], 
                "tests": [
                    {"name": "Lactate", "result": "4.8", "unit": "mmol/L", "ref": "<2.0", "status": "ABNORMAL"},
                    {"name": "WBC", "result": "21.4", "unit": "x10^9/L", "ref": "4-11", "status": "ABNORMAL"}
                ], 
                "aiSummary": { 
                    "stage": "Severe", "trajectory": "Stabilizing on vasopressors.", 
                    "priorities": ["Source control", "Hemodynamic monitoring", "Lactate clearance"], 
                    "resources": {"icu": "Required", "vent": "Likely", "surg": "None"}, 
                    "flags": ["Sepsis"] 
                }, 
                "med": [{"name": "Norepinephrine", "route": "IV", "dose": "0.1mcg/kg/min", "freq": "Continuous", "status": "Active"}] 
            },
            { 
                "id": "P-022", "name": "Michael Brown", "age": 28, "gender": "M", "bloodGroup": "AB+", 
                "diagnosis": "Femur fracture", "mechanism": "Fall", "admittedAt": 3, 
                "attendingDoctor": "DR-2025-001", "consultedDoctors": [], "bedId": "EM-02", 
                "status": "STABLE", 
                "vitals": {"bp": "120/80", "spo2": 98, "gcs": 15, "hr": 85, "temp": 36.8, "rr": 16, "spco2": 40, "map": 93}, 
                "treatments": ["Splinting", "Analgesia"], 
                "tests": [
                    {"name": "CBC", "result": "WBC 7.8", "unit": "", "ref": "4-11", "status": "NORMAL"},
                    {"name": "BMP", "result": "K 4.0", "unit": "", "ref": "3.5-5.0", "status": "NORMAL"}
                ], 
                "aiSummary": { 
                    "stage": "Moderate", "trajectory": "Stable awaiting surgery.", 
                    "priorities": ["Pain control", "Ortho review"], 
                    "resources": {"icu": "Not required", "vent": "Not required", "surg": "Elective"}, 
                    "flags": [] 
                }, 
                "med": [] 
            },
            { 
                "id": "P-015", "name": "William Wilson", "age": 72, "gender": "M", "bloodGroup": "A+", 
                "diagnosis": "Post-op cardiac", "mechanism": "CABG", "admittedAt": 24, 
                "attendingDoctor": "DR-2025-002", "consultedDoctors": [], "bedId": "ICU-03", 
                "status": "STABLE", 
                "vitals": {"bp": "118/75", "spo2": 96, "gcs": 15, "hr": 78, "temp": 37.1, "rr": 14, "spco2": 42, "map": 89}, 
                "treatments": ["Monitoring"], 
                "tests": [
                    {"name": "ECG", "result": "Normal sinus", "unit": "", "ref": "Normal", "status": "NORMAL"}
                ], 
                "aiSummary": { 
                    "stage": "Moderate", "trajectory": "Recovering well.", 
                    "priorities": ["Wean sedation", "Extubation trial"], 
                    "resources": {"icu": "Required", "vent": "Not required", "surg": "None"}, 
                    "flags": [] 
                }, 
                "med": [] 
            }
        ]

        for p_data in nexus_patients_data:
            patient = Patient(
                id=p_data["id"],
                name_encrypted=p_data["name"],
                triage_level=1 if p_data["status"] == "CRITICAL" else 3,
                status=p_data["status"],
                clinical_data_json=json.dumps({"summary": p_data["diagnosis"]}),
                name=p_data["name"],
                age=p_data["age"],
                gender=p_data["gender"],
                bloodGroup=p_data["bloodGroup"],
                diagnosis=p_data["diagnosis"],
                mechanism=p_data["mechanism"],
                admittedAt=p_data["admittedAt"],
                attendingDoctor=p_data["attendingDoctor"],
                consultedDoctors=json.dumps(p_data["consultedDoctors"]),
                bedId=p_data["bedId"],
                vitals=json.dumps(p_data["vitals"]),
                treatments=json.dumps(p_data["treatments"]),
                tests=json.dumps(p_data["tests"]),
                aiSummary=json.dumps(p_data["aiSummary"]),
                med=json.dumps(p_data["med"]),
                notes=None
            )
            db.add(patient)
        db.flush()

        # 6. Seed NEXUS Beds
        beds_list = []
        for i in range(1, 9):
            beds_list.append({"id": f"ICU-0{i}", "zone": "ICU"})
        for i in range(1, 5):
            beds_list.append({"id": f"EM-0{i}", "zone": "EM"})
        for i in range(1, 13):
            beds_list.append({"id": f"GA-{str(i).zfill(2)}", "zone": "GA"})
        for i in range(1, 17):
            beds_list.append({"id": f"GB-{str(i).zfill(2)}", "zone": "GB"})
        for i in range(1, 5):
            beds_list.append({"id": f"OT-0{i}", "zone": "OT"})

        for b_info in beds_list:
            assigned_patient = next((p for p in nexus_patients_data if p["bedId"] == b_info["id"]), None)
            bed = Bed(
                id=b_info["id"],
                zone=b_info["zone"],
                status=assigned_patient["status"] if assigned_patient else "AVAILABLE",
                patientId=assigned_patient["id"] if assigned_patient else None
            )
            db.add(bed)
        db.flush()

        # 7. Seed NEXUS Ventilators
        vent_data = {
            'VENT-01': { "status": 'OCCUPIED', "assignedTo": 'P-019', "location": 'ICU-01' },
            'VENT-02': { "status": 'OCCUPIED', "assignedTo": 'P-021', "location": 'ICU-02' },
            'VENT-03': { "status": 'OCCUPIED', "assignedTo": 'P-003', "location": 'OT-02' },
            'VENT-04': { "status": 'AVAILABLE', "assignedTo": None, "location": 'Storage' },
            'VENT-05': { "status": 'AVAILABLE', "assignedTo": None, "location": 'Storage' },
            'VENT-06': { "status": 'AVAILABLE', "assignedTo": None, "location": 'Storage' },
            'VENT-07': { "status": 'AVAILABLE', "assignedTo": None, "location": 'Storage' },
            'VENT-08': { "status": 'AVAILABLE', "assignedTo": None, "location": 'Storage' },
            'VENT-09': { "status": 'AVAILABLE', "assignedTo": None, "location": 'Storage' },
            'VENT-10': { "status": 'AVAILABLE', "assignedTo": None, "location": 'Storage' }
        }
        for v_id, v_info in vent_data.items():
            vent = Ventilator(
                id=v_id,
                status=v_info["status"],
                assignedTo=v_info["assignedTo"],
                location=v_info["location"]
            )
            db.add(vent)

        # Seed initial notifications
        notifications = [
            Notification(role="Doctor", text="Critical intake alert: Inbound patient P-024 (Tension Pneumothorax) needs urgent review.", severity="critical"),
            Notification(role="Nurse", text="Bed Assignment update: Patient Sarah Smith (P-021) assigned to bed ICU-02.", severity="info"),
            Notification(role="Receptionist", text="Discharge checklist ready for patient William Wilson (P-015).", severity="warning"),
            Notification(role="Administrator", text="System Diagnostics: Connected successfully to database backup.", severity="info")
        ]
        for n in notifications:
            db.add(n)
 
        db.commit()
        print("Database seeded successfully with Hospital, Users, and Resource Inventory.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
