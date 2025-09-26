from flask import Blueprint, request, jsonify
from services.payment_service import PaymentService
from services.auth_service import AuthService
import logging

logger = logging.getLogger(__name__)
payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/initiate', methods=['POST'])
def initiate_payment():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        booking_id = data.get('booking_id')
        email = data.get('email')
        
        if not all([booking_id, email]):
            return jsonify({'error': 'booking_id and email are required'}), 400
        
        payment_service = PaymentService()
        result = payment_service.process_overtime_payment(booking_id, email)
        
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Overtime payment initiation error: {str(e)}")
        return jsonify({'error': 'Overtime payment initiation failed'}), 500service.initiate_payment(booking_id, email)
        
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Payment initiation error: {str(e)}")
        return jsonify({'error': 'Payment initiation failed'}), 500

@payment_bp.route('/callback', methods=['POST'])
def payment_callback():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        reference = data.get('reference')
        if not reference:
            return jsonify({'error': 'Payment reference is required'}), 400
        
        payment_service = PaymentService()
        result = payment_service.handle_payment_callback(reference)
        
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Payment callback error: {str(e)}")
        return jsonify({'error': 'Payment processing failed'}), 500

@payment_bp.route('/verify/<reference>', methods=['GET'])
def verify_payment(reference):
    """Get current payment status"""
    try:
        payment_service = PaymentService()
        result = payment_service.verify_payment_status(reference)
        
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Payment verification error: {str(e)}")
        return jsonify({'error': 'Payment verification failed'}), 500

# Additional endpoint for the frontend status polling
@payment_bp.route('/status/<reference>', methods=['GET'])
def get_payment_status(reference):
    """
    Frontend polling endpoint - same as verify but with better error handling
    """
    try:
        payment_service = PaymentService()
        result = payment_service.verify_payment_status(reference)
        
        # Enhanced logging for debugging
        logger.info(f"Payment status check for {reference}: {result.get('status')}")
        
        return jsonify(result), 200
        
    except ValueError as e:
        logger.error(f"Payment status validation error for {reference}: {str(e)}")
        return jsonify({'error': str(e), 'status': 'not_found'}), 404
    except Exception as e:
        logger.error(f"Payment status check error for {reference}: {str(e)}")
        return jsonify({
            'error': 'Failed to get payment status', 
            'status': 'error',
            'reference': reference
        }), 500

# Add overtime endpoints from your working code
@payment_bp.route('/overtime/calculate/<booking_id>', methods=['GET'])
def calculate_overtime(booking_id):
    """Calculate overtime amount for a booking"""
    try:
        payment_service = PaymentService()
        result = payment_service.calculate_overtime_amount(booking_id)
        
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Overtime calculation error: {str(e)}")
        return jsonify({'error': 'Failed to calculate overtime'}), 500

@payment_bp.route('/overtime/initiate', methods=['POST'])
def initiate_overtime_payment():
    """Initiate overtime payment"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        booking_id = data.get('booking_id')
        email = data.get('email')
        
        if not all([booking_id, email]):
            return jsonify({'error': 'booking_id and email are required'}), 400
        
        payment_service = PaymentService()
        result = payment_