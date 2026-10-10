"""Payment service for payment approval and session completion."""
from app.extensions import db
from app.models.payment import Payment
from app.models.order import Order
from app.models.customer_session import CustomerSession
from app.models.restaurant import Restaurant
from app.services.token_service import TokenService
from app.services.billing_service import BillingService
from app.services.notification_service import NotificationService
from datetime import datetime, timezone


class PaymentService:
    """Service for payment approval and session completion workflow."""
    
    @staticmethod
    def create_payment_for_session(session):
        """Create or update payment record for a session."""
        # Calculate totals from all orders in session
        orders = session.orders.all()
        subtotal = sum(o.subtotal for o in orders)
        tax_amount = sum(o.tax_amount for o in orders)
        service_charge = sum(o.service_charge for o in orders)
        discount_amount = sum(o.discount_amount for o in orders)
        total_amount = sum(o.total_amount for o in orders)
        
        payment = session.payment
        if not payment:
            payment = Payment(session_id=session.id)
            db.session.add(payment)
        
        payment.subtotal = subtotal
        payment.tax_amount = tax_amount
        payment.service_charge = service_charge
        payment.discount_amount = discount_amount
        payment.total_amount = total_amount
        payment.status = Payment.PENDING
        
        db.session.commit()
        return payment
    
    @staticmethod
    def approve_payment(session_id, admin_user_id, payment_method='cash'):
        """Admin approves payment for a session.
        
        This triggers the full payment completion flow:
        1. Mark payment as PAID
        2. Mark all session orders as PAID
        3. Generate final bill
        4. Mark session as COMPLETED
        5. Release token (make AVAILABLE)
        6. Create customer notification
        """
        session = db.session.get(CustomerSession, session_id)
        if not session:
            raise ValueError('Session not found')
        
        # Step 1: Mark payment as paid
        payment = session.payment
        if not payment:
            payment = PaymentService.create_payment_for_session(session)
        
        payment.status = Payment.PAID
        payment.payment_method = payment_method
        payment.approved_by = admin_user_id
        payment.paid_at = datetime.now(timezone.utc)
        
        # Step 2: Mark all orders as PAID
        for order in session.orders.all():
            if order.status in [Order.SERVED, Order.PREPARING, Order.CONFIRMED, Order.PENDING, Order.READY, Order.SERVING]:
                order.status = Order.PAID
                order.paid_at = datetime.now(timezone.utc)
            order.payment_status = 'paid'
        
        # Step 3: Generate final bill
        bill = BillingService.generate_bill(session)
        
        # Step 4: Mark session as completed
        session.status = CustomerSession.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        
        # Step 5: Release token
        if session.token_id:
            TokenService.release_token(session.token_id)
        
        db.session.commit()
        
        # Step 6: Send notification
        NotificationService.notify_payment_success(session)
        
        return payment
    
    @staticmethod
    def pay_online(session_id, payment_method='online_upi', transaction_id=None):
        """Customer pays directly online from their table/mobile phone."""
        session = db.session.get(CustomerSession, session_id)
        if not session:
            raise ValueError('Session not found')
        
        orders = session.orders.all()
        if not orders:
            raise ValueError('No orders found to pay for')
            
        # Step 1: Mark or create payment record
        payment = session.payment
        if not payment:
            payment = PaymentService.create_payment_for_session(session)
        
        payment.status = Payment.PAID
        payment.payment_method = payment_method or 'online_upi'
        payment.paid_at = datetime.now(timezone.utc)
        
        # Step 2: Mark all orders as PAID
        for order in orders:
            if order.status in [Order.SERVED, Order.PREPARING, Order.CONFIRMED, Order.PENDING, Order.READY, Order.SERVING, Order.TRANSFERRED_TO_WAITER]:
                order.status = Order.PAID
                order.paid_at = datetime.now(timezone.utc)
            order.payment_status = 'paid'
        
        # Step 3: Generate final bill
        bill = BillingService.generate_bill(session)
        
        # Step 4: Mark session as completed
        session.status = CustomerSession.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        
        # Step 5: Release token
        if session.token_id:
            TokenService.release_token(session.token_id)
        
        db.session.commit()
        
        # Step 6: Send customer notification
        NotificationService.notify_payment_success(session)
        
        return payment
    
    @staticmethod
    def request_counter_payment(session_id, payment_method='counter_cash'):
        """Customer requests to pay at the restaurant counter (cash or counter scan/card)."""
        session = db.session.get(CustomerSession, session_id)
        if not session:
            raise ValueError('Session not found')
            
        payment = session.payment
        if not payment:
            payment = PaymentService.create_payment_for_session(session)
            
        payment.status = Payment.PENDING
        payment.payment_method = payment_method or 'counter_cash'
        session.status = CustomerSession.COUNTER_PAYMENT_REQUESTED
        db.session.commit()
        
        NotificationService.notify_counter_payment_requested(session, payment_method)
        return payment

    @staticmethod
    def get_pending_payments():
        """Get all sessions with pending payments, including counter payment requests."""
        sessions = CustomerSession.query.filter(
            CustomerSession.status.in_(['active', 'payment_pending', 'counter_payment_requested'])
        ).all()
        
        result = []
        for session in sessions:
            orders = session.orders.all()
            if orders:
                # Check if any orders are served/ready
                has_served = any(o.status in ['served', 'payment_pending', 'ready'] for o in orders)
                total = sum(o.total_amount for o in orders)
                is_counter_requested = (
                    session.status == CustomerSession.COUNTER_PAYMENT_REQUESTED or
                    (session.payment and session.payment.status == 'pending' and str(session.payment.payment_method).startswith('counter_'))
                )
                requested_method = session.payment.payment_method if session.payment else 'counter_cash'
                result.append({
                    'session': session,
                    'orders': orders,
                    'total': total,
                    'has_served': has_served,
                    'is_counter_requested': is_counter_requested,
                    'requested_method': requested_method,
                })
        
        return result
    
    @staticmethod
    def get_payment_stats():
        """Get payment statistics."""
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        paid_today = Payment.query.filter(
            Payment.paid_at >= today,
            Payment.status == Payment.PAID,
        ).all()
        
        total_collected = sum(p.total_amount for p in paid_today)
        payment_count = len(paid_today)
        pending = Payment.query.filter_by(status=Payment.PENDING).count()
        
        return {
            'total_collected_today': total_collected,
            'payments_today': payment_count,
            'pending_payments': pending,
        }
