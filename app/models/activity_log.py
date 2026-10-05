"""ActivityLog model for audit trail."""
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime, timezone


class ActivityLog(BaseModel):
    """Audit log for important system actions."""
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(200), nullable=False)
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    @staticmethod
    def log(action, user_id=None, entity_type=None, entity_id=None, details=None, ip_address=None):
        """Create a new activity log entry."""
        entry = ActivityLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address
        )
        db.session.add(entry)
        return entry
    
    def __repr__(self):
        return f'<ActivityLog {self.action}>'
