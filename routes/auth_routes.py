from flask import Blueprint, request, jsonify
from services.auth_service import AuthService
from middleware.auth_middleware import token_required
from flask import g
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not all([name, email, password]):
            return jsonify({'error': 'Name, email, and password are required'}), 400
        
        auth_service = AuthService()
        result = auth_service.signup(name, email, password)
        
        return jsonify(result), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not all([email, password]):
            return jsonify({'error': 'Email and password are required'}), 400
        
        auth_service = AuthService()
        result = auth_service.login(email, password)
        
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user():
    try:
        auth_service = AuthService()
        user = auth_service.get_user_by_id(g.current_user_id)
        
        return jsonify(user), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        return jsonify({'error': 'Failed to get user details'}), 500