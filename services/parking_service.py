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
        """Validate QR code for parking entry/exit - Now handles 10-digit booking IDs"""
        # Parse QR code data: PARKING:{booking_id}:{user_id}:{slot_id}
        parts = qr_data.split(':')
        if len(parts) != 4 or parts[0] != 'PARKING':
            raise ValueError('Invalid QR code format')
        
        _, booking_id, user_id, slot_id = parts
        
        # Validate booking ID format (should be 10 characters now)
        if len(booking_id) != 10:
            raise ValueError('Invalid booking ID format')
        
        # Get booking details
        try:
            booking = self.booking_service.get_booking_by_id(booking_id)
        except ValueError:
            raise ValueError('Booking not found')
        
        # Verify booking belongs to the user and slot
        if booking['user_id'] != user_id or booking['slot_id'] != slot_id:
            raise ValueError('Invalid booking credentials')
        
        now = datetime.datetime.now()
        start_time = datetime.datetime.fromisoformat(booking['start_time'].replace('Z', ''))
        end_time = datetime.datetime.fromisoformat(booking['end_time'].replace('Z', ''))
        grace_period = datetime.timedelta(minutes=getattr(Config, 'GRACE_PERIOD_MINUTES', 15))
        
        # Handle different booking statuses
        if booking['status'] == 'confirmed':
            # Entry validation
            if now < start_time:
                remaining_time = start_time - now
                raise ValueError(f'Entry time not yet reached. Please wait {str(remaining_time).split(".")[0]}')
            
            # Allow entry if within reasonable time window (not too late)
            max_late_entry = datetime.timedelta(hours=2)  # Allow 2 hours late entry
            if now > start_time + max_late_entry:
                raise ValueError('Entry time has passed. Please contact support.')
            
            # Allow entry and update status
            self.booking_service.update_booking_status(booking_id, 'in_use', {
                'actual_entry_time': now.isoformat(),
                'scan_count': 1
            })
            
            logger.info(f"Entry granted for booking: {booking_id}")
            return {
                'status': 'allowed',
                'message': f'Entry granted for booking {booking_id}. Welcome!',
                'open_barrier': True,
                'action': 'entry',
                'booking_id': booking_id,
                'slot_location': booking.get('slot_location', 'Unknown')
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
                overtime_amount = round(overtime_hours * getattr(Config, 'DEFAULT_PARKING_RATE', 100.0), 2)
                
                return {
                    'status': 'overtime_due',
                    'message': f'Overtime payment required: ₦{overtime_amount:.2f}',
                    'open_barrier': False,
                    'overtime': True,
                    'overtime_amount': overtime_amount,
                    'overtime_duration': str(overtime_duration).split('.')[0],  # Remove microseconds
                    'booking_id': booking_id
                }
            
            # Allow exit and complete booking
            self.booking_service.update_booking_status(booking_id, 'completed', {
                'actual_exit_time': now.isoformat(),
                'scan_count': scan_count + 1
            })
            
            logger.info(f"Exit granted for booking: {booking_id}")
            return {
                'status': 'allowed',
                'message': f'Exit granted for booking {booking_id}. Thank you!',
                'open_barrier': True,
                'action': 'exit',
                'booking_id': booking_id,
                'total_duration': str(now - datetime.datetime.fromisoformat(booking.get('actual_entry_time', booking['start_time']).replace('Z', ''))).split('.')[0]
            }
        
        elif booking['status'] == 'completed':
            raise ValueError(f'Booking {booking_id} already completed')
        
        elif booking['status'] == 'cancelled':
            raise ValueError(f'Booking {booking_id} has been cancelled')
        
        elif booking['status'] == 'pending':
            raise ValueError(f'Booking {booking_id} payment is still pending')
        
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
        
        # Generate slot ID (keeping UUID for slots as they're different from bookings)
        import uuid
        slot_id = str(uuid.uuid4())
        
        slot_data = {
            'location': location.strip(),
            'description': description.strip(),
            'rate_per_hour': rate_per_hour,
            'is_active': True,
            'current_occupancy': 0,  # 0 = empty, 1 = occupied
            'created_at': datetime.datetime.utcnow().isoformat()
        }
        
        self.slots_ref.child(slot_id).set(slot_data)
        
        logger.info(f"New parking slot created: {slot_id}")
        return {
            'slot_id': slot_id,
            'location': location,
            'rate_per_hour': rate_per_hour,
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
    
    def update_slot_occupancy(self, slot_id, occupancy_status):
        """Update slot occupancy status (0 = empty, 1 = occupied)"""
        slot = self.slots_ref.child(slot_id).get()
        if not slot:
            raise ValueError('Slot not found')
        
        if occupancy_status not in [0, 1]:
            raise ValueError('Occupancy status must be 0 (empty) or 1 (occupied)')
        
        self.slots_ref.child(slot_id).update({
            'current_occupancy': occupancy_status,
            'occupancy_updated_at': datetime.datetime.utcnow().isoformat()
        })
        
        status_text = 'occupied' if occupancy_status == 1 else 'empty'
        logger.info(f"Slot {slot_id} occupancy updated to {status_text}")
        
        return {'message': f'Slot occupancy updated to {status_text}'}
    
    def get_booking_details_from_qr(self, qr_data):
        """Extract and return booking details from QR code for display purposes"""
        try:
            parts = qr_data.split(':')
            if len(parts) != 4 or parts[0] != 'PARKING':
                raise ValueError('Invalid QR code format')
            
            _, booking_id, user_id, slot_id = parts
            
            # Get booking and slot details
            booking = self.booking_service.get_booking_by_id(booking_id)
            slot = self.slots_ref.child(slot_id).get()
            
            return {
                'booking_id': booking_id,
                'booking_reference': booking.get('booking_reference'),
                'user_id': user_id,
                'slot_id': slot_id,
                'slot_location': slot.get('location', 'Unknown') if slot else 'Unknown',
                'start_time': booking.get('start_time'),
                'end_time': booking.get('end_time'),
                'status': booking.get('status'),
                'total_amount': booking.get('total_amount')
            }
            
        except Exception as e:
            logger.error(f"Error extracting booking details from QR: {str(e)}")
            raise ValueError('Unable to extract booking details from QR code')