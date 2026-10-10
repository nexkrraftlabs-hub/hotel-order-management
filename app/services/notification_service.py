"""Notification service for real-time customer/staff notifications."""
from app.extensions import db, socketio
from app.models.notification import Notification


class NotificationService:
    """Service for creating and broadcasting notifications."""
    
    @staticmethod
    def create_notification(session, notification_type, title, message, data=None):
        """Create a notification and emit via SocketIO."""
        notification = Notification(
            session_id=session.id if session else None,
            type=notification_type,
            title=title,
            message=message,
            data=data,
        )
        db.session.add(notification)
        db.session.commit()
        
        # Emit via SocketIO
        room = f'session_{session.session_id}' if session else 'admin'
        socketio.emit('notification', notification.to_dict(), to=room)
        
        # Also emit to admin room
        socketio.emit('admin_notification', {
            'type': notification_type,
            'title': title,
            'message': message,
            'session_id': session.session_id if session else None,
        }, to='admin')
        
        return notification
    
    @staticmethod
    def notify_order_placed(session, order):
        """Notify that a new order has been placed."""
        NotificationService.create_notification(
            session,
            Notification.ORDER_PLACED,
            'Order Placed!',
            f'Your order {order.order_id} has been placed successfully. Token: #{session.token.token_number:02d}' if session.token else f'Your order {order.order_id} has been placed.',
        )
        # Emit to kitchen and admin
        socketio.emit('new_order', {
            'order_id': order.order_id,
            'token': session.token.token_number if session.token else None,
            'items_count': len(order.items),
        }, to='admin')
        socketio.emit('new_order', {
            'order_id': order.order_id,
            'token': session.token.token_number if session.token else None,
        }, to='kitchen')
    
    @staticmethod
    def notify_order_status_change(session, order, new_status):
        """Notify customer about order status change."""
        status_messages = {
            'confirmed': ('Order Confirmed', f'Your order {order.order_id} has been confirmed.'),
            'sent_to_kitchen': ('Sent to Kitchen', f'Your order {order.order_id} has been sent to the kitchen.'),
            'kitchen_accepted': ('Kitchen Accepted', f'The kitchen has accepted your order {order.order_id}.'),
            'preparing': ('Preparing Your Food', f'Your order {order.order_id} is being prepared.'),
            'ready': ('Order Ready!', f'Your order {order.order_id} is ready!'),
            'transferred_to_waiter': ('On the Way', f'Your order {order.order_id} is on its way to you.'),
            'serving': ('Being Served', f'Your order {order.order_id} is being served.'),
            'served': ('Order Served', f'Your order {order.order_id} has been served. Enjoy your meal!'),
        }
        
        title, message = status_messages.get(new_status, ('Order Updated', f'Order {order.order_id} status: {new_status}'))
        
        notification_type = new_status
        NotificationService.create_notification(session, notification_type, title, message)
        
        # Emit order status update
        socketio.emit('order_update', {
            'order_id': order.order_id,
            'status': new_status,
            'token': session.token.token_number if session.token else None,
        }, to=f'session_{session.session_id}')
        
        # Notify relevant dashboards
        if new_status in ['ready', 'transferred_to_waiter']:
            socketio.emit('order_update', {
                'order_id': order.order_id,
                'status': new_status,
            }, to='waiter')
        
        socketio.emit('order_update', {
            'order_id': order.order_id,
            'status': new_status,
        }, to='kitchen')
    
    @staticmethod
    def notify_payment_success(session):
        """Notify customer about successful payment."""
        NotificationService.create_notification(
            session,
            Notification.PAYMENT_SUCCESS,
            'Payment Successful!',
            'Your payment has been received. Your bill is ready for download.',
        )
        
        # Emit payment success event
        socketio.emit('payment_success', {
            'session_id': session.session_id,
            'token': session.token.token_number if session.token else None,
        }, to=f'session_{session.session_id}')
        
        # Also notify admin
        socketio.emit('admin_notification', {
            'type': 'payment_success',
            'title': 'Payment Received!',
            'message': f'Payment of ₹{session.total_amount:.0f} received for Token #{session.token.token_number if session.token else "N/A"}.',
            'session_id': session.session_id,
        }, to='admin')
    
    @staticmethod
    def notify_item_ready(order_item):
        """Notify customer that a specific item in their order is ready at the counter."""
        order = order_item.order
        session = order.session if order else None
        token_num = session.token.token_number if session and session.token else 0
        token_str = f"#{token_num:02d}" if token_num else "your order"
        title = "🔔 Food Ready at Counter!"
        message = f"Token {token_str}: '{order_item.item_name}' (x{order_item.quantity}) is ready at the counter! Please collect it."
        
        NotificationService.create_notification(
            session,
            Notification.ITEM_READY,
            title,
            message,
            data=f'{{"order_id": "{order.order_id if order else ""}", "item_id": {order_item.id}}}'
        )
        
        # Emit real-time item ready event to customer session
        if session:
            socketio.emit('item_ready', {
                'order_id': order.order_id if order else '',
                'item_id': order_item.id,
                'item_name': order_item.item_name,
                'quantity': order_item.quantity,
                'token': token_num,
                'message': message,
            }, to=f'session_{session.session_id}')
            
        # Emit to staff rooms
        socketio.emit('item_status_update', {
            'order_id': order.order_id if order else '',
            'item_id': order_item.id,
            'item_name': order_item.item_name,
            'status': 'ready',
            'token': token_num,
        }, to='admin')
        socketio.emit('item_status_update', {
            'order_id': order.order_id if order else '',
            'item_id': order_item.id,
            'item_name': order_item.item_name,
            'status': 'ready',
            'token': token_num,
        }, to='kitchen')

    @staticmethod
    def notify_item_collected(order_item):
        """Notify that customer collected an item from counter."""
        order = order_item.order
        session = order.session if order else None
        token_num = session.token.token_number if session and session.token else 0
        
        if session:
            socketio.emit('item_collected', {
                'order_id': order.order_id if order else '',
                'item_id': order_item.id,
                'item_name': order_item.item_name,
                'token': token_num,
            }, to=f'session_{session.session_id}')
            
        socketio.emit('item_status_update', {
            'order_id': order.order_id if order else '',
            'item_id': order_item.id,
            'item_name': order_item.item_name,
            'status': 'collected',
            'token': token_num,
        }, to='admin')
        socketio.emit('item_status_update', {
            'order_id': order.order_id if order else '',
            'item_id': order_item.id,
            'item_name': order_item.item_name,
            'status': 'collected',
            'token': token_num,
        }, to='kitchen')

    @staticmethod
    def notify_counter_payment_requested(session, payment_method='cash'):
        """Notify staff that customer requested to pay at counter."""
        token_num = session.token.token_number if session.token else 0
        token_str = f"#{token_num:02d}" if token_num else "Customer"
        title = "🏢 Counter Payment Requested"
        method_label = "Cash" if payment_method in ['cash', 'counter_cash'] else "Counter UPI / Card"
        message = f"Token {token_str} requested to pay ₹{session.total_amount:.0f} at counter via {method_label}."
        
        NotificationService.create_notification(
            session,
            Notification.COUNTER_PAYMENT_REQUESTED,
            title,
            message
        )
        
        socketio.emit('counter_payment_requested', {
            'session_id': session.session_id,
            'token': token_num,
            'total_amount': session.total_amount,
            'payment_method': payment_method,
            'message': message,
        }, to='admin')
    
    @staticmethod
    def get_session_notifications(session_id):
        """Get all notifications for a session."""
        return Notification.query.filter_by(session_id=session_id).order_by(
            Notification.created_at.desc()
        ).all()
    
    @staticmethod
    def get_unread_count(session_id):
        """Get unread notification count for a session."""
        return Notification.query.filter_by(
            session_id=session_id,
            is_read=False
        ).count()
    
    @staticmethod
    def mark_as_read(notification_id):
        """Mark a notification as read."""
        notification = db.session.get(Notification, notification_id)
        if notification:
            notification.is_read = True
            db.session.commit()
    
    @staticmethod
    def mark_all_read(session_id):
        """Mark all session notifications as read."""
        Notification.query.filter_by(
            session_id=session_id,
            is_read=False
        ).update({'is_read': True})
        db.session.commit()
