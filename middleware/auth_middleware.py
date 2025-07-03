from functools import wraps
from flask import request, jsonify, g
from services.auth_service import AuthService
import logging

logger = logging.getLogger(__name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Authorization token is required'}), 401
        
        try:
            auth_service = AuthService()
            payload = auth_service.verify_token(token)
            g.current_user_id = payload['user_id']
            
        except ValueError as e:
            return jsonify({'error': str(e)}), 401
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            return jsonify({'error': 'Authentication failed'}), 401
        
        return f(*args, **kwargs)
    
    return decorated