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
    
    # Relationships
    menu_item = db.relationship('MenuItem', lazy='joined')
    
    def to_dict(self):
        """Serialize for API responses."""
        return {
            'id': self.id,
            'menu_item_id': self.menu_item_id,
            'item_name': self.item_name,
            'unit_price': self.unit_price,
            'quantity': self.quantity,
            'line_total': self.line_total,
            'is_veg': self.is_veg,
            'image': self.menu_item.image if self.menu_item else None,
            'special_instructions': self.special_instructions,
        }
    
    def __repr__(self):
        return f'<OrderItem {self.item_name} x{self.quantity}>'
