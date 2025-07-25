import datetime
from hashlib import sha256
from services.firebase_service import FirebaseService
from config import Config
import logging

logger = logging.getLogger(__name__)

class BookingService:
    def __init__(self):
        self.firebase = FirebaseService()
        self.bookings_ref = self.firebase.get_db_reference('bookings')
        self.slots_ref = self.firebase.get_db_reference('slots')
    
    def get_available_slots(self, start_time_str, end_time_str):
        """Get available parking slots for given time range"""
        try:
            start_dt = datetime.datetime.fromisoformat(start_time_str)
            end_dt = datetime.datetime.fromisoformat(end_time_str)
        except ValueError:
            raise ValueError("Invalid datetime format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
        
        if start_dt >= end_dt:
            raise ValueError("Start time must be before end time")
        
        if start_dt < datetime.datetime.now():
            raise ValueError("Start time cannot be in the past")
        
        # Get all slots and bookings
        all_slots = self.slots_ref.get() or {}
        all_bookings = self.bookings_ref.get() or {}
        
        available_slots = []
        
        for slot_id, slot in all_slots.items():
            if not slot.get('is_active', True):
                continue
                
            is_available = True
            
            # Check if slot is already booked during requested time
            for booking in all_bookings.values():
                if (booking['slot_id'] == slot_id and 
                    booking['status'] in ['confirmed', 'in_use']):
                    
                    booking_start = datetime.datetime.fromisoformat(booking['start_time'])
                    booking_end = datetime.datetime.fromisoformat(booking['end_time'])
                    
                    # Check for time overlap
                    if not (end_dt <= booking_start or start_dt >= booking_end):
                        is_available = False
                        break
            
            if is_available:
                available_slots.append({
                    'slot_id': slot_id,
                    'location': slot.get('location', 'Nigeria'),
                    'description': slot.get('description', 'Unavailable'),
                    'rate_per_hour': slot.get('rate_per_hour', Config.DEFAULT_PARKING_RATE)
                })
        
        return available_slots
    
    def create_booking(self, user_id, slot_id, start_time_str, end_time_str):
        """Create a new parking booking"""
        try:
            start_dt = datetime.datetime.fromisoformat(start_time_str)
            end_dt = datetime.datetime.fromisoformat(end_time_str)
        except ValueError:
            raise ValueError("Invalid datetime format")
        
        # Validate booking duration
        duration = end_dt - start_dt
        if duration.total_seconds() < 1800:  # 30 minutes minimum
            raise ValueError("Minimum booking duration is 30 minutes")
        
        if duration.total_seconds() > 86400:  # 24 hours maximum
            raise ValueError("Maximum booking duration is 24 hours")
        
        # Check if slot exists and is available
        slot = self.slots_ref.child(slot_id).get()
        if not slot:
            raise ValueError("Parking slot not found")
        
        if not slot.get('is_active', True):
            raise ValueError("Parking slot is not available")
        
        # Check availability again
        available_slots = self.get_available_slots(start_time_str, end_time_str)
        if not any(s['slot_id'] == slot_id for s in available_slots):
            raise ValueError("Slot is not available for the selected time")
        
        # Calculate booking amount
        duration_hours = duration.total_seconds() / 3600
        rate_per_hour = slot.get('rate_per_hour', Config.DEFAULT_PARKING_RATE)
        total_amount = round(duration_hours * rate_per_hour, 2)
        
        # Generate booking ID
        booking_id = sha256(f'{user_id}{slot_id}{start_time_str}{datetime.datetime.now().isoformat()}'.encode()).hexdigest()
        
        # Create booking
        booking_data = {
            'user_id': user_id,
            'slot_id': slot_id,
            'start_time': start_time_str,
            'end_time': end_time_str,
            'status': 'pending',
            'total_amount': total_amount,
            'rate_per_hour': rate_per_hour,
            'duration_hours': round(duration_hours, 2),
            'created_at': datetime.datetime.utcnow().isoformat(),
            'booking_reference': f'PK{booking_id[:8].upper()}'
        }
        
        self.bookings_ref.child(booking_id).set(booking_data)
        
        logger.info(f"Booking created: {booking_id} for user: {user_id}")
        
        return {
            'booking_id': booking_id,
            'booking_reference': booking_data['booking_reference'],
            'total_amount': total_amount,
            'message': 'Booking created successfully. Please proceed to payment.'
        }
    
    def get_user_bookings(self, user_id):
        """Get all bookings for a user"""
        user_bookings = self.bookings_ref.order_by_child('user_id').equal_to(user_id).get()
        
        if not user_bookings:
            return []
        
        # Enrich bookings with slot information
        bookings_list = []
        for booking_id, booking in user_bookings.items():
            slot = self.slots_ref.child(booking['slot_id']).get()
            booking_info = booking.copy()
            booking_info['booking_id'] = booking_id
            booking_info['slot_location'] = slot.get('location') if slot else 'Unknown'
            bookings_list.append(booking_info)
        
        # Sort by creation date (newest first)
        bookings_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return bookings_list
    
    def get_booking_by_id(self, booking_id):
        """Get booking by ID"""
        booking = self.bookings_ref.child(booking_id).get()
        if not booking:
            raise ValueError("Booking not found")
        
        return booking
    
    def update_booking_status(self, booking_id, status, additional_data=None):
        """Update booking status"""
        valid_statuses = ['pending', 'confirmed', 'in_use', 'completed', 'cancelled']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        
        update_data = {
            'status': status,
            'updated_at': datetime.datetime.utcnow().isoformat()
        }
        
        if additional_data:
            update_data.update(additional_data)
        
        self.bookings_ref.child(booking_id).update(update_data)
        logger.info(f"Booking {booking_id} status updated to {status}")