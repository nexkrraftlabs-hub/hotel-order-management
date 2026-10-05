"""Order model with state machine for order lifecycle."""
import uuid
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime, timezone


class Order(BaseModel):
    """Customer order with strict state machine transitions."""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(64), unique=True, nullable=False, index=True,
                         default=lambda: f'ORD-{datetime.now(timezone.utc).strftime("%Y%m%d")}-{uuid.uuid4().hex[:6].upper()}')
    session_id = db.Column(db.Integer, db.ForeignKey('customer_sessions.id'), nullable=False)
    
    # Order details
    subtotal = db.Column(db.Float, default=0)
    tax_amount = db.Column(db.Float, default=0)
    service_charge = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, default=0)
    
    # Status
    status = db.Column(db.String(30), nullable=False, default='pending', index=True)
    payment_status = db.Column(db.String(30), nullable=False, default='pending')
    special_instructions = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    confirmed_at = db.Column(db.DateTime)
    sent_to_kitchen_at = db.Column(db.DateTime)
    kitchen_accepted_at = db.Column(db.DateTime)
    preparing_at = db.Column(db.DateTime)
    ready_at = db.Column(db.DateTime)
    served_at = db.Column(db.DateTime)
    paid_at = db.Column(db.DateTime)
    
    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy='joined',
                           cascade='all, delete-orphan')
    kitchen_assignment = db.relationship('KitchenAssignment', backref='order', 
                                         uselist=False, lazy='joined')
    waiter_assignment = db.relationship('WaiterAssignment', backref='order',
                                        uselist=False, lazy='joined')
    
    # Status constants
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    SENT_TO_KITCHEN = 'sent_to_kitchen'
    KITCHEN_ACCEPTED = 'kitchen_accepted'
    PREPARING = 'preparing'
    READY = 'ready'
    TRANSFERRED_TO_WAITER = 'transferred_to_waiter'
    SERVING = 'serving'
    SERVED = 'served'
    PAYMENT_PENDING = 'payment_pending'
    PAID = 'paid'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    
    # Valid transitions
    VALID_TRANSITIONS = {
        PENDING: [CONFIRMED, CANCELLED],
        CONFIRMED: [SENT_TO_KITCHEN, CANCELLED],
        SENT_TO_KITCHEN: [KITCHEN_ACCEPTED, CANCELLED],
        KITCHEN_ACCEPTED: [PREPARING, CANCELLED],
        PREPARING: [READY],
        READY: [TRANSFERRED_TO_WAITER],
        TRANSFERRED_TO_WAITER: [SERVING],
        SERVING: [SERVED],
        SERVED: [PAYMENT_PENDING, PAID],
        PAYMENT_PENDING: [PAID],
        PAID: [COMPLETED],
        COMPLETED: [],
        CANCELLED: [],
    }
    
    def can_transition_to(self, new_status):
        """Check if transition to new status is valid."""
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])
    
    def transition_to(self, new_status):
        """Transition order to a new status with validation."""
        if not self.can_transition_to(new_status):
            raise ValueError(f'Invalid transition from {self.status} to {new_status}')
        
        self.status = new_status
        now = datetime.now(timezone.utc)
        
        timestamp_map = {
            self.CONFIRMED: 'confirmed_at',
            self.SENT_TO_KITCHEN: 'sent_to_kitchen_at',
            self.KITCHEN_ACCEPTED: 'kitchen_accepted_at',
            self.PREPARING: 'preparing_at',
            self.READY: 'ready_at',
            self.SERVED: 'served_at',
            self.PAID: 'paid_at',
        }
        
        if new_status in timestamp_map:
            setattr(self, timestamp_map[new_status], now)
        
        self.updated_at = now
    
    @property
    def status_display(self):
        """Human-readable status."""
        return self.status.replace('_', ' ').title()
    
    @property
    def token_number(self):
        """Get token number from session."""
        if self.session and self.session.token:
            return self.session.token.token_number
        return None
    
    def to_dict(self):
        """Serialize for API responses."""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'status': self.status,
            'status_display': self.status_display,
            'payment_status': self.payment_status,
            'items': [item.to_dict() for item in self.items],
            'subtotal': self.subtotal,
            'tax_amount': self.tax_amount,
            'service_charge': self.service_charge,
            'discount_amount': self.discount_amount,
            'total_amount': self.total_amount,
            'special_instructions': self.special_instructions,
            'token_number': self.token_number,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self):
        return f'<Order {self.order_id} ({self.status})>'
