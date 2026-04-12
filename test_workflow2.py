import urllib.request
import urllib.error
import json
import time

BASE_URL = "http://localhost:5000"
TS = str(int(time.time()))[-4:]

def req(method, path, data=None, token=None):
    url = BASE_URL + path
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
        headers["Content-Length"] = str(len(body))
    else:
        body = None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {"error": str(e)}
    except Exception as e:
        return 0, {"error": str(e)}

def login(email, password):
    s, b = req("POST", "/api/auth/login", {"email": email, "password": password})
    if s == 200 and "token" in b:
        return b["token"]
    if s == 200 and "access_token" in b:
        return b["access_token"]
    return None

results = {}

# ─── STEP 1: Register accounts ─────────────────────────────────────────────
print("\n=== STEP 1: Register accounts ===")

NURSE_EMAIL    = "nurse" + TS + "@test.com"
DOCTOR_EMAIL   = "doctor" + TS + "@test.com"
LAB_EMAIL      = "lab" + TS + "@test.com"
PHARMA_EMAIL   = "pharma" + TS + "@test.com"
PATIENT_EMAIL  = "patient" + TS + "@test.com"

accounts = [
    {"username": "nurse" + TS,   "email": NURSE_EMAIL,   "password": "Nurse1234",   "role": "nurse"},
    {"username": "doctor" + TS,  "email": DOCTOR_EMAIL,  "password": "Doctor1234",  "role": "doctor"},
    {"username": "lab" + TS,     "email": LAB_EMAIL,     "password": "Lab12345",    "role": "lab_technician"},
    {"username": "pharma" + TS,  "email": PHARMA_EMAIL,  "password": "Pharma1234",  "role": "pharmacist"},
    {"username": "patient" + TS, "email": PATIENT_EMAIL, "password": "Patient1234", "role": "patient"},
]

step1_pass = True
for acc in accounts:
    s, b = req("POST", "/api/auth/register", acc)
    ok = s in (200, 201)
    label = "PASS" if ok else "FAIL"
    print("  " + label + " Register " + acc["username"] + " -> " + str(s) + " " + json.dumps(b)[:150])
    if not ok:
        step1_pass = False

results["step1"] = "PASS" if step1_pass else "FAIL"

# Get tokens
nurse_token   = login(NURSE_EMAIL,   "Nurse1234")
doctor_token  = login(DOCTOR_EMAIL,  "Doctor1234")
lab_token     = login(LAB_EMAIL,     "Lab12345")
pharma_token  = login(PHARMA_EMAIL,  "Pharma1234")
patient_token = login(PATIENT_EMAIL, "Patient1234")

print("  Tokens: nurse=" + str(bool(nurse_token)) + " doctor=" + str(bool(doctor_token)) +
      " lab=" + str(bool(lab_token)) + " pharma=" + str(bool(pharma_token)) +
      " patient=" + str(bool(patient_token)))

# Get patient_id — use dashboard (lighter query) then fall back to profile
patient_id = None
if patient_token:
    s, b = req("GET", "/api/patient/dashboard", token=patient_token)
    print("  Patient dashboard -> " + str(s) + " " + json.dumps(b)[:300])
    patient_id = ((b.get("dashboard") or {}).get("patient_info") or {}).get("id")
    if not patient_id:
        # fall back: decode token to get user_id
        import base64, json as _json
        try:
            payload_b64 = patient_token.split(".")[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload = _json.loads(base64.b64decode(payload_b64))
            patient_id = payload.get("user_id")
            print("  patient_id from token = " + str(patient_id))
        except Exception as te:
            print("  token decode error: " + str(te))
    print("  patient_id = " + str(patient_id))

# ─── STEP 2: Nurse records vitals ──────────────────────────────────────────
print("\n=== STEP 2: Nurse records vitals ===")
if nurse_token and patient_id:
    vitals = {
        "patient_id": patient_id,
        "blood_pressure_diastolic": 80,
        "blood_pressure_systolic": 120,
        "height": 170,
        "weight": 75,
        "skin_thickness": 20,
        "pregnancies": 2,
        "diabetes_pedigree": 0.6,
        "age": 35
    }
    s, b = req("POST", "/api/nurse/vitals", vitals, nurse_token)
    ok = s in (200, 201)
    print("  " + ("PASS" if ok else "FAIL") + " POST /api/nurse/vitals -> " + str(s) + " " + json.dumps(b)[:300])
    results["step2"] = "PASS" if ok else "FAIL"
else:
    print("  FAIL: nurse_token=" + str(bool(nurse_token)) + " patient_id=" + str(patient_id))
    results["step2"] = "FAIL"

# ─── STEP 3: Doctor orders lab test ────────────────────────────────────────
print("\n=== STEP 3: Doctor orders lab test ===")
if doctor_token and patient_id:
    lab_req = {"patient_id": patient_id, "test_name": "Fasting Glucose", "priority": "normal"}
    s, b = req("POST", "/api/doctor/lab-requests", lab_req, doctor_token)
    ok = s in (200, 201)
    print("  " + ("PASS" if ok else "FAIL") + " POST /api/doctor/lab-requests -> " + str(s) + " " + json.dumps(b)[:300])
    results["step3"] = "PASS" if ok else "FAIL"
else:
    print("  FAIL: doctor_token=" + str(bool(doctor_token)) + " patient_id=" + str(patient_id))
    results["step3"] = "FAIL"

# ─── STEP 4: Lab tech enters results ───────────────────────────────────────
print("\n=== STEP 4: Lab tech enters results ===")
test_id = None
if lab_token:
    s, b = req("GET", "/api/labs/pending", token=lab_token)
    print("  GET /api/labs/pending -> " + str(s) + " " + json.dumps(b)[:400])
    tests = b if isinstance(b, list) else (b.get("pending_tests") or b.get("tests") or b.get("lab_requests") or b.get("data") or [])
    for t in tests:
        if str(t.get("patient_id")) == str(patient_id) or t.get("test_name") == "Fasting Glucose":
            test_id = t.get("id") or t.get("test_id")
            break
    if not test_id and tests:
        test_id = tests[0].get("id") or tests[0].get("test_id")
    print("  test_id = " + str(test_id))
    if test_id:
        res_data = {"test_id": test_id, "results": "148", "unit": "mg/dL", "normal_range": "70-99"}
        s, b = req("POST", "/api/labs/results", res_data, lab_token)
        ok = s in (200, 201)
        print("  " + ("PASS" if ok else "FAIL") + " POST /api/labs/results -> " + str(s) + " " + json.dumps(b)[:300])
        results["step4"] = "PASS" if ok else "FAIL"
    else:
        print("  FAIL: No test_id found")
        results["step4"] = "FAIL"
else:
    print("  FAIL: No lab token")
    results["step4"] = "FAIL"

# ─── STEP 5: Patient checks vitals and lab results ─────────────────────────
print("\n=== STEP 5: Patient checks vitals/lab results ===")
if patient_token:
    s, b = req("GET", "/api/patient/vitals/latest", token=patient_token)
    ok_v = s == 200
    print("  " + ("PASS" if ok_v else "FAIL") + " GET /api/patient/vitals/latest -> " + str(s) + " " + json.dumps(b)[:300])

    s2, b2 = req("GET", "/api/patient/lab-results", token=patient_token)
    ok_l = s2 == 200
    print("  " + ("PASS" if ok_l else "FAIL") + " GET /api/patient/lab-results -> " + str(s2) + " " + json.dumps(b2)[:300])
    results["step5"] = "PASS" if (ok_v and ok_l) else ("PARTIAL" if (ok_v or ok_l) else "FAIL")
else:
    print("  FAIL: No patient token")
    results["step5"] = "FAIL"

# ─── STEP 6: Process payment ────────────────────────────────────────────────
print("\n=== STEP 6: Process payment ===")
if patient_token:
    pay = {
        "amount": 150,
        "payment_method": "cash",
        "payment_type": "prediction",
        "payer_name": "Test Patient",
        "payer_phone": "0911000000"
    }
    s, b = req("POST", "/api/payments/process", pay, patient_token)
    ok = s in (200, 201)
    print("  " + ("PASS" if ok else "FAIL") + " POST /api/payments/process -> " + str(s) + " " + json.dumps(b)[:300])
    results["step6"] = "PASS" if ok else "FAIL"
else:
    print("  FAIL: No patient token")
    results["step6"] = "FAIL"

# ─── STEP 7: Run prediction ─────────────────────────────────────────────────
print("\n=== STEP 7: Run prediction ===")
if patient_token:
    pred = {
        "glucose": 148,
        "blood_pressure": 80,
        "bmi": 26.0,
        "age": 35,
        "pregnancies": 2,
        "skin_thickness": 20,
        "insulin": 0,
        "diabetes_pedigree": 0.6
    }
    s, b = req("POST", "/api/patient/predict", pred, patient_token)
    ok = s in (200, 201)
    print("  " + ("PASS" if ok else "FAIL") + " POST /api/patient/predict -> " + str(s) + " " + json.dumps(b)[:400])
    results["step7"] = "PASS" if ok else "FAIL"
else:
    print("  FAIL: No patient token")
    results["step7"] = "FAIL"

# ─── STEP 8: Doctor prescribes ──────────────────────────────────────────────
print("\n=== STEP 8: Doctor prescribes ===")
prescription_id = None
if doctor_token and patient_id:
    rx = {
        "patient_id": patient_id,
        "medication": "Metformin 500mg",
        "dosage": "500mg",
        "frequency": "Twice daily",
        "duration": "30 days"
    }
    s, b = req("POST", "/api/doctor/prescriptions", rx, doctor_token)
    ok = s in (200, 201)
    print("  " + ("PASS" if ok else "FAIL") + " POST /api/doctor/prescriptions -> " + str(s) + " " + json.dumps(b)[:300])
    prescription_id = (b.get("id") or b.get("prescription_id") or
                       (b.get("prescription") or {}).get("id"))
    results["step8"] = "PASS" if ok else "FAIL"
else:
    print("  FAIL: doctor_token=" + str(bool(doctor_token)) + " patient_id=" + str(patient_id))
    results["step8"] = "FAIL"

# ─── STEP 9: Pharmacist verifies and dispenses ──────────────────────────────
print("\n=== STEP 9: Pharmacist verifies and dispenses ===")
if pharma_token:
    s, b = req("GET", "/api/pharmacy/prescriptions", token=pharma_token)
    print("  GET /api/pharmacy/prescriptions -> " + str(s) + " " + json.dumps(b)[:400])
    rxs = b if isinstance(b, list) else (b.get("prescriptions") or b.get("data") or [])
    # Find the prescription for our specific patient
    for rx in rxs:
        if (rx.get("patient") or {}).get("id") == patient_id or rx.get("patient_id") == patient_id:
            if not prescription_id:
                prescription_id = rx.get("id") or rx.get("prescription_id")
            break
    if not prescription_id and rxs:
        prescription_id = rxs[0].get("id") or rxs[0].get("prescription_id")
    print("  prescription_id = " + str(prescription_id))
    if prescription_id:
        s2, b2 = req("POST", "/api/pharmacy/verify/" + str(prescription_id), {}, pharma_token)
        ok_v = s2 in (200, 201)
        print("  " + ("PASS" if ok_v else "FAIL") + " POST /api/pharmacy/verify/" + str(prescription_id) + " -> " + str(s2) + " " + json.dumps(b2)[:200])

        s3, b3 = req("POST", "/api/pharmacy/dispense/" + str(prescription_id), {}, pharma_token)
        ok_d = s3 in (200, 201)
        print("  " + ("PASS" if ok_d else "FAIL") + " POST /api/pharmacy/dispense/" + str(prescription_id) + " -> " + str(s3) + " " + json.dumps(b3)[:200])
        results["step9"] = "PASS" if (ok_v and ok_d) else ("PARTIAL" if (ok_v or ok_d) else "FAIL")
    else:
        print("  FAIL: No prescription_id found")
        results["step9"] = "FAIL"
else:
    print("  FAIL: No pharma token")
    results["step9"] = "FAIL"

# ─── STEP 10: Patient checks prescriptions ──────────────────────────────────
print("\n=== STEP 10: Patient checks prescriptions ===")
if patient_token:
    s, b = req("GET", "/api/patient/prescriptions", token=patient_token)
    ok = s == 200
    print("  " + ("PASS" if ok else "FAIL") + " GET /api/patient/prescriptions -> " + str(s) + " " + json.dumps(b)[:400])
    results["step10"] = "PASS" if ok else "FAIL"
else:
    print("  FAIL: No patient token")
    results["step10"] = "FAIL"

# ─── Summary ────────────────────────────────────────────────────────────────
print("\n" + "=" * 50)
print("SUMMARY")
print("=" * 50)
for step, result in results.items():
    print("  " + step.upper() + ": " + result)
