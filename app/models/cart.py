"""Cart model for customer shopping cart."""
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime, timezone


class Cart(BaseModel):
    """Shopping cart linked to customer session."""
    __tablename__ = 'carts'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('customer_sessions.id'), nullable=False, unique=True)
    special_instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    items = db.relationship('CartItem', backref='cart', lazy='joined',
                           cascade='all, delete-orphan')
    
    @property
    def total_items(self):
        """Total number of items (sum of quantities)."""
        return sum(item.quantity for item in self.items)
    
    @property
    def subtotal(self):
        """Calculate cart subtotal."""
        return sum(item.line_total for item in self.items)
    
    @property
    def is_empty(self):
        """Check if cart is empty."""
        return len(self.items) == 0
    
    def to_dict(self):
        """Serialize cart for API responses."""
        return {
            'id': self.id,
            'items': [item.to_dict() for item in self.items],
            'total_items': self.total_items,
            'subtotal': self.subtotal,
            'special_instructions': self.special_instructions,
        }
    
    def __repr__(self):
        return f'<Cart {self.id} ({self.total_items} items)>'
