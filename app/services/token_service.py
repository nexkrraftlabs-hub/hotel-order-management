"""Token service for atomic token allocation and management."""
from app.extensions import db
from app.models.token import Token
from sqlalchemy import text
import threading

# Lock for token allocation to prevent race conditions
_token_lock = threading.Lock()


class TokenService:
    """Service for managing token allocation, release, and reuse."""
    
    @staticmethod
    def initialize_tokens(start=1, end=50):
        """Initialize token pool if not already created."""
        existing = Token.query.count()
        if existing > 0:
            return existing
        
        for num in range(start, end + 1):
            token = Token(token_number=num, status=Token.AVAILABLE)
            db.session.add(token)
        
        db.session.commit()
        return end - start + 1
    
    @staticmethod
    def allocate_token():
        """Atomically allocate the next available token.
        
        Uses threading lock for SQLite, would use SELECT FOR UPDATE for PostgreSQL.
        Returns the allocated Token or None if no tokens available.
        """
        with _token_lock:
            token = Token.query.filter_by(
                status=Token.AVAILABLE,
                is_enabled=True
            ).order_by(Token.token_number.asc()).first()
            
            if token is None:
                return None
            
            token.status = Token.ACTIVE
            db.session.commit()
            return token
    
    @staticmethod
    def release_token(token_id):
        """Release a token back to available pool."""
        with _token_lock:
            token = db.session.get(Token, token_id)
            if token:
                token.status = Token.AVAILABLE
                db.session.commit()
                return True
            return False
    
    @staticmethod
    def set_payment_pending(token_id):
        """Mark token as payment pending."""
        token = db.session.get(Token, token_id)
        if token and token.status == Token.ACTIVE:
            token.status = Token.PAYMENT_PENDING
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def get_token_stats():
        """Get token statistics."""
        total = Token.query.filter_by(is_enabled=True).count()
        available = Token.query.filter_by(status=Token.AVAILABLE, is_enabled=True).count()
        active = Token.query.filter_by(status=Token.ACTIVE).count()
        payment_pending = Token.query.filter_by(status=Token.PAYMENT_PENDING).count()
        
        return {
            'total': total,
            'available': available,
            'active': active,
            'payment_pending': payment_pending,
        }
    
    @staticmethod
    def get_all_tokens():
        """Get all tokens with status."""
        return Token.query.order_by(Token.token_number.asc()).all()
    
    @staticmethod
    def configure_tokens(start, end):
        """Reconfigure token range (add new tokens only)."""
        for num in range(start, end + 1):
            existing = Token.query.filter_by(token_number=num).first()
            if not existing:
                token = Token(token_number=num, status=Token.AVAILABLE)
                db.session.add(token)
        db.session.commit()
