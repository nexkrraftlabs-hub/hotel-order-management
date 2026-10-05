"""Comprehensive automated tests for Hotel/Restaurant Management System."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.role import Role
from app.models.token import Token
from app.models.category import Category
from app.models.menu_item import MenuItem
from app.models.order import Order
from app.models.customer_session import CustomerSession
from app.services.session_service import SessionService
from app.services.token_service import TokenService
from app.services.cart_service import CartService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.billing_service import BillingService
from app.services.qr_service import QRService


def setup_test_app():
    app = create_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False
    return app


def test_system_end_to_end():
    app = setup_test_app()
    with app.app_context():
        db.create_all()

        # 1. Create Roles
        roles = {}
        for r_name in ['admin', 'kitchen', 'waiter', 'customer']:
            role = Role(name=r_name, description=r_name)
            db.session.add(role)
            db.session.flush()
            roles[r_name] = role

        # 2. Create Users
        admin = User(username='admin', email='admin@test.com', full_name='Admin User', role_id=roles['admin'].id)
        admin.set_password('pass123')
        kitchen = User(username='kitchen', email='kitchen@test.com', full_name='Kitchen User', role_id=roles['kitchen'].id)
        kitchen.set_password('pass123')
        waiter = User(username='waiter', email='waiter@test.com', full_name='Waiter User', role_id=roles['waiter'].id)
        waiter.set_password('pass123')
        db.session.add_all([admin, kitchen, waiter])

        # 3. Create Tokens (5 tokens for test)
        for i in range(1, 6):
            tok = Token(token_number=i, is_enabled=True, status='available')
            db.session.add(tok)

        # 4. Create Category & Menu Items
        cat = Category(name='Starters', description='Appetizers', display_order=1)
        db.session.add(cat)
        db.session.flush()

        item1 = MenuItem(name='Tandoori Tikka', description='Smoky tikka', price=300, discount_price=270, category_id=cat.id, is_veg=False)
        item2 = MenuItem(name='Paneer Tikka', description='Spiced paneer', price=250, discount_price=None, category_id=cat.id, is_veg=True)
        db.session.add_all([item1, item2])
        db.session.commit()

        # 5. Customer Session Creation
        client = app.test_client()
        browser_id = 'test_guest_session_99'
        session = SessionService.get_or_create_session(browser_id)
        assert session is not None
        assert session.token_id is None  # Token not assigned until first order

        # 6. Cart Service - Add items
        cart = CartService.get_cart(session)
        CartService.add_item(cart, item1.id, 2, 'Spicy')
        CartService.add_item(cart, item2.id, 1, 'Mild')
        db.session.refresh(cart)
        assert cart.total_items == 3
        # item1: 270*2 = 540, item2: 250*1 = 250. Subtotal = 790
        assert cart.subtotal == 790.0

        # 7. Order Placement -> Allocates Token #1
        order1 = OrderService.place_order(session, 'No plastic cutlery')
        db.session.refresh(session)
        assert session.token_id is not None
        assigned_token_num = session.token.token_number
        assert assigned_token_num == 1
        assert session.token.status == 'active'
        assert order1.status == Order.PENDING

        # 8. Second Order in same session -> Reuses Token #1
        CartService.add_item(cart, item2.id, 2)
        order2 = OrderService.place_order(session)
        db.session.refresh(session)
        assert session.token.token_number == 1  # Reused!
        assert session.orders.count() == 2

        # 9. State Machine Transitions for Order 1
        OrderService.confirm_order(order1.id)
        assert order1.status == Order.CONFIRMED

        OrderService.send_to_kitchen(order1.id)
        assert order1.status == Order.SENT_TO_KITCHEN

        OrderService.kitchen_accept(order1.id, kitchen.id)
        assert order1.status == Order.KITCHEN_ACCEPTED

        OrderService.start_preparing(order1.id)
        assert order1.status == Order.PREPARING

        OrderService.mark_ready(order1.id)
        assert order1.status == Order.READY

        OrderService.transfer_to_waiter(order1.id)
        assert order1.status == Order.TRANSFERRED_TO_WAITER

        OrderService.waiter_accept(order1.id, waiter.id)
        assert order1.status == Order.SERVING

        OrderService.mark_served(order1.id)
        assert order1.status == Order.SERVED

        # 10. Test Invalid State Machine Transition
        try:
            order1.transition_to(Order.PREPARING)
            assert False, "Should have raised ValueError on illegal transition"
        except ValueError:
            pass

        # 11. Payment Approval & Settlement
        OrderService.confirm_order(order2.id)
        OrderService.send_to_kitchen(order2.id)
        OrderService.kitchen_accept(order2.id, kitchen.id)
        OrderService.start_preparing(order2.id)
        OrderService.mark_ready(order2.id)
        OrderService.transfer_to_waiter(order2.id)
        OrderService.waiter_accept(order2.id, waiter.id)
        OrderService.mark_served(order2.id)

        payment = PaymentService.approve_payment(session.id, admin.id, payment_method='upi')
        db.session.refresh(session)
        assert payment.status == 'paid'
        assert session.status == CustomerSession.COMPLETED
        assert session.bill is not None

        # 12. Token is released back to available!
        released_token = db.session.get(Token, assigned_token_num)
        assert released_token.status == Token.AVAILABLE

        # 13. PDF Generation Test
        pdf = BillingService.generate_pdf(session.bill)
        assert pdf is not None
        assert len(pdf.getvalue()) > 1000

        # 14. QR Code Generation Test
        qr_b64 = QRService.generate_qr_base64("http://localhost:5000")
        assert qr_b64 is not None
        assert len(qr_b64) > 100

        print("=== ALL FULL SYSTEM TESTS PASSED SUCCESSFULLY! ===")


if __name__ == '__main__':
    test_system_end_to_end()
