"""Authentication routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.activity_log import ActivityLog
from datetime import datetime, timezone

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Staff login page."""
    if current_user.is_authenticated:
        return redirect_by_role(current_user)
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated.', 'danger')
                return render_template('auth/login.html')
            
            login_user(user, remember=True)
            user.last_login = datetime.now(timezone.utc)
            
            ActivityLog.log(
                action='User logged in',
                user_id=user.id,
                entity_type='user',
                entity_id=user.id,
                ip_address=request.remote_addr,
            )
            db.session.commit()
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect_by_role(user)
        
        flash('Invalid username or password.', 'danger')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout current user."""
    ActivityLog.log(
        action='User logged out',
        user_id=current_user.id,
        entity_type='user',
        entity_id=current_user.id,
        ip_address=request.remote_addr,
    )
    db.session.commit()
    
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


def redirect_by_role(user):
    """Redirect user to appropriate dashboard based on role."""
    if user.is_admin or user.is_super_admin:
        return redirect(url_for('admin.dashboard'))
    elif user.is_kitchen:
        return redirect(url_for('kitchen.dashboard'))
    elif user.is_waiter:
        return redirect(url_for('waiter.dashboard'))
    return redirect(url_for('customer.home'))
