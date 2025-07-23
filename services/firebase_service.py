import firebase_admin
from firebase_admin import credentials, db
from config import Config
import logging
import os

logger = logging.getLogger(__name__)

class FirebaseService:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseService, cls).__new__(cls)
        return cls._instance
    
    def initialize(self):
        """Initialize Firebase Admin SDK"""
        if self._initialized:
            return
            
        try:
            # Check if we have environment variables for Firebase (production)
            if all([Config.FIREBASE_PROJECT_ID, Config.FIREBASE_PRIVATE_KEY, Config.FIREBASE_CLIENT_EMAIL]):
                logger.info("Initializing Firebase with environment variables")
                
                # Create credentials from environment variables
                cred_dict = {
                    "type": "service_account",
                    "project_id": Config.FIREBASE_PROJECT_ID,
                    "private_key_id": Config.PRIVATE_KEY_ID,
                    "private_key": Config.FIREBASE_PRIVATE_KEY.replace('\\n', '\n'),  # Handle escaped newlines
                    "client_email": Config.FIREBASE_CLIENT_EMAIL,
                    "client_id": Config.CLIENT_ID,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40car-22792.iam.gserviceaccount.com",
                    "universe_domain": "googleapis.com"
                }
                
                cred = credentials.Certificate(cred_dict)
                
            # Fallback to credential file (local development)
            elif os.path.exists(Config.FIREBASE_CREDENTIALS_PATH):
                logger.info("Initializing Firebase with credential file")
                cred = credentials.Certificate(Config.FIREBASE_CREDENTIALS_PATH)
                
            else:
                raise Exception("No Firebase credentials found. Please provide either credential file or environment variables.")
            
            # Initialize Firebase App
            firebase_admin.initialize_app(cred, {
                'databaseURL': Config.FIREBASE_DATABASE_URL
            })
            
            self._initialized = True
            logger.info("Firebase initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            raise
    
    @staticmethod
    def get_db_reference(path=''):
        """Get Firebase database reference"""
        return db.reference(path)
    
    def is_initialized(self):
        """Check if Firebase is initialized"""
        return self._initialized