from flask import Blueprint, request, jsonify
from services.parking_service import ParkingService
import logging

logger = logging.getLogger(__name__)
parking_bp = Blueprint('parking', __name__)

@parking_bp.route('/validate', methods=['POST'])
def validate_qr():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        qr_data = data.get('qr_data')
        if not qr_data:
            return jsonify({'error': 'qr_data is required'}), 400
        
        parking_service = ParkingService()
        result = parking_service.validate_qr_code(qr_data)
        
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({
            'status': 'invalid',
            'message': str(e),
            'open_barrier': False
        }), 400
    except Exception as e:
        logger.error(f"QR validation error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Validation failed',
            'open_barrier': False
        }), 500

@parking_bp.route('/slots', methods=['GET'])
def get_all_slots():
    try:
        parking_service = ParkingService()
        slots = parking_service.get_all_slots()
        
        return jsonify({'slots': slots}), 200
        
    except Exception as e:
        logger.error(f"Get slots error: {str(e)}")
        return jsonify({'error': 'Failed to get parking slots'}), 500

@parking_bp.route('/slots', methods=['POST'])
def create_slot():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        location = data.get('location')
        description = data.get('description', '')
        rate_per_hour = data.get('rate_per_hour')
        
        if not all([location, rate_per_hour]):
            return jsonify({'error': 'location and rate_per_hour are required'}), 400
        
        parking_service = ParkingService()
        result = parking_service.create_slot(location, description, rate_per_hour)
        
        return jsonify(result), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Create slot error: {str(e)}")
        return jsonify({'error': 'Failed to create parking slot'}), 500