"""Admin dashboard routes."""
import os
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.extensions import db, csrf
from app.models.user import User
from app.models.role import Role
from app.models.restaurant import Restaurant
from app.models.category import Category
from app.models.menu_item import MenuItem
from app.models.order import Order
from app.models.token import Token
from app.models.customer_session import CustomerSession
from app.models.payment import Payment
from app.models.bill import Bill
from app.models.notification import Notification
from app.models.activity_log import ActivityLog
from app.services.token_service import TokenService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.qr_service import QRService
from app.services.billing_service import BillingService
from datetime import datetime, timezone

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def allowed_file(filename):
    """Check if file extension is allowed."""
    allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed


from app.services.cloudinary_service import CloudinaryService


def save_upload(file, folder='restaurant'):
    """Save uploaded file using Cloudinary CDN if configured, or local static uploads."""
    if not file or not file.filename:
        return None
    if not allowed_file(file.filename):
        raise ValueError('Invalid file type. Allowed: png, jpg, jpeg, gif, webp')
    
    return CloudinaryService.upload_file(file, folder=folder)


# ─── DASHBOARD ───────────────────────────────────────────────
@admin_bp.route('/')
@admin_required
def dashboard():
    """Admin dashboard with analytics."""
    order_stats = OrderService.get_order_stats()
    token_stats = TokenService.get_token_stats()
    payment_stats = PaymentService.get_payment_stats()
    
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    
    qr_url = os.environ.get('APP_BASE_URL') or current_app.config.get('APP_BASE_URL') or 'https://hotel-order-management-zdnb.onrender.com/'
    if 'the-royal-feast' in qr_url:
        qr_url = 'https://hotel-order-management-zdnb.onrender.com/'
    qr_img_url = 'https://res.cloudinary.com/dqh2jlqza/image/upload/v1791167187/royal_feast/branding/live_restaurant_qr.png'

    return render_template('admin/dashboard.html',
                         order_stats=order_stats,
                         token_stats=token_stats,
                         payment_stats=payment_stats,
                         recent_orders=recent_orders,
                         qr_url=qr_url,
                         qr_img_url=qr_img_url)


# ─── ORDERS ──────────────────────────────────────────────────
@admin_bp.route('/orders')
@admin_required
def orders():
    """Order management page."""
    status_filter = request.args.get('status', 'all')
    
    query = Order.query.order_by(Order.created_at.desc())
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    orders_list = query.all()
    return render_template('admin/orders.html', orders=orders_list, status_filter=status_filter)


@admin_bp.route('/orders/live')
@admin_required
def live_orders():
    """Live orders dashboard."""
    active_statuses = ['pending', 'confirmed', 'sent_to_kitchen', 'kitchen_accepted', 
                       'preparing', 'ready', 'transferred_to_waiter', 'serving', 'served']
    orders_list = Order.query.filter(Order.status.in_(active_statuses)).order_by(Order.created_at.desc()).all()
    return render_template('admin/live_orders.html', orders=orders_list)


@admin_bp.route('/order/<int:order_id>/confirm', methods=['POST'])
@admin_required
@csrf.exempt
def confirm_order(order_id):
    """Confirm an order."""
    try:
        OrderService.confirm_order(order_id)
        ActivityLog.log('Order confirmed', user_id=current_user.id, entity_type='order', entity_id=order_id)
        db.session.commit()
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@admin_bp.route('/order/<int:order_id>/send-to-kitchen', methods=['POST'])
@admin_required
@csrf.exempt
def send_to_kitchen(order_id):
    """Send order to kitchen."""
    try:
        OrderService.send_to_kitchen(order_id)
        ActivityLog.log('Order sent to kitchen', user_id=current_user.id, entity_type='order', entity_id=order_id)
        db.session.commit()
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# ─── TOKENS ──────────────────────────────────────────────────
@admin_bp.route('/tokens')
@admin_required
def tokens():
    """Token management dashboard."""
    all_tokens = TokenService.get_all_tokens()
    stats = TokenService.get_token_stats()
    return render_template('admin/tokens.html', tokens=all_tokens, stats=stats)


@admin_bp.route('/token/<int:token_id>/toggle', methods=['POST'])
@admin_required
@csrf.exempt
def toggle_token(token_id):
    """Enable/disable a token."""
    token = db.session.get(Token, token_id)
    if token:
        token.is_enabled = not token.is_enabled
        db.session.commit()
        return jsonify({'success': True, 'is_enabled': token.is_enabled})
    return jsonify({'error': 'Token not found'}), 404


# ─── PAYMENTS ────────────────────────────────────────────────
@admin_bp.route('/payments')
@admin_required
def payments():
    """Payment management page."""
    pending = PaymentService.get_pending_payments()
    completed = Payment.query.filter_by(status='paid').order_by(Payment.paid_at.desc()).limit(50).all()
    return render_template('admin/payments.html', pending=pending, completed=completed)


@admin_bp.route('/payment/approve/<int:session_id>', methods=['POST'])
@admin_required
@csrf.exempt
def approve_payment(session_id):
    """Approve payment for a session."""
    try:
        data = request.get_json() or {}
        payment_method = data.get('payment_method', 'cash')
        
        PaymentService.approve_payment(session_id, current_user.id, payment_method)
        ActivityLog.log('Payment approved', user_id=current_user.id, 
                       entity_type='session', entity_id=session_id)
        db.session.commit()
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# ─── BILLS ───────────────────────────────────────────────────
@admin_bp.route('/bills')
@admin_required
def bills():
    """Bills management page."""
    all_bills = Bill.query.order_by(Bill.created_at.desc()).all()
    return render_template('admin/bills.html', bills=all_bills)


@admin_bp.route('/bill/<int:bill_id>/pdf')
@admin_required
def bill_pdf(bill_id):
    """Download bill PDF."""
    from flask import send_file
    bill = db.session.get(Bill, bill_id)
    if not bill:
        flash('Bill not found.', 'danger')
        return redirect(url_for('admin.bills'))
    
    pdf_buffer = BillingService.generate_pdf(bill)
    return send_file(pdf_buffer, mimetype='application/pdf', 
                    as_attachment=True, download_name=f'bill_{bill.bill_number}.pdf')


# ─── MENU MANAGEMENT ────────────────────────────────────────
@admin_bp.route('/categories')
@admin_required
def categories():
    """Category management page."""
    cats = Category.query.order_by(Category.display_order).all()
    return render_template('admin/categories.html', categories=cats)


@admin_bp.route('/category/add', methods=['POST'])
@admin_required
def add_category():
    """Add a new category."""
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    display_order = request.form.get('display_order', 0, type=int)
    
    if not name:
        flash('Category name is required.', 'danger')
        return redirect(url_for('admin.categories'))
    
    image_path = None
    if 'image' in request.files:
        try:
            image_path = save_upload(request.files['image'], folder='categories')
        except ValueError as e:
            flash(str(e), 'danger')
            return redirect(url_for('admin.categories'))
    
    cat = Category(name=name, description=description, image=image_path, display_order=display_order)
    db.session.add(cat)
    ActivityLog.log('Category added', user_id=current_user.id, entity_type='category', details=name)
    db.session.commit()
    
    flash(f'Category "{name}" added successfully.', 'success')
    return redirect(url_for('admin.categories'))


@admin_bp.route('/category/<int:cat_id>/edit', methods=['POST'])
@admin_required
def edit_category(cat_id):
    """Edit a category."""
    cat = db.session.get(Category, cat_id)
    if not cat:
        flash('Category not found.', 'danger')
        return redirect(url_for('admin.categories'))
    
    cat.name = request.form.get('name', cat.name).strip()
    cat.description = request.form.get('description', cat.description).strip()
    cat.display_order = request.form.get('display_order', cat.display_order, type=int)
    
    if 'image' in request.files and request.files['image'].filename:
        try:
            cat.image = save_upload(request.files['image'], folder='categories')
        except ValueError as e:
            flash(str(e), 'danger')
            return redirect(url_for('admin.categories'))
    
    ActivityLog.log('Category updated', user_id=current_user.id, entity_type='category', entity_id=cat_id)
    db.session.commit()
    flash(f'Category "{cat.name}" updated.', 'success')
    return redirect(url_for('admin.categories'))


@admin_bp.route('/category/<int:cat_id>/toggle', methods=['POST'])
@admin_required
@csrf.exempt
def toggle_category(cat_id):
    """Enable/disable a category."""
    cat = db.session.get(Category, cat_id)
    if cat:
        cat.is_active = not cat.is_active
        db.session.commit()
        return jsonify({'success': True, 'is_active': cat.is_active})
    return jsonify({'error': 'Category not found'}), 404


@admin_bp.route('/category/<int:cat_id>/delete', methods=['POST'])
@admin_required
@csrf.exempt
def delete_category(cat_id):
    """Delete a category."""
    cat = db.session.get(Category, cat_id)
    if cat:
        ActivityLog.log('Category deleted', user_id=current_user.id, entity_type='category', details=cat.name)
        db.session.delete(cat)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'Category not found'}), 404


# ─── FOOD ITEMS ──────────────────────────────────────────────
@admin_bp.route('/menu-items')
@admin_required
def menu_items():
    """Food item management page."""
    items = MenuItem.query.order_by(MenuItem.category_id, MenuItem.name).all()
    categories_list = Category.query.order_by(Category.display_order).all()
    return render_template('admin/menu_items.html', items=items, categories=categories_list)


@admin_bp.route('/menu-item/add', methods=['POST'])
@admin_required
def add_menu_item():
    """Add a new menu item."""
    name = request.form.get('name', '').strip()
    if not name:
        flash('Item name is required.', 'danger')
        return redirect(url_for('admin.menu_items'))
    
    image_path = None
    if 'image' in request.files and request.files['image'].filename:
        try:
            image_path = save_upload(request.files['image'], folder='menu_items')
        except ValueError as e:
            flash(str(e), 'danger')
            return redirect(url_for('admin.menu_items'))
    
    item = MenuItem(
        name=name,
        description=request.form.get('description', '').strip(),
        price=float(request.form.get('price', 0)),
        discount_price=float(request.form.get('discount_price', 0)) or None,
        category_id=int(request.form.get('category_id', 1)),
        image=image_path,
        is_veg=request.form.get('is_veg') == 'on',
        is_featured=request.form.get('is_featured') == 'on',
        is_popular=request.form.get('is_popular') == 'on',
        is_spicy=request.form.get('is_spicy') == 'on',
        preparation_time=int(request.form.get('preparation_time', 15)),
    )
    db.session.add(item)
    ActivityLog.log('Menu item added', user_id=current_user.id, entity_type='menu_item', details=name)
    db.session.commit()
    
    flash(f'"{name}" added to menu.', 'success')
    return redirect(url_for('admin.menu_items'))


@admin_bp.route('/menu-item/<int:item_id>/edit', methods=['POST'])
@admin_required
def edit_menu_item(item_id):
    """Edit a menu item."""
    item = db.session.get(MenuItem, item_id)
    if not item:
        flash('Item not found.', 'danger')
        return redirect(url_for('admin.menu_items'))
    
    item.name = request.form.get('name', item.name).strip()
    item.description = request.form.get('description', item.description).strip()
    item.price = float(request.form.get('price', item.price))
    item.discount_price = float(request.form.get('discount_price', 0)) or None
    item.category_id = int(request.form.get('category_id', item.category_id))
    item.is_veg = request.form.get('is_veg') == 'on'
    item.is_featured = request.form.get('is_featured') == 'on'
    item.is_popular = request.form.get('is_popular') == 'on'
    item.is_spicy = request.form.get('is_spicy') == 'on'
    item.preparation_time = int(request.form.get('preparation_time', item.preparation_time))
    
    if 'image' in request.files and request.files['image'].filename:
        try:
            item.image = save_upload(request.files['image'], folder='menu_items')
        except ValueError as e:
            flash(str(e), 'danger')
            return redirect(url_for('admin.menu_items'))
    
    ActivityLog.log('Menu item updated', user_id=current_user.id, entity_type='menu_item', entity_id=item_id)
    db.session.commit()
    flash(f'"{item.name}" updated.', 'success')
    return redirect(url_for('admin.menu_items'))


@admin_bp.route('/menu-item/<int:item_id>/toggle', methods=['POST'])
@admin_required
@csrf.exempt
def toggle_menu_item(item_id):
    """Enable/disable a menu item."""
    item = db.session.get(MenuItem, item_id)
    if item:
        item.is_available = not item.is_available
        db.session.commit()
        return jsonify({'success': True, 'is_available': item.is_available})
    return jsonify({'error': 'Item not found'}), 404


@admin_bp.route('/menu-item/<int:item_id>/delete', methods=['POST'])
@admin_required
@csrf.exempt
def delete_menu_item(item_id):
    """Delete a menu item."""
    item = db.session.get(MenuItem, item_id)
    if item:
        ActivityLog.log('Menu item deleted', user_id=current_user.id, entity_type='menu_item', details=item.name)
        db.session.delete(item)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'Item not found'}), 404


# ─── RESTAURANT SETTINGS ────────────────────────────────────
@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    """Restaurant settings page."""
    restaurant = Restaurant.query.first()
    if not restaurant:
        restaurant = Restaurant(name='My Restaurant')
        db.session.add(restaurant)
        db.session.commit()
    
    if request.method == 'POST':
        restaurant.name = request.form.get('name', restaurant.name).strip()
        restaurant.description = request.form.get('description', '').strip()
        restaurant.phone = request.form.get('phone', '').strip()
        restaurant.email = request.form.get('email', '').strip()
        restaurant.address = request.form.get('address', '').strip()
        restaurant.gst_number = request.form.get('gst_number', '').strip()
        restaurant.cuisine_type = request.form.get('cuisine_type', '').strip()
        restaurant.opening_time = request.form.get('opening_time', '09:00')
        restaurant.closing_time = request.form.get('closing_time', '23:00')
        restaurant.is_open = request.form.get('is_open') == 'on'
        restaurant.tax_percent = float(request.form.get('tax_percent', 10.0))
        restaurant.service_charge_percent = float(request.form.get('service_charge_percent', 5.0))
        
        if 'logo' in request.files and request.files['logo'].filename:
            try:
                restaurant.logo = save_upload(request.files['logo'], folder='branding')
            except ValueError as e:
                flash(str(e), 'danger')
                return redirect(url_for('admin.settings'))
        
        if 'cover_image' in request.files and request.files['cover_image'].filename:
            try:
                restaurant.cover_image = save_upload(request.files['cover_image'], folder='branding')
            except ValueError as e:
                flash(str(e), 'danger')
                return redirect(url_for('admin.settings'))
        
        ActivityLog.log('Restaurant settings updated', user_id=current_user.id, entity_type='restaurant')
        db.session.commit()
        flash('Settings updated successfully.', 'success')
        return redirect(url_for('admin.settings'))
    
    # Generate QR code pointing to live production URL (Render) with embedded logo
    app_base_url = os.environ.get('APP_BASE_URL') or current_app.config.get('APP_BASE_URL') or 'https://hotel-order-management-zdnb.onrender.com/'
    if 'the-royal-feast' in app_base_url:
        app_base_url = 'https://hotel-order-management-zdnb.onrender.com/'
    qr_url = request.args.get('qr_url') or app_base_url
    logo_path = os.path.join(current_app.root_path, 'static', 'img', 'restaurant-logo.png')
    qr_img_url = 'https://res.cloudinary.com/dqh2jlqza/image/upload/v1791167187/royal_feast/branding/live_restaurant_qr.png'
    try:
        qr_base64 = QRService.generate_qr_base64(qr_url, logo_path=logo_path)
    except Exception as e:
        current_app.logger.warning(f'QR generation failed: {e}')
        qr_base64 = None
    
    return render_template('admin/settings.html', restaurant=restaurant, qr_base64=qr_base64, qr_url=qr_url, qr_img_url=qr_img_url)


@admin_bp.route('/qr/download')
@admin_required
def download_qr():
    """Download the high-resolution QR code PNG image for printing table/standee boards."""
    from flask import send_file
    app_base_url = os.environ.get('APP_BASE_URL') or current_app.config.get('APP_BASE_URL') or 'https://hotel-order-management-zdnb.onrender.com/'
    if 'the-royal-feast' in app_base_url:
        app_base_url = 'https://hotel-order-management-zdnb.onrender.com/'
    qr_url = request.args.get('qr_url') or app_base_url
    logo_path = os.path.join(current_app.root_path, 'static', 'img', 'restaurant-logo.png')
    buffer = QRService.generate_qr(qr_url, size=15, logo_path=logo_path)
    return send_file(
        buffer,
        mimetype='image/png',
        as_attachment=True,
        download_name='restaurant_ordering_qr.png'
    )


# ─── CUSTOMERS ───────────────────────────────────────────────
@admin_bp.route('/customers')
@admin_required
def customers():
    """Customer sessions list."""
    sessions = CustomerSession.query.order_by(CustomerSession.created_at.desc()).all()
    return render_template('admin/customers.html', sessions=sessions)


# ─── ANALYTICS ───────────────────────────────────────────────
@admin_bp.route('/analytics')
@admin_required
def analytics():
    """Analytics dashboard."""
    order_stats = OrderService.get_order_stats()
    token_stats = TokenService.get_token_stats()
    payment_stats = PaymentService.get_payment_stats()
    
    # Popular items
    from sqlalchemy import func
    from app.models.order_item import OrderItem
    popular = db.session.query(
        OrderItem.item_name,
        func.sum(OrderItem.quantity).label('total_qty'),
        func.sum(OrderItem.line_total).label('total_revenue')
    ).group_by(OrderItem.item_name).order_by(func.sum(OrderItem.quantity).desc()).limit(10).all()
    
    return render_template('admin/analytics.html',
                         order_stats=order_stats,
                         token_stats=token_stats,
                         payment_stats=payment_stats,
                         popular_items=popular)


# ─── ACTIVITY LOGS ───────────────────────────────────────────
@admin_bp.route('/activity-logs')
@admin_required
def activity_logs():
    """Activity logs page."""
    logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(200).all()
    return render_template('admin/activity_logs.html', logs=logs)


# ─── USERS ───────────────────────────────────────────────────
@admin_bp.route('/users')
@admin_required
def users():
    """User management page."""
    all_users = User.query.all()
    roles = Role.query.all()
    return render_template('admin/users.html', users=all_users, roles=roles)


@admin_bp.route('/user/add', methods=['POST'])
@admin_required
def add_user():
    """Add a new staff user."""
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    full_name = request.form.get('full_name', '').strip()
    role_id = request.form.get('role_id', type=int)
    
    if not all([username, email, password, full_name, role_id]):
        flash('All fields are required.', 'danger')
        return redirect(url_for('admin.users'))
    
    if User.query.filter_by(username=username).first():
        flash('Username already exists.', 'danger')
        return redirect(url_for('admin.users'))
    
    user = User(username=username, email=email, full_name=full_name, role_id=role_id)
    user.set_password(password)
    db.session.add(user)
    ActivityLog.log('User created', user_id=current_user.id, entity_type='user', details=username)
    db.session.commit()
    
    flash(f'User "{username}" created.', 'success')
    return redirect(url_for('admin.users'))


# ─── NOTIFICATIONS ───────────────────────────────────────────
@admin_bp.route('/notifications')
@admin_required
def admin_notifications():
    """Admin notifications page."""
    return render_template('admin/notifications.html')


# ─── API ENDPOINTS FOR ADMIN ────────────────────────────────
@admin_bp.route('/api/dashboard-stats')
@admin_required
def api_dashboard_stats():
    """Get live dashboard statistics."""
    order_stats = OrderService.get_order_stats()
    token_stats = TokenService.get_token_stats()
    payment_stats = PaymentService.get_payment_stats()
    
    return jsonify({
        'orders': order_stats,
        'tokens': token_stats,
        'payments': payment_stats,
    })
