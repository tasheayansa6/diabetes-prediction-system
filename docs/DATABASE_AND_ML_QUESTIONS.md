# Database & ML Model — Exam Questions & Answers
### Diabetes Prediction System — Viva / Defense Preparation

---

# PART A: DATABASE QUESTIONS

---

## SECTION 1: DATABASE DESIGN

**Q1. What database did you use and why?**

We use **SQLite** for development and **PostgreSQL** for production.

- **SQLite** — lightweight, file-based, zero configuration, perfect for development and testing. The database file is at `database/diabetes.db`.
- **PostgreSQL** — production-grade, supports concurrent connections, ACID compliant, used on Render cloud deployment.

The application uses **SQLAlchemy ORM** (Object Relational Mapper) with **Flask-Migrate** (Alembic) for schema migrations, so switching between SQLite and PostgreSQL requires only changing the `DATABASE_URL` environment variable.

---

**Q2. How many tables does your database have? List them.**

The database has **22 tables**:

| Table | Purpose |
|-------|---------|
| `users` | Base table for all users (polymorphic inheritance) |
| `patients` | Patient-specific data (extends users) |
| `doctors` | Doctor-specific data (extends users) |
| `nurses` | Nurse-specific data (extends users) |
| `lab_technicians` | Lab tech data (extends users) |
| `pharmacists` | Pharmacist data (extends users) |
| `admins` | Admin data (extends users) |
| `health_records` | Patient health measurements (8 ML features) |
| `predictions` | ML prediction results |
| `vital_signs` | Nurse-recorded vitals (BP, BMI, temperature, etc.) |
| `appointments` | Patient-doctor appointments |
| `prescriptions` | Doctor prescriptions |
| `lab_tests` | Lab test orders and results |
| `test_types` | Available lab test types |
| `payments` | Payment records (Chapa, cash, insurance) |
| `invoices` | Payment invoices |
| `notifications` | In-app notifications |
| `audit_logs` | Security and action audit trail |
| `notes` | Doctor clinical notes |
| `patient_queue` | Nurse waiting queue |
| `medicine_inventory` | Pharmacy medication stock |
| `subscriptions` | Service subscriptions |

---

**Q3. Explain your database design pattern for users.**

We use **Single Table Inheritance (STI) / Joined Table Inheritance (JTI)** via SQLAlchemy's polymorphic mapping.

The `users` table is the **base table** with common fields:
- `id`, `username`, `email`, `password_hash`, `role`, `is_active`, `created_at`

Each role has its own **child table** that extends users:
- `patients` table has `patient_id`, `blood_group`, `medical_history`, `allergies`
- `doctors` table has `doctor_id`, `specialization`, `license_number`
- `nurses` table has `nurse_id`, `department`

The `type` column in `users` is the **discriminator** — SQLAlchemy uses it to determine which child class to instantiate.

**Why this design?**
- Single authentication system (all roles log in through `users`)
- Role-specific data is cleanly separated
- Queries can target all users or specific roles
- Foreign keys from other tables point to `users.id` or role-specific tables

---

**Q4. What is the relationship between health_records and predictions?**

```
patients (1) ──── (many) health_records
health_records (1) ──── (many) predictions
patients (1) ──── (many) predictions
```

- A **patient** can have many **health records** (one per visit/day)
- Each **health record** stores the 8 ML input features (glucose, BMI, etc.)
- A **prediction** is linked to both the patient AND the health record that generated it
- The `predictions.input_data` column (JSON) also stores a snapshot of the input for audit purposes

**Key columns in `predictions`:**
```
id, patient_id, health_record_id, prediction (0/1),
probability, probability_percent, risk_level,
model_version, input_data (JSON), created_at
```

---

**Q5. How does the payment system link to predictions?**

The `payments` table has a critical field: `prediction_consumed` (BOOLEAN).

Flow:
1. Patient pays → `payment_status = 'pending'` or `'completed'`
2. Before prediction runs → check for `completed` payment with `prediction_consumed = False`
3. Prediction runs successfully → `prediction_consumed = True`

This ensures **one payment = one prediction**. A patient cannot run multiple predictions on a single payment.

**Special rules:**
- **Chapa**: `completed` OR `pending` within 2 hours (webhook delay)
- **Cash/Insurance**: ONLY `completed` (admin must manually approve)

---

**Q6. What is the purpose of the audit_logs table?**

The `audit_logs` table records **every significant action** in the system for HIPAA compliance:

```
id, action, resource, resource_id, description,
ip_address, status, created_at, user_id
```

It is used for:
1. **Security events** — login, logout, failed login, token blacklist
2. **OTP storage** — `action='otp_store'`, `resource=email`, `description=otp|username`
3. **Password reset tokens** — `action='reset_store'`
4. **Token blacklist** — `action='token_blacklist'` (logout invalidation)
5. **Prediction audit** — who ran what prediction, when, from which IP

This provides a complete, immutable audit trail required by healthcare regulations.

---

**Q7. How do you prevent SQL injection in your application?**

We use **SQLAlchemy ORM** which uses **parameterized queries** by default. All database operations go through the ORM:

```python
# Safe — SQLAlchemy parameterizes automatically
user = User.query.filter_by(email=email).first()

# When raw SQL is needed — use text() with bound parameters
result = db.session.execute(
    text("SELECT username FROM users WHERE id = :id"),
    {"id": user_id}
)
```

We never use string concatenation to build SQL queries. This completely prevents SQL injection.

---

**Q8. What is database normalization and how is your database normalized?**

Normalization eliminates data redundancy and ensures data integrity.

**Our database follows 3NF (Third Normal Form):**

- **1NF** — All columns have atomic values. No repeating groups. Each table has a primary key.
- **2NF** — No partial dependencies. All non-key columns depend on the full primary key.
- **3NF** — No transitive dependencies. Patient data is in `patients`, not duplicated in `predictions`.

**Example of normalization:**
- Patient name is stored ONCE in `users.username`
- `predictions` stores `patient_id` (FK) — not the patient name
- `appointments` stores `doctor_id` (FK) — not the doctor name
- When displaying, we JOIN tables to get the name

---

**Q9. What are foreign keys and how do you use them?**

A **foreign key** is a column that references the primary key of another table, enforcing referential integrity.

**Examples in our database:**
```
patients.id          → users.id          (patient IS a user)
predictions.patient_id → patients.id     (prediction belongs to patient)
predictions.health_record_id → health_records.id
vital_signs.patient_id → users.id
vital_signs.nurse_id   → nurses.id
appointments.patient_id → patients.id
appointments.doctor_id  → doctors.id
payments.patient_id    → patients.id
```

**Why important:**
- Cannot create a prediction for a non-existent patient
- Deleting a patient cascades to delete their predictions, health records, etc.
- Ensures data consistency across all tables

---

**Q10. How do you handle database migrations?**

We use **Flask-Migrate** (built on Alembic) for schema migrations:

```bash
flask db init      # Initialize migrations folder
flask db migrate   # Auto-detect schema changes, generate migration script
flask db upgrade   # Apply migrations to database
flask db downgrade # Roll back last migration
```

Migration files are stored in `migrations/versions/` and tracked in Git. This allows:
- Safe schema changes in production without data loss
- Version control of database schema
- Rollback if a migration causes issues

---

**Q11. What is the patient_queue table and how does it work?**

The `patient_queue` table manages the **nurse waiting list**:

```
queue_id, patient_id, nurse_id, queue_number,
priority (0=Normal, 1=Urgent, 2=Emergency),
status (waiting/called/in_progress/completed),
purpose, check_in_time, created_at
```

**Flow:**
1. Patient registers → automatically added to queue with `status='waiting'`
2. Nurse dashboard shows all waiting patients ordered by priority then queue number
3. Nurse records vitals → queue entry updated to `status='completed'`
4. Patient disappears from waiting list

**Priority levels:**
- 0 = Normal (green)
- 1 = Urgent (orange)
- 2 = Emergency (red)

---

**Q12. How is sensitive patient data protected in the database?**

Three layers of protection:

1. **Field-level encryption** — PHI (Protected Health Information) fields are encrypted using **Fernet AES-128** before storage:
   - `medical_history`, `allergies`, `current_medications`
   - `emergency_contact`, `emergency_contact_name`
   - Encryption key stored in `data/db_encryption.key`

2. **Password hashing** — Passwords stored as **bcrypt hashes**, never plain text

3. **Consent tracking** — `patients.consent_given` and `patients.consent_given_at` track HIPAA consent. Predictions blocked if `consent_given = False`

---

# PART B: ML MODEL QUESTIONS

---

## SECTION 2: ML MODEL BASICS

**Q13. What ML algorithm did you use and why?**

**Gradient Boosting Classifier** (scikit-learn `GradientBoostingClassifier`).

Chosen after comparing three models:

| Model | CV ROC-AUC |
|-------|-----------|
| Logistic Regression | 86.35% |
| Random Forest | 93.43% |
| **Gradient Boosting** | **94.32%** |

Gradient Boosting won because:
- Highest ROC-AUC (best discrimination ability)
- Handles non-linear relationships between features
- Built-in feature importance for clinical interpretation
- Robust to outliers with proper regularization

---

**Q14. What are the 8 input features of your model?**

| Feature | Description | Source |
|---------|-------------|--------|
| Glucose | Blood glucose (mg/dL) | Lab result |
| BMI | Body Mass Index (kg/m²) | Nurse vitals |
| BloodPressure | Diastolic BP (mmHg) | Nurse vitals |
| Age | Patient age (years) | Nurse vitals |
| Pregnancies | Number of pregnancies | Nurse vitals |
| Insulin | Serum insulin (μU/mL) | Lab result |
| SkinThickness | Triceps skin fold (mm) | Nurse vitals |
| DiabetesPedigreeFunction | Family history score | Nurse vitals |

**Important:** Glucose is the ONLY feature that comes from a lab result. All others come from nurse vitals recording. The health form is disabled until a glucose lab result is available.

---

**Q15. What are your model's performance metrics?**

Tested on 214 held-out samples (20% of dataset):

| Metric | Value | Meaning |
|--------|-------|---------|
| Accuracy | **89.25%** | 89% of all predictions correct |
| Precision | **88.61%** | 89% of "diabetic" predictions are correct |
| Recall | **83.33%** | Catches 83% of actual diabetics |
| F1 Score | **85.89%** | Balanced precision-recall |
| ROC-AUC | **97.06%** | Excellent discrimination ability |
| CV ROC-AUC | **94.32% ±1.53%** | Stable across 5 folds |
| Overfitting gap | **3.60%** | Train 92.86% vs Test 89.25% |

---

**Q16. What is the confusion matrix result?**

```
                  Predicted Non-Diabetic   Predicted Diabetic
Actual Non-Diabetic       121 (TN)              9 (FP)
Actual Diabetic            14 (FN)             70 (TP)
```

- **121** correctly identified as non-diabetic
- **70** correctly identified as diabetic
- **9** false alarms (non-diabetic flagged as diabetic)
- **14** missed diabetics ← most critical in healthcare

Sensitivity = 83.3% | Specificity = 93.1%

---

**Q17. What is feature importance in your model?**

| Feature | Importance |
|---------|-----------|
| Insulin | 39.4% |
| Glucose | 23.9% |
| Age | 9.5% |
| BMI | 9.0% |
| SkinThickness | 7.6% |
| DiabetesPedigreeFunction | 5.6% |
| Pregnancies | 2.9% |
| BloodPressure | 2.1% |

Insulin and Glucose together account for **63.3%** of the model's decisions — consistent with medical literature where these are the primary diabetes markers.

---

**Q18. How does the model output a risk level?**

The model outputs a **probability** (0.0 to 1.0) that the patient is diabetic. This is mapped to 4 risk tiers:

| Probability | Risk Level | Action |
|-------------|-----------|--------|
| 0% – 30% | 🟢 LOW RISK | Regular checkups every 2-3 years |
| 30% – 50% | 🟡 MODERATE RISK | Annual checkup, lifestyle changes |
| 50% – 70% | 🟠 HIGH RISK | Doctor consultation within 1 month |
| 70% – 100% | 🔴 VERY HIGH RISK | Immediate medical attention |

When HIGH or VERY HIGH RISK is detected, **all doctors are notified instantly** via WebSocket push notification.

---

**Q19. How is the model integrated into the web application?**

```
Patient submits health form
    ↓
POST /api/patient/predict
    ↓
backend/services/ml_service.py → MLService.predict()
    ↓
Loads gradient_boosting.pkl + scaler.pkl
    ↓
Scales input with StandardScaler
    ↓
model.predict_proba() → probability
    ↓
Maps to risk level
    ↓
Saves to predictions table (DB)
    ↓
Returns JSON to frontend
    ↓
Redirects to prediction_result.html?id=X
```

The model is loaded **once at startup** and kept in memory as a singleton (`_ml_service_instance`). This avoids reloading the model on every request.

---

**Q20. Where is the trained model stored and how is it loaded?**

Stored in `ml_model/saved_models/`:
- `gradient_boosting.pkl` — the trained model (serialized with joblib)
- `scaler.pkl` — the fitted StandardScaler
- `feature_names.json` — ordered list of feature names
- `model_metadata.json` — accuracy, version, hyperparameters
- `model_registry.json` — version history, active model flag

Loading:
```python
import joblib
model  = joblib.load('ml_model/saved_models/gradient_boosting.pkl')
scaler = joblib.load('ml_model/saved_models/scaler.pkl')
```

The `model_registry.json` determines which model is **active**. Admins can switch models through the admin panel without restarting the server.

---

**Q21. Was the model trained on Google Colab?**

**No.** The model was trained **locally** on a Windows machine using:
- Python 3.11
- scikit-learn 1.8.0
- Training script: `ml_model/training/train_gradient_boosting.py`
- Dataset: `ml_model/dataset/diabetes.csv` (local file)

The `predict.py` file contains some old Colab path references (`/content/drive/MyDrive/...`) from an earlier version, but the actual model was trained and saved locally. The `model_metadata.json` confirms: `"trained_at": "2026-05-12T06:35:26"`.

---

**Q22. How did you prevent overfitting in your model?**

Initial model (v2.2.0) had a **10% overfitting gap** (train 98.83% vs test 88.79%).

Fixed by increasing regularization:

| Parameter | Before | After | Effect |
|-----------|--------|-------|--------|
| `max_depth` | 4 | **3** | Shallower trees, less memorization |
| `min_samples_split` | 10 | **20** | Requires more samples to split |
| `min_samples_leaf` | 4 | **10** | Requires more samples in leaves |
| `max_features` | None | **'sqrt'** | Each tree sees only √8 ≈ 3 features |

Result: Gap reduced from **10.04% → 3.60%**, test accuracy improved from 88.79% → **89.25%**.

---

**Q23. How does the system handle a patient with no lab result (no glucose)?**

The health form **requires glucose from a lab result** — it cannot be manually entered by the patient.

If no lab result exists:
- Glucose field is `readonly` and shows "No lab result yet"
- Submit button is **disabled**
- Message shown: "Ask your doctor to order a glucose test"

If a lab result is pending (lab tech hasn't entered it yet):
- Field shows "Waiting for lab result..."
- Form polls every 20 seconds for new results
- Auto-fills when result is entered

This ensures glucose always comes from a verified clinical measurement, not patient self-reporting.

---

**Q24. What is the difference between the health_records table and the predictions table?**

| Aspect | health_records | predictions |
|--------|---------------|-------------|
| Purpose | Stores raw input data | Stores ML output |
| Created | When patient submits form | After ML model runs |
| Key columns | glucose, bmi, blood_pressure, age, etc. | probability, risk_level, model_version |
| Relationship | One health record per day | Multiple predictions possible |
| Used for | Audit trail of inputs | Patient history, doctor review |

Both tables are linked: `predictions.health_record_id → health_records.id`

The `predictions.input_data` (JSON) also stores a snapshot of the input values at prediction time, so even if the health record is updated, the prediction's input is preserved.

---

**Q25. How does the admin manage the ML model?**

The admin panel has a **Model Management** section:

1. **View all models** — lists all trained models from `model_registry.json` with their metrics
2. **Switch active model** — admin can activate a different model version (e.g. switch from Gradient Boosting to Random Forest)
3. **View model metrics** — accuracy, precision, recall, F1, ROC-AUC for each model
4. **Retrain trigger** — admin can trigger model retraining via `retrain_all.py`

When admin switches the active model:
- `model_registry.json` is updated (status: 'active' / 'archived')
- `MLService` reloads the new model on next prediction request
- No server restart required

---

**Q26. What happens if the ML model fails to load?**

The `MLService` has a **multi-level fallback**:

1. Try loading the active model from registry (`gradient_boosting.pkl`)
2. If fails → try `logistic_regression.pkl` (fallback)
3. If fails → try any `.pkl` file in `saved_models/`
4. If all fail → attempt auto-retrain using `retrain_all.py`
5. If retrain fails → return error: "ML model is not ready. Please contact admin."

The prediction endpoint returns HTTP 500 with a clear message if the model cannot be loaded, rather than crashing silently.

---

**Q27. How does the system ensure the same patient cannot run multiple predictions on one payment?**

The `payments` table has a `prediction_consumed` (BOOLEAN) column:

```python
# Before prediction runs — check for unconsumed completed payment
paid = Payment.query.filter(
    Payment.patient_id == current_user['id'],
    Payment.payment_type == 'prediction',
    Payment.payment_status == 'completed',
    Payment.prediction_consumed == False,   # ← key check
).first()

# After prediction runs successfully — mark as consumed
payment.prediction_consumed = True
db.session.commit()
```

This is a **server-side gate** — the frontend cannot bypass it. Even if a patient manipulates the browser, the backend always checks the database before running the ML model.

---

*All database schema verified from live SQLite database*
*All ML metrics verified from actual model evaluation on test set*
*Model: GradientBoostingClassifier v2.3.1 | sklearn 1.8.0*
