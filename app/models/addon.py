"""MenuAddon model for food item add-ons."""
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime, timezone


class MenuAddon(BaseModel):
    """Add-on options for menu items."""
    __tablename__ = 'menu_addons'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False, default=0)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<MenuAddon {self.name}>'
