"""WaiterAssignment model for waiter order tracking."""
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime, timezone


class WaiterAssignment(BaseModel):
    """Tracks order assignment to waiter."""
    __tablename__ = 'waiter_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, unique=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.String(30), default='pending')
    
    assigned_at = db.Column(db.DateTime)
    accepted_at = db.Column(db.DateTime)
    served_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    waiter = db.relationship('User', foreign_keys=[assigned_to])
    
    def __repr__(self):
        return f'<WaiterAssignment order={self.order_id} ({self.status})>'
