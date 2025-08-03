from datetime import datetime
from flask import Blueprint, request, jsonify, g
from services.booking_service import BookingService
from services.qr_service import QRService
import io
from middleware.auth_middleware import token_required
import logging

logger = logging.getLogger(__name__)
booking_bp = Blueprint('booking', __name__)

@booking_bp.route('/slots/available', methods=['GET'])
def get_available_slots():
    try:
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        if not all([start_time, end_time]):
            return jsonify({'error': 'start_time and end_time parameters are required'}), 400
        
        booking_service = BookingService()
        available_slots = booking_service.get_available_slots(start_time, end_time)
        
        return jsonify({'available_slots': available_slots}), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Get available slots error: {str(e)}")
        return jsonify({'error': 'Failed to get available slots'}), 500

@booking_bp.route('/bookings', methods=['POST'])
@token_required
def create_booking():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        slot_id = data.get('slot_id')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if not all([slot_id, start_time, end_time]):
            return jsonify({'error': 'slot_id, start_time, and end_time are required'}), 400
        
        booking_service = BookingService()
        result = booking_service.create_booking(g.current_user_id, slot_id, start_time, end_time)
        
        return jsonify(result), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Create booking error: {str(e)}")
        return jsonify({'error': 'Failed to create booking'}), 500

@booking_bp.route('/user/bookings', methods=['GET'])
@token_required
def get_user_bookings():
    try:
        booking_service = BookingService()
        bookings = booking_service.get_user_bookings(g.current_user_id)
        
        return jsonify({'bookings': bookings}), 200
        
    except Exception as e:
        logger.error(f"Get user bookings error: {str(e)}")
        return jsonify({'error': 'Failed to get user bookings'}), 500
    
@booking_bp.route('/bookings/<booking_id>/qr', methods=['GET'])
@token_required
def get_booking_qr(booking_id):
    """Get QR code for a specific booking"""
    try:
        booking_service = BookingService()
        booking = booking_service.get_booking_by_id(booking_id)
        
        # Verify booking belongs to current user
        if booking['user_id'] != g.current_user_id:
            return jsonify({'error': 'Unauthorized access to booking'}), 403
        
        # Check if booking is confirmed
        if booking['status'] != 'confirmed' and booking['status'] != 'in_use':
            return jsonify({'error': 'QR code not available for this booking status'}), 400
        
        # Return QR code data
        qr_data = booking.get('qr_data')
        qr_image = booking.get('qr_image_base64')
        
        if not qr_data:
            return jsonify({'error': 'QR code not generated yet'}), 404
        
        return jsonify({
            'qr_data': qr_data,
            'qr_image': qr_image,
            'booking_reference': booking.get('booking_reference'),
            'download_url': f'/bookings/{booking_id}/qr/download'
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Get booking QR error: {str(e)}")
        return jsonify({'error': 'Failed to get QR code'}), 500


@booking_bp.route('/bookings/<booking_id>/qr/download', methods=['GET'])
@token_required
def download_booking_qr(booking_id):
    """Download QR code image for a specific booking"""
    try:
        from flask import send_file
        
        booking_service = BookingService()
        booking = booking_service.get_booking_by_id(booking_id)
        
        # Verify booking belongs to current user
        if booking['user_id'] != g.current_user_id:
            return jsonify({'error': 'Unauthorized access to booking'}), 403
        
        # Check if booking is confirmed
        if booking['status'] != 'confirmed' and booking['status'] != 'in_use':
            return jsonify({'error': 'QR code not available for this booking status'}), 400
        
        qr_data = booking.get('qr_data')
        if not qr_data:
            return jsonify({'error': 'QR code not generated yet'}), 404
        
        # Generate fresh QR code image
        qr_service = QRService()
        booking_details = {
            'booking_reference': booking.get('booking_reference'),
            'slot_location': booking.get('slot_location'),
            'start_time': booking.get('start_time'),
            'end_time': booking.get('end_time'),
            'total_amount': booking.get('total_amount')
        }
        
        qr_image = qr_service.generate_qr_code(qr_data, booking_details)
        qr_bytes = qr_service.qr_to_bytes(qr_image)
        
        # Create file-like object
        qr_file = io.BytesIO(qr_bytes)
        
        # Generate filename
        booking_ref = booking.get('booking_reference', booking_id)
        filename = f"parking_qr_{booking_ref}.png"
        
        return send_file(
            qr_file,
            mimetype='image/png',
            as_attachment=True,
            download_name=filename
        )
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Download QR error: {str(e)}")
        return jsonify({'error': 'Failed to download QR code'}), 500


@booking_bp.route('/bookings/<booking_id>/qr/regenerate', methods=['POST'])
@token_required
def regenerate_booking_qr(booking_id):
    """Regenerate QR code for a booking (in case of corruption)"""
    try:
        booking_service = BookingService()
        booking = booking_service.get_booking_by_id(booking_id)
        
        # Verify booking belongs to current user
        if booking['user_id'] != g.current_user_id:
            return jsonify({'error': 'Unauthorized access to booking'}), 403
        
        # Check if booking is confirmed
        if booking['status'] != 'confirmed' and booking['status'] != 'in_use':
            return jsonify({'error': 'Cannot regenerate QR code for this booking status'}), 400
        
        # Regenerate QR code
        qr_service = QRService()
        qr_data = booking.get('qr_data')
        
        if not qr_data:
            return jsonify({'error': 'Original QR data not found'}), 404
        
        booking_details = {
            'booking_reference': booking.get('booking_reference'),
            'slot_location': booking.get('slot_location'),
            'start_time': booking.get('start_time'),
            'end_time': booking.get('end_time'),
            'total_amount': booking.get('total_amount')
        }
        
        qr_image = qr_service.generate_qr_code(qr_data, booking_details)
        qr_base64 = qr_service.qr_to_base64(qr_image)
        
        # Update booking with new QR image
        booking_service.update_booking_status(booking_id, booking['status'], {
            'qr_image_base64': qr_base64,
            'qr_regenerated_at': datetime.datetime.utcnow().isoformat()
        })
        
        return jsonify({
            'message': 'QR code regenerated successfully',
            'qr_image': qr_base64
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Regenerate QR error: {str(e)}")
        return jsonify({'error': 'Failed to regenerate QR code'}), 500