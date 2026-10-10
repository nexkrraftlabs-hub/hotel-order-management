"""API routes for AJAX operations (cart, orders, sessions)."""
from flask import Blueprint, request, jsonify, send_file
from app.extensions import db, csrf
from app.models.menu_item import MenuItem
from app.models.category import Category
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.restaurant import Restaurant
from app.models.notification import Notification
from app.models.customer_session import CustomerSession
from app.services.session_service import SessionService
from app.services.cart_service import CartService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.notification_service import NotificationService
from app.services.billing_service import BillingService

api_bp = Blueprint('api', __name__)


@api_bp.before_request
def before_api_request():
    """Exempt API routes from CSRF for AJAX calls."""
    pass


@api_bp.route('/session', methods=['POST'])
@csrf.exempt
def get_or_create_session():
    """Get or create customer session based on browser session ID."""
    data = request.get_json() or {}
    browser_session_id = data.get('browser_session_id')
    
    session = SessionService.get_or_create_session(browser_session_id)
    
    cart = CartService.get_cart(session)
    
    return jsonify({
        'session_id': session.session_id,
        'browser_session_id': session.browser_session_id,
        'status': session.status,
        'token': session.token.token_number if session.token else None,
        'cart': cart.to_dict() if cart else {'items': [], 'total_items': 0, 'subtotal': 0},
    })


@api_bp.route('/cart/add', methods=['POST'])
@csrf.exempt
def add_to_cart():
    """Add item to cart."""
    data = request.get_json() or {}
    browser_session_id = data.get('browser_session_id')
    menu_item_id = data.get('menu_item_id')
    quantity = data.get('quantity', 1)
    
    if not browser_session_id or not menu_item_id:
        return jsonify({'error': 'Missing required fields'}), 400
    
    session = SessionService.get_or_create_session(browser_session_id)
    cart = CartService.get_cart(session)
    
    try:
        CartService.add_item(cart, menu_item_id, quantity, data.get('special_instructions'))
        # Refresh cart
        db.session.refresh(cart)
        return jsonify({
            'success': True,
            'cart': cart.to_dict(),
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/cart/update', methods=['POST'])
@csrf.exempt
def update_cart_item():
    """Update cart item quantity."""
    data = request.get_json() or {}
    browser_session_id = data.get('browser_session_id')
    item_id = data.get('item_id')
    quantity = data.get('quantity', 1)
    
    if not browser_session_id or not item_id:
        return jsonify({'error': 'Missing required fields'}), 400
    
    session = SessionService.get_session_by_browser_id(browser_session_id)
    if not session or not session.cart:
        return jsonify({'error': 'Session not found'}), 404
    
    try:
        CartService.update_item_quantity(session.cart, item_id, quantity)
        db.session.refresh(session.cart)
        return jsonify({
            'success': True,
            'cart': session.cart.to_dict(),
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/cart/remove', methods=['POST'])
@csrf.exempt
def remove_from_cart():
    """Remove item from cart."""
    data = request.get_json() or {}
    browser_session_id = data.get('browser_session_id')
    item_id = data.get('item_id')
    
    if not browser_session_id or not item_id:
        return jsonify({'error': 'Missing required fields'}), 400
    
    session = SessionService.get_session_by_browser_id(browser_session_id)
    if not session or not session.cart:
        return jsonify({'error': 'Session not found'}), 404
    
    CartService.remove_item(session.cart, item_id)
    db.session.refresh(session.cart)
    return jsonify({
        'success': True,
        'cart': session.cart.to_dict(),
    })


@api_bp.route('/cart', methods=['GET'])
def get_cart():
    """Get current cart state."""
    browser_session_id = request.args.get('browser_session_id')
    if not browser_session_id:
        return jsonify({'cart': {'items': [], 'total_items': 0, 'subtotal': 0}})
    
    session = SessionService.get_session_by_browser_id(browser_session_id)
    if not session or not session.cart:
        return jsonify({'cart': {'items': [], 'total_items': 0, 'subtotal': 0}})
    
    return jsonify({'cart': session.cart.to_dict()})


@api_bp.route('/order/place', methods=['POST'])
@csrf.exempt
def place_order():
    """Place an order from cart."""
    data = request.get_json() or {}
    browser_session_id = data.get('browser_session_id')
    
    if not browser_session_id:
        return jsonify({'error': 'Session required'}), 400
    
    session = SessionService.get_session_by_browser_id(browser_session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    try:
        order = OrderService.place_order(session, data.get('special_instructions'))
        return jsonify({
            'success': True,
            'order': order.to_dict(),
            'token': session.token.token_number if session.token else None,
            'session_id': session.session_id,
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/orders', methods=['GET'])
def get_orders():
    """Get orders for a session with live item-by-item status and payment information."""
    browser_session_id = request.args.get('browser_session_id')
    if not browser_session_id:
        return jsonify({
            'orders': [],
            'token': None,
            'is_paid': False,
            'is_counter_requested': False,
            'has_ready_items': False,
            'ready_items': [],
        })
    
    session = SessionService.get_session_by_browser_id(browser_session_id)
    if not session:
        return jsonify({
            'orders': [],
            'token': None,
            'is_paid': False,
            'is_counter_requested': False,
            'has_ready_items': False,
            'ready_items': [],
        })
    
    orders = session.orders.all()
    ready_items = []
    for o in orders:
        for item in o.items:
            if getattr(item, 'status', None) == 'ready':
                ready_items.append({
                    'id': item.id,
                    'order_id': o.order_id,
                    'item_name': item.item_name,
                    'quantity': item.quantity,
                    'is_veg': item.is_veg,
                })
                
    is_paid = getattr(session, 'is_paid', False)
    is_counter_requested = getattr(session, 'is_counter_payment_requested', False)
    
    return jsonify({
        'orders': [o.to_dict() for o in orders],
        'token': session.token.token_number if session.token else None,
        'session_id': session.session_id,
        'session_status': session.status,
        'total_amount': session.total_amount,
        'has_bill': session.bill is not None,
        'ready_items': ready_items,
        'has_ready_items': len(ready_items) > 0,
        'is_paid': is_paid,
        'payment_status': session.payment.status if session.payment else 'pending',
        'payment_method': session.payment.payment_method if session.payment else None,
        'is_counter_requested': is_counter_requested,
    })


@api_bp.route('/order/<order_id>/status', methods=['GET'])
def get_order_status(order_id):
    """Get live order status."""
    order = Order.query.filter_by(order_id=order_id).first()
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    return jsonify({
        'order_id': order.order_id,
        'status': order.status,
        'status_display': order.status_display,
        'created_at': order.created_at.isoformat() if order.created_at else None,
        'confirmed_at': order.confirmed_at.isoformat() if order.confirmed_at else None,
        'sent_to_kitchen_at': order.sent_to_kitchen_at.isoformat() if order.sent_to_kitchen_at else None,
        'kitchen_accepted_at': order.kitchen_accepted_at.isoformat() if order.kitchen_accepted_at else None,
        'preparing_at': order.preparing_at.isoformat() if order.preparing_at else None,
        'ready_at': order.ready_at.isoformat() if order.ready_at else None,
        'served_at': order.served_at.isoformat() if order.served_at else None,
        'paid_at': order.paid_at.isoformat() if order.paid_at else None,
    })


@api_bp.route('/notifications', methods=['GET'])
def get_notifications():
    """Get notifications for a session."""
    browser_session_id = request.args.get('browser_session_id')
    if not browser_session_id:
        return jsonify({'notifications': [], 'unread_count': 0})
    
    session = SessionService.get_session_by_browser_id(browser_session_id)
    if not session:
        # Also check completed sessions
        sessions = SessionService.get_session_history(browser_session_id)
        if sessions:
            session = sessions[0]
        else:
            return jsonify({'notifications': [], 'unread_count': 0})
    
    notifications = NotificationService.get_session_notifications(session.id)
    unread = NotificationService.get_unread_count(session.id)
    
    return jsonify({
        'notifications': [n.to_dict() for n in notifications],
        'unread_count': unread,
    })


@api_bp.route('/notifications/read', methods=['POST'])
@csrf.exempt
def mark_notifications_read():
    """Mark all notifications as read."""
    data = request.get_json() or {}
    browser_session_id = data.get('browser_session_id')
    
    if not browser_session_id:
        return jsonify({'error': 'Session required'}), 400
    
    session = SessionService.get_session_by_browser_id(browser_session_id)
    if session:
        NotificationService.mark_all_read(session.id)
    
    return jsonify({'success': True})


@api_bp.route('/menu/items', methods=['GET'])
def get_menu_items():
    """Get menu items with optional filtering."""
    category_id = request.args.get('category_id', type=int)
    search_query = request.args.get('q', '').strip()
    
    query = MenuItem.query.filter_by(is_available=True)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if search_query:
        query = query.filter(MenuItem.name.ilike(f'%{search_query}%'))
    
    items = query.all()
    return jsonify({
        'items': [item.to_dict() for item in items],
    })


@api_bp.route('/menu/categories', methods=['GET'])
def get_categories():
    """Get all active categories."""
    categories = Category.query.filter_by(is_active=True).order_by(Category.display_order).all()
    return jsonify({
        'categories': [{
            'id': c.id,
            'name': c.name,
            'description': c.description,
            'image': c.image,
            'items_count': c.active_items_count,
        } for c in categories],
    })


@api_bp.route('/bill/download/<session_id>', methods=['GET'])
def download_bill(session_id):
    """Download bill as PDF."""
    session = SessionService.get_session_by_id(session_id)
    if not session or not session.bill:
        return jsonify({'error': 'Bill not found'}), 404
    
    pdf_buffer = BillingService.generate_pdf(session.bill)
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'bill_{session.bill.bill_number}.pdf',
    )


@api_bp.route('/session/update', methods=['POST'])
@csrf.exempt
def update_session_info():
    """Update customer info on session."""
    data = request.get_json() or {}
    browser_session_id = data.get('browser_session_id')
    
    if not browser_session_id:
        return jsonify({'error': 'Session required'}), 400
    
    session = SessionService.get_session_by_browser_id(browser_session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    SessionService.update_customer_info(
        session,
        name=data.get('name'),
        phone=data.get('phone'),
        email=data.get('email'),
    )
    
    return jsonify({'success': True})


# ─── DUAL PAYMENT APIS (TABLE/MOBILE PAY & COUNTER PAY) ──────
@api_bp.route('/payment/info', methods=['GET'])
def get_payment_info():
    """Get payment details for table/mobile payment (UPI QR string, total, restaurant info)."""
    import urllib.parse
    browser_session_id = request.args.get('browser_session_id')
    if not browser_session_id:
        return jsonify({'error': 'Session required'}), 400
    
    session = SessionService.get_session_by_browser_id(browser_session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
        
    restaurant = Restaurant.query.first()
    rest_name = restaurant.name if restaurant else 'The Royal Feast'
    upi_id = getattr(restaurant, 'upi_id', None) or 'royalfeast@upi'
    
    total = session.total_amount
    token_num = session.token.token_number if session.token else 0
    token_str = f"{token_num:02d}" if token_num else "00"
    
    encoded_name = urllib.parse.quote(rest_name)
    upi_uri = f"upi://pay?pa={upi_id}&pn={encoded_name}&am={total:.2f}&cu=INR&tn=Token_{token_str}"
    
    return jsonify({
        'session_id': session.session_id,
        'token': token_num,
        'total_amount': total,
        'restaurant_name': rest_name,
        'upi_id': upi_id,
        'upi_uri': upi_uri,
        'is_paid': getattr(session, 'is_paid', False),
        'is_counter_requested': getattr(session, 'is_counter_payment_requested', False),
        'payment_status': session.payment.status if session.payment else 'pending',
        'has_bill': session.bill is not None,
    })


@api_bp.route('/payment/pay-online', methods=['POST'])
@csrf.exempt
def pay_online():
    """Customer pays directly from mobile / table (UPI / QR / Instant online payment)."""
    data = request.get_json() or {}
    browser_session_id = data.get('browser_session_id')
    payment_method = data.get('payment_method', 'online_upi')
    transaction_id = data.get('transaction_id')
    
    if not browser_session_id:
        return jsonify({'error': 'Session required'}), 400
        
    session = SessionService.get_session_by_browser_id(browser_session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
        
    try:
        payment = PaymentService.pay_online(session.id, payment_method=payment_method, transaction_id=transaction_id)
        return jsonify({
            'success': True,
            'message': 'Payment completed successfully!',
            'session_id': session.session_id,
            'bill_url': f'/bill/{session.session_id}',
            'payment_status': 'paid',
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/payment/request-counter', methods=['POST'])
@csrf.exempt
def request_counter_payment():
    """Customer requests to pay at the counter (cash or card/counter scanner)."""
    data = request.get_json() or {}
    browser_session_id = data.get('browser_session_id')
    payment_method = data.get('payment_method', 'counter_cash')
    
    if not browser_session_id:
        return jsonify({'error': 'Session required'}), 400
        
    session = SessionService.get_session_by_browser_id(browser_session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
        
    try:
        PaymentService.request_counter_payment(session.id, payment_method=payment_method)
        return jsonify({
            'success': True,
            'message': 'Counter payment requested. Please visit the counter to complete payment.',
            'session_status': 'counter_payment_requested',
            'token': session.token.token_number if session.token else None,
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# ─── ITEM-LEVEL STATUS APIS (PREPARATION & COUNTER PICKUP) ───
@api_bp.route('/order/item/<int:item_id>/status', methods=['POST'])
@csrf.exempt
def update_item_status(item_id):
    """Update individual order item status (pending, preparing, ready, collected)."""
    data = request.get_json() or {}
    new_status = data.get('status')
    if not new_status:
        return jsonify({'error': 'Status is required'}), 400
        
    try:
        item = OrderService.update_item_status(item_id, new_status)
        return jsonify({
            'success': True,
            'item': item.to_dict(),
            'order_id': item.order.order_id,
            'order_status': item.order.status,
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/order/<int:order_id>/items/ready', methods=['POST'])
@csrf.exempt
def mark_all_order_items_ready(order_id):
    """Mark all items of an order ready for counter pickup."""
    try:
        order = OrderService.mark_all_items_ready(order_id)
        return jsonify({'success': True, 'order': order.to_dict()})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/order/<int:order_id>/items/collected', methods=['POST'])
@csrf.exempt
def mark_all_order_items_collected(order_id):
    """Mark all items of an order as collected by customer from counter."""
    try:
        order = OrderService.mark_served(order_id)
        return jsonify({'success': True, 'order': order.to_dict()})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
