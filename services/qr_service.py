import qrcode # type: ignore
import io
import base64
from PIL import Image, ImageDraw, ImageFont
from config import Config
import logging

logger = logging.getLogger(__name__)

class QRService:
    def __init__(self):
        self.qr_settings = {
            'version': 1,
            'error_correction': qrcode.constants.ERROR_CORRECT_L,
            'box_size': 10,
            'border': 4,
        }
    
    def generate_qr_code(self, data, booking_details=None):
        """Generate QR code image with optional booking details overlay"""
        try:
            # Create QR code
            qr = qrcode.QRCode(**self.qr_settings)
            qr.add_data(data)
            qr.make(fit=True)
            
            # Create QR code image
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # If booking details provided, add them to the image
            if booking_details:
                qr_img = self._add_booking_details(qr_img, booking_details)
            
            return qr_img
            
        except Exception as e:
            logger.error(f"QR code generation failed: {str(e)}")
            raise Exception("Failed to generate QR code")
    
    def _add_booking_details(self, qr_img, booking_details):
        """Add booking details text to QR code image"""
        # Convert to RGB if needed
        if qr_img.mode != 'RGB':
            qr_img = qr_img.convert('RGB')
        
        # Calculate new image size (QR + text area)
        qr_width, qr_height = qr_img.size
        text_height = 120  # Height for text area
        new_height = qr_height + text_height
        
        # Create new image with white background
        new_img = Image.new('RGB', (qr_width, new_height), 'white')
        
        # Paste QR code at the top
        new_img.paste(qr_img, (0, 0))
        
        # Add text below QR code
        draw = ImageDraw.Draw(new_img)
        
        try:
            # Try to use a nice font, fall back to default if not available
            font_large = ImageFont.truetype("arial.ttf", 16)
            font_small = ImageFont.truetype("arial.ttf", 12)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Prepare text
        texts = [
            f"Booking: {booking_details.get('booking_reference', 'N/A')}",
            f"Slot: {booking_details.get('slot_id', 'N/A')}",
            f"Start: {self._format_datetime(booking_details.get('start_time'))}",
            f"End: {self._format_datetime(booking_details.get('end_time'))}"
        ]
        
        # Draw text
        y_offset = qr_height + 10
        for i, text in enumerate(texts):
            font = font_large if i == 0 else font_small
            draw.text((10, y_offset), text, fill='black', font=font)
            y_offset += 20 if i == 0 else 15
        
        return new_img
    
    def _format_datetime(self, datetime_str):
        """Format datetime string for display"""
        if not datetime_str:
            return "N/A"
        
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(datetime_str)
            return dt.strftime("%Y-%m-%d %H:%M")
        except:
            return datetime_str
    
    def qr_to_base64(self, qr_img):
        """Convert QR code image to base64 string"""
        buffer = io.BytesIO()
        qr_img.save(buffer, format='PNG')
        buffer.seek(0)
        
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_base64}"
    
    def qr_to_bytes(self, qr_img):
        """Convert QR code image to bytes for download"""
        buffer = io.BytesIO()
        qr_img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer.getvalue()