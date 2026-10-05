"""Category model for menu organization."""
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime, timezone


class Category(BaseModel):
    """Food menu category."""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(500))
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    menu_items = db.relationship('MenuItem', backref='category', lazy='dynamic')
    
    @property
    def active_items_count(self):
        """Count active menu items in this category."""
        return self.menu_items.filter_by(is_available=True).count()
    
    def __repr__(self):
        return f'<Category {self.name}>'
