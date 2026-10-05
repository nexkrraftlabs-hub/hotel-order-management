"""Role model for RBAC."""
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime, timezone


class Role(BaseModel):
    """Role model for role-based access control."""
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    users = db.relationship('User', backref='role', lazy='dynamic')
    
    # Role constants
    SUPER_ADMIN = 'super_admin'
    ADMIN = 'admin'
    KITCHEN = 'kitchen'
    WAITER = 'waiter'
    CUSTOMER = 'customer'
    
    def __repr__(self):
        return f'<Role {self.name}>'
    
    @staticmethod
    def get_or_create(name, description=''):
        """Get existing role or create a new one."""
        role = Role.query.filter_by(name=name).first()
        if not role:
            role = Role(name=name, description=description)
            db.session.add(role)
        return role
