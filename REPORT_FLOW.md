# Report Generation Flow - Diabetes Prediction System

## Overview
This document describes who generates reports, why they need them, and how they link to the database.

---

## 1. PATIENT REPORTS (Personal Health Summary)

### Who Creates It?
**Patient** (from their dashboard)

### Why?
- Track personal diabetes risk over time
- Share health history with doctors
- Monitor treatment effectiveness
- Download for insurance/medical records

### Endpoint
```
GET /api/patient/report
```

### Data Sources (Database Links)
```sql
-- Patient Info
SELECT * FROM users WHERE id = patient_id
SELECT * FROM patients WHERE id = patient_id

-- Health Records
SELECT * FROM health_records WHERE patient_id = ? ORDER BY created_at DESC

-- ML Predictions
SELECT * FROM predictions WHERE patient_id = ? ORDER BY created_at DESC

-- Prescriptions
SELECT p.*, u.username as doctor_name 
FROM prescriptions p 
LEFT JOIN users u ON p.doctor_id = u.id 
WHERE p.patient_id = ?

-- Lab Results
SELECT l.*, u.username as doctor_name 
FROM lab_tests l 
LEFT JOIN users u ON l.doctor_id = u.id 
WHERE l.patient_id = ?

-- Appointments
SELECT a.*, u.username as doctor_name 
FROM appointments a 
LEFT JOIN users u ON a.doctor_id = u.id 
WHERE a.patient_id = ?
```

### Report Contents
1. **Personal Info**: Name, Patient ID, Blood Group, Contact
2. **Health Trends**: Glucose, BMI, Blood Pressure over time (charts)
3. **Risk Assessment**: All ML predictions with risk levels
4. **Medications**: All prescriptions (active and past)
5. **Lab Results**: All test results with normal ranges
6. **Appointments**: Past and upcoming appointments
7. **Recommendations**: Based on latest risk level

### Output Formats
- JSON (for web display)
- PDF (downloadable)
- CSV (for data analysis)

---

## 2. DOCTOR REPORTS (Clinical Summary)

### Who Creates It?
**Doctor** (for specific patient)

### Why?
- Clinical decision-making
- Treatment planning
- Referral documentation
- Medical-legal records

### Endpoint
```
GET /api/doctor/patients/<patient_id>/report
```

### Data Sources
```sql
-- Patient Demographics
SELECT u.*, p.* 
FROM users u 
JOIN patients p ON u.id = p.id 
WHERE u.id = ?

-- Vital Signs (from Nurse)
SELECT v.*, u.username as nurse_name 
FROM vital_signs v 
LEFT JOIN users u ON v.nurse_id = u.id 
WHERE v.patient_id = ?

-- Health Records
SELECT * FROM health_records WHERE patient_id = ?

-- ML Predictions
SELECT * FROM predictions WHERE patient_id = ?

-- Lab Tests (ordered by this doctor)
SELECT * FROM lab_tests 
WHERE patient_id = ? AND doctor_id = ?

-- Prescriptions (written by this doctor)
SELECT * FROM prescriptions 
WHERE patient_id = ? AND doctor_id = ?

-- Doctor's Notes
SELECT * FROM notes 
WHERE patient_id = ? AND doctor_id = ?
```

### Report Contents
1. **Patient Summary**: Demographics, medical history, allergies
2. **Vital Signs**: Temperature, BP, Heart Rate trends
3. **Health Metrics**: Glucose, BMI, Insulin levels
4. **Risk Assessment**: ML predictions with interpretations
5. **Lab Results**: All test results with abnormal flags
6. **Current Medications**: Active prescriptions
7. **Clinical Notes**: Doctor's observations
8. **Treatment Plan**: Recommendations and follow-up

---

## 3. LAB REPORTS (Test Results)

### Who Creates It?
**Lab Technician** (for each test)

### Why?
- Official test results documentation
- Doctor review and diagnosis
- Patient medical records
- Quality assurance

### Endpoint
```
GET /api/labs/results/<test_id>/report
```

### Data Sources
```sql
-- Test Details
SELECT l.*, 
       p.username as patient_name, p.patient_id,
       d.username as doctor_name, d.doctor_id,
       t.username as tech_name, t.technician_id
FROM lab_tests l
LEFT JOIN users p ON l.patient_id = p.id
LEFT JOIN users d ON l.doctor_id = d.id
LEFT JOIN users t ON l.technician_id = t.id
WHERE l.id = ?

-- Test Type Info
SELECT * FROM test_types WHERE test_code = ?
```

### Report Contents
1. **Lab Header**: Lab name, address, accreditation
2. **Patient Info**: Name, Age, Gender, Patient ID
3. **Test Details**: Test name, type, category, priority
4. **Results**: Values, Units, Normal Range
5. **Abnormal Flags**: Highlighted if outside normal range
6. **Technician Info**: Who performed the test
7. **Validation**: Who validated results, when
8. **Doctor Info**: Who ordered the test
9. **Remarks**: Clinical notes

### Output Format
- PDF (official lab report)
- Sent to: Patient, Doctor, System

---

## 4. PHARMACIST REPORTS (Dispensing Records)

### Who Creates It?
**Pharmacist** (daily/monthly)

### Why?
- Track medication dispensing
- Inventory management
- Audit trail
- Revenue tracking

### Endpoint
```
GET /api/pharmacy/reports/dispensing?start_date=&end_date=
```

### Data Sources
```sql
-- Dispensed Prescriptions
SELECT p.*, 
       pat.username as patient_name,
       doc.username as doctor_name,
       ph.username as pharmacist_name
FROM prescriptions p
LEFT JOIN users pat ON p.patient_id = pat.id
LEFT JOIN users doc ON p.doctor_id = doc.id
LEFT JOIN users ph ON p.dispensed_by = ph.id
WHERE p.status = 'dispensed'
  AND p.dispensed_at BETWEEN ? AND ?

-- Inventory Changes
SELECT * FROM medicine_inventory 
WHERE updated_at BETWEEN ? AND ?

-- Revenue (if tracked)
SELECT SUM(cost) FROM prescriptions 
WHERE status = 'dispensed' 
  AND dispensed_at BETWEEN ? AND ?
```

### Report Contents
1. **Summary**: Total prescriptions dispensed, patients served
2. **Medications**: List of all medications dispensed
3. **Inventory Usage**: Stock deducted per medication
4. **Doctors**: Prescriptions by doctor
5. **Revenue**: Total sales (if prices tracked)
6. **Low Stock Alerts**: Items below minimum stock

---

## 5. NURSE REPORTS (Daily Activity)

### Who Creates It?
**Nurse** (end of shift)

### Why?
- Track daily patient care
- Vital signs monitoring
- Queue management
- Handover to next shift

### Endpoint
```
GET /api/nurse/reports/daily?date=
```

### Data Sources
```sql
-- Patients Registered
SELECT COUNT(*) FROM patients 
WHERE registered_by = ? 
  AND DATE(created_at) = ?

-- Vital Signs Recorded
SELECT v.*, u.username as patient_name 
FROM vital_signs v
LEFT JOIN users u ON v.patient_id = u.id
WHERE v.nurse_id = ? 
  AND DATE(v.recorded_at) = ?

-- Queue Statistics
SELECT * FROM patient_queue 
WHERE nurse_id = ? 
  AND DATE(check_in_time) = ?

-- Critical Alerts
SELECT * FROM vital_signs 
WHERE nurse_id = ?
  AND DATE(recorded_at) = ?
  AND (temperature > 39 OR blood_pressure_systolic > 180 OR oxygen_saturation < 90)
```

### Report Contents
1. **Patients Registered**: Count and names
2. **Vital Signs**: Total recorded, critical alerts
3. **Queue Stats**: Patients seen, average wait time
4. **Critical Cases**: Abnormal vital signs
5. **Predictions Reviewed**: ML results checked

---

## 6. ADMIN REPORTS (System-Wide)

### Who Creates It?
**Admin** (weekly/monthly)

### Why?
- System performance monitoring
- Resource allocation
- Strategic planning
- Compliance reporting

### Endpoint
```
GET /api/admin/reports/system?start_date=&end_date=
```

### Data Sources
```sql
-- User Statistics
SELECT role, COUNT(*) FROM users GROUP BY role

-- Prediction Statistics
SELECT risk_level, COUNT(*) FROM predictions GROUP BY risk_level

-- Prescription Statistics
SELECT status, COUNT(*) FROM prescriptions GROUP BY status

-- Lab Test Statistics
SELECT status, COUNT(*) FROM lab_tests GROUP BY status

-- Appointment Statistics
SELECT status, COUNT(*) FROM appointments GROUP BY status

-- Revenue (if tracked)
SELECT SUM(amount) FROM payments WHERE DATE(created_at) BETWEEN ? AND ?

-- Activity Logs
SELECT action, COUNT(*) FROM audit_logs 
WHERE DATE(created_at) BETWEEN ? AND ?
GROUP BY action
```

### Report Contents
1. **User Statistics**: Total users by role
2. **Prediction Analytics**: Risk distribution, trends
3. **Prescription Metrics**: Pending, verified, dispensed
4. **Lab Test Metrics**: Pending, completed, turnaround time
5. **Appointment Metrics**: Scheduled, completed, no-shows
6. **Revenue**: Total payments, outstanding invoices
7. **System Activity**: Logins, predictions, prescriptions per day
8. **ML Model Performance**: Accuracy, predictions count

---

## Report Generation Workflow

```
User Request → Backend Route → Database Queries → Report Service → Format Output
     ↓              ↓                  ↓                  ↓              ↓
  Patient      patient_bp.py    health_records    ReportService    JSON/PDF
  Doctor       doctor_bp.py     prescriptions     format_data()    Download
  Lab Tech     lab_bp.py        lab_tests         generate_pdf()   Email
  Pharmacist   pharmacist_bp.py medicine_inv      export_csv()     Print
  Nurse        nurse_bp.py      vital_signs       
  Admin        admin_bp.py      all_tables        
```

---

## Database Relationships for Reports

```
PATIENT REPORT:
  users → patients → health_records
                  → predictions
                  → prescriptions → doctors
                  → lab_tests → doctors
                  → appointments → doctors

DOCTOR REPORT:
  patients → health_records
          → predictions
          → vital_signs → nurses
          → lab_tests (doctor_id)
          → prescriptions (doctor_id)
          → notes (doctor_id)

LAB REPORT:
  lab_tests → patients
           → doctors
           → lab_technicians
           → test_types

PHARMACIST REPORT:
  prescriptions (status=dispensed) → patients
                                   → doctors
                                   → pharmacists
  medicine_inventory (quantity changes)

NURSE REPORT:
  vital_signs (nurse_id) → patients
  patient_queue (nurse_id)
  patients (registered_by=nurse_id)

ADMIN REPORT:
  users (all roles)
  predictions (all)
  prescriptions (all)
  lab_tests (all)
  appointments (all)
  payments (all)
  audit_logs (all)
```

---

## Implementation Status

✅ **Completed:**
- Patient report endpoint (`GET /api/patient/report`)
- Admin system report endpoint (`GET /api/admin/reports/system`)
- Report service (`backend/services/report_service.py`)

⏳ **To Implement:**
- Doctor patient report endpoint
- Lab test report PDF generation
- Pharmacist dispensing report
- Nurse daily activity report
- CSV/PDF export functionality
- Email report delivery
- Scheduled report generation

---

## Next Steps

1. Add missing report endpoints to each role's routes
2. Implement PDF generation using `reportlab` or `weasyprint`
3. Add CSV export functionality
4. Create report templates (HTML/PDF)
5. Add email delivery for reports
6. Implement scheduled reports (cron jobs)
7. Add report history/archive
8. Create report dashboard for admins
