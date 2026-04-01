# Web-Based Diabetes Prediction System
### Frontend Documentation — Summary

---

## 1. Project Overview

A multi-role, web-based clinical platform for early diabetes detection using machine learning. Patients submit health data and receive an AI-generated risk prediction. The result feeds into a full clinical workflow involving doctors, nurses, lab technicians, pharmacists, and administrators — all connected through a single frontend system.

**Technology Stack**
- HTML5, CSS3, Vanilla JavaScript
- Bootstrap 5.3 (UI framework)
- Bootstrap Icons 1.10
- Chart.js (local vendor, offline-capable)
- No backend dependency — pure frontend with simulated data

---

## 2. System Goal

Solve the problem of late diabetes detection and fragmented clinical workflows by providing:
- Instant ML-based diabetes risk prediction for patients
- Integrated clinical management for all healthcare roles
- A single digital loop from screening → diagnosis → lab → pharmacy → payment

---

## 3. User Roles & Capabilities

| Role | Key Capabilities |
|---|---|
| Patient | Submit health data, view prediction results, view prescriptions, download reports, make payments |
| Doctor | View patient list, write diagnosis, create prescriptions, request lab tests |
| Nurse | Record vitals, enter clinical measurements, view prediction outcomes |
| Lab Technician | Manage test types, enter lab results, generate lab reports |
| Pharmacist | Review prescriptions, check/approve/dispense medications |
| Administrator | Manage users & roles, upload/activate ML models, generate system reports |

---

## 4. System Flow

```
Patient registers → submits health data → ML prediction generated
        ↓
Doctor reviews prediction → diagnoses → prescribes → requests lab tests
        ↓
Nurse records vitals → monitors patient
        ↓
Lab Technician processes test → enters results → generates report
        ↓
Pharmacist reviews prescription → approves → dispenses medication
        ↓
Patient pays (TeleBirr / CBE Birr / M-Birr / Amole / Cash / Insurance / PayPal)
        ↓
Admin oversees all activity → manages users, ML models, reports
```

---

## 5. Modules & Pages

### Authentication
- `login.html` — Login with role-based redirect
- `register.html` — New user registration
- `forgot-password.html` — Request password reset
- `reset-password.html` — Set new password via token
- `verify-email.html` — Email verification

### Patient (`templates/patient/`)
- `dashboard.html` — Stats, charts, quick actions
- `health_data_form.html` — Submit glucose, BMI, age, BP, insulin
- `prediction_result.html` — 4-level risk bar, confidence arc, breakdown
- `prediction_history.html` — All past predictions
- `prescriptions.html` — View doctor prescriptions
- `profile.html` — Update personal info
- `report_download.html` — Download medical reports

### Doctor (`templates/doctor/`)
- `dashboard.html` — Patient stats, appointments, high-risk list
- `patient_list.html` — All assigned patients
- `diagnosis.html` — Write clinical diagnosis
- `prescribe_medication.html` — Create prescriptions
- `lab_requests.html` — Request lab tests

### Nurse (`templates/nurse/`)
- `dashboard.html` — Activity stats, recent measurements
- `record_vitals.html` — Record BP, HR, temperature
- `clinical_measurement.html` — Enter clinical data
- `view_predictions.html` — Monitor patient predictions

### Lab Technician (`templates/lab/`)
- `dashboard.html` — Pending/completed tests, charts
- `enter_lab_results.html` — Enter test results
- `add_test_type.html` — Define new test types
- `lab_test_service.html` — Manage test services
- `lab_report.html` — Generate and view reports

### Pharmacist (`templates/pharmacist/`)
- `dashboard.html` — Pending prescriptions, dispensed stats
- `prescription_review.html` — Review incoming prescriptions
- `check_medication.html` — Check medication availability
- `approve_medication.html` — Approve for dispensing
- `dispense_medication.html` — Mark as dispensed

### Admin (`templates/admin/`)
- `dashboard.html` — System stats, user growth charts
- `manage_users.html` — Create/edit/delete users
- `manage_roles.html` — Assign and configure roles
- `manage_models.html` — Upload, activate, archive ML models
- `system_reports.html` — Generate system-wide reports

### Payment (`templates/payment/`)
- `payment_page.html` — Select service and payment method
- `payment_success.html` — Confirmation with reference number
- `payment_failed.html` — Failure with retry option
- `payment_history.html` — All past transactions
- `invoice.html` — Printable invoice

---

## 6. Payment System

**Services & Pricing (USD + 8% tax)**
| Service | Base Price |
|---|---|
| Diabetes Prediction | $45.00 |
| Doctor Consultation | $50.00 |
| Lab Test | $75.00 |
| Medication | $50.00 |

**Supported Payment Methods (Ethiopian-localized)**
- TeleBirr
- CBE Birr
- M-Birr
- Amole (Dashen Bank)
- Bank Transfer
- Cash (with cashier reference)
- Insurance (7 Ethiopian providers)
- PayPal (simulated redirect)

---

## 7. Prediction Result System

The ML prediction returns one of 4 risk levels:

| Level | Confidence | Color |
|---|---|---|
| Low Risk | ~20% | Green |
| Moderate Risk | ~38% | Yellow |
| Medium Risk | ~63% | Orange |
| High Risk | ~85% | Red |

Result page shows: 4-segment risk bar, SVG confidence arc, factor breakdown boxes (glucose, BMI, age, blood pressure, insulin).

---

## 8. Notification System

A shared notification bell is present in all 6 dashboard navbars.

**Features**
- Bell icon with red unread count badge
- Click to open dropdown with role-specific alerts
- Colored icon per notification type
- Click to mark individual notification as read
- "Mark all read" button
- Closes on outside click

**Role-specific notifications**
- Patient: prescription ready, prediction complete, payment confirmed, lab results
- Doctor: high-risk patient alert, lab results ready, new patient assigned
- Nurse: new patient waiting, abnormal vitals alert
- Lab Tech: new lab test requests from doctors
- Pharmacist: new prescriptions to review
- Admin: new registrations, ML model alerts, security notices

**Files:** `static/js/notifications.js`, `static/css/notifications.css`

---

## 9. Key Technical Decisions

| Decision | Reason |
|---|---|
| Pure frontend (no backend) | Portable, demo-ready, no server setup required |
| Chart.js loaded locally | Works offline after first load |
| Role-based simulated data | Each role sees realistic, context-appropriate data |
| Ethiopian payment methods | Localized for target deployment context |
| Relative CSS/JS paths | Avoids broken links when served from file system |
| Shared `notifications.js` | Single file maintains consistency across all 6 dashboards |
| `dashboard-common.css` | Shared layout rules (sidebar, navbar, stat cards) |

---

## 10. File Structure

```
frontend/
├── index.html                  Landing page
├── login.html
├── register.html
├── forgot-password.html
├── reset-password.html
├── verify-email.html
├── 404.html
├── static/
│   ├── css/
│   │   ├── base.css
│   │   ├── home.css
│   │   ├── login.css
│   │   ├── register.css
│   │   ├── password-recovery.css
│   │   ├── notifications.css
│   │   ├── dashboard-common.css
│   │   ├── *_dashboard.css     (6 role dashboards)
│   │   ├── admin/              (5 page-specific CSS)
│   │   ├── doctor/             (5 page-specific CSS)
│   │   ├── nurse/              (4 page-specific CSS)
│   │   ├── lab/                (5 page-specific CSS)
│   │   ├── pharmacist/         (5 page-specific CSS)
│   │   ├── patient/            (6 page-specific CSS)
│   │   └── payment/            (6 page-specific CSS)
│   └── js/
│       ├── auth.js
│       ├── notifications.js
│       ├── index.js
│       ├── login.js / register.js
│       ├── forgot-password.js / reset-password.js / verify-email.js
│       ├── admin-*.js          (5 files)
│       ├── doctor-*.js         (5 files)
│       ├── nurse-*.js          (4 files)
│       ├── lab-*.js            (5 files)
│       ├── pharmacist-*.js     (5 files)
│       ├── patient-*.js        (7 files)
│       ├── payment-*.js        (6 files)
│       └── vendor/
│           └── chart.min.js
└── templates/
    ├── admin/                  (5 pages)
    ├── doctor/                 (5 pages)
    ├── nurse/                  (4 pages)
    ├── lab/                    (5 pages)
    ├── pharmacist/             (5 pages)
    ├── patient/                (7 pages)
    └── payment/                (5 pages)
```

---

## 11. Design System

- Primary color: `#1e3a8a` (dark blue) — dashboards, headers
- Accent color: `#2563eb` / `#3b82f6` — buttons, links, highlights
- Landing page navbar: `#0f172a` (very dark navy)
- Background: `#f8fafc` (light gray) for content areas
- Font: Bootstrap default (system font stack)
- All dashboards share the same navbar, sidebar, stat card, and footer pattern

---

*Last updated: March 2026*
