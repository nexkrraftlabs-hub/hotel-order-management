"""KitchenAssignment model for kitchen order tracking."""
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime, timezone


class KitchenAssignment(BaseModel):
    """Tracks order assignment to kitchen."""
    __tablename__ = 'kitchen_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, unique=True)
    accepted_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.String(30), default='pending')
    
    accepted_at = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    kitchen_staff = db.relationship('User', foreign_keys=[accepted_by])
    
    def __repr__(self):
        return f'<KitchenAssignment order={self.order_id} ({self.status})>'
