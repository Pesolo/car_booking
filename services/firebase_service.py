import firebase_admin
from firebase_admin import credentials, db
from config import Config
import logging

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
            cred = credentials.Certificate(Config.FIREBASE_CREDENTIALS_PATH)
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