"""Order service for order creation and lifecycle management."""
from app.extensions import db
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.customer_session import CustomerSession
from app.models.restaurant import Restaurant
from app.services.token_service import TokenService
from app.services.cart_service import CartService
from app.services.notification_service import NotificationService
from datetime import datetime, timezone


class OrderService:
    """Service for order creation, state transitions, and management."""
    
    @staticmethod
    def place_order(session, special_instructions=None):
        """Place an order from the session's cart.
        
        - If session has no token, allocate one.
        - If session already has a token, reuse it (multiple orders before payment).
        - Calculate totals server-side (never trust frontend).
        - Clear cart after successful order creation.
        """
        cart = session.cart
        if not cart or cart.is_empty:
            raise ValueError('Cart is empty')
        
        # Allocate token if needed (first order in session)
        if not session.token_id:
            token = TokenService.allocate_token()
            if not token:
                raise ValueError('No tokens available. Please try again later.')
            session.token_id = token.id
        
        # Get restaurant settings for tax/service charge
        restaurant = Restaurant.query.first()
        tax_percent = restaurant.tax_percent if restaurant else 10.0
        service_charge_percent = restaurant.service_charge_percent if restaurant else 5.0
        
        # Calculate totals server-side
        subtotal = 0
        order_items = []
        
        for cart_item in cart.items:
            menu_item = cart_item.menu_item
            if not menu_item or not menu_item.is_available:
                continue
            
            unit_price = menu_item.effective_price
            line_total = unit_price * cart_item.quantity
            subtotal += line_total
            
            order_item = OrderItem(
                menu_item_id=menu_item.id,
                item_name=menu_item.name,
                unit_price=unit_price,
                quantity=cart_item.quantity,
                line_total=line_total,
                is_veg=menu_item.is_veg,
                special_instructions=cart_item.special_instructions,
            )
            order_items.append(order_item)
        
        if not order_items:
            raise ValueError('No available items in cart')
        
        tax_amount = round(subtotal * tax_percent / 100, 2)
        service_charge = round(subtotal * service_charge_percent / 100, 2)
        total_amount = round(subtotal + tax_amount + service_charge, 2)
        
        # Create order
        order = Order(
            session_id=session.id,
            subtotal=subtotal,
            tax_amount=tax_amount,
            service_charge=service_charge,
            total_amount=total_amount,
            special_instructions=special_instructions or cart.special_instructions,
            status=Order.PENDING,
            payment_status='pending',
        )
        db.session.add(order)
        db.session.flush()  # Get order ID
        
        # Add items to order
        for item in order_items:
            item.order_id = order.id
            db.session.add(item)
        
        # Clear cart after order placement
        CartService.clear_cart(cart)
        
        db.session.commit()
        
        # Send notification
        NotificationService.notify_order_placed(session, order)
        
        return order
    
    @staticmethod
    def update_order_status(order_id, new_status, user_id=None):
        """Update order status with state machine validation."""
        order = db.session.get(Order, order_id)
        if not order:
            raise ValueError('Order not found')
        
        order.transition_to(new_status)
        db.session.commit()
        
        # Send appropriate notification
        NotificationService.notify_order_status_change(order.session, order, new_status)
        
        return order
    
    @staticmethod
    def confirm_order(order_id):
        """Admin confirms an order."""
        return OrderService.update_order_status(order_id, Order.CONFIRMED)
    
    @staticmethod
    def send_to_kitchen(order_id):
        """Admin sends order to kitchen."""
        from app.models.kitchen_assignment import KitchenAssignment
        
        order = OrderService.update_order_status(order_id, Order.SENT_TO_KITCHEN)
        
        # Create kitchen assignment
        assignment = KitchenAssignment(order_id=order.id, status='pending')
        db.session.add(assignment)
        db.session.commit()
        
        return order
    
    @staticmethod
    def kitchen_accept(order_id, kitchen_user_id=None):
        """Kitchen accepts an order."""
        from app.models.kitchen_assignment import KitchenAssignment
        
        order = OrderService.update_order_status(order_id, Order.KITCHEN_ACCEPTED)
        
        assignment = KitchenAssignment.query.filter_by(order_id=order.id).first()
        if assignment:
            assignment.status = 'accepted'
            assignment.accepted_by = kitchen_user_id
            assignment.accepted_at = datetime.now(timezone.utc)
            db.session.commit()
        
        return order
    
    @staticmethod
    def start_preparing(order_id):
        """Kitchen starts preparing order."""
        from app.models.kitchen_assignment import KitchenAssignment
        
        order = OrderService.update_order_status(order_id, Order.PREPARING)
        
        assignment = KitchenAssignment.query.filter_by(order_id=order.id).first()
        if assignment:
            assignment.status = 'preparing'
            assignment.started_at = datetime.now(timezone.utc)
            db.session.commit()
        
        return order
    
    @staticmethod
    def mark_ready(order_id):
        """Kitchen marks order as ready."""
        from app.models.kitchen_assignment import KitchenAssignment
        
        order = OrderService.update_order_status(order_id, Order.READY)
        
        assignment = KitchenAssignment.query.filter_by(order_id=order.id).first()
        if assignment:
            assignment.status = 'ready'
            assignment.completed_at = datetime.now(timezone.utc)
            db.session.commit()
        
        return order
    
    @staticmethod
    def transfer_to_waiter(order_id, waiter_user_id=None):
        """Transfer order from kitchen to waiter."""
        from app.models.waiter_assignment import WaiterAssignment
        
        order = OrderService.update_order_status(order_id, Order.TRANSFERRED_TO_WAITER)
        
        assignment = WaiterAssignment(
            order_id=order.id,
            assigned_to=waiter_user_id,
            status='pending',
            assigned_at=datetime.now(timezone.utc),
        )
        db.session.add(assignment)
        db.session.commit()
        
        return order
    
    @staticmethod
    def waiter_accept(order_id, waiter_user_id=None):
        """Waiter accepts an order for serving."""
        from app.models.waiter_assignment import WaiterAssignment
        
        order = OrderService.update_order_status(order_id, Order.SERVING)
        
        assignment = WaiterAssignment.query.filter_by(order_id=order.id).first()
        if assignment:
            assignment.status = 'serving'
            assignment.assigned_to = waiter_user_id
            assignment.accepted_at = datetime.now(timezone.utc)
            db.session.commit()
        
        return order
    
    @staticmethod
    def mark_served(order_id):
        """Waiter marks order as served."""
        from app.models.waiter_assignment import WaiterAssignment
        
        order = OrderService.update_order_status(order_id, Order.SERVED)
        
        assignment = WaiterAssignment.query.filter_by(order_id=order.id).first()
        if assignment:
            assignment.status = 'served'
            assignment.served_at = datetime.now(timezone.utc)
            db.session.commit()
        
        return order
    
    @staticmethod
    def get_orders_by_status(status):
        """Get all orders with a specific status."""
        return Order.query.filter_by(status=status).order_by(Order.created_at.desc()).all()
    
    @staticmethod
    def get_session_orders(session_id):
        """Get all orders for a session."""
        return Order.query.filter_by(session_id=session_id).order_by(Order.created_at.desc()).all()
    
    @staticmethod
    def get_today_orders():
        """Get all orders placed today."""
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        return Order.query.filter(Order.created_at >= today).order_by(Order.created_at.desc()).all()
    
    @staticmethod
    def get_order_stats():
        """Get order statistics for dashboard."""
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_orders = Order.query.filter(Order.created_at >= today)
        
        total_orders = today_orders.count()
        total_revenue = sum(o.total_amount for o in today_orders.filter_by(payment_status='paid').all())
        pending_orders = today_orders.filter_by(status=Order.PENDING).count()
        preparing_orders = today_orders.filter(Order.status.in_([Order.PREPARING, Order.KITCHEN_ACCEPTED])).count()
        ready_orders = today_orders.filter_by(status=Order.READY).count()
        served_orders = today_orders.filter_by(status=Order.SERVED).count()
        
        avg_order_value = round(total_revenue / total_orders, 2) if total_orders > 0 else 0
        
        return {
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'pending_orders': pending_orders,
            'preparing_orders': preparing_orders,
            'ready_orders': ready_orders,
            'served_orders': served_orders,
            'avg_order_value': avg_order_value,
        }
