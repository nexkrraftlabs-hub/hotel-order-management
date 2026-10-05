"""MenuItem model for food items."""
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime, timezone


class MenuItem(BaseModel):
    """Individual food/drink item on the menu."""
    __tablename__ = 'menu_items'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    discount_price = db.Column(db.Float)
    image = db.Column(db.String(500))
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    
    # Attributes
    is_veg = db.Column(db.Boolean, default=True)
    is_available = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    is_popular = db.Column(db.Boolean, default=False)
    is_spicy = db.Column(db.Boolean, default=False)
    preparation_time = db.Column(db.Integer, default=15)  # minutes
    rating = db.Column(db.Float, default=4.0)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    addons = db.relationship('MenuAddon', backref='menu_item', lazy='dynamic')
    
    @property
    def effective_price(self):
        """Return discount price if available, otherwise regular price."""
        if self.discount_price and self.discount_price < self.price:
            return self.discount_price
        return self.price
    
    @property
    def discount_percentage(self):
        """Calculate discount percentage."""
        if self.discount_price and self.discount_price < self.price:
            return round((1 - self.discount_price / self.price) * 100)
        return 0
    
    def to_dict(self):
        """Serialize to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'discount_price': self.discount_price,
            'effective_price': self.effective_price,
            'discount_percentage': self.discount_percentage,
            'image': self.image,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'is_veg': self.is_veg,
            'is_available': self.is_available,
            'is_featured': self.is_featured,
            'is_popular': self.is_popular,
            'is_spicy': self.is_spicy,
            'preparation_time': self.preparation_time,
            'rating': self.rating,
        }
    
    def __repr__(self):
        return f'<MenuItem {self.name}>'
