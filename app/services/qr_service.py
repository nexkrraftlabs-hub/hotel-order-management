"""QR code generation service."""
import qrcode
from io import BytesIO
import base64


class QRService:
    """Service for generating QR codes."""
    
    @staticmethod
    def generate_qr(url, size=10):
        """Generate QR code image for a URL."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=size,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color='#1a1a2e', back_color='white')
        
        buffer = BytesIO()
        img.save(buffer)
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def generate_qr_base64(url, size=10):
        """Generate QR code as base64 string for embedding in HTML."""
        buffer = QRService.generate_qr(url, size)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        return f'data:image/png;base64,{img_base64}'
