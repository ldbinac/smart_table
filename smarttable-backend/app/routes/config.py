"""
公开配置路由模块
返回前端需要的非敏感系统配置
"""
from flask import Blueprint, current_app

from app.utils.response import success_response

config_bp = Blueprint('config', __name__)
config_bp.strict_slashes = False


@config_bp.route('/demo', methods=['GET'])
def get_demo_config() -> tuple:
    """
    获取演示环境配置
    ---
    tags:
      - Config
    responses:
      200:
        description: 返回演示环境配置
    """
    is_demo = current_app.config.get('IS_DEMO_ENVIRONMENT', False)
    owner = current_app.config.get('GITEE_REPO_OWNER', 'binac')
    repo = current_app.config.get('GITEE_REPO_NAME', 'smart_table')

    return success_response(
        data={
            'is_demo_environment': is_demo,
            'gitee_repo_url': f'https://gitee.com/{owner}/{repo}',
            'gitee_repo_owner': owner,
            'gitee_repo_name': repo,
        },
        message='获取成功'
    )
