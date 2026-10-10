"""CustomerSession model - connects customer activity with token."""
import uuid
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime, timezone


class CustomerSession(BaseModel):
    """Customer session entity linking token, cart, orders, and payment."""
    __tablename__ = 'customer_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), unique=True, nullable=False, 
                           default=lambda: f'SES-{uuid.uuid4().hex[:12].upper()}', index=True)
    browser_session_id = db.Column(db.String(128), index=True)
    token_id = db.Column(db.Integer, db.ForeignKey('tokens.id'), nullable=True)
    
    # Customer info (optional)
    customer_name = db.Column(db.String(120))
    customer_phone = db.Column(db.String(20))
    customer_email = db.Column(db.String(120))
    
    # Session state
    status = db.Column(db.String(30), nullable=False, default='active', index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    cart = db.relationship('Cart', backref='session', uselist=False, lazy='joined')
    orders = db.relationship('Order', backref='session', lazy='dynamic',
                             order_by='Order.created_at.desc()')
    payment = db.relationship('Payment', backref='session', uselist=False, lazy='joined')
    bill = db.relationship('Bill', backref='session', uselist=False, lazy='joined')
    notifications = db.relationship('Notification', backref='session', lazy='dynamic')
    
    # Status constants
    ACTIVE = 'active'
    PAYMENT_PENDING = 'payment_pending'
    COUNTER_PAYMENT_REQUESTED = 'counter_payment_requested'
    PAID = 'paid'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    
    @property
    def total_amount(self):
        """Calculate total amount across all orders in session."""
        total = 0
        for order in self.orders.all():
            total += order.total_amount or 0
        return total
    
    @property
    def order_count(self):
        """Get number of orders in this session."""
        return self.orders.count()
    
    @property
    def ready_items_list(self):
        """List of all items ready for counter pickup across all orders."""
        ready_list = []
        for order in self.orders.all():
            for item in order.items:
                if getattr(item, 'status', None) == 'ready':
                    ready_list.append(item)
        return ready_list
    
    @property
    def is_counter_payment_requested(self):
        """Check if customer requested to pay at counter."""
        if self.status == self.COUNTER_PAYMENT_REQUESTED:
            return True
        if self.payment and self.payment.status == 'pending' and str(self.payment.payment_method).startswith('counter_'):
            return True
        return False
        
    @property
    def is_paid(self):
        """Check if session is fully paid."""
        return self.status in [self.PAID, self.COMPLETED] or (self.payment and self.payment.status == 'paid')
    
    def __repr__(self):
        return f'<CustomerSession {self.session_id}>'
