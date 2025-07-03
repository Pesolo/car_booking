import jwt
import datetime
from hashlib import sha256
from flask import current_app
from services.firebase_service import FirebaseService
from utils.validators import validate_email, validate_password
from config import Config
import logging

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        self.firebase = FirebaseService()
        self.users_ref = self.firebase.get_db_reference('users')
    
    def generate_user_id(self, email):
        """Generate unique user ID from email"""
        return sha256(email.encode()).hexdigest()
    
    def hash_password(self, password):
        """Hash password using SHA256"""
        return sha256(password.encode()).hexdigest()
    
    def generate_token(self, user_id):
        """Generate JWT token for user"""
        try:
            payload = {
                'user_id': user_id,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=Config.JWT_EXPIRATION_HOURS),
                'iat': datetime.datetime.utcnow()
            }
            token = jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)
            return token
        except Exception as e:
            logger.error(f"Token generation failed: {str(e)}")
            raise
    
    def verify_token(self, token):
        """Verify JWT token and return payload"""
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
    
    def signup(self, name, email, password):
        """Register new user"""
        # Validate inputs
        if not validate_email(email):
            raise ValueError("Invalid email format")
        
        if not validate_password(password):
            raise ValueError("Password must be at least 8 characters long")
        
        if not name or len(name.strip()) < 2:
            raise ValueError("Name must be at least 2 characters long")
        
        # Check if user already exists
        existing_user = self.users_ref.order_by_child('email').equal_to(email).get()
        if existing_user:
            raise ValueError("Email already exists")
        
        # Create new user
        user_id = self.generate_user_id(email)
        user_data = {
            'name': name.strip(),
            'email': email.lower(),
            'password': self.hash_password(password),
            'created_at': datetime.datetime.utcnow().isoformat(),
            'is_active': True
        }
        
        self.users_ref.child(user_id).set(user_data)
        token = self.generate_token(user_id)
        
        logger.info(f"New user registered: {email}")
        return {'token': token, 'user_id': user_id}
    
    def login(self, email, password):
        """Authenticate user login"""
        if not email or not password:
            raise ValueError("Email and password are required")
        
        # Find user by email
        user_query = self.users_ref.order_by_child('email').equal_to(email.lower()).get()
        if not user_query:
            raise ValueError("Invalid email or password")
        
        user_id, user_data = next(iter(user_query.items()))
        
        # Check if user is active
        if not user_data.get('is_active', True):
            raise ValueError("Account is deactivated")
        
        # Verify password
        if user_data['password'] != self.hash_password(password):
            raise ValueError("Invalid email or password")
        
        # Update last login
        self.users_ref.child(user_id).update({
            'last_login': datetime.datetime.utcnow().isoformat()
        })
        
        token = self.generate_token(user_id)
        logger.info(f"User logged in: {email}")
        
        return {'token': token, 'user_id': user_id}
    
    def get_user_by_id(self, user_id):
        """Get user details by ID"""
        user = self.users_ref.child(user_id).get()
        if not user:
            raise ValueError("User not found")
        
        # Remove sensitive information
        user_safe = {
            'name': user.get('name'),
            'email': user.get('email'),
            'created_at': user.get('created_at'),
            'last_login': user.get('last_login')
        }
        return user_safe