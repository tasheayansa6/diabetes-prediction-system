"""
Input validation utilities
"""
import re
from typing import Tuple, Union, Any

def validate_email(email: str) -> bool:
    """
    Validate email format
    
    Args:
        email: Email address to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))

def validate_password(password: str) -> Tuple[bool, str]:
    """
    Validate password strength
    
    Rules:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    
    Args:
        password: Password to validate
    
    Returns:
        Tuple of (is_valid, message)
    """
    if not password or not isinstance(password, str):
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is valid"

def validate_health_data(data: dict) -> Tuple[bool, str]:
    """
    Validate health measurement data
    
    Args:
        data: Dictionary with health measurements
    
    Returns:
        Tuple of (is_valid, message)
    """
    required_fields = ['glucose', 'bmi', 'age', 'blood_pressure']
    
    # Check required fields
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    # Validate pregnancies — dataset max is 17
    if 'pregnancies' in data:
        try:
            pregnancies = int(data['pregnancies'])
            if pregnancies < 0 or pregnancies > 17:
                return False, "Pregnancies must be between 0 and 17 (enter 0 if male)"
        except (ValueError, TypeError):
            return False, "Pregnancies must be a valid integer"
    
    # Validate glucose (dataset range: 1–199 mg/dL)
    try:
        glucose = float(data['glucose'])
        if glucose < 1 or glucose > 199:
            return False, "Glucose must be between 1–199 mg/dL"
    except (ValueError, TypeError):
        return False, "Glucose must be a valid number"
    
    # Validate BMI (dataset range: 1–67.1)
    try:
        bmi = float(data['bmi'])
        if bmi < 1 or bmi > 67.1:
            return False, "BMI must be between 1–67.1"
    except (ValueError, TypeError):
        return False, "BMI must be a valid number"
    
    # Validate age — accept any realistic age; model handles extrapolation
    try:
        age = int(data['age'])
        if age < 1 or age > 120:
            return False, "Age must be between 1 and 120"
    except (ValueError, TypeError):
        return False, "Age must be a valid number"
    
    # Validate blood pressure (diastolic, reasonable range)
    try:
        bp = float(data['blood_pressure'])
        if bp < 1 or bp > 200:
            return False, "Blood pressure must be between 1–200 mm Hg"
    except (ValueError, TypeError):
        return False, "Blood pressure must be a valid number"
    
    # Validate skin thickness (dataset range: 0–99 mm)
    if 'skin_thickness' in data:
        try:
            st = float(data['skin_thickness'])
            if st < 0 or st > 99:
                return False, "Skin thickness must be between 0–99 mm"
        except (ValueError, TypeError):
            return False, "Skin thickness must be a valid number"
    
    # Validate insulin (dataset range: 0–846 mu U/ml)
    if 'insulin' in data:
        try:
            insulin = float(data['insulin'])
            if insulin < 0 or insulin > 846:
                return False, "Insulin must be between 0–846 mu U/ml"
        except (ValueError, TypeError):
            return False, "Insulin must be a valid number"
    
    # Validate diabetes pedigree function
    if 'diabetes_pedigree' in data:
        try:
            dpf = float(data['diabetes_pedigree'])
            if dpf < 0.001 or dpf > 3.0:
                return False, "Diabetes pedigree function must be between 0.001–3.0"
        except (ValueError, TypeError):
            return False, "Diabetes pedigree function must be a valid number"
    
    return True, "Health data is valid"

def validate_phone(phone: str) -> bool:
    """
    Validate phone number format
    
    Args:
        phone: Phone number to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not phone:
        return False
    
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
    
    # Check if it's all digits and length is valid
    return cleaned.isdigit() and 10 <= len(cleaned) <= 15