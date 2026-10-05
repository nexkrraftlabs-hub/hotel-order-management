/**
 * The Royal Feast - Core App JS
 * Audio Synthesis, SocketIO Client & Toast System
 */

const App = {
  socket: null,

  // Toast Notification System
  showToast(message, type = 'info', duration = 3500) {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = 'bi-info-circle';
    if (type === 'success') icon = 'bi-check-circle-fill';
    if (type === 'warning') icon = 'bi-exclamation-triangle-fill';
    if (type === 'error') icon = 'bi-x-circle-fill';

    toast.innerHTML = `
      <i class="bi ${icon}" style="font-size: 1.2rem;"></i>
      <div style="flex: 1; font-size: 0.88rem; font-weight: 600;">${message}</div>
    `;

    container.appendChild(toast);
    App.playChime(type);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(-15px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  },

  // Web Audio Synthesizer Chime (Zero external audio file dependencies!)
  playChime(type = 'success') {
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return;
      const ctx = new AudioContext();
      
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.connect(gain);
      gain.connect(ctx.destination);

      if (type === 'success') {
        // Cheerful double chime
        osc.frequency.setValueAtTime(587.33, now); // D5
        osc.frequency.setValueAtTime(880, now + 0.1); // A5
        gain.gain.setValueAtTime(0.2, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.4);
        osc.start(now);
        osc.stop(now + 0.4);
      } else if (type === 'warning' || type === 'new_order') {
        // Alert chime
        osc.frequency.setValueAtTime(440, now); // A4
        osc.frequency.setValueAtTime(659.25, now + 0.12); // E5
        osc.frequency.setValueAtTime(880, now + 0.24); // A5
        gain.gain.setValueAtTime(0.3, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.6);
        osc.start(now);
        osc.stop(now + 0.6);
      } else {
        // Subtle click
        osc.frequency.setValueAtTime(523.25, now);
        gain.gain.setValueAtTime(0.15, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.2);
        osc.start(now);
        osc.stop(now + 0.2);
      }
    } catch (e) {
      // Audio autoplay policy handled silently
    }
  },

  // Initialize SocketIO connection
  initSocket(role = 'customer', sessionId = null) {
    if (typeof io === 'undefined') return;

    this.socket = io({
      transports: ['polling', 'websocket']
    });

    this.socket.on('connect', () => {
      console.log('[Socket] Connected as', role);
      if (role === 'customer' && sessionId) {
        this.socket.emit('join_session', { session_id: sessionId });
      } else if (role === 'admin') {
        this.socket.emit('join_admin');
      } else if (role === 'kitchen') {
        this.socket.emit('join_kitchen');
      } else if (role === 'waiter') {
        this.socket.emit('join_waiter');
      }
    });

    return this.socket;
  }
};

window.App = App;
