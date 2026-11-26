"""plugin 路由子包 — Blueprint 定义（避免循环依赖）"""
from flask import Blueprint, request, g, jsonify, current_app

plugins_bp = Blueprint('plugins', __name__)

# 导入子模块触发路由注册
from app.routes.plugin._crud import *  # noqa
from app.routes.plugin._base import *  # noqa
from app.routes.plugin._runtime import *  # noqa
