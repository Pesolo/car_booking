import re
from datetime import datetime

def validate_email(email):
    """Validate email format"""
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if not password:
        return False
    
    # At least 8 characters
    if len(password) < 8:
        return False
    
    # Contains at least one letter and one number
    has_letter = any(c.isalpha() for c in password)
    has_number = any(c.isdigit() for c in password)
    
    return has_letter and has_number

def validate_datetime_format(datetime_str):
    """Validate ISO datetime format"""
    try:
        datetime.fromisoformat(datetime_str)
        return True
    except ValueError:
        return False