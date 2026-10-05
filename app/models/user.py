"""User model with authentication."""
from app.extensions import db
from app.models.base import BaseModel
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone


class User(UserMixin, BaseModel):
    """User model for all system roles."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)
    
    # Relationships
    activity_logs = db.relationship('ActivityLog', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        """Hash and set user password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password against hash."""
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_admin(self):
        return self.role.name in ('admin', 'super_admin')
    
    @property
    def is_super_admin(self):
        return self.role.name == 'super_admin'
    
    @property
    def is_kitchen(self):
        return self.role.name == 'kitchen'
    
    @property
    def is_waiter(self):
        return self.role.name == 'waiter'
    
    @property
    def is_customer(self):
        return self.role.name == 'customer'
    
    def has_role(self, role_name):
        """Check if user has a specific role."""
        return self.role.name == role_name
    
    def __repr__(self):
        return f'<User {self.username}>'
