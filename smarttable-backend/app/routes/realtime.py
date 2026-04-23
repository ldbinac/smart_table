from flask import Blueprint, current_app
from app.utils.response import success_response

realtime_bp = Blueprint('realtime', __name__)


@realtime_bp.route('/realtime/status', methods=['GET'])
def get_realtime_status():
    """
    获取实时服务状态（公开接口）
    ---
    tags:
      - Realtime
    description: 获取实时协作服务的状态和 WebSocket 连接地址
    responses:
      200:
        description: 实时服务状态
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 200
            message:
              type: string
              example: "success"
            data:
              type: object
              properties:
                enabled:
                  type: boolean
                  description: 实时服务是否启用
                  example: true
                socket_url:
                  type: string
                  description: WebSocket 连接地址（服务启用时返回）
                  example: "ws://localhost:5000"
    """
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
