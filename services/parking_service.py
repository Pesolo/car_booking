import datetime
from services.firebase_service import FirebaseService
from services.booking_service import BookingService
from config import Config
import logging

logger = logging.getLogger(__name__)

class ParkingService:
    def __init__(self):
        self.firebase = FirebaseService()
        self.slots_ref = self.firebase.get_db_reference('slots')
        self.bookings_ref = self.firebase.get_db_reference('bookings')
        self.booking_service = BookingService()
    
    def validate_qr_code(self, qr_data):
        """Validate QR code for parking entry/exit"""
        # Parse QR code data
        parts = qr_data.split(':')
        if len(parts) != 4 or parts[0] != 'PARKING':
            raise ValueError('Invalid QR code format')
        
        _, booking_id, user_id, slot_id = parts
        
        # Get booking details
        booking = self.booking_service.get_booking_by_id(booking_id)
        if not booking:
            raise ValueError('Booking not found')
        
        # Verify booking belongs to the user and slot
        if booking['user_id'] != user_id or booking['slot_id'] != slot_id:
            raise ValueError('Invalid booking credentials')
        
        now = datetime.datetime.now()
        start_time = datetime.datetime.fromisoformat(booking['start_time'])
        end_time = datetime.datetime.fromisoformat(booking['end_time'])
        grace_period = datetime.timedelta(minutes=Config.GRACE_PERIOD_MINUTES)
        
        # Handle different booking statuses
        if booking['status'] == 'confirmed':
            # Entry validation
            if now < start_time:
                raise ValueError('Entry time not yet reached')
            
            # Allow entry and update status
            self.booking_service.update_booking_status(booking_id, 'in_use', {
                'actual_entry_time': now.isoformat(),
                'scan_count': 1
            })
            
            logger.info(f"Entry granted for booking: {booking_id}")
            return {
                'status': 'allowed',
                'message': 'Entry granted. Welcome!',
                'open_barrier': True,
                'action': 'entry'
            }
        
        elif booking['status'] == 'in_use':
            # Exit validation
            scan_count = booking.get('scan_count', 1)
            if scan_count >= 2:
                raise ValueError('Booking already completed')
            
            # Check for overtime
            overtime_required = now > end_time + grace_period
            if overtime_required and not booking.get('overtime_paid', False):
                overtime_duration = now - end_time
                overtime_hours = overtime_duration.total_seconds() / 3600
                overtime_amount = round(overtime_hours * Config.DEFAULT_PARKING_RATE, 2)
                
                return {
                    'status': 'overtime_due',
                    'message': f'Overtime payment required: ${overtime_amount:.2f}',
                    'open_barrier': False,
                    'overtime': True,
                    'overtime_amount': overtime_amount,
                    'overtime_duration': str(overtime_duration).split('.')[0]  # Remove microseconds
                }
            
            # Allow exit and complete booking
            self.booking_service.update_booking_status(booking_id, 'completed', {
                'actual_exit_time': now.isoformat(),
                'scan_count': scan_count + 1
            })
            
            logger.info(f"Exit granted for booking: {booking_id}")
            return {
                'status': 'allowed',
                'message': 'Exit granted. Thank you!',
                'open_barrier': True,
                'action': 'exit'
            }
        
        elif booking['status'] == 'completed':
            raise ValueError('Booking already completed')
        
        elif booking['status'] == 'cancelled':
            raise ValueError('Booking has been cancelled')
        
        else:
            raise ValueError(f'Invalid booking status: {booking["status"]}')
    
    def get_all_slots(self):
        """Get all parking slots"""
        slots = self.slots_ref.get() or {}
        
        slots_list = []
        for slot_id, slot_data in slots.items():
            slot_info = slot_data.copy()
            slot_info['slot_id'] = slot_id
            slots_list.append(slot_info)
        
        return slots_list
    
    def create_slot(self, location, description, rate_per_hour):
        """Create a new parking slot"""
        if not location or not location.strip():
            raise ValueError('Location is required')
        
        try:
            rate_per_hour = float(rate_per_hour)
            if rate_per_hour <= 0:
                raise ValueError('Rate per hour must be positive')
        except (ValueError, TypeError):
            raise ValueError('Invalid rate per hour')
        
        # Generate slot ID
        import uuid
        slot_id = str(uuid.uuid4())
        
        slot_data = {
            'location': location.strip(),
            'description': description.strip(),
            'rate_per_hour': rate_per_hour,
            'is_active': True,
            'created_at': datetime.datetime.utcnow().isoformat()
        }
        
        self.slots_ref.child(slot_id).set(slot_data)
        
        logger.info(f"New parking slot created: {slot_id}")
        return {
            'slot_id': slot_id,
            'message': 'Parking slot created successfully'
        }
    
    def update_slot_status(self, slot_id, is_active):
        """Update slot active status"""
        slot = self.slots_ref.child(slot_id).get()
        if not slot:
            raise ValueError('Slot not found')
        
        self.slots_ref.child(slot_id).update({
            'is_active': is_active,
            'updated_at': datetime.datetime.utcnow().isoformat()
        })
        
        status = 'activated' if is_active else 'deactivated'
        logger.info(f"Slot {slot_id} {status}")
        
        return {'message': f'Slot {status} successfully'}