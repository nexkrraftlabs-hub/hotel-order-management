/**
 * The Royal Feast - Customer App JS
 * Handles Client Session, Dynamic Cart, Quantity Steppers & Live Order Status
 */

const CustomerApp = {
  browserSessionId: null,
  sessionId: null,
  tokenNumber: null,
  cart: { items: [], total_items: 0, subtotal: 0 },

  init() {
    this.initBrowserSession();
    this.fetchSessionAndCart();
    this.setupListeners();
  },

  initBrowserSession() {
    let id = localStorage.getItem('rf_browser_session_id');
    if (!id) {
      id = 'bs_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
      localStorage.setItem('rf_browser_session_id', id);
    }
    this.browserSessionId = id;
  },

  async fetchSessionAndCart() {
    try {
      const res = await fetch('/api/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ browser_session_id: this.browserSessionId })
      });
      const data = await res.json();
      
      this.sessionId = data.session_id;
      this.tokenNumber = data.token;
      this.cart = data.cart || { items: [], total_items: 0, subtotal: 0 };

      // Update UI components
      this.updateTokenUI();
      this.updateCartUI();
      this.updateItemCardSteppers();

      // Connect Socket
      if (window.App && this.sessionId) {
        const socket = App.initSocket('customer', this.sessionId);
        if (socket) {
          socket.on('order_update', (msg) => this.handleOrderUpdate(msg));
          socket.on('notification', (msg) => this.handleNotification(msg));
          socket.on('payment_success', (msg) => this.handlePaymentSuccess(msg));
        }
      }
    } catch (err) {
      console.error('Failed to init session:', err);
    }
  },

  updateTokenUI() {
    const tokenBadges = document.querySelectorAll('.active-token-num');
    const tokenContainers = document.querySelectorAll('.active-token-container');
    
    if (this.tokenNumber) {
      tokenBadges.forEach(el => el.textContent = '#' + String(this.tokenNumber).padStart(2, '0'));
      tokenContainers.forEach(el => el.style.display = 'flex');
    } else {
      tokenContainers.forEach(el => el.style.display = 'none');
    }
  },

  async addToCart(menuItemId, quantity = 1, specialInstructions = '') {
    try {
      const res = await fetch('/api/cart/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          browser_session_id: this.browserSessionId,
          menu_item_id: parseInt(menuItemId),
          quantity: quantity,
          special_instructions: specialInstructions
        })
      });
      const data = await res.json();
      if (data.success) {
        this.cart = data.cart;
        this.updateCartUI();
        this.updateItemCardSteppers();
        App.showToast('Item added to cart', 'success');
      } else {
        App.showToast(data.error || 'Failed to add item', 'error');
      }
    } catch (err) {
      App.showToast('Network error adding item', 'error');
    }
  },

  async updateItemQty(cartItemId, newQty) {
    try {
      let res;
      if (newQty <= 0) {
        res = await fetch('/api/cart/remove', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            browser_session_id: this.browserSessionId,
            item_id: cartItemId
          })
        });
      } else {
        res = await fetch('/api/cart/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            browser_session_id: this.browserSessionId,
            item_id: cartItemId,
            quantity: newQty
          })
        });
      }
      const data = await res.json();
      if (data.success) {
        this.cart = data.cart;
        this.updateCartUI();
        this.updateItemCardSteppers();
        if (typeof renderCartItems === 'function') {
          renderCartItems();
        }
      }
    } catch (err) {
      App.showToast('Error updating quantity', 'error');
    }
  },

  updateCartUI() {
    const floatingBar = document.getElementById('floating-cart-bar');
    const badgeCounters = document.querySelectorAll('.cart-badge-count');
    const totalAmounts = document.querySelectorAll('.cart-total-amount');

    const totalItems = this.cart.total_items || 0;
    const subtotal = this.cart.subtotal || 0;

    badgeCounters.forEach(el => {
      el.textContent = totalItems;
      el.style.display = totalItems > 0 ? 'flex' : 'none';
    });

    totalAmounts.forEach(el => {
      el.textContent = '\u20B9' + subtotal.toFixed(0);
    });

    if (floatingBar) {
      // Don't show floating bar if already on cart page
      if (window.location.pathname === '/cart') {
        floatingBar.style.display = 'none';
      } else {
        floatingBar.style.display = totalItems > 0 ? 'flex' : 'none';
      }
    }

    // Re-render cart page items when data is freshly loaded
    if (window.location.pathname === '/cart' && typeof renderCartItems === 'function') {
      renderCartItems();
    }
  },

  updateItemCardSteppers() {
    // Map of menu_item_id -> { cart_item_id, qty }
    const cartMap = {};
    if (this.cart && this.cart.items) {
      this.cart.items.forEach(ci => {
        cartMap[ci.menu_item_id] = { id: ci.id, qty: ci.quantity };
      });
    }

    document.querySelectorAll('.add-btn-wrapper').forEach(wrapper => {
      const menuItemId = parseInt(wrapper.getAttribute('data-item-id'));
      if (!menuItemId) return;

      const inCart = cartMap[menuItemId];
      if (inCart) {
        wrapper.innerHTML = `
          <div class="qty-stepper">
            <button class="stepper-btn" onclick="CustomerApp.updateItemQty(${inCart.id}, ${inCart.qty - 1})">−</button>
            <span class="stepper-qty">${inCart.qty}</span>
            <button class="stepper-btn" onclick="CustomerApp.updateItemQty(${inCart.id}, ${inCart.qty + 1})">+</button>
          </div>
        `;
      } else {
        wrapper.innerHTML = `
          <button class="btn-add-food" data-item-id="${menuItemId}" onclick="CustomerApp.addToCart(this.getAttribute('data-item-id'), 1)">ADD</button>
        `;
      }
    });
  },

  async placeOrder(specialInstructions = '') {
    try {
      const res = await fetch('/api/order/place', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          browser_session_id: this.browserSessionId,
          special_instructions: specialInstructions
        })
      });
      const data = await res.json();
      if (data.success) {
        this.tokenNumber = data.token;
        this.cart = { items: [], total_items: 0, subtotal: 0 };
        this.updateTokenUI();
        this.updateCartUI();
        this.updateItemCardSteppers();
        App.showToast(`Order placed! Your Token is #${String(data.token).padStart(2, '0')}`, 'success');
        window.location.href = '/orders';
      } else {
        App.showToast(data.error || 'Failed to place order', 'error');
      }
    } catch (err) {
      App.showToast('Failed to place order', 'error');
    }
  },

  handleOrderUpdate(data) {
    App.showToast(`Order Update: ${data.order_id} is now ${data.status.replace(/_/g, ' ')}`, 'warning');
    if (window.location.pathname === '/orders') {
      this.refreshOrdersView();
    }
  },

  handleNotification(data) {
    App.showToast(`${data.title}: ${data.message}`, 'info');
  },

  handlePaymentSuccess(data) {
    App.showToast('Payment received! Your digital bill is ready.', 'success');
    setTimeout(() => {
      window.location.href = `/bill/${this.sessionId}`;
    }, 1500);
  },

  async refreshOrdersView() {
    if (typeof loadCustomerOrders === 'function') {
      loadCustomerOrders();
    }
  },

  setupListeners() {
    // Dietary filter pills
    document.querySelectorAll('.diet-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        document.querySelectorAll('.diet-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        const filter = pill.getAttribute('data-filter');
        this.filterMenuByDiet(filter);
      });
    });
  },

  filterMenuByDiet(filter) {
    const cards = document.querySelectorAll('.food-card');
    cards.forEach(card => {
      const isVeg = card.getAttribute('data-is-veg') === 'true';
      if (filter === 'all') {
        card.style.display = 'flex';
      } else if (filter === 'veg') {
        card.style.display = isVeg ? 'flex' : 'none';
      } else if (filter === 'nonveg') {
        card.style.display = !isVeg ? 'flex' : 'none';
      }
    });
  }
};

document.addEventListener('DOMContentLoaded', () => {
  CustomerApp.init();
});

window.CustomerApp = CustomerApp;
