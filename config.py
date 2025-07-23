import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.getenv('FLASK_ENV') == 'development'
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    
    # Firebase Configuration - Support both file and env vars
    FIREBASE_CREDENTIALS_PATH = os.getenv('FIREBASE_CREDENTIALS_PATH', 'config/serviceAccountKey.json')
    FIREBASE_DATABASE_URL = os.getenv('FIREBASE_DATABASE_URL', 'https://your-firebase-project.firebaseio.com')
    
    # Firebase Environment Variables (for production)
    FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID')
    FIREBASE_PRIVATE_KEY = os.getenv('FIREBASE_PRIVATE_KEY')
    FIREBASE_CLIENT_EMAIL = os.getenv('FIREBASE_CLIENT_EMAIL')
    CLIENT_ID = os.getenv('CLIENT_ID')
    PRIVATE_KEY_ID = os.getenv('PRIVATE_KEY_ID')
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', 24))
    
    # Paystack Configuration
    PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
    PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY')
    PAYSTACK_BASE_URL = 'https://api.paystack.co'
    
    # Parking Configuration
    DEFAULT_PARKING_RATE = float(os.getenv('DEFAULT_PARKING_RATE', 2.0))  # per hour
    GRACE_PERIOD_MINUTES = int(os.getenv('GRACE_PERIOD_MINUTES', 10))
    
    # CORS Configuration - Enhanced for mobile apps
    ALLOWED_ORIGINS_ENV = os.getenv('ALLOWED_ORIGINS', '*')
    ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_ENV.split(',')] if ALLOWED_ORIGINS_ENV != '*' else ['*']
    CORS_SUPPORTS_CREDENTIALS = os.getenv('CORS_SUPPORTS_CREDENTIALS', 'false').lower() == 'true'
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE_PATH = os.getenv('LOG_FILE_PATH', 'logs/app.log')