from flask import Blueprint, current_app
from app.utils.response import success_response

realtime_bp = Blueprint('realtime', __name__)


@realtime_bp.route('/realtime/status', methods=['GET'])
def get_realtime_status():
    enabled = current_app.config.get('REALTIME_ENABLED', False)
    socket_url = None
    if enabled:
        host = current_app.config.get('SOCKET_HOST', current_app.config.get('HOST', 'localhost'))
        port = current_app.config.get('SOCKET_PORT', current_app.config.get('PORT', 5000))
        socket_url = f"ws://{host}:{port}"
    return success_response(data={
        'enabled': enabled,
        'socket_url': socket_url
    })


def register_handlers(socketio):
    @socketio.on('connect')
    def handle_connect():
        pass

    @socketio.on('disconnect')
    def handle_disconnect():
        pass
