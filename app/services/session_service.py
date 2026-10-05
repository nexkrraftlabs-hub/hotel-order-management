"""Session service for customer session management and cart recovery."""
import uuid
from app.extensions import db
from app.models.customer_session import CustomerSession
from app.models.cart import Cart
from app.models.token import Token


class SessionService:
    """Service for managing customer sessions with cart recovery."""
    
    @staticmethod
    def get_or_create_session(browser_session_id):
        """Get existing active session or create a new one for the browser.
        
        This is the primary cart recovery mechanism. If a customer closes
        the browser and rescans QR, their browser_session_id (stored in
        localStorage + cookie) will reconnect them to their active session.
        """
        if browser_session_id:
            session = CustomerSession.query.filter_by(
                browser_session_id=browser_session_id,
            ).filter(
                CustomerSession.status.in_(['active', 'payment_pending'])
            ).first()
            
            if session:
                return session
        
        # Create new session
        new_session = CustomerSession(
            browser_session_id=browser_session_id or str(uuid.uuid4()),
            status=CustomerSession.ACTIVE,
        )
        db.session.add(new_session)
        
        # Create empty cart for the session
        cart = Cart(session=new_session)
        db.session.add(cart)
        
        db.session.commit()
        return new_session
    
    @staticmethod
    def get_session_by_id(session_id):
        """Get session by session_id string."""
        return CustomerSession.query.filter_by(session_id=session_id).first()
    
    @staticmethod
    def get_session_by_browser_id(browser_session_id):
        """Get active session by browser session ID."""
        if not browser_session_id:
            return None
        return CustomerSession.query.filter_by(
            browser_session_id=browser_session_id,
        ).filter(
            CustomerSession.status.in_(['active', 'payment_pending'])
        ).first()
    
    @staticmethod
    def get_active_session_for_token(token_id):
        """Get the active session for a given token."""
        return CustomerSession.query.filter_by(
            token_id=token_id,
        ).filter(
            CustomerSession.status.in_(['active', 'payment_pending'])
        ).first()
    
    @staticmethod
    def update_customer_info(session, name=None, phone=None, email=None):
        """Update customer information on a session."""
        if name:
            session.customer_name = name
        if phone:
            session.customer_phone = phone
        if email:
            session.customer_email = email
        db.session.commit()
    
    @staticmethod
    def complete_session(session):
        """Mark session as completed and release token."""
        from app.services.token_service import TokenService
        from datetime import datetime, timezone
        
        session.status = CustomerSession.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        
        if session.token_id:
            TokenService.release_token(session.token_id)
        
        db.session.commit()
    
    @staticmethod
    def get_session_history(browser_session_id):
        """Get all sessions (including completed) for a browser."""
        return CustomerSession.query.filter_by(
            browser_session_id=browser_session_id
        ).order_by(CustomerSession.created_at.desc()).all()
