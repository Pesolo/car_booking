# services/payment_service.py
from datetime import datetime, timedelta
import requests
from config import Config
from services.booking_service import BookingService
from services.firebase_service import FirebaseService
from services.qr_service import QRService
import logging

logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self):
        self.booking_service = BookingService()
        self.firebase = FirebaseService()
        self.qr_service = QRService()
        self.bookings_ref = self.firebase.get_db_reference('bookings')
        self.payments_ref = self.firebase.get_db_reference('payments')
    
    def initiate_payment(self, booking_id, email):
        """Initiate payment with Paystack"""
        booking = self.booking_service.get_booking_by_id(booking_id)
        if booking['status'] != 'pending':
            raise ValueError("Booking is not pending payment")
        
        amount_kobo = int(booking['total_amount'] * 100)
        frontend_url = getattr(Config, 'FRONTEND_URL', 'http://localhost:3000')
        timestamp = int(datetime.now().timestamp())
        unique_reference = f"booking_{booking_id}_{timestamp}"
        
        payload = {
            'email': email,
            'amount': amount_kobo,
            'reference': unique_reference,
            'callback_url': f"{frontend_url}/payment/callback",
            'metadata': {
                'booking_id': booking_id,
                'type': 'parking_booking'
            }
        }
        
        headers = {
            'Authorization': f'Bearer {Config.PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json'
        }
        
        try:
            paystack_base_url = getattr(Config, 'PAYSTACK_BASE_URL', 'https://api.paystack.co')
            response = requests.post(
                f'{paystack_base_url}/transaction/initialize',
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Paystack API error: {response.text}")
                raise Exception("Payment initiation failed")
            
            payment_data = response.json()['data']
            
            payment_record = {
                'booking_id': booking_id,
                'reference': payload['reference'],
                'amount': booking['total_amount'],
                'status': 'pending',
                'paystack_reference': payment_data['reference'],
                'created_at': datetime.utcnow().isoformat()
            }
            
            self.payments_ref.child(payment_data['reference']).set(payment_record)
            
            return {
                'authorization_url': payment_data['authorization_url'],
                'reference': payment_data['reference']
            }
            
        except requests.RequestException as e:
            logger.error(f"Payment initiation network error: {str(e)}")
            raise Exception("Payment service unavailable")
    
    def handle_payment_callback(self, reference):
        """Verify and complete a payment using Paystack"""
        headers = {'Authorization': f'Bearer {Config.PAYSTACK_SECRET_KEY}'}
        paystack_base_url = getattr(Config, 'PAYSTACK_BASE_URL', 'https://api.paystack.co')
        
        try:
            response = requests.get(
                f'{paystack_base_url}/transaction/verify/{reference}',
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception("Payment verification failed")
            
            payment_data = response.json()['data']
            
            if payment_data['status'] != 'success':
                raise Exception("Payment was not successful")
            
            # Get payment record
            payment_record = self.payments_ref.child(reference).get()
            if not payment_record:
                raise Exception("Payment record not found")
            
            booking_id = payment_record['booking_id']
            booking = self.booking_service.get_booking_by_id(booking_id)
            
            # Update payment
            self.payments_ref.child(reference).update({
                'status': 'completed',
                'completed_at': datetime.utcnow().isoformat(),
                'paystack_data': payment_data
            })
            
            # Generate QR
            qr_data = f'PARKING:{booking_id}:{booking.get("user_id", "")}:{booking.get("slot_id", "")}'
            booking_details = {
                'booking_reference': booking.get('booking_reference'),
                'slot_location': booking.get('slot_location'),
                'start_time': booking.get('start_time'),
                'end_time': booking.get('end_time'),
                'total_amount': booking.get('total_amount')
            }
            
            qr_image = self.qr_service.generate_qr_code(qr_data, booking_details)
            qr_base64 = self.qr_service.qr_to_base64(qr_image)
            
            self.booking_service.update_booking_status(booking_id, 'confirmed', {
                'qr_data': qr_data,
                'qr_image_base64': qr_base64,
                'payment_reference': reference,
                'paid_at': datetime.utcnow().isoformat()
            })
            
            logger.info(f"Payment completed for booking: {booking_id}")
            
            return {
                'status': 'completed',
                'message': 'Payment successful',
                'booking_id': booking_id,
                'qr_data': qr_data,
                'qr_image': qr_base64,
                'booking_reference': booking.get('booking_reference')
            }
            
        except requests.RequestException as e:
            logger.error(f"Payment verification network error: {str(e)}")
            raise Exception("Payment verification failed")

    def verify_payment_status(self, reference, auto_verify=False):
        """Check Firebase payment record, optionally re-verify with Paystack if pending"""
        payment_record = self.payments_ref.child(reference).get()
        if not payment_record:
            raise ValueError('Payment record not found')
        
        status = payment_record.get('status')
        
        # Auto-check Paystack if still pending
        if auto_verify and status in ['pending', 'processing']:
            try:
                return self.handle_payment_callback(reference)
            except Exception as e:
                logger.warning(f"Auto verification for {reference} failed: {str(e)}")
        
        return {
            'reference': reference,
            'status': status,
            'amount': payment_record.get('amount'),
            'booking_id': payment_record.get('booking_id'),
            'created_at': payment_record.get('created_at'),
            'completed_at': payment_record.get('completed_at')
        }
