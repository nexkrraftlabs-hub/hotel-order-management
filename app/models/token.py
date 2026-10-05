"""Token model for reusable token allocation system."""
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime, timezone


class Token(BaseModel):
    """Reusable token for customer ordering sessions."""
    __tablename__ = 'tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token_number = db.Column(db.Integer, unique=True, nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default='available', index=True)
    is_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    sessions = db.relationship('CustomerSession', backref='token', lazy='dynamic')
    
    # Status constants
    AVAILABLE = 'available'
    ACTIVE = 'active'
    PAYMENT_PENDING = 'payment_pending'
    COMPLETED = 'completed'
    
    VALID_STATUSES = [AVAILABLE, ACTIVE, PAYMENT_PENDING, COMPLETED]
    
    @property
    def display_number(self):
        """Return formatted token number like TOKEN #01."""
        return f'TOKEN #{self.token_number:02d}'
    
    @property
    def active_session(self):
        """Get current active session for this token."""
        from app.models.customer_session import CustomerSession
        return self.sessions.filter(
            CustomerSession.status.in_(['active', 'payment_pending'])
        ).first()
    
    def is_available(self):
        """Check if token is available for allocation."""
        return self.status == self.AVAILABLE and self.is_enabled
    
    def __repr__(self):
        return f'<Token #{self.token_number:02d} ({self.status})>'
