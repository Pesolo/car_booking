from datetime import datetime
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
        # Get booking details
        booking = self.booking_service.get_booking_by_id(booking_id)
        if booking['status'] != 'pending':
            raise ValueError("Booking is not pending payment")
        
        amount_kobo = int(booking['total_amount'] * 100)  # Convert to kobo
        
        # Get frontend URL with fallback
        frontend_url = getattr(Config, 'FRONTEND_URL', 'http://localhost:3000')
        
        # Generate unique reference to avoid duplicates
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
            # Get Paystack base URL with fallback
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
            
            # Store payment record - FIXED: Use datetime instead of datetime.datetime
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
        """Handle payment callback from Paystack"""
        # Verify payment with Paystack
        headers = {
            'Authorization': f'Bearer {Config.PAYSTACK_SECRET_KEY}'
        }
        
        try:
            # Get Paystack base URL with fallback
            paystack_base_url = getattr(Config, 'PAYSTACK_BASE_URL', 'https://api.paystack.co')
            
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
            
            # After successful payment verification, generate QR code
            if payment_data['status'] == 'success':
                # Get payment record
                payment_record = self.payments_ref.child(reference).get()
                if not payment_record:
                    raise Exception("Payment record not found")
                
                booking_id = payment_record['booking_id']
                
                # Get booking details for QR code
                booking = self.booking_service.get_booking_by_id(booking_id)
                
                # Update payment status - FIXED: Use datetime instead of datetime.datetime
                self.payments_ref.child(reference).update({
                    'status': 'completed',
                    'completed_at': datetime.utcnow().isoformat(),
                    'paystack_data': payment_data
                })
                
                # Generate QR code data and image
                qr_data = f'PARKING:{booking_id}:{booking.get("user_id", "")}:{booking.get("slot_id", "")}'
                
                # Generate QR code image
                booking_details = {
                    'booking_reference': booking.get('booking_reference'),
                    'slot_location': booking.get('slot_location'),
                    'start_time': booking.get('start_time'),
                    'end_time': booking.get('end_time'),
                    'total_amount': booking.get('total_amount')
                }
                
                qr_image = self.qr_service.generate_qr_code(qr_data, booking_details)
                qr_base64 = self.qr_service.qr_to_base64(qr_image)
                
                # Update booking with QR data and image - FIXED: Use datetime instead of datetime.datetime
                self.booking_service.update_booking_status(booking_id, 'confirmed', {
                    'qr_data': qr_data,
                    'qr_image_base64': qr_base64,
                    'payment_reference': reference,
                    'paid_at': datetime.utcnow().isoformat()
                })
                
                logger.info(f"Payment completed for booking: {booking_id}")
                
                return {
                    'message': 'Payment successful',
                    'booking_id': booking_id,
                    'qr_data': qr_data,
                    'qr_image': qr_base64
                }
            
        except requests.RequestException as e:
            logger.error(f"Payment verification network error: {str(e)}")
            raise Exception("Payment verification failed")

    def verify_payment_status(self, reference):
        """Verify payment status by reference"""
        payment_record = self.payments_ref.child(reference).get()
        if not payment_record:
            raise ValueError('Payment record not found')
        
        return {
            'reference': reference,
            'status': payment_record.get('status'),
            'amount': payment_record.get('amount'),
            'booking_id': payment_record.get('booking_id'),
            'created_at': payment_record.get('created_at'),
            'completed_at': payment_record.get('completed_at')
        }
    
    def calculate_overtime_amount(self, booking_id):
        """Calculate overtime amount for a booking"""
        booking = self.booking_service.get_booking_by_id(booking_id)
        
        now = datetime.now()
        end_time = datetime.fromisoformat(booking['end_time'])
        
        # Get grace period with fallback
        grace_period_minutes = getattr(Config, 'GRACE_PERIOD_MINUTES', 15)
        grace_period = datetime.timedelta(minutes=grace_period_minutes)
        
        if now <= end_time + grace_period:
            return {'overtime_required': False, 'amount': 0}
        
        overtime_duration = now - end_time
        overtime_hours = overtime_duration.total_seconds() / 3600
        
        # Get default parking rate with fallback
        default_rate = getattr(Config, 'DEFAULT_PARKING_RATE', 100.0)
        overtime_amount = round(overtime_hours * default_rate, 2)
        
        return {
            'overtime_required': True,
            'amount': overtime_amount,
            'duration_hours': round(overtime_hours, 2),
            'rate_per_hour': default_rate
        }
    
    def process_overtime_payment(self, booking_id, email):
        """Process overtime payment for a booking"""
        overtime_info = self.calculate_overtime_amount(booking_id)
        
        if not overtime_info['overtime_required']:
            raise ValueError('No overtime payment required')
        
        # Similar to initiate_payment but for overtime
        amount_kobo = int(overtime_info['amount'] * 100)
        
        # Get frontend URL with fallback
        frontend_url = getattr(Config, 'FRONTEND_URL', 'http://localhost:3000')
        
        payload = {
            'email': email,
            'amount': amount_kobo,
            'reference': f"overtime_{booking_id}_{int(datetime.now().timestamp())}",
            'callback_url': f"{frontend_url}/payment/overtime-callback",
            'metadata': {
                'booking_id': booking_id,
                'type': 'overtime_payment'
            }
        }
        
        headers = {
            'Authorization': f'Bearer {Config.PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Get Paystack base URL with fallback
            paystack_base_url = getattr(Config, 'PAYSTACK_BASE_URL', 'https://api.paystack.co')
            
            response = requests.post(
                f'{paystack_base_url}/transaction/initialize',
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception("Overtime payment initiation failed")
            
            payment_data = response.json()['data']
            
            # Store overtime payment record - FIXED: Use datetime instead of datetime.datetime
            payment_record = {
                'booking_id': booking_id,
                'reference': payload['reference'],
                'amount': overtime_info['amount'],
                'status': 'pending',
                'type': 'overtime',
                'paystack_reference': payment_data['reference'],
                'created_at': datetime.utcnow().isoformat()
            }
            
            self.payments_ref.child(payment_data['reference']).set(payment_record)
            
            return {
                'authorization_url': payment_data['authorization_url'],
                'reference': payment_data['reference'],
                'overtime_amount': overtime_info['amount']
            }
            
        except requests.RequestException as e:
            logger.error(f"Overtime payment initiation error: {str(e)}")
            raise Exception("Overtime payment service unavailable")