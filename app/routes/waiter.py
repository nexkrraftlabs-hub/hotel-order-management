"""Waiter dashboard routes."""
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
from app.extensions import db, csrf
from app.models.order import Order
from app.models.activity_log import ActivityLog
from app.services.order_service import OrderService

waiter_bp = Blueprint('waiter', __name__)


def waiter_required(f):
    """Decorator to require waiter or admin role."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not (current_user.is_waiter or current_user.is_admin):
            flash('Access denied. Waiter privileges required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@waiter_bp.route('/')
@waiter_required
def dashboard():
    """Waiter dashboard showing orders ready to serve and active deliveries."""
    ready_for_pickup = Order.query.filter_by(
        status=Order.TRANSFERRED_TO_WAITER
    ).order_by(Order.ready_at.asc()).all()
    
    serving_orders = Order.query.filter_by(
        status=Order.SERVING
    ).order_by(Order.updated_at.asc()).all()
    
    recently_served = Order.query.filter_by(
        status=Order.SERVED
    ).order_by(Order.served_at.desc()).limit(20).all()
    
    return render_template('waiter/dashboard.html',
                         ready_for_pickup=ready_for_pickup,
                         serving_orders=serving_orders,
                         recently_served=recently_served)


@waiter_bp.route('/accept/<int:order_id>', methods=['POST'])
@waiter_required
@csrf.exempt
def accept_order(order_id):
    """Waiter accepts order for delivery to customer."""
    try:
        OrderService.waiter_accept(order_id, current_user.id)
        ActivityLog.log('Waiter accepted order for serving', user_id=current_user.id,
                       entity_type='order', entity_id=order_id)
        db.session.commit()
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@waiter_bp.route('/served/<int:order_id>', methods=['POST'])
@waiter_required
@csrf.exempt
def mark_served(order_id):
    """Waiter marks order as served to customer."""
    try:
        OrderService.mark_served(order_id)
        ActivityLog.log('Order marked as served', user_id=current_user.id,
                       entity_type='order', entity_id=order_id)
        db.session.commit()
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@waiter_bp.route('/api/orders')
@waiter_required
def api_waiter_orders():
    """Get waiter orders JSON for live polling/updates."""
    ready_for_pickup = Order.query.filter_by(
        status=Order.TRANSFERRED_TO_WAITER
    ).order_by(Order.ready_at.asc()).all()
    
    serving = Order.query.filter_by(
        status=Order.SERVING
    ).order_by(Order.updated_at.asc()).all()
    
    served = Order.query.filter_by(
        status=Order.SERVED
    ).order_by(Order.served_at.desc()).limit(15).all()
    
    def order_to_dict(o):
        return {
            'id': o.id,
            'order_id': o.order_id,
            'status': o.status,
            'token': o.session.token.token_number if o.session and o.session.token else None,
            'customer_name': o.session.customer_name if o.session else None,
            'items': [{'name': i.item_name, 'qty': i.quantity, 'is_veg': i.is_veg} for i in o.items],
            'special_instructions': o.special_instructions,
            'created_at': o.created_at.isoformat() if o.created_at else None,
            'ready_at': o.ready_at.isoformat() if o.ready_at else None,
            'waiter_name': o.waiter_assignment.waiter.full_name if o.waiter_assignment and o.waiter_assignment.waiter else None
        }
    
    return jsonify({
        'ready_for_pickup': [order_to_dict(o) for o in ready_for_pickup],
        'serving': [order_to_dict(o) for o in serving],
        'recently_served': [order_to_dict(o) for o in served],
    })
