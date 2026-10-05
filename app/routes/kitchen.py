"""Kitchen dashboard routes."""
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
from app.extensions import db, csrf
from app.models.order import Order
from app.models.activity_log import ActivityLog
from app.services.order_service import OrderService

kitchen_bp = Blueprint('kitchen', __name__)


def kitchen_required(f):
    """Decorator to require kitchen or admin role."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not (current_user.is_kitchen or current_user.is_admin):
            flash('Access denied. Kitchen privileges required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@kitchen_bp.route('/')
@kitchen_required
def dashboard():
    """Kitchen dashboard showing orders by status."""
    new_orders = Order.query.filter_by(status=Order.SENT_TO_KITCHEN).order_by(Order.created_at.asc()).all()
    accepted = Order.query.filter_by(status=Order.KITCHEN_ACCEPTED).order_by(Order.created_at.asc()).all()
    preparing = Order.query.filter_by(status=Order.PREPARING).order_by(Order.created_at.asc()).all()
    ready = Order.query.filter_by(status=Order.READY).order_by(Order.created_at.asc()).all()
    
    return render_template('kitchen/dashboard.html',
                         new_orders=new_orders,
                         accepted=accepted,
                         preparing=preparing,
                         ready=ready)


@kitchen_bp.route('/accept/<int:order_id>', methods=['POST'])
@kitchen_required
@csrf.exempt
def accept_order(order_id):
    """Accept a kitchen order."""
    try:
        OrderService.kitchen_accept(order_id, current_user.id)
        ActivityLog.log('Kitchen accepted order', user_id=current_user.id, 
                       entity_type='order', entity_id=order_id)
        db.session.commit()
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@kitchen_bp.route('/prepare/<int:order_id>', methods=['POST'])
@kitchen_required
@csrf.exempt
def start_preparing(order_id):
    """Start preparing an order."""
    try:
        OrderService.start_preparing(order_id)
        ActivityLog.log('Kitchen started preparing', user_id=current_user.id,
                       entity_type='order', entity_id=order_id)
        db.session.commit()
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@kitchen_bp.route('/ready/<int:order_id>', methods=['POST'])
@kitchen_required
@csrf.exempt
def mark_ready(order_id):
    """Mark order as ready."""
    try:
        OrderService.mark_ready(order_id)
        ActivityLog.log('Kitchen marked order ready', user_id=current_user.id,
                       entity_type='order', entity_id=order_id)
        db.session.commit()
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@kitchen_bp.route('/transfer/<int:order_id>', methods=['POST'])
@kitchen_required
@csrf.exempt
def transfer_to_waiter(order_id):
    """Transfer order to waiter."""
    try:
        OrderService.transfer_to_waiter(order_id)
        ActivityLog.log('Order transferred to waiter', user_id=current_user.id,
                       entity_type='order', entity_id=order_id)
        db.session.commit()
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@kitchen_bp.route('/api/orders')
@kitchen_required
def api_kitchen_orders():
    """Get kitchen orders as JSON for live updates."""
    new_orders = Order.query.filter_by(status=Order.SENT_TO_KITCHEN).order_by(Order.created_at.asc()).all()
    accepted = Order.query.filter_by(status=Order.KITCHEN_ACCEPTED).order_by(Order.created_at.asc()).all()
    preparing = Order.query.filter_by(status=Order.PREPARING).order_by(Order.created_at.asc()).all()
    ready = Order.query.filter_by(status=Order.READY).order_by(Order.created_at.asc()).all()
    
    def order_to_dict(o):
        return {
            'id': o.id,
            'order_id': o.order_id,
            'status': o.status,
            'token': o.session.token.token_number if o.session and o.session.token else None,
            'items': [{'name': i.item_name, 'qty': i.quantity, 'is_veg': i.is_veg} for i in o.items],
            'special_instructions': o.special_instructions,
            'created_at': o.created_at.isoformat() if o.created_at else None,
        }
    
    return jsonify({
        'new_orders': [order_to_dict(o) for o in new_orders],
        'accepted': [order_to_dict(o) for o in accepted],
        'preparing': [order_to_dict(o) for o in preparing],
        'ready': [order_to_dict(o) for o in ready],
    })
