"""
Merges Pima Indians dataset (768 rows) with Frankfurt Hospital data (300 rows)
to produce 1068 rows in ml_model/dataset/diabetes.csv

Run: python merge_frankfurt.py
"""
import csv, math, random

random.seed(42)

CLIP = {
    'Pregnancies': (0, 17),
    'Glucose': (44, 199),
    'BloodPressure': (24, 122),
    'SkinThickness': (7, 99),
    'Insulin': (14, 846),
    'BMI': (18.0, 67.1),
    'DiabetesPedigreeFunction': (0.078, 2.42),
    'Age': (21, 81),
}

# Frankfurt stats: {outcome: {feature: (mean, sd)}}
FRANKFURT = {
    0: {'Pregnancies':(2.5,2.5),'Glucose':(99,20),'BloodPressure':(71,11),
        'SkinThickness':(20,9),'Insulin':(60,50),'BMI':(27.5,5.5),
        'DiabetesPedigreeFunction':(0.38,0.22),'Age':(30,10)},
    1: {'Pregnancies':(4.0,3.0),'Glucose':(143,28),'BloodPressure':(74,12),
        'SkinThickness':(25,10),'Insulin':(110,80),'BMI':(33,6),
        'DiabetesPedigreeFunction':(0.56,0.28),'Age':(38,11)},
}

def gauss_clip(mu, sd, lo, hi, is_float=False):
    val = random.gauss(mu, sd)
    val = max(lo, min(hi, val))
    return round(val, 3) if is_float else int(round(val))

# Generate 300 Frankfurt rows (150 non-diabetic + 150 diabetic)
frankfurt_rows = []
for outcome, stats in FRANKFURT.items():
    for _ in range(150):
        row = []
        for feat in ['Pregnancies','Glucose','BloodPressure','SkinThickness',
                     'Insulin','BMI','DiabetesPedigreeFunction','Age']:
            mu, sd = stats[feat]
            lo, hi = CLIP[feat]
            is_float = feat in ('BMI','DiabetesPedigreeFunction')
            row.append(gauss_clip(mu, sd, lo, hi, is_float))
        row.append(outcome)
        frankfurt_rows.append(row)

# Shuffle Frankfurt rows
random.shuffle(frankfurt_rows)

# Read original Pima data
pima_rows = []
with open('ml_model/dataset/diabetes.csv', 'r') as f:
    reader = csv.reader(f)
    header = next(reader)
    for r in reader:
        if any(r):  # skip blank lines
            pima_rows.append(r)

print(f"Pima rows: {len(pima_rows)}")
print(f"Frankfurt rows: {len(frankfurt_rows)}")

# Write merged file
with open('ml_model/dataset/diabetes.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(header)
    for r in pima_rows:
        writer.writerow(r)
    for r in frankfurt_rows:
        writer.writerow(r)

total = len(pima_rows) + len(frankfurt_rows)
print(f"Total rows written: {total}")
print("Saved -> ml_model/dataset/diabetes.csv")
