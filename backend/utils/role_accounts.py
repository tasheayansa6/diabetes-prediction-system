"""
Create polymorphic User subclasses (Patient, Doctor, Admin, …) — single place for
public registration and admin-provisioned accounts.
"""
from datetime import datetime

from backend.models.patient import Patient
from backend.models.doctor import Doctor
from backend.models.nurse import Nurse
from backend.models.lab_technician import LabTechnician
from backend.models.pharmacist import Pharmacist
from backend.models.admin import Admin


def create_polymorphic_user(data, password_hash, role):
    """
    Build and return an ORM user instance (not yet added to session).
    role: lowercase string.
    data: dict with username, email, full_name (required), and role-specific fields.
    
    Required fields:
    - username: Unique username
    - email: Unique email address
    - full_name: User's full name (required for all roles)
    - role: User role (patient, doctor, nurse, etc.)
    
    Optional role-specific unique IDs:
    - patient_id, doctor_id, nurse_id, technician_id, pharmacist_id, admin_id
    If not provided, auto-generated IDs will be created.
    """
    role = (role or "").lower().strip()
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    
    # Full name is now REQUIRED for all roles
    full_name = (data.get("full_name") or "").strip()
    if not full_name:
        # Fallback: use username if full_name not provided (for backward compatibility)
        full_name = username
    
    # Generate unique ID prefix based on role
    ID_PREFIXES = {
        'patient': 'PAT',
        'doctor': 'DOC',
        'nurse': 'NUR',
        'lab_technician': 'LAB',
        'pharmacist': 'PHR',
        'admin': 'ADM'
    }

    if role == "patient":
        return Patient(
            username=username,
            email=email,
            password_hash=password_hash,
            role="patient",
            full_name=full_name,
            patient_id=data.get("patient_id") or f"PAT{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            blood_group=data.get("blood_group"),
            emergency_contact=data.get("emergency_contact"),
            emergency_contact_name=data.get("emergency_contact_name"),
            created_at=datetime.utcnow(),
            is_active=True,
            email_verified=False,
        )

    if role == "doctor":
        return Doctor(
            username=username,
            email=email,
            password_hash=password_hash,
            role="doctor",
            full_name=full_name,
            doctor_id=data.get("doctor_id") or f"DOC{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            specialization=data.get("specialization"),
            qualification=data.get("qualification"),
            license_number=data.get("license_number"),
            years_of_experience=data.get("years_of_experience"),
            created_at=datetime.utcnow(),
            is_active=True,
            email_verified=False,
        )

    if role == "nurse":
        return Nurse(
            username=username,
            email=email,
            password_hash=password_hash,
            role="nurse",
            full_name=full_name,
            nurse_id=data.get("nurse_id") or f"NUR{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            department=data.get("department"),
            shift=data.get("shift"),
            qualification=data.get("qualification"),
            license_number=data.get("license_number"),
            created_at=datetime.utcnow(),
            is_active=True,
            email_verified=False,
        )

    if role == "lab_technician":
        return LabTechnician(
            username=username,
            email=email,
            password_hash=password_hash,
            role="lab_technician",
            full_name=full_name,
            technician_id=data.get("technician_id") or f"LAB{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            qualification=data.get("qualification"),
            license_number=data.get("license_number"),
            specialization=data.get("specialization"),
            created_at=datetime.utcnow(),
            is_active=True,
            email_verified=False,
        )

    if role == "pharmacist":
        return Pharmacist(
            username=username,
            email=email,
            password_hash=password_hash,
            role="pharmacist",
            full_name=full_name,
            pharmacist_id=data.get("pharmacist_id") or f"PHR{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            license_number=data.get("license_number"),
            created_at=datetime.utcnow(),
            is_active=True,
            email_verified=False,
        )

    if role == "admin":
        return Admin(
            username=username,
            email=email,
            password_hash=password_hash,
            role="admin",
            full_name=full_name,
            admin_id=data.get("admin_id") or f"ADM{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            created_at=datetime.utcnow(),
            is_active=True,
            email_verified=False,
        )

    return None
