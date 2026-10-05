"""SocketIO event handlers for real-time communication."""
from flask_socketio import join_room, leave_room, emit


def register_socket_events(socketio):
    """Register all SocketIO event handlers."""
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        emit('connected', {'status': 'connected'})
    
    @socketio.on('join_session')
    def handle_join_session(data):
        """Customer joins their session room for real-time updates."""
        session_id = data.get('session_id')
        if session_id:
            join_room(f'session_{session_id}')
            emit('joined', {'room': f'session_{session_id}'})
    
    @socketio.on('join_admin')
    def handle_join_admin(data=None):
        """Admin joins admin room."""
        join_room('admin')
        emit('joined', {'room': 'admin'})
    
    @socketio.on('join_kitchen')
    def handle_join_kitchen(data=None):
        """Kitchen staff joins kitchen room."""
        join_room('kitchen')
        emit('joined', {'room': 'kitchen'})
    
    @socketio.on('join_waiter')
    def handle_join_waiter(data=None):
        """Waiter joins waiter room."""
        join_room('waiter')
        emit('joined', {'room': 'waiter'})
    
    @socketio.on('leave_session')
    def handle_leave_session(data):
        """Customer leaves session room."""
        session_id = data.get('session_id')
        if session_id:
            leave_room(f'session_{session_id}')
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        pass
