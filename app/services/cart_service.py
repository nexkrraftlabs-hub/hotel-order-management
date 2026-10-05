"""Cart service for managing shopping cart operations."""
from app.extensions import db
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.menu_item import MenuItem


class CartService:
    """Service for cart CRUD operations."""
    
    @staticmethod
    def get_cart(session):
        """Get cart for a session, creating one if needed."""
        if not session.cart:
            cart = Cart(session=session)
            db.session.add(cart)
            db.session.commit()
        return session.cart
    
    @staticmethod
    def add_item(cart, menu_item_id, quantity=1, special_instructions=None):
        """Add item to cart or update quantity if already exists."""
        menu_item = db.session.get(MenuItem, menu_item_id)
        if not menu_item or not menu_item.is_available:
            raise ValueError('Item is not available')
        
        # Check if item already in cart
        existing = CartItem.query.filter_by(
            cart_id=cart.id,
            menu_item_id=menu_item_id
        ).first()
        
        if existing:
            existing.quantity += quantity
            if special_instructions:
                existing.special_instructions = special_instructions
        else:
            item = CartItem(
                cart_id=cart.id,
                menu_item_id=menu_item_id,
                quantity=quantity,
                special_instructions=special_instructions,
            )
            db.session.add(item)
        
        db.session.commit()
        return cart
    
    @staticmethod
    def update_item_quantity(cart, item_id, quantity):
        """Update quantity of a cart item."""
        item = CartItem.query.filter_by(id=item_id, cart_id=cart.id).first()
        if not item:
            raise ValueError('Item not found in cart')
        
        if quantity <= 0:
            db.session.delete(item)
        else:
            item.quantity = quantity
        
        db.session.commit()
        return cart
    
    @staticmethod
    def remove_item(cart, item_id):
        """Remove an item from cart."""
        item = CartItem.query.filter_by(id=item_id, cart_id=cart.id).first()
        if item:
            db.session.delete(item)
            db.session.commit()
        return cart
    
    @staticmethod
    def clear_cart(cart):
        """Clear all items from cart."""
        CartItem.query.filter_by(cart_id=cart.id).delete()
        cart.special_instructions = None
        db.session.commit()
        return cart
    
    @staticmethod
    def update_instructions(cart, instructions):
        """Update special instructions for the cart."""
        cart.special_instructions = instructions
        db.session.commit()
        return cart
    
    @staticmethod
    def get_cart_summary(cart):
        """Get formatted cart summary."""
        return {
            'items': [item.to_dict() for item in cart.items],
            'total_items': cart.total_items,
            'subtotal': cart.subtotal,
            'is_empty': cart.is_empty,
            'special_instructions': cart.special_instructions,
        }
