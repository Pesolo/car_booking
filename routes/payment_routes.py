# routes/payment_routes.py
from flask import Blueprint, request, jsonify
from services.payment_service import PaymentService
from services.booking_service import BookingService
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
        result = payment_service.initiate_payment(booking_id, email)
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
    try:
        payment_service = PaymentService()
        result = payment_service.verify_payment_status(reference)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Payment verification error: {str(e)}")
        return jsonify({'error': 'Payment verification failed'}), 500

@payment_bp.route('/status/<reference>', methods=['GET'])
def get_payment_status(reference):
    """Detailed payment status including booking info + auto-verify with Paystack"""
    try:
        payment_service = PaymentService()
        result = payment_service.verify_payment_status(reference, auto_verify=True)

        if result.get('status') == 'completed':
            booking_service = BookingService()
            booking = booking_service.get_booking_by_id(result['booking_id'])
            result['booking_details'] = {
                'booking_reference': booking.get('booking_reference'),
                'slot_location': booking.get('slot_location'),
                'start_time': booking.get('start_time'),
                'end_time': booking.get('end_time'),
                'qr_data': booking.get('qr_data'),
                'status': booking.get('status')
            }

        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Payment status check error: {str(e)}")
        return jsonify({'error': 'Failed to get payment status'}), 500
