"""Notification model for customer and staff notifications."""
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime, timezone


class Notification(BaseModel):
    """System notifications for customers and staff."""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('customer_sessions.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    data = db.Column(db.Text)  # JSON extra data
    is_read = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Notification type constants
    ORDER_PLACED = 'order_placed'
    ORDER_CONFIRMED = 'order_confirmed'
    SENT_TO_KITCHEN = 'sent_to_kitchen'
    KITCHEN_ACCEPTED = 'kitchen_accepted'
    ORDER_PREPARING = 'order_preparing'
    ORDER_READY = 'order_ready'
    WAITER_ASSIGNED = 'waiter_assigned'
    ORDER_SERVED = 'order_served'
    PAYMENT_SUCCESS = 'payment_success'
    BILL_READY = 'bill_ready'
    
    def to_dict(self):
        """Serialize for API responses."""
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f'<Notification {self.type}: {self.title}>'
