import joblib
import numpy as np
import pandas as pd
import os

def explain_prediction(features, 
                      model_path='ml_model/saved_models/logistic_regression.pkl',
                      scaler_path='ml_model/saved_models/scaler.pkl',
                      feature_names_path='ml_model/saved_models/feature_names.json'):
   
    import json
    
    # Load model and scaler
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    
    # Load feature names (or use defaults)
    try:
        with open(feature_names_path, 'r') as f:
            feature_names = json.load(f)
    except:
        feature_names = ['Pregnancies', 'Glucose', 'BloodPressure', 'SkinThickness', 
                         'Insulin', 'BMI', 'DiabetesPedigreeFunction', 'Age']
    
    # Prepare feature array with proper mapping
    feature_mapping = {
        'pregnancies': 'Pregnancies',
        'glucose': 'Glucose',
        'blood_pressure': 'BloodPressure',
        'bp': 'BloodPressure',
        'skin_thickness': 'SkinThickness',
        'skin': 'SkinThickness',
        'insulin': 'Insulin',
        'bmi': 'BMI',
        'diabetes_pedigree': 'DiabetesPedigreeFunction',
        'pedigree': 'DiabetesPedigreeFunction',
        'dpf': 'DiabetesPedigreeFunction',
        'age': 'Age'
    }
    
    # Create feature array in correct order
    feature_values = []
    feature_dict = {}
    
    for feat_name in feature_names:
        found = False
        for input_key, input_value in features.items():
            input_key_lower = input_key.lower().strip()
            if input_key_lower in feature_mapping and feature_mapping[input_key_lower] == feat_name:
                feature_values.append(float(input_value))
                feature_dict[feat_name] = float(input_value)
                found = True
                break
        
        if not found:
            # Use defaults for missing features
            defaults = {
                'Pregnancies': 0,
                'Glucose': 100,
                'BloodPressure': 70,
                'SkinThickness': 20,
                'Insulin': 80,
                'BMI': 25,
                'DiabetesPedigreeFunction': 0.5,
                'Age': 30
            }
            default_val = defaults.get(feat_name, 0)
            feature_values.append(default_val)
            feature_dict[feat_name] = default_val
    
    # Convert to numpy array
    feature_array = np.array([feature_values])
    
    # Scale features
    feature_scaled = scaler.transform(feature_array)
    
    # Get prediction
    probability = model.predict_proba(feature_scaled)[0][1]
    prediction = model.predict(feature_scaled)[0]
    
    # Get coefficients (for logistic regression)
    if hasattr(model, 'coef_'):
        coefficients = model.coef_[0]
        
        # Calculate feature contributions (using scaled values for accurate interpretation)
        scaled_contributions = feature_scaled[0] * coefficients
        original_contributions = feature_array[0] * coefficients  # for reference
        
        # Get baseline (intercept)
        intercept = model.intercept_[0] if hasattr(model, 'intercept_') else 0
        
        # Create detailed explanation
        feature_impact = []
        for i, name in enumerate(feature_names):
            impact_type = 'Increases risk' if coefficients[i] > 0 else 'Decreases risk'
            strength = 'Strong' if abs(coefficients[i]) > 0.5 else 'Moderate' if abs(coefficients[i]) > 0.2 else 'Weak'
            
            feature_impact.append({
                'feature': name,
                'value': float(feature_array[0][i]),
                'scaled_value': float(feature_scaled[0][i]),
                'coefficient': float(coefficients[i]),
                'contribution': float(scaled_contributions[i]),
                'impact_direction': impact_type,
                'impact_strength': strength,
                'percent_contribution': float(abs(scaled_contributions[i]) / (sum(abs(scaled_contributions)) + 1e-10) * 100)
            })
        
        # Sort by absolute contribution
        feature_impact.sort(key=lambda x: abs(x['contribution']), reverse=True)
        
        # Calculate probability formula
        log_odds = intercept + sum(scaled_contributions)
        calculated_prob = 1 / (1 + np.exp(-log_odds))
        
        return {
            'success': True,
            'prediction': 'Diabetic' if prediction == 1 else 'Non-Diabetic',
            'prediction_code': int(prediction),
            'probability': float(probability),
            'probability_percent': float(probability * 100),
            'log_odds': float(log_odds),
            'intercept': float(intercept),
            'top_factors': feature_impact[:5],
            'all_factors': feature_impact,
            'feature_importance': [{'feature': f['feature'], 
                                   'importance': abs(f['coefficient'])} 
                                  for f in feature_impact],
            'formula': {
                'log_odds_formula': f"log_odds = {intercept:.4f} + " + " + ".join([f"({f['coefficient']:.4f} × {f['scaled_value']:.2f})" for f in feature_impact[:3]]),
                'probability_formula': f"probability = 1 / (1 + e^(-log_odds)) = {calculated_prob:.4f}"
            }
        }
    
    return {'success': False, 'message': 'Model does not support feature importance'}


def get_risk_factors(features, medical_thresholds=None):
    
    # Default medical thresholds
    default_thresholds = {
        'glucose': {
            'normal': (70, 99),
            'prediabetes': (100, 125),
            'diabetes': (126, float('inf')),
            'warning': 'High glucose level'
        },
        'bmi': {
            'normal': (18.5, 24.9),
            'overweight': (25, 29.9),
            'obese': (30, float('inf')),
            'warning': 'High BMI'
        },
        'blood_pressure': {
            'normal': (60, 80),
            'elevated': (81, 89),
            'high': (90, float('inf')),
            'warning': 'High blood pressure'
        },
        'age': {
            'low_risk': (0, 35),
            'moderate_risk': (36, 50),
            'high_risk': (51, float('inf')),
            'warning': 'Age-related risk'
        },
        'diabetes_pedigree': {
            'low': (0, 0.3),
            'moderate': (0.3, 0.7),
            'high': (0.7, float('inf')),
            'warning': 'Family history risk'
        },
        'pregnancies': {
            'low': (0, 3),
            'moderate': (4, 6),
            'high': (7, float('inf')),
            'warning': 'Multiple pregnancies'
        }
    }
    
    thresholds = medical_thresholds or default_thresholds
    
    risk_factors = {
        'critical_risks': [],
        'moderate_risks': [],
        'lifestyle_factors': [],
        'protective_factors': []
    }
    
    # Check glucose
    glucose = features.get('glucose', features.get('Glucose', 100))
    if glucose >= 126:
        risk_factors['critical_risks'].append({
            'factor': 'High Glucose',
            'value': glucose,
            'threshold': '≥126 mg/dL',
            'advice': 'Immediate medical consultation needed',
            'severity': 'CRITICAL'
        })
    elif glucose >= 100:
        risk_factors['moderate_risks'].append({
            'factor': 'Elevated Glucose',
            'value': glucose,
            'threshold': '100-125 mg/dL (Pre-diabetes)',
            'advice': 'Dietary changes recommended',
            'severity': 'MODERATE'
        })
    else:
        risk_factors['protective_factors'].append({
            'factor': 'Normal Glucose',
            'value': glucose,
            'threshold': '<100 mg/dL',
            'advice': 'Maintain current diet'
        })
    
    # Check BMI
    bmi = features.get('bmi', features.get('BMI', 25))
    if bmi >= 30:
        risk_factors['critical_risks'].append({
            'factor': 'Obese BMI',
            'value': bmi,
            'threshold': '≥30 (Obese)',
            'advice': 'Weight loss program recommended',
            'severity': 'HIGH'
        })
    elif bmi >= 25:
        risk_factors['moderate_risks'].append({
            'factor': 'Overweight BMI',
            'value': bmi,
            'threshold': '25-29.9 (Overweight)',
            'advice': 'Consider weight management',
            'severity': 'MODERATE'
        })
    else:
        risk_factors['protective_factors'].append({
            'factor': 'Healthy BMI',
            'value': bmi,
            'threshold': '18.5-24.9',
            'advice': 'Maintain healthy weight'
        })
    
    # Check Blood Pressure
    bp = features.get('blood_pressure', features.get('BloodPressure', features.get('bp', 80)))
    if bp >= 90:
        risk_factors['critical_risks'].append({
            'factor': 'High Blood Pressure',
            'value': bp,
            'threshold': '≥90 mmHg',
            'advice': 'Monitor BP regularly, consult doctor',
            'severity': 'HIGH'
        })
    elif bp >= 80:
        risk_factors['moderate_risks'].append({
            'factor': 'Elevated Blood Pressure',
            'value': bp,
            'threshold': '80-89 mmHg',
            'advice': 'Reduce sodium intake',
            'severity': 'MODERATE'
        })
    
    # Check Age
    age = features.get('age', features.get('Age', 30))
    if age >= 50:
        risk_factors['moderate_risks'].append({
            'factor': 'Age',
            'value': age,
            'threshold': '≥50 years',
            'advice': 'Regular screening recommended',
            'severity': 'MODERATE'
        })
    
    # Check Family History
    dpf = features.get('diabetes_pedigree', features.get('DiabetesPedigreeFunction', 
                     features.get('pedigree', features.get('dpf', 0.5))))
    if dpf >= 0.7:
        risk_factors['moderate_risks'].append({
            'factor': 'Strong Family History',
            'value': dpf,
            'threshold': '≥0.7',
            'advice': 'Genetic predisposition - extra vigilance needed',
            'severity': 'MODERATE'
        })
    
    # Check Pregnancies (if female)
    pregnancies = features.get('pregnancies', features.get('Pregnancies', 0))
    if pregnancies >= 7:
        risk_factors['moderate_risks'].append({
            'factor': 'Multiple Pregnancies',
            'value': pregnancies,
            'threshold': '≥7',
            'advice': 'History of gestational diabetes risk',
            'severity': 'MODERATE'
        })
    
    # Check Insulin (if provided)
    insulin = features.get('insulin', features.get('Insulin', None))
    if insulin and insulin > 200:
        risk_factors['critical_risks'].append({
            'factor': 'High Insulin',
            'value': insulin,
            'threshold': '>200 μU/ml',
            'advice': 'Possible insulin resistance',
            'severity': 'HIGH'
        })
    
    return risk_factors


def generate_personalized_recommendations(features, risk_factors):
    """
    Generate personalized recommendations based on risk factors
    """
    recommendations = []
    
    # Diet recommendations
    glucose = features.get('glucose', features.get('Glucose', 100))
    if glucose > 100:
        recommendations.append({
            'category': 'Diet',
            'recommendation': 'Reduce sugar and refined carbohydrates',
            'specifics': ['Limit sugary drinks', 'Choose whole grains', 'Eat more fiber'],
            'priority': 'HIGH' if glucose > 125 else 'MEDIUM'
        })
    
    # Exercise recommendations
    bmi = features.get('bmi', features.get('BMI', 25))
    if bmi > 25:
        recommendations.append({
            'category': 'Exercise',
            'recommendation': 'Increase physical activity',
            'specifics': ['30 min moderate exercise daily', 'Brisk walking', 'Strength training 2x/week'],
            'priority': 'HIGH' if bmi > 30 else 'MEDIUM'
        })
    
    # Blood pressure recommendations
    bp = features.get('blood_pressure', features.get('BloodPressure', 80))
    if bp > 80:
        recommendations.append({
            'category': 'Lifestyle',
            'recommendation': 'Manage blood pressure',
            'specifics': ['Reduce sodium', 'Limit alcohol', 'Manage stress', 'Quit smoking if applicable'],
            'priority': 'HIGH' if bp > 90 else 'MEDIUM'
        })
    
    # Age-based recommendations
    age = features.get('age', features.get('Age', 30))
    if age > 40:
        recommendations.append({
            'category': 'Screening',
            'recommendation': 'Regular health checkups',
            'specifics': ['Annual blood glucose test', 'HbA1c test if recommended', 'Eye examination'],
            'priority': 'MEDIUM'
        })
    
    return recommendations


def print_pretty_explanation(features):
    """
    Print a nicely formatted explanation
    """
    print("\n" + "="*70)
    print("DIABETES RISK ASSESSMENT REPORT")
    print("="*70)
    
    # Get prediction explanation
    explanation = explain_prediction(features)
    
    if not explanation.get('success'):
        print("Error generating explanation")
        return
    
    # Get risk factors
    risk_factors = get_risk_factors(features)
    
    # Print patient data
    print("\n📋 PATIENT DATA:")
    print("-"*40)
    for key, value in features.items():
        print(f"   {key:20s}: {value}")
    
    # Print prediction
    print(f"\n🎯 PREDICTION: {explanation['prediction']}")
    print(f"   Probability: {explanation['probability_percent']:.1f}%")
    
    # Print risk level with color
    prob = explanation['probability_percent']
    if prob < 30:
        risk_color, risk_level = "🟢", "LOW RISK"
    elif prob < 60:
        risk_color, risk_level = "🟡", "MODERATE RISK"
    elif prob < 80:
        risk_color, risk_level = "🟠", "HIGH RISK"
    else:
        risk_color, risk_level = "🔴", "VERY HIGH RISK"
    
    print(f"   Risk Level: {risk_color} {risk_level}")
    
    # Print top contributing factors
    print("\n📊 TOP CONTRIBUTING FACTORS:")
    print("-"*40)
    for i, factor in enumerate(explanation['top_factors'][:5], 1):
        arrow = "⬆️" if factor['impact_direction'] == 'Increases risk' else "⬇️"
        print(f"   {i}. {factor['feature']}: {factor['value']} {arrow}")
        print(f"      Contribution: {factor['percent_contribution']:.1f}% | Impact: {factor['impact_strength']}")
    
    # Print critical risks
    if risk_factors['critical_risks']:
        print("\n🔴 CRITICAL RISK FACTORS:")
        print("-"*40)
        for risk in risk_factors['critical_risks']:
            print(f"   • {risk['factor']}: {risk['value']} ({risk['advice']})")
    
    # Print moderate risks
    if risk_factors['moderate_risks']:
        print("\n🟡 MODERATE RISK FACTORS:")
        print("-"*40)
        for risk in risk_factors['moderate_risks']:
            print(f"   • {risk['factor']}: {risk['value']} ({risk['advice']})")
    
    # Print protective factors
    if risk_factors['protective_factors']:
        print("\n🟢 PROTECTIVE FACTORS:")
        print("-"*40)
        for factor in risk_factors['protective_factors']:
            print(f"   • {factor['factor']}: {factor['value']} ({factor['advice']})")
    
    # Generate and print recommendations
    recommendations = generate_personalized_recommendations(features, risk_factors)
    if recommendations:
        print("\n💡 PERSONALIZED RECOMMENDATIONS:")
        print("-"*40)
        for rec in recommendations:
            print(f"   • {rec['category']} ({rec['priority']}):")
            print(f"     {rec['recommendation']}")
            for specific in rec['specifics'][:2]:
                print(f"     - {specific}")
    
    print("\n" + "="*70)
    print("⚠️ NOTE: This is a screening tool only.")
    print("Please consult a healthcare provider for medical advice.")
    print("="*70)


if __name__ == '__main__':
    # Example usage with different risk profiles
    
    print("="*70)
    print("DIABETES PREDICTION EXPLANATION SYSTEM")
    print("="*70)
    
    # Example 1: High risk patient
    print("\n📌 EXAMPLE 1: High Risk Patient")
    sample_data_1 = {
        'pregnancies': 5,
        'glucose': 180,
        'blood_pressure': 95,
        'skin_thickness': 35,
        'insulin': 200,
        'bmi': 35.5,
        'diabetes_pedigree': 0.8,
        'age': 55
    }
    print_pretty_explanation(sample_data_1)
    
    # Example 2: Low risk patient
    print("\n📌 EXAMPLE 2: Low Risk Patient")
    sample_data_2 = {
        'pregnancies': 0,
        'glucose': 85,
        'blood_pressure': 65,
        'skin_thickness': 15,
        'insulin': 50,
        'bmi': 22.5,
        'diabetes_pedigree': 0.2,
        'age': 25
    }
    print_pretty_explanation(sample_data_2)
    
    # Example 3: How to use the functions programmatically
    print("\n📌 EXAMPLE 3: Programmatic Usage")
    sample_data_3 = {
        'pregnancies': 2,
        'glucose': 130,
        'blood_pressure': 82,
        'bmi': 28.5,
        'diabetes_pedigree': 0.6,
        'age': 45
    }
    
    # Get explanation
    explanation = explain_prediction(sample_data_3)
    
    # Get risk factors
    risks = get_risk_factors(sample_data_3)
    
    print(f"\nPrediction: {explanation['prediction']} ({explanation['probability_percent']:.1f}%)")
    print(f"Top risk factor: {explanation['top_factors'][0]['feature']} - {explanation['top_factors'][0]['value']}")
    
    # Save results to file (optional)
    import json
    output = {
        'prediction': explanation,
        'risk_factors': risks,
        'timestamp': pd.Timestamp.now().isoformat()
    }
    
   