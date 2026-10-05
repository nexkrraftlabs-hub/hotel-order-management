import sys
import os
import re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app

app = create_app('development')
client = app.test_client()

# 1. Admin Login
login_get = client.get('/auth/login').get_data(as_text=True)
match = re.search(r'name="csrf_token" value="([^"]+)"', login_get)
csrf_val = match.group(1) if match else ''

admin_login = client.post('/auth/login', data={'username': 'admin', 'password': 'admin123', 'csrf_token': csrf_val}, follow_redirects=True)
print('Admin Login status:', admin_login.status_code)

admin_routes = [
    '/admin/', '/admin/orders', '/admin/orders/live', '/admin/tokens', 
    '/admin/payments', '/admin/bills', '/admin/categories', '/admin/menu-items', 
    '/admin/settings', '/admin/qr/download', '/admin/customers', '/admin/analytics', 
    '/admin/activity-logs', '/admin/users', '/admin/notifications'
]
for r in admin_routes:
    resp = client.get(r)
    print(f'Admin {r:24} -> {resp.status_code}')

# 2. Kitchen Login
client.get('/auth/logout')
login_get = client.get('/auth/login').get_data(as_text=True)
csrf_val = re.search(r'name="csrf_token" value="([^"]+)"', login_get).group(1)
k_login = client.post('/auth/login', data={'username': 'kitchen', 'password': 'kitchen123', 'csrf_token': csrf_val}, follow_redirects=True)
print('Kitchen Login status:', k_login.status_code)
print('Kitchen Dashboard status:', client.get('/kitchen/').status_code)

# 3. Waiter Login
client.get('/auth/logout')
login_get = client.get('/auth/login').get_data(as_text=True)
csrf_val = re.search(r'name="csrf_token" value="([^"]+)"', login_get).group(1)
w_login = client.post('/auth/login', data={'username': 'waiter', 'password': 'waiter123', 'csrf_token': csrf_val}, follow_redirects=True)
print('Waiter Login status:', w_login.status_code)
print('Waiter Dashboard status:', client.get('/waiter/').status_code)
