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
        
        payload = {
            'email': email,
            'amount': amount_kobo,
            'reference': f"booking_{booking_id}",
            'callback_url': f"{Config.FRONTEND_URL}/payment/callback",
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
            response = requests.post(
                f'{Config.PAYSTACK_BASE_URL}/transaction/initialize',
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Paystack API error: {response.text}")
                raise Exception("Payment initiation failed")
            
            payment_data = response.json()['data']
            
            # Store payment record
            payment_record = {
                'booking_id': booking_id,
                'reference': payload['reference'],
                'amount': booking['total_amount'],
                'status': 'pending',
                'paystack_reference': payment_data['reference'],
                'created_at': datetime.datetime.utcnow().isoformat()
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
            response = requests.get(
                f'{Config.PAYSTACK_BASE_URL}/transaction/verify/{reference}',
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
                
                # Update payment status
                self.payments_ref.child(reference).update({
                    'status': 'completed',
                    'completed_at': datetime.datetime.utcnow().isoformat(),
                    'paystack_data': payment_data
                })
                
                # Generate QR code data and image
                qr_data = f'PARKING:{booking_id}:{booking.get("user_id", "")}:{booking.get("slot_id", "")}'
                
                # # Generate QR code image
                booking_details = {
                    'booking_reference': booking.get('booking_reference'),
                    'slot_location': booking.get('slot_location'),
                    'start_time': booking.get('start_time'),
                    'end_time': booking.get('end_time'),
                    'total_amount': booking.get('total_amount')
                }
                
                qr_image = self.qr_service.generate_qr_code(qr_data, booking_details)
                qr_base64 = self.qr_service.qr_to_base64(qr_image)
                
                # Update booking with QR data and image
                self.booking_service.update_booking_status(booking_id, 'confirmed', {
                    'qr_data': qr_data,
                    'qr_image_base64': qr_base64,
                    'payment_reference': reference,
                    'paid_at': datetime.datetime.utcnow().isoformat()
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
        
        now = datetime.datetime.now()
        end_time = datetime.datetime.fromisoformat(booking['end_time'])
        grace_period = datetime.timedelta(minutes=Config.GRACE_PERIOD_MINUTES)
        
        if now <= end_time + grace_period:
            return {'overtime_required': False, 'amount': 0}
        
        overtime_duration = now - end_time
        overtime_hours = overtime_duration.total_seconds() / 3600
        overtime_amount = round(overtime_hours * Config.DEFAULT_PARKING_RATE, 2)
        
        return {
            'overtime_required': True,
            'amount': overtime_amount,
            'duration_hours': round(overtime_hours, 2),
            'rate_per_hour': Config.DEFAULT_PARKING_RATE
        }
    
    def process_overtime_payment(self, booking_id, email):
        """Process overtime payment for a booking"""
        overtime_info = self.calculate_overtime_amount(booking_id)
        
        if not overtime_info['overtime_required']:
            raise ValueError('No overtime payment required')
        
        # Similar to initiate_payment but for overtime
        amount_kobo = int(overtime_info['amount'] * 100)
        
        payload = {
            'email': email,
            'amount': amount_kobo,
            'reference': f"overtime_{booking_id}_{int(datetime.datetime.now().timestamp())}",
            'callback_url': f"{Config.FRONTEND_URL}/payment/overtime-callback",
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
            response = requests.post(
                f'{Config.PAYSTACK_BASE_URL}/transaction/initialize',
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception("Overtime payment initiation failed")
            
            payment_data = response.json()['data']
            
            # Store overtime payment record
            payment_record = {
                'booking_id': booking_id,
                'reference': payload['reference'],
                'amount': overtime_info['amount'],
                'status': 'pending',
                'type': 'overtime',
                'paystack_reference': payment_data['reference'],
                'created_at': datetime.datetime.utcnow().isoformat()
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