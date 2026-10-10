"""Flask application factory."""
import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()


def create_app(config_name=None):
    """Create and configure the Flask application."""
    app = Flask(__name__,
                static_folder='static',
                template_folder='templates')
    
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    from config import config_by_name
    app.config.from_object(config_by_name.get(config_name, config_by_name['development']))
    
    # Ensure directories exist
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'app/static/uploads'), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, '..', 'instance'), exist_ok=True)
    
    # Initialize extensions
    from app.extensions import db, migrate, login_manager, socketio, csrf
    
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')
    csrf.init_app(app)
    
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return db.session.get(User, int(user_id))
    
    # Import models for migration detection
    from app.models import (user, role, restaurant, token, customer_session,
                            category, menu_item, addon, cart, cart_item,
                            order, order_item, payment, bill, notification,
                            kitchen_assignment, waiter_assignment, activity_log)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.customer import customer_bp
    from app.routes.admin import admin_bp
    from app.routes.kitchen import kitchen_bp
    from app.routes.waiter import waiter_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(kitchen_bp, url_prefix='/kitchen')
    app.register_blueprint(waiter_bp, url_prefix='/waiter')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register template context processors
    register_context_processors(app)
    
    # Register SocketIO events
    from app.sockets import register_socket_events
    register_socket_events(socketio)
    
    # Ensure database schema is up-to-date
    ensure_schema_updates(app)
    
    return app


def ensure_schema_updates(app):
    """Ensure database schema includes new columns across SQLite/PostgreSQL."""
    with app.app_context():
        try:
            from sqlalchemy import inspect, text
            from app.extensions import db
            insp = inspect(db.engine)
            if 'order_items' in insp.get_table_names():
                cols = [c['name'] for c in insp.get_columns('order_items')]
                with db.engine.connect() as conn:
                    if 'status' not in cols:
                        conn.execute(text("ALTER TABLE order_items ADD COLUMN status VARCHAR(30) DEFAULT 'pending'"))
                    if 'ready_at' not in cols:
                        conn.execute(text("ALTER TABLE order_items ADD COLUMN ready_at DATETIME"))
                    if 'collected_at' not in cols:
                        conn.execute(text("ALTER TABLE order_items ADD COLUMN collected_at DATETIME"))
                    conn.commit()
        except Exception as e:
            pass


def register_error_handlers(app):
    """Register custom error handlers."""
    from flask import render_template, jsonify, request
    
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Not found', 'status': 404}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(403)
    def forbidden(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Forbidden', 'status': 403}), 403
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(500)
    def server_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error', 'status': 500}), 500
        return render_template('errors/500.html'), 500


def register_context_processors(app):
    """Register Jinja2 context processors."""
    @app.context_processor
    def inject_globals():
        from app.models.restaurant import Restaurant
        from app.extensions import db
        restaurant = db.session.query(Restaurant).first()
        return {
            'restaurant': restaurant,
            'currency': app.config.get('CURRENCY_SYMBOL', '₹'),
        }
