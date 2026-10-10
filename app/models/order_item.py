"""OrderItem model for items within an order."""
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime, timezone


class OrderItem(BaseModel):
    """Individual item within an order (snapshot of menu item at order time)."""
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    
    # Snapshot of item at order time (prices may change later)
    item_name = db.Column(db.String(200), nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    line_total = db.Column(db.Float, nullable=False)
    is_veg = db.Column(db.Boolean, default=True)
    special_instructions = db.Column(db.Text)
    addons_text = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(30), nullable=False, default='pending')
    ready_at = db.Column(db.DateTime, nullable=True)
    collected_at = db.Column(db.DateTime, nullable=True)
    
    # Status constants
    PENDING = 'pending'
    PREPARING = 'preparing'
    READY = 'ready'          # Ready at counter for pickup
    COLLECTED = 'collected'  # Handed over / picked up by customer
    
    # Relationships
    menu_item = db.relationship('MenuItem', lazy='joined')
    
    @property
    def is_ready(self):
        return self.status == self.READY
    
    @property
    def is_collected(self):
        return self.status == self.COLLECTED
    
    @property
    def status_display(self):
        display_map = {
            self.PENDING: 'Order Placed',
            self.PREPARING: 'Cooking in Kitchen',
            self.READY: 'Ready at Counter 🔔',
            self.COLLECTED: 'Collected ✅',
        }
        return display_map.get(self.status, self.status.replace('_', ' ').title() if self.status else 'Pending')
    
    def to_dict(self):
        """Serialize for API responses."""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'menu_item_id': self.menu_item_id,
            'item_name': self.item_name,
            'unit_price': self.unit_price,
            'quantity': self.quantity,
            'line_total': self.line_total,
            'is_veg': self.is_veg,
            'image': self.menu_item.image if self.menu_item else None,
            'special_instructions': self.special_instructions,
            'status': self.status or self.PENDING,
            'status_display': self.status_display,
            'is_ready': self.is_ready,
            'is_collected': self.is_collected,
            'ready_at': self.ready_at.isoformat() if self.ready_at else None,
            'collected_at': self.collected_at.isoformat() if self.collected_at else None,
        }
    
    def __repr__(self):
        return f'<OrderItem {self.item_name} x{self.quantity} ({self.status})>'
