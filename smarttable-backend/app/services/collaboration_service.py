import json
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict, Any

from flask import current_app

from app.extensions import db, socketio, redis_client
from app.models.collaboration_session import CollaborationSession
from app.models.user import User


def _get_redis_client():
    """
    获取 Redis 客户端实例
    
    Returns:
        Redis 客户端实例，如果未初始化则返回 None
    """
    if redis_client is None:
        current_app.logger.warning('[CollaborationService] Redis client not initialized')
        return None
    return redis_client


class CollaborationService:

    LOCK_TIMEOUT = 60

    @staticmethod
    def join_room(base_id: str, user_id: str, socket_id: str) -> dict:
        r = _get_redis_client()
        
        user = User.query.get(user_id)
        user_info = {
            'user_id': user_id,
            'name': user.name if user else 'Unknown',
            'avatar': user.avatar if user else None,
            'socket_id': socket_id,
            'joined_at': datetime.now(timezone.utc).isoformat()
        }
        
        if r:
            room_key = f'collab:room:{base_id}:users'
            r.hset(room_key, user_id, json.dumps(user_info))

        existing = CollaborationSession.query.filter_by(
            base_id=base_id,
            user_id=user_id,
            is_active=True
        ).first()

        if existing:
            existing.socket_id = socket_id
            existing.last_active_at = datetime.now(timezone.utc)
            existing.is_active = True
        else:
            session = CollaborationSession(
                base_id=base_id,
                user_id=user_id,
                socket_id=socket_id,
                is_active=True
            )
            db.session.add(session)

        db.session.commit()
        return user_info

    @staticmethod
    def leave_room(base_id: str, user_id: str):
        r = _get_redis_client()
        
        if r:
            room_key = f'collab:room:{base_id}:users'
            r.hdel(room_key, user_id)

            presence_key = f'collab:presence:{base_id}:{user_id}'
            r.delete(presence_key)

        session = CollaborationSession.query.filter_by(
            base_id=base_id,
            user_id=user_id,
            is_active=True
        ).first()
        if session:
            session.is_active = False
            db.session.commit()

    @staticmethod
    def get_online_users(base_id: str) -> List[dict]:
        r = _get_redis_client()
        if not r:
            return []
        
        room_key = f'collab:room:{base_id}:users'
        users_data = r.hgetall(room_key)
        result = []
        for uid, info_json in users_data.items():
            try:
                result.append(json.loads(info_json))
            except (json.JSONDecodeError, TypeError):
                pass
        return result

    @staticmethod
    def update_user_view(base_id: str, user_id: str, table_id: str, view_id: str, view_type: str):
        r = _get_redis_client()
        
        if r:
            presence_key = f'collab:presence:{base_id}:{user_id}'
            r.hset(presence_key, mapping={
                'table_id': table_id or '',
                'view_id': view_id or '',
                'view_type': view_type or ''
            })

        session = CollaborationSession.query.filter_by(
            base_id=base_id,
            user_id=user_id,
            is_active=True
        ).first()
        if session:
            session.current_table_id = table_id
            session.current_view_id = view_id
            session.current_view_type = view_type
            session.last_active_at = datetime.now(timezone.utc)
            db.session.commit()

    @staticmethod
    def update_user_cell(base_id: str, user_id: str, table_id: str, record_id: str, field_id: str):
        r = _get_redis_client()
        
        if r:
            presence_key = f'collab:presence:{base_id}:{user_id}'
            r.hset(presence_key, mapping={
                'table_id': table_id or '',
                'record_id': record_id or '',
                'field_id': field_id or ''
            })

        session = CollaborationSession.query.filter_by(
            base_id=base_id,
            user_id=user_id,
            is_active=True
        ).first()
        if session:
            session.current_table_id = table_id
            session.last_active_at = datetime.now(timezone.utc)
            db.session.commit()

    @staticmethod
    def get_user_presence(base_id: str, user_id: str) -> Optional[dict]:
        r = _get_redis_client()
        if not r:
            return None
        
        presence_key = f'collab:presence:{base_id}:{user_id}'
        data = r.hgetall(presence_key)
        if not data:
            return None
        return {
            'user_id': user_id,
            'table_id': data.get('table_id', ''),
            'view_id': data.get('view_id', ''),
            'view_type': data.get('view_type', ''),
            'record_id': data.get('record_id', ''),
            'field_id': data.get('field_id', '')
        }

    @staticmethod
    def acquire_lock(base_id: str, user_id: str, table_id: str, record_id: str, field_id: str) -> Tuple[bool, Optional[dict]]:
        r = _get_redis_client()
        if not r:
            return False, None
        
        lock_key = f'collab:lock:{base_id}:{table_id}:{record_id}:{field_id}'

        current_holder = r.get(lock_key)
        if current_holder:
            if current_holder == user_id:
                r.expire(lock_key, CollaborationService.LOCK_TIMEOUT)
                return True, None
            else:
                holder_info = CollaborationService._get_user_brief(current_holder)
                return False, holder_info

        was_set = r.set(lock_key, user_id, ex=CollaborationService.LOCK_TIMEOUT, nx=True)
        if was_set:
            return True, None
        else:
            current_holder = r.get(lock_key)
            if current_holder and current_holder != user_id:
                holder_info = CollaborationService._get_user_brief(current_holder)
                return False, holder_info
            return False, None

    @staticmethod
    def release_lock(base_id: str, user_id: str, table_id: str, record_id: str, field_id: str):
        r = _get_redis_client()
        if not r:
            return
        
        lock_key = f'collab:lock:{base_id}:{table_id}:{record_id}:{field_id}'

        current_holder = r.get(lock_key)
        if current_holder == user_id:
            r.delete(lock_key)

    @staticmethod
    def release_all_locks(base_id: str, user_id: str):
        r = _get_redis_client()
        if not r:
            return
        
        pattern = f'collab:lock:{base_id}:*'
        cursor = 0
        while True:
            cursor, keys = r.scan(cursor, match=pattern, count=100)
            for key in keys:
                holder = r.get(key)
                if holder == user_id:
                    r.delete(key)
            if cursor == 0:
                break

    @staticmethod
    def get_lock_info(base_id: str, table_id: str, record_id: str, field_id: str) -> Optional[dict]:
        r = _get_redis_client()
        if not r:
            return None
        
        lock_key = f'collab:lock:{base_id}:{table_id}:{record_id}:{field_id}'
        holder = r.get(lock_key)
        if not holder:
            return None
        return CollaborationService._get_user_brief(holder)

    @staticmethod
    def broadcast_change(event_name: str, base_id: str, data: dict):
        current_app.logger.info(f'[CollaborationService] Broadcasting {event_name} to base:{base_id}')
        current_app.logger.info(f'[CollaborationService] Broadcast data: {data}')
        current_app.logger.info(f'[CollaborationService] SocketIO instance: {socketio}')
        try:
            result = socketio.emit(event_name, data, room=f'base:{base_id}')
            current_app.logger.info(f'[CollaborationService] Broadcast result: {result}')
        except Exception as e:
            current_app.logger.error(f'[CollaborationService] Broadcast error: {e}')
            import traceback
            traceback.print_exc()

    @staticmethod
    def broadcast_presence(base_id: str, event_name: str, data: dict):
        current_app.logger.info(f'[CollaborationService] Broadcasting presence {event_name} to base:{base_id}')
        socketio.emit(event_name, data, room=f'base:{base_id}')

    @staticmethod
    def broadcast_lock(base_id: str, event_name: str, data: dict):
        current_app.logger.info(f'[CollaborationService] Broadcasting lock {event_name} to base:{base_id}')
        socketio.emit(event_name, data, room=f'base:{base_id}')

    @staticmethod
    def broadcast_if_enabled(event_name: str, base_id: str, data: dict):
        if not current_app.config.get('REALTIME_ENABLED', False):
            current_app.logger.info(f'[CollaborationService] Realtime disabled, skipping {event_name}')
            return
        current_app.logger.info(f'[CollaborationService] broadcast_if_enabled: {event_name} to base:{base_id}')
        CollaborationService.broadcast_change(event_name, base_id, data)

    @staticmethod
    def handle_disconnect(socket_id: str):
        sessions = CollaborationSession.query.filter_by(
            socket_id=socket_id,
            is_active=True
        ).all()

        for session in sessions:
            base_id = session.base_id
            user_id = session.user_id

            r = _get_redis_client()
            if r:
                room_key = f'collab:room:{base_id}:users'
                r.hdel(room_key, user_id)

                presence_key = f'collab:presence:{base_id}:{user_id}'
                r.delete(presence_key)

            CollaborationService.release_all_locks(base_id, user_id)

            session.is_active = False

            user_info = CollaborationService._get_user_brief(user_id)
            socketio.emit('presence:user_left', {
                'base_id': base_id,
                'user_id': user_id,
                'nickname': user_info.get('name', 'Unknown'),
                'name': user_info.get('name', 'Unknown'),
                'avatar': user_info.get('avatar')
            }, room=f'base:{base_id}')

        if sessions:
            db.session.commit()

    @staticmethod
    def _get_user_brief(user_id: str) -> dict:
        user = User.query.get(user_id)
        if user:
            return {
                'user_id': str(user.id),
                'name': user.name,
                'avatar': user.avatar
            }
        return {
            'user_id': user_id,
            'name': 'Unknown',
            'avatar': None
        }
