"""
Replace all test types with only diabetes-relevant lab tests.
Run: venv\Scripts\python.exe seed_test_types.py
"""
import sqlite3
from datetime import datetime

conn = sqlite3.connect('database/diabetes.db')
cur  = conn.cursor()

# Clear all existing test types
cur.execute("DELETE FROM test_types")
print("Cleared all existing test types.")

# Diabetes-relevant tests only
TESTS = [
    # ── Blood Glucose ──────────────────────────────────────────────────────
    ("Blood Glucose (Fasting)",       "BG001",   "Blood Glucose",  25.0,  "70–99 mg/dL",           "Fast for 8 hours before test"),
    ("Random Blood Glucose",          "RBG001",  "Blood Glucose",  25.0,  "< 200 mg/dL",            "No fasting required"),
    ("Postprandial Glucose (2hr)",    "PPG001",  "Blood Glucose",  30.0,  "< 140 mg/dL",            "Test 2 hours after a meal"),
    ("Oral Glucose Tolerance (OGTT)", "OGTT001", "Blood Glucose",  60.0,  "< 140 mg/dL at 2hr",     "Fast 8hrs, drink 75g glucose solution"),

    # ── Long-term Glucose Control ──────────────────────────────────────────
    ("HbA1c (Glycated Hemoglobin)",   "HBA1C",   "Glucose Control", 45.0, "< 5.7% (normal), 5.7–6.4% (prediabetes), ≥6.5% (diabetes)", "No fasting required"),
    ("Fructosamine",                  "FRUCT001","Glucose Control", 55.0, "200–285 umol/L",          "No fasting required — reflects 2–3 week glucose average"),

    # ── Insulin & Pancreatic Function ──────────────────────────────────────
    ("Fasting Insulin Level",         "INS001",  "Insulin & Pancreas", 55.0, "2–25 uU/mL",          "Fast for 8 hours before test"),
    ("C-Peptide",                     "CPEP001", "Insulin & Pancreas", 80.0, "0.5–2.0 ng/mL",       "Fast 8 hours before test — measures insulin production"),
    ("Insulin Resistance (HOMA-IR)",  "HOMA001", "Insulin & Pancreas", 90.0, "< 2.0 (normal)",      "Calculated from fasting glucose + insulin"),

    # ── Kidney Function (Diabetes Complication) ────────────────────────────
    ("Microalbumin (Urine)",          "MALB001", "Kidney Function", 40.0,  "< 30 mg/g creatinine",  "Random urine sample — early kidney damage marker"),
    ("Kidney Function (Creatinine)",  "KFT001",  "Kidney Function", 40.0,  "0.6–1.2 mg/dL",         "No fasting required"),
    ("eGFR",                          "EGFR001", "Kidney Function", 45.0,  "> 60 mL/min/1.73m²",    "Calculated from creatinine — kidney filtration rate"),
    ("Blood Urea Nitrogen (BUN)",     "BUN001",  "Kidney Function", 35.0,  "7–20 mg/dL",             "No fasting required"),

    # ── Lipid Panel (Diabetes Risk Factor) ────────────────────────────────
    ("Lipid Profile (Full)",          "LIP001",  "Lipid Panel",    50.0,  "LDL < 100, HDL > 40, TG < 150 mg/dL", "Fast for 12 hours"),
    ("Total Cholesterol",             "CHOL001", "Lipid Panel",    25.0,  "< 200 mg/dL",             "Fast 12 hours"),
    ("Triglycerides",                 "TRIG001", "Lipid Panel",    30.0,  "< 150 mg/dL",             "Fast 12 hours — elevated in diabetes"),

    # ── Liver Function (Metformin Monitoring) ─────────────────────────────
    ("Liver Function (ALT/AST)",      "LFT001",  "Liver Function", 45.0,  "ALT 7–56 U/L, AST 10–40 U/L", "No fasting required — required before Metformin"),

    # ── Complete Blood Count ───────────────────────────────────────────────
    ("Complete Blood Count (CBC)",    "CBC001",  "Blood Count",    35.0,  "WBC 4.5–11 x10⁹/L, Hgb 12–17 g/dL", "No fasting required"),

    # ── Urine Analysis ─────────────────────────────────────────────────────
    ("Urine Analysis (Full)",         "UA001",   "Urine Analysis", 20.0,  "Normal — checks glucose, protein, ketones in urine", "Midstream clean catch urine"),
    ("Urine Glucose",                 "UG001",   "Urine Analysis", 15.0,  "Negative (< 0.8 mmol/L)", "Spot urine sample"),
    ("Urine Ketones",                 "UK001",   "Urine Analysis", 15.0,  "Negative",                 "Spot urine — elevated in diabetic ketoacidosis"),

    # ── Thyroid (Affects Blood Sugar) ─────────────────────────────────────
    ("Thyroid (TSH)",                 "TSH001",  "Thyroid",        50.0,  "0.4–4.0 mIU/L",           "No fasting required — thyroid affects glucose metabolism"),
]

added = 0
for test_name, test_code, category, cost, normal_range, prep in TESTS:
    cur.execute("""
        INSERT INTO test_types (test_name, test_code, category, cost, normal_range, preparation_instructions, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (test_name, test_code, category, cost, normal_range, prep, datetime.utcnow().isoformat()))
    added += 1
    print(f"  {category:25} | {test_name}")

conn.commit()
cur.execute("SELECT COUNT(*) FROM test_types")
print(f"\nTotal: {cur.fetchone()[0]} diabetes-relevant tests added.")
conn.close()
