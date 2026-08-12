import json
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict, Any

from flask import current_app

from app.extensions import db, socketio
import app.extensions as _app_extensions
from app.models.collaboration_session import CollaborationSession
from app.models.user import User


def _get_redis_client():
    """
    获取 Redis 客户端实例，支持懒连接。

    后端启动时 Redis 可能未就绪导致 redis_client 为 None，
    此处会在首次调用时尝试重新连接，避免锁功能永久失效。

    Returns:
        Redis 客户端实例，如果连接失败则返回 None
    """
    # 通过模块引用动态获取，避免 from import 值快照过期问题
    rc = _app_extensions.redis_client
    if rc is not None:
        return rc

    # 懒连接：尝试重新初始化 Redis 客户端
    try:
        import redis as _redis_lib
        redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        new_client = _redis_lib.from_url(redis_url, decode_responses=True)
        new_client.ping()
        # 写回模块全局变量，后续调用直接复用
        _app_extensions.redis_client = new_client
        current_app.logger.info('[CollaborationService] Redis client lazy-initialized successfully')
        return new_client
    except Exception as e:
        current_app.logger.warning(f'[CollaborationService] Redis lazy-connect failed: {e}')
        return None


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
    def release_all_locks(base_id: str, user_id: str) -> List[dict]:
        """
        释放指定用户在某 base 下的所有单元格锁。

        Returns:
            被释放的锁列表，每项包含 table_id / record_id / field_id
        """
        r = _get_redis_client()
        if not r:
            return []

        pattern = f'collab:lock:{base_id}:*'
        cursor = 0
        released: List[dict] = []
        while True:
            cursor, keys = r.scan(cursor, match=pattern, count=100)
            for key in keys:
                holder = r.get(key)
                if holder == user_id:
                    r.delete(key)
                    # 解析 lock_key: collab:lock:{base_id}:{table_id}:{record_id}:{field_id}
                    parts = key.split(':') if isinstance(key, str) else key.decode().split(':')
                    # parts: ['collab', 'lock', base_id, table_id, record_id, field_id]
                    if len(parts) >= 6:
                        released.append({
                            'table_id': parts[3],
                            'record_id': parts[4],
                            'field_id': parts[5],
                        })
            if cursor == 0:
                break
        return released

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

            released_locks = CollaborationService.release_all_locks(base_id, user_id)

            session.is_active = False

            user_info = CollaborationService._get_user_brief(user_id)
            socketio.emit('presence:user_left', {
                'base_id': base_id,
                'user_id': user_id,
                'nickname': user_info.get('name', 'Unknown'),
                'name': user_info.get('name', 'Unknown'),
                'avatar': user_info.get('avatar')
            }, room=f'base:{base_id}')

            # 广播断线释放的单元格锁，通知其他在线用户
            for lock in released_locks:
                socketio.emit('lock:released', {
                    'base_id': base_id,
                    'user_id': user_id,
                    'nickname': user_info.get('name', 'Unknown'),
                    'name': user_info.get('name', 'Unknown'),
                    'avatar': user_info.get('avatar'),
                    'table_id': lock['table_id'],
                    'record_id': lock['record_id'],
                    'field_id': lock['field_id'],
                    'reason': 'disconnect'
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
