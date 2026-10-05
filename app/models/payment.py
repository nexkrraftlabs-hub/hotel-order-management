"""Payment model for session payment tracking."""
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime, timezone


class Payment(BaseModel):
    """Payment record for a customer session."""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('customer_sessions.id'), nullable=False, unique=True)
    
    # Amounts
    subtotal = db.Column(db.Float, default=0)
    tax_amount = db.Column(db.Float, default=0)
    service_charge = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, default=0)
    
    # Payment info
    payment_method = db.Column(db.String(50), default='cash')
    status = db.Column(db.String(30), nullable=False, default='pending', index=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    paid_at = db.Column(db.DateTime)
    
    # Relationships
    approver = db.relationship('User', foreign_keys=[approved_by])
    
    # Status constants
    PENDING = 'pending'
    APPROVED = 'approved'
    PAID = 'paid'
    
    def __repr__(self):
        return f'<Payment {self.id} ({self.status})>'
