"""Restaurant model for settings and configuration."""
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime, timezone


class Restaurant(BaseModel):
    """Restaurant configuration and settings."""
    __tablename__ = 'restaurants'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, default='My Restaurant')
    description = db.Column(db.Text)
    logo = db.Column(db.String(500))
    cover_image = db.Column(db.String(500))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    gst_number = db.Column(db.String(50))
    cuisine_type = db.Column(db.String(200))
    rating = db.Column(db.Float, default=4.5)
    
    # Operating hours
    opening_time = db.Column(db.String(10), default='09:00')
    closing_time = db.Column(db.String(10), default='23:00')
    is_open = db.Column(db.Boolean, default=True)
    
    # Financial
    tax_percent = db.Column(db.Float, default=10.0)
    service_charge_percent = db.Column(db.Float, default=5.0)
    currency_symbol = db.Column(db.String(10), default='₹')
    
    # Metadata
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<Restaurant {self.name}>'
