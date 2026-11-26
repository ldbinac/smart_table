"""Auto-split init_app helpers"""
from ._blueprints import register_blueprints
from ._swagger import register_api_docs, init_swagger
from ._setup import register_health_check, register_lifecycle_hooks, register_error_handlers, register_shell_context, register_socketio_handlers
