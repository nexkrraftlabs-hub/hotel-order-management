"""API routes for AJAX operations (cart, orders, sessions)."""
from flask import Blueprint, request, jsonify, send_file
from app.extensions import db, csrf
from app.models.menu_item import MenuItem
from app.models.category import Category
from app.models.order import Order
from app.models.notification import Notification
from app.models.customer_session import CustomerSession
from app.services.session_service import SessionService
from app.services.cart_service import CartService
from app.services.order_service import OrderService
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
    """Get orders for a session."""
    browser_session_id = request.args.get('browser_session_id')
    if not browser_session_id:
        return jsonify({'orders': []})
    
    session = SessionService.get_session_by_browser_id(browser_session_id)
    if not session:
        return jsonify({'orders': [], 'token': None})
    
    orders = session.orders.all()
    return jsonify({
        'orders': [o.to_dict() for o in orders],
        'token': session.token.token_number if session.token else None,
        'session_id': session.session_id,
        'session_status': session.status,
        'total_amount': session.total_amount,
        'has_bill': session.bill is not None,
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
