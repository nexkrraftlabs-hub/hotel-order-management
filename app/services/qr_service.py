"""QR code generation service with branded logo embedding."""
import os
import qrcode
from io import BytesIO
import base64
try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    Image = None
    ImageDraw = None
    PIL_AVAILABLE = False


class QRService:
    """Service for generating QR codes with optional branded logo embedding."""
    
    @staticmethod
    def generate_qr(url, size=10, logo_path=None):
        """Generate QR code image for a URL with embedded center logo if available."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=size,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color='#0F172A', back_color='white').convert('RGBA')
        
        # If logo_path not passed, check default static logo
        if not logo_path:
            default_logo = os.path.join(os.path.dirname(__file__), '..', 'static', 'img', 'restaurant-logo.png')
            if os.path.exists(default_logo):
                logo_path = default_logo

        # Embed logo in the center if valid logo file exists and PIL is available
        if PIL_AVAILABLE and Image is not None and logo_path and os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path).convert('RGBA')
                qr_w, qr_h = img.size
                
                # Size logo to 24% of QR dimension
                logo_size = max(40, int(qr_w * 0.24))
                logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                
                # Create white circular badge background for maximum contrast & scan reliability
                badge_padding = 10
                bg_size = logo_size + badge_padding
                badge = Image.new('RGBA', (bg_size, bg_size), (0, 0, 0, 0))
                draw = ImageDraw.Draw(badge)
                draw.ellipse([0, 0, bg_size - 1, bg_size - 1], fill='white', outline='#E23744', width=3)
                
                pos_bg = ((qr_w - bg_size) // 2, (qr_h - bg_size) // 2)
                pos_logo = ((qr_w - logo_size) // 2, (qr_h - logo_size) // 2)
                
                img.paste(badge, pos_bg, badge)
                img.paste(logo, pos_logo, logo)
            except Exception as e:
                print(f"[QR Warning] Could not embed logo into QR: {e}")

        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def generate_qr_base64(url, size=10, logo_path=None):
        """Generate QR code as base64 string for embedding in HTML."""
        buffer = QRService.generate_qr(url, size, logo_path=logo_path)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        return f'data:image/png;base64,{img_base64}'
