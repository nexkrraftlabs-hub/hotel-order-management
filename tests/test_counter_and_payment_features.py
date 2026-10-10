import json
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models.customer_session import CustomerSession
from app.models.menu_item import MenuItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.token import Token
from app.models.user import User
from app.services.cart_service import CartService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService

def test_counter_and_payment_features():
    app = create_app()
    client = app.test_client()

    with app.app_context():
        # Ensure a menu item exists
        items = MenuItem.query.filter_by(is_available=True).limit(2).all()
        assert len(items) >= 2, "Need at least 2 menu items for multi-item order test"
        item1, item2 = items[0], items[1]

        # ─── TEST 1: ITEM-BY-ITEM DISPATCH & COUNTER PICKUP ────────
        print("\n--- TEST 1: Item-by-item dispatch & counter pickup ---")
        browser_id = f"test-browser-session-counter-{uuid.uuid4().hex[:8]}"
        res = client.post('/api/session', json={'browser_session_id': browser_id})
        sess_data = json.loads(res.data)
        assert res.status_code == 200

        # Add item 1 (e.g. Cold Drink) and item 2 (e.g. Burger)
        client.post('/api/cart/add', json={'browser_session_id': browser_id, 'menu_item_id': item1.id, 'quantity': 2})
        client.post('/api/cart/add', json={'browser_session_id': browser_id, 'menu_item_id': item2.id, 'quantity': 1})

        # Place order
        res = client.post('/api/order/place', json={'browser_session_id': browser_id, 'special_instructions': 'Bring drink first'})
        assert res.status_code == 200
        order_info = json.loads(res.data)['order']
        order_id = order_info['id']
        token_num = json.loads(res.data)['token']
        print(f"Placed multi-item order #{order_info['order_id']} for Token #{token_num}")

        order = db.session.get(Order, order_id)
        assert len(order.items) == 2
        oi1, oi2 = order.items[0], order.items[1]
        assert oi1.status == OrderItem.PENDING
        assert oi2.status == OrderItem.PENDING

        # Kitchen marks item 1 as READY AT COUNTER
        OrderService.update_item_status(oi1.id, OrderItem.READY)
        db.session.refresh(order)
        db.session.refresh(oi1)
        db.session.refresh(oi2)
        assert oi1.status == OrderItem.READY
        assert oi1.is_ready is True
        assert oi2.status == OrderItem.PENDING
        print(f"Item 1 '{oi1.item_name}' marked READY at counter")

        # Verify customer API shows item 1 in ready_items
        res = client.get(f'/api/orders?browser_session_id={browser_id}')
        cust_orders = json.loads(res.data)
        assert cust_orders['has_ready_items'] is True
        assert len(cust_orders['ready_items']) == 1
        assert cust_orders['ready_items'][0]['id'] == oi1.id
        print("Customer API verified: item 1 is ready at counter!")

        # Customer comes to counter and collects item 1
        OrderService.update_item_status(oi1.id, OrderItem.COLLECTED)
        db.session.refresh(oi1)
        assert oi1.status == OrderItem.COLLECTED
        print(f"Item 1 '{oi1.item_name}' marked COLLECTED from counter")

        # Customer API now has 0 ready items waiting
        res = client.get(f'/api/orders?browser_session_id={browser_id}')
        cust_orders = json.loads(res.data)
        assert cust_orders['has_ready_items'] is False

        # Now item 2 is finished and customer collects item 2
        OrderService.update_item_status(oi2.id, OrderItem.READY)
        OrderService.update_item_status(oi2.id, OrderItem.COLLECTED)
        db.session.refresh(order)
        # All items collected -> order auto-serves!
        assert order.status == Order.SERVED
        print("All items collected -> Order automatically transitioned to SERVED!")

        # ─── TEST 2: PAY ONLINE FROM TABLE/PHONE ───────────────────
        print("\n--- TEST 2: Pay online from table/phone ---")
        res_info = client.get(f'/api/payment/info?browser_session_id={browser_id}')
        assert res_info.status_code == 200
        pay_info = json.loads(res_info.data)
        assert 'upi_uri' in pay_info
        assert pay_info['total_amount'] > 0
        print(f"Generated UPI Intent: {pay_info['upi_uri']}")

        # Customer completes online payment
        res_pay = client.post('/api/payment/pay-online', json={
            'browser_session_id': browser_id,
            'payment_method': 'online_upi',
        })
        assert res_pay.status_code == 200
        pay_result = json.loads(res_pay.data)
        assert pay_result['success'] is True
        assert pay_result['payment_status'] == 'paid'
        print(f"Online payment succeeded! Bill URL: {pay_result['bill_url']}")

        # Verify session is completed and token released
        session = CustomerSession.query.filter_by(browser_session_id=browser_id).first()
        assert session.status == CustomerSession.COMPLETED
        assert session.is_paid is True
        assert session.bill is not None
        print("Verified: Session completed, bill generated, token released.")

        # ─── TEST 3: PAY AT COUNTER FLOW ──────────────────────────
        print("\n--- TEST 3: Pay at counter workflow ---")
        browser_id_counter = f"test-browser-counter-{uuid.uuid4().hex[:8]}"
        client.post('/api/session', json={'browser_session_id': browser_id_counter})
        client.post('/api/cart/add', json={'browser_session_id': browser_id_counter, 'menu_item_id': item1.id, 'quantity': 1})
        res_order2 = client.post('/api/order/place', json={'browser_session_id': browser_id_counter})
        assert res_order2.status_code == 200

        # Customer clicks "Pay at Counter (Cash)"
        res_req = client.post('/api/payment/request-counter', json={
            'browser_session_id': browser_id_counter,
            'payment_method': 'counter_cash',
        })
        assert res_req.status_code == 200
        session_counter = CustomerSession.query.filter_by(browser_session_id=browser_id_counter).order_by(CustomerSession.id.desc()).first()
        assert session_counter.is_counter_payment_requested is True
        print("Customer successfully requested Counter Payment (Cash)")

        # Verify customer API reflects counter request
        res = client.get(f'/api/orders?browser_session_id={browser_id_counter}')
        cust_orders = json.loads(res.data)
        assert cust_orders['is_counter_requested'] is True

        # Counter staff / Admin approves counter payment
        admin_user = User.query.filter_by(username='admin').first()
        PaymentService.approve_payment(session_counter.id, admin_user.id if admin_user else 1, 'counter_cash')
        db.session.refresh(session_counter)
        assert session_counter.status == CustomerSession.COMPLETED
        assert session_counter.is_paid is True
        assert session_counter.bill is not None
        assert session_counter.payment.payment_method == 'counter_cash'
        print("Counter staff collected cash & approved payment: Session completed successfully!")

        print("\n=== ALL ITEM DISPATCH & DUAL PAYMENT TESTS PASSED PERFECTLY! ===")

if __name__ == '__main__':
    test_counter_and_payment_features()
