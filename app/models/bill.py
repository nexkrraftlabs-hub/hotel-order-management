"""Bill model for invoice generation."""
import uuid
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime, timezone


class Bill(BaseModel):
    """Final bill/invoice for a customer session."""
    __tablename__ = 'bills'
    
    id = db.Column(db.Integer, primary_key=True)
    bill_number = db.Column(db.String(64), unique=True, nullable=False,
                            default=lambda: f'BILL-{datetime.now(timezone.utc).strftime("%Y%m%d")}-{uuid.uuid4().hex[:6].upper()}')
    session_id = db.Column(db.Integer, db.ForeignKey('customer_sessions.id'), nullable=False, unique=True)
    
    # Restaurant info snapshot
    restaurant_name = db.Column(db.String(200))
    restaurant_address = db.Column(db.Text)
    restaurant_phone = db.Column(db.String(20))
    restaurant_email = db.Column(db.String(120))
    restaurant_gst = db.Column(db.String(50))
    
    # Token/Session info
    token_number = db.Column(db.Integer)
    
    # Amounts
    subtotal = db.Column(db.Float, default=0)
    tax_percent = db.Column(db.Float, default=0)
    tax_amount = db.Column(db.Float, default=0)
    service_charge_percent = db.Column(db.Float, default=0)
    service_charge = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, default=0)
    
    # Status
    payment_status = db.Column(db.String(30), default='paid')
    payment_method = db.Column(db.String(50), default='cash')
    
    # Bill data (JSON serialized order details)
    bill_data = db.Column(db.Text)  # JSON string with full order details
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<Bill {self.bill_number}>'
