"""workflow 路由子包 — Blueprint 定义（避免循环依赖）"""
from flask import Blueprint, request, g, jsonify, current_app

workflows_bp = Blueprint('workflows', __name__)

# 导入子模块触发路由注册
from app.routes.workflow._crud import *  # noqa
from app.routes.workflow._nodes import *  # noqa
from app.routes.workflow._trigger import *  # noqa
from app.routes.workflow._instances import *  # noqa
