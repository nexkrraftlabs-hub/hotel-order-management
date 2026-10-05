"""CartItem model for items in shopping cart."""
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime, timezone


class CartItem(BaseModel):
    """Individual item in a shopping cart."""
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('carts.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    special_instructions = db.Column(db.Text)
    addons = db.Column(db.Text)  # JSON string of selected addon IDs
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    menu_item = db.relationship('MenuItem', lazy='joined')
    
    @property
    def unit_price(self):
        """Get effective unit price of the menu item."""
        return self.menu_item.effective_price if self.menu_item else 0
    
    @property
    def line_total(self):
        """Calculate total for this line item."""
        return self.unit_price * self.quantity
    
    def to_dict(self):
        """Serialize for API responses."""
        return {
            'id': self.id,
            'menu_item_id': self.menu_item_id,
            'name': self.menu_item.name if self.menu_item else '',
            'image': self.menu_item.image if self.menu_item else '',
            'is_veg': self.menu_item.is_veg if self.menu_item else True,
            'unit_price': self.unit_price,
            'quantity': self.quantity,
            'line_total': self.line_total,
            'special_instructions': self.special_instructions,
        }
    
    def __repr__(self):
        return f'<CartItem {self.menu_item.name if self.menu_item else "?"} x{self.quantity}>'
