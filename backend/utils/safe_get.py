"""
safe_get.py - Safe ORM helpers that avoid SQLAlchemy polymorphic mapper crashes.

When Patient.query.get(id) is called with an ID belonging to a different role
(e.g. a Nurse), SQLAlchemy throws a polymorphic discriminator error.
These helpers catch that and fall back to User.query.get() safely.
"""
from backend.models.user import User


def safe_get_patient(patient_id):
    if not patient_id:
        return None
    try:
        from backend.models.patient import Patient
        return Patient.query.get(patient_id)
    except Exception:
        u = User.query.get(patient_id)
        return u if u and u.role == 'patient' else None


def safe_get_doctor(doctor_id):
    if not doctor_id:
        return None
    try:
        from backend.models.doctor import Doctor
        return Doctor.query.get(doctor_id)
    except Exception:
        u = User.query.get(doctor_id)
        return u if u and u.role == 'doctor' else None


def safe_get_nurse(nurse_id):
    if not nurse_id:
        return None
    try:
        from backend.models.nurse import Nurse
        return Nurse.query.get(nurse_id)
    except Exception:
        u = User.query.get(nurse_id)
        return u if u and u.role == 'nurse' else None


def safe_get_lab_tech(tech_id):
    if not tech_id:
        return None
    try:
        from backend.models.lab_technician import LabTechnician
        return LabTechnician.query.get(tech_id)
    except Exception:
        u = User.query.get(tech_id)
        return u if u and u.role == 'lab_technician' else None


def safe_get_user(user_id):
    """Return any User regardless of role. Always safe."""
    if not user_id:
        return None
    return User.query.get(user_id)
