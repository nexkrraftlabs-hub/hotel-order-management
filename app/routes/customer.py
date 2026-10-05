from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session as flask_session
from app.extensions import db
from app.models.category import Category
from app.models.menu_item import MenuItem
from app.models.restaurant import Restaurant
from app.services.session_service import SessionService
from app.services.cart_service import CartService

customer_bp = Blueprint('customer', __name__)


@customer_bp.route('/login')
def login_redirect():
    """Convenience redirect to staff login."""
    return redirect(url_for('auth.login'))


@customer_bp.route('/')
def home():
    """Customer home page - main entry point after QR scan."""
    restaurant = Restaurant.query.first()
    categories = Category.query.filter_by(is_active=True).order_by(Category.display_order).all()
    popular_items = MenuItem.query.filter_by(is_popular=True, is_available=True).limit(10).all()
    featured_items = MenuItem.query.filter_by(is_featured=True, is_available=True).limit(10).all()
    
    return render_template('customer/home.html',
                         restaurant=restaurant,
                         categories=categories,
                         popular_items=popular_items,
                         featured_items=featured_items)


@customer_bp.route('/menu')
def menu():
    """Full menu page with category filtering."""
    categories = Category.query.filter_by(is_active=True).order_by(Category.display_order).all()
    category_id = request.args.get('category', type=int)
    
    if category_id:
        items = MenuItem.query.filter_by(category_id=category_id, is_available=True).all()
        active_category = db.session.get(Category, category_id)
    else:
        items = MenuItem.query.filter_by(is_available=True).all()
        active_category = None
    
    return render_template('customer/menu.html',
                         categories=categories,
                         items=items,
                         active_category=active_category)


@customer_bp.route('/search')
def search():
    """Search page."""
    query = request.args.get('q', '').strip()
    items = []
    if query:
        items = MenuItem.query.filter(
            MenuItem.is_available == True,
            MenuItem.name.ilike(f'%{query}%')
        ).all()
    
    categories = Category.query.filter_by(is_active=True).order_by(Category.display_order).all()
    return render_template('customer/search.html', items=items, query=query, categories=categories)


@customer_bp.route('/item/<int:item_id>')
def item_detail(item_id):
    """Food item detail page/modal data."""
    item = db.session.get(MenuItem, item_id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    return render_template('customer/item_detail.html', item=item)


@customer_bp.route('/cart')
def cart():
    """Cart page."""
    return render_template('customer/cart.html')


@customer_bp.route('/orders')
def orders():
    """Customer orders page showing current session orders."""
    return render_template('customer/orders.html')


@customer_bp.route('/profile')
def profile():
    """Customer profile page."""
    return render_template('customer/profile.html')


@customer_bp.route('/notifications')
def notifications():
    """Customer notifications page."""
    return render_template('customer/notifications.html')


@customer_bp.route('/bill/<session_id>')
def view_bill(session_id):
    """View bill for a session."""
    from app.services.billing_service import BillingService
    session = SessionService.get_session_by_id(session_id)
    if not session or not session.bill:
        return render_template('errors/404.html'), 404
    return render_template('customer/bill.html', session=session, bill=session.bill)
