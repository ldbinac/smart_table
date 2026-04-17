import json
from datetime import datetime, timezone
from functools import wraps

from flask import request, current_app
from flask_socketio import emit, join_room, leave_room, disconnect
from flask_jwt_extended import decode_token

from app.extensions import socketio as socketio_ext
from app.services.collaboration_service import CollaborationService
from app.services.permission_service import PermissionService
from app.models.base import MemberRole


def _authenticate_connection():
    token = request.args.get('token')
    current_app.logger.info(f'[SocketIO] Auth attempt - token from args: {bool(token)}')
    
    if not token:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            current_app.logger.info(f'[SocketIO] Auth - token from header: {bool(token)}')
    
    if not token:
        auth = getattr(request, 'auth', None)
        current_app.logger.info(f'[SocketIO] Auth - request.auth: {auth}')
        if auth and isinstance(auth, dict):
            token = auth.get('token')
            current_app.logger.info(f'[SocketIO] Auth - token from request.auth: {bool(token)}')
    
    if not token:
        from flask import g
        auth_data = getattr(g, 'auth', None)
        current_app.logger.info(f'[SocketIO] Auth - g.auth: {auth_data}')
        if auth_data and isinstance(auth_data, dict):
            token = auth_data.get('token')
            current_app.logger.info(f'[SocketIO] Auth - token from g.auth: {bool(token)}')
    
    if not token:
        current_app.logger.info(f'[SocketIO] Auth - request.headers: {dict(request.headers)}')
        current_app.logger.info(f'[SocketIO] Auth - request.args: {dict(request.args)}')
        current_app.logger.warning('[SocketIO] Auth - no token found')
        return None
    try:
        decoded = decode_token(token)
        user_id = decoded.get('sub')
        if not user_id:
            current_app.logger.warning('[SocketIO] Auth - no user_id in token')
            return None
        current_app.logger.info(f'[SocketIO] Auth - success, user_id={user_id}')
        return user_id
    except Exception as e:
        current_app.logger.error(f'[SocketIO] Auth - token decode error: {e}')
        return None


def register_socketio_handlers(socketio, app):

    @socketio.on('connect')
    def handle_connect():
        current_app.logger.info(f'[SocketIO] Connect event received, sid={request.sid}')
        user_id = _authenticate_connection()
        if not user_id:
            current_app.logger.warning(f'SocketIO connect rejected: no valid token, sid={request.sid}')
            disconnect()
            return False
        current_app.logger.info(f'SocketIO connected: user_id={user_id}, sid={request.sid}')
        emit('connect_ack', {'status': 'ok', 'sid': request.sid})

    @socketio.on('disconnect')
    def handle_disconnect():
        current_app.logger.info(f'SocketIO disconnected: sid={request.sid}')
        try:
            CollaborationService.handle_disconnect(request.sid)
        except Exception as e:
            current_app.logger.error(f'SocketIO disconnect handler error: {e}')

    @socketio.on('room:join')
    def handle_room_join(data):
        user_id = _authenticate_connection()
        if not user_id:
            disconnect()
            return
        base_id = data.get('base_id')
        if not base_id:
            emit('error', {'message': 'base_id is required'})
            return
        if not PermissionService.check_permission(base_id, user_id, MemberRole.VIEWER):
            emit('error', {'message': 'Permission denied'})
            return
        try:
            result = CollaborationService.join_room(base_id, user_id, request.sid)
            join_room(f'base:{base_id}')
            online_users = CollaborationService.get_online_users(base_id)
            emit('room:joined', {'status': 'ok', 'base_id': base_id, 'online_users': online_users})
            socketio_ext.emit('presence:user_joined', {
                'base_id': base_id,
                'user_id': user_id,
                'online_users': online_users
            }, room=f'base:{base_id}')
        except Exception as e:
            current_app.logger.error(f'room:join error: {e}')
            emit('error', {'message': str(e)})

    @socketio.on('room:leave')
    def handle_room_leave(data):
        user_id = _authenticate_connection()
        if not user_id:
            return
        base_id = data.get('base_id')
        if not base_id:
            return
        try:
            CollaborationService.leave_room(base_id, user_id)
            leave_room(f'base:{base_id}')
            socketio_ext.emit('presence:user_left', {
                'base_id': base_id,
                'user_id': user_id
            }, room=f'base:{base_id}')
        except Exception as e:
            current_app.logger.error(f'room:leave error: {e}')

    @socketio.on('presence:view_changed')
    def handle_view_changed(data):
        user_id = _authenticate_connection()
        if not user_id:
            return
        base_id = data.get('base_id')
        table_id = data.get('table_id')
        view_id = data.get('view_id')
        view_type = data.get('view_type')
        if not base_id:
            return
        try:
            CollaborationService.update_user_view(base_id, user_id, table_id, view_id, view_type)
            socketio_ext.emit('presence:view_changed', {
                'base_id': base_id,
                'user_id': user_id,
                'table_id': table_id,
                'view_id': view_id,
                'view_type': view_type
            }, room=f'base:{base_id}')
        except Exception as e:
            current_app.logger.error(f'presence:view_changed error: {e}')

    @socketio.on('presence:cell_selected')
    def handle_cell_selected(data):
        user_id = _authenticate_connection()
        if not user_id:
            return
        base_id = data.get('base_id')
        table_id = data.get('table_id')
        record_id = data.get('record_id')
        field_id = data.get('field_id')
        if not all([base_id, table_id]):
            return
        try:
            CollaborationService.update_user_cell(base_id, user_id, table_id, record_id, field_id)
            socketio_ext.emit('presence:cell_selected', {
                'base_id': base_id,
                'user_id': user_id,
                'table_id': table_id,
                'record_id': record_id,
                'field_id': field_id
            }, room=f'base:{base_id}')
        except Exception as e:
            current_app.logger.error(f'presence:cell_selected error: {e}')

    @socketio.on('lock:acquire')
    def handle_lock_acquire(data):
        user_id = _authenticate_connection()
        if not user_id:
            emit('lock_result', {'success': False, 'message': 'Not authenticated'})
            return
        base_id = data.get('base_id')
        table_id = data.get('table_id')
        record_id = data.get('record_id')
        field_id = data.get('field_id')
        if not all([base_id, table_id, record_id, field_id]):
            emit('lock_result', {'success': False, 'message': 'Missing required fields'})
            return
        try:
            success, locked_by = CollaborationService.acquire_lock(
                base_id, user_id, table_id, record_id, field_id
            )
            emit('lock_result', {
                'success': success,
                'base_id': base_id,
                'table_id': table_id,
                'record_id': record_id,
                'field_id': field_id,
                'locked_by': locked_by
            })
            if success:
                socketio_ext.emit('lock:acquired', {
                    'base_id': base_id,
                    'user_id': user_id,
                    'table_id': table_id,
                    'record_id': record_id,
                    'field_id': field_id
                }, room=f'base:{base_id}')
        except Exception as e:
            current_app.logger.error(f'lock:acquire error: {e}')
            emit('lock_result', {'success': False, 'message': str(e)})

    @socketio.on('lock:release')
    def handle_lock_release(data):
        user_id = _authenticate_connection()
        if not user_id:
            return
        base_id = data.get('base_id')
        table_id = data.get('table_id')
        record_id = data.get('record_id')
        field_id = data.get('field_id')
        if not all([base_id, table_id, record_id, field_id]):
            return
        try:
            CollaborationService.release_lock(base_id, user_id, table_id, record_id, field_id)
            socketio_ext.emit('lock:released', {
                'base_id': base_id,
                'user_id': user_id,
                'table_id': table_id,
                'record_id': record_id,
                'field_id': field_id
            }, room=f'base:{base_id}')
        except Exception as e:
            current_app.logger.error(f'lock:release error: {e}')

    @socketio.on('ping')
    def handle_ping():
        emit('pong')
