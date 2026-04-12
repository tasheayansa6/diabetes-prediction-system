import urllib.request
import urllib.error
import json
import sys

BASE_URL = "http://localhost:5000"

def request(method, path, data=None, token=None):
    url = BASE_URL + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except:
            return e.code, {"error": str(e)}
    except Exception as e:
        return 0, {"error": str(e)}

def login(email, password):
    status, body = request("POST", "/api/auth/login", {"email": email, "password": password})
    if status == 200 and "access_token" in body:
        return body["access_token"]
    return None

results = {}

# ─── STEP 1: Register all 5 accounts ───────────────────────────────────────
print("\n=== STEP 1: Register accounts ===")
accounts = [
    {"username": "testnurse",   "email": "testnurse@test.com",   "password": "Nurse1234",   "role": "nurse"},
    {"username": "testdoctor",  "email": "testdoctor@test.com",  "password": "Doctor1234",  "role": "doctor"},
    {"username": "testlab",     "email": "testlab@test.com",     "password": "Lab12345",    "role": "lab_technician"},
    {"username": "testpharma",  "email": "testpharma@test.com",  "password": "Pharma1234",  "role": "pharmacist"},
    {"username": "testpatient", "email": "testpatient@test.com", "password": "Patient1234", "role": "patient"},
]
step1_pass = True
patient_id = None
for acc in accounts:
    status, body = request("POST", "/api/auth/register", acc)
    ok = status in (200, 201)
    if not ok:
        # might already exist — try login to confirm
        tok = login(acc["email"], acc["password"])
        ok = tok is not None
    print(f"  {'PASS' if ok else 'FAIL'} Register {acc['username']} → {status} {body}")
    if not ok:
        step1_pass = False
results["step1"] = "PASS" if step1_pass else "FAIL"

# Get patient_id by logging in as patient
patient_token = login("testpatient@test.com", "Patient1234")
if patient_token:
    s, b = request("GET", "/api/patient/profile", token=patient_token)
    patient_id = b.get("id") or b.get("patient_id") or b.get("user", {}).get("id")
    print(f"  Patient token obtained. Profile → {s} {b}")
    print(f"  patient_id = {patient_id}")
else:
    print("  FAIL: Could not get patient token")

# ─── STEP 2: Nurse records vitals ──────────────────────────────────────────
print("\n=== STEP 2: Nurse records vitals ===")
nurse_token = login("testnurse@test.com", "Nurse1234")
if nurse_token and patient_id:
    vitals_data = {
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
    status, body = request("POST", "/api/nurse/vitals", vitals_data, nurse_token)
    ok = status in (200, 201)
    print(f"  {'PASS' if ok else 'FAIL'} POST /api/nurse/vitals → {status} {body}")
    results["step2"] = "PASS" if ok else "FAIL"
else:
    print(f"  FAIL: nurse_token={bool(nurse_token)}, patient_id={patient_id}")
    results["step2"] = "FAIL"

# ─── STEP 3: Doctor orders lab test ────────────────────────────────────────
print("\n=== STEP 3: Doctor orders lab test ===")
doctor_token = login("testdoctor@test.com", "Doctor1234")
lab_request_id = None
if doctor_token and patient_id:
    lab_data = {
        "patient_id": patient_id,
        "test_name": "Fasting Glucose",
        "priority": "normal"
    }
    status, body = request("POST", "/api/doctor/lab-requests", lab_data, doctor_token)
    ok = status in (200, 201)
    print(f"  {'PASS' if ok else 'FAIL'} POST /api/doctor/lab-requests → {status} {body}")
    results["step3"] = "PASS" if ok else "FAIL"
else:
    print(f"  FAIL: doctor_token={bool(doctor_token)}, patient_id={patient_id}")
    results["step3"] = "FAIL"

# ─── STEP 4: Lab tech enters results ───────────────────────────────────────
print("\n=== STEP 4: Lab tech enters results ===")
lab_token = login("testlab@test.com", "Lab12345")
test_id = None
if lab_token:
    status, body = request("GET", "/api/labs/pending", token=lab_token)
    print(f"  GET /api/labs/pending → {status} {json.dumps(body)[:300]}")
    # find the test
    tests = body if isinstance(body, list) else body.get("tests") or body.get("lab_requests") or body.get("data") or []
    for t in tests:
        if str(t.get("patient_id")) == str(patient_id) or t.get("test_name") == "Fasting Glucose":
            test_id = t.get("id") or t.get("test_id")
            break
    if not test_id and tests:
        test_id = tests[0].get("id") or tests[0].get("test_id")
    print(f"  test_id = {test_id}")
    if test_id:
        result_data = {
            "test_id": test_id,
            "results": "148",
            "unit": "mg/dL",
            "normal_range": "70-99"
        }
        status, body = request("POST", "/api/labs/results", result_data, lab_token)
        ok = status in (200, 201)
        print(f"  {'PASS' if ok else 'FAIL'} POST /api/labs/results → {status} {body}")
        results["step4"] = "PASS" if ok else "FAIL"
    else:
        print("  FAIL: No test_id found in pending list")
        results["step4"] = "FAIL"
else:
    print("  FAIL: Could not get lab token")
    results["step4"] = "FAIL"

# ─── STEP 5: Patient checks vitals and lab results ─────────────────────────
print("\n=== STEP 5: Patient checks vitals/lab results ===")
if patient_token:
    status, body = request("GET", "/api/patient/vitals/latest", token=patient_token)
    ok_vitals = status == 200
    print(f"  {'PASS' if ok_vitals else 'FAIL'} GET /api/patient/vitals/latest → {status} {json.dumps(body)[:300]}")

    status2, body2 = request("GET", "/api/patient/lab-results", token=patient_token)
    ok_labs = status2 == 200
    print(f"  {'PASS' if ok_labs else 'FAIL'} GET /api/patient/lab-results → {status2} {json.dumps(body2)[:300]}")
    results["step5"] = "PASS" if (ok_vitals and ok_labs) else "PARTIAL" if (ok_vitals or ok_labs) else "FAIL"
else:
    print("  FAIL: No patient token")
    results["step5"] = "FAIL"

# ─── STEP 6: Process payment ────────────────────────────────────────────────
print("\n=== STEP 6: Process payment ===")
if patient_token:
    pay_data = {
        "amount": 150,
        "payment_method": "cash",
        "payment_type": "prediction",
        "payer_name": "Test Patient",
        "payer_phone": "0911000000"
    }
    status, body = request("POST", "/api/payments/process", pay_data, patient_token)
    ok = status in (200, 201)
    print(f"  {'PASS' if ok else 'FAIL'} POST /api/payments/process → {status} {body}")
    results["step6"] = "PASS" if ok else "FAIL"
else:
    print("  FAIL: No patient token")
    results["step6"] = "FAIL"

# ─── STEP 7: Run prediction ─────────────────────────────────────────────────
print("\n=== STEP 7: Run prediction ===")
if patient_token:
    pred_data = {
        "glucose": 148,
        "blood_pressure": 80,
        "bmi": 26.0,
        "age": 35,
        "pregnancies": 2,
        "skin_thickness": 20,
        "insulin": 0,
        "diabetes_pedigree": 0.6
    }
    status, body = request("POST", "/api/patient/predict", pred_data, patient_token)
    ok = status in (200, 201)
    print(f"  {'PASS' if ok else 'FAIL'} POST /api/patient/predict → {status} {body}")
    results["step7"] = "PASS" if ok else "FAIL"
else:
    print("  FAIL: No patient token")
    results["step7"] = "FAIL"

# ─── STEP 8: Doctor prescribes ──────────────────────────────────────────────
print("\n=== STEP 8: Doctor prescribes ===")
prescription_id = None
if doctor_token and patient_id:
    rx_data = {
        "patient_id": patient_id,
        "medication": "Metformin 500mg",
        "dosage": "500mg",
        "frequency": "Twice daily",
        "duration": "30 days"
    }
    status, body = request("POST", "/api/doctor/prescriptions", rx_data, doctor_token)
    ok = status in (200, 201)
    print(f"  {'PASS' if ok else 'FAIL'} POST /api/doctor/prescriptions → {status} {body}")
    prescription_id = body.get("id") or body.get("prescription_id") or (body.get("prescription") or {}).get("id")
    results["step8"] = "PASS" if ok else "FAIL"
else:
    print(f"  FAIL: doctor_token={bool(doctor_token)}, patient_id={patient_id}")
    results["step8"] = "FAIL"

# ─── STEP 9: Pharmacist verifies and dispenses ──────────────────────────────
print("\n=== STEP 9: Pharmacist verifies and dispenses ===")
pharma_token = login("testpharma@test.com", "Pharma1234")
if pharma_token:
    status, body = request("GET", "/api/pharmacy/prescriptions", token=pharma_token)
    print(f"  GET /api/pharmacy/prescriptions → {status} {json.dumps(body)[:300]}")
    rxs = body if isinstance(body, list) else body.get("prescriptions") or body.get("data") or []
    if not prescription_id and rxs:
        prescription_id = rxs[0].get("id") or rxs[0].get("prescription_id")
    print(f"  prescription_id = {prescription_id}")
    if prescription_id:
        status2, body2 = request("PUT", f"/api/pharmacy/verify/{prescription_id}", token=pharma_token)
        ok_verify = status2 in (200, 201)
        print(f"  {'PASS' if ok_verify else 'FAIL'} PUT /api/pharmacy/verify/{prescription_id} → {status2} {body2}")

        status3, body3 = request("POST", f"/api/pharmacy/dispense/{prescription_id}", token=pharma_token)
        ok_dispense = status3 in (200, 201)
        print(f"  {'PASS' if ok_dispense else 'FAIL'} POST /api/pharmacy/dispense/{prescription_id} → {status3} {body3}")
        results["step9"] = "PASS" if (ok_verify and ok_dispense) else "PARTIAL" if (ok_verify or ok_dispense) else "FAIL"
    else:
        print("  FAIL: No prescription_id found")
        results["step9"] = "FAIL"
else:
    print("  FAIL: Could not get pharma token")
    results["step9"] = "FAIL"

# ─── STEP 10: Patient checks prescriptions ──────────────────────────────────
print("\n=== STEP 10: Patient checks prescriptions ===")
if patient_token:
    status, body = request("GET", "/api/patient/prescriptions", token=patient_token)
    ok = status == 200
    print(f"  {'PASS' if ok else 'FAIL'} GET /api/patient/prescriptions → {status} {json.dumps(body)[:400]}")
    results["step10"] = "PASS" if ok else "FAIL"
else:
    print("  FAIL: No patient token")
    results["step10"] = "FAIL"

# ─── Summary ────────────────────────────────────────────────────────────────
print("\n" + "="*50)
print("SUMMARY")
print("="*50)
for step, result in results.items():
    print(f"  {step.upper()}: {result}")
