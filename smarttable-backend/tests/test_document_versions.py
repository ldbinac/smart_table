"""
文档版本历史 API 测试
"""
import pytest
from app.extensions import db
from app.models import Document, DocumentVersion
from app.services.document_service import DocumentService
from app.services.document_version_service import DocumentVersionService
from datetime import datetime, timezone, timedelta


@pytest.fixture
def document_version_service():
    """创建版本服务实例"""
    return DocumentVersionService()


@pytest.fixture
def document_service():
    """创建文档服务实例"""
    return DocumentService()


def test_get_document_versions(client, auth_headers, test_base):
    """测试获取文档版本列表"""
    # 创建测试文档
    create_resp = client.post(
        f'/api/bases/{test_base.id}/documents',
        json={'name': '版本测试文档', 'content': '{"ops":[]}'},
        headers=auth_headers
    )
    doc_id = create_resp.get_json()['data']['id']

    response = client.get(f'/api/documents/{doc_id}/versions', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data['code'] == 200


def test_restore_version(client, auth_headers, test_base):
    """测试恢复版本"""
    # 创建测试文档
    create_resp = client.post(
        f'/api/bases/{test_base.id}/documents',
        json={'name': '恢复测试文档', 'content': '{"ops":[{"insert":"v1\\n"}]}'},
        headers=auth_headers
    )
    doc_id = create_resp.get_json()['data']['id']

    # 获取版本列表
    versions_resp = client.get(f'/api/documents/{doc_id}/versions', headers=auth_headers)
    versions = versions_resp.get_json()['data']['items']
    assert len(versions) >= 1

    version_id = versions[0]['id']
    response = client.post(
        f'/api/document-versions/{version_id}/restore',
        headers=auth_headers
    )
    assert response.status_code == 200


class TestVersionThreshold:
    """测试版本创建阈值逻辑"""

    def test_small_content_change_does_not_create_version(
        self, app, db_session, test_user, test_base, document_service, document_version_service
    ):
        """小幅内容变更（<100字符）不创建新版本"""
        with app.app_context():
            doc = document_service.create(
                base_id=test_base.id,
                name='测试文档',
                content='{"ops":[{"insert":"initial content\\n"}]}',
                content_format='delta',
                created_by=test_user.id
            )

            # 创建时已经生成一个版本
            assert document_version_service.get_version_count(doc.id) == 1

            # 小幅修改内容（<100字符差异）
            document_service.update(
                doc_id=doc.id,
                user_id=test_user.id,
                content='{"ops":[{"insert":"initial content updated\\n"}]}'
            )

            # 不创建新版本
            assert document_version_service.get_version_count(doc.id) == 1

    def test_large_content_change_creates_version(
        self, app, db_session, test_user, test_base, document_service, document_version_service
    ):
        """大幅内容变更（>100字符）创建新版本"""
        with app.app_context():
            doc = document_service.create(
                base_id=test_base.id,
                name='测试文档',
                content='{"ops":[{"insert":"initial\\n"}]}',
                content_format='delta',
                created_by=test_user.id
            )

            assert document_version_service.get_version_count(doc.id) == 1

            # 大幅修改内容（>100字符差异）
            long_text = 'a' * 150
            document_service.update(
                doc_id=doc.id,
                user_id=test_user.id,
                content=f'{{"ops":[{{"insert":"{long_text}\\n"}}]}}'
            )

            # 创建新版本
            assert document_version_service.get_version_count(doc.id) == 2

    def test_time_interval_creates_version(
        self, app, db_session, test_user, test_base, document_service, document_version_service
    ):
        """超过15分钟间隔后保存创建新版本"""
        with app.app_context():
            doc = document_service.create(
                base_id=test_base.id,
                name='测试文档',
                content='{"ops":[{"insert":"initial\\n"}]}',
                content_format='delta',
                created_by=test_user.id
            )

            assert document_version_service.get_version_count(doc.id) == 1

            # 修改最新版本的创建时间，使其超过 15 分钟
            latest = document_version_service.get_latest_version(doc.id)
            latest.created_at = datetime.now(timezone.utc) - timedelta(minutes=16)
            db.session.commit()

            # 小幅修改内容
            document_service.update(
                doc_id=doc.id,
                user_id=test_user.id,
                content='{"ops":[{"insert":"initial updated\\n"}]}'
            )

            # 创建新版本
            assert document_version_service.get_version_count(doc.id) == 2

    def test_name_update_does_not_create_version(
        self, app, db_session, test_user, test_base, document_service, document_version_service
    ):
        """仅修改文档名称不创建新版本"""
        with app.app_context():
            doc = document_service.create(
                base_id=test_base.id,
                name='测试文档',
                content='{"ops":[{"insert":"initial\\n"}]}',
                content_format='delta',
                created_by=test_user.id
            )

            assert document_version_service.get_version_count(doc.id) == 1

            # 修改名称
            document_service.update(
                doc_id=doc.id,
                user_id=test_user.id,
                name='新名称'
            )

            # 不创建新版本
            assert document_version_service.get_version_count(doc.id) == 1

    def test_should_create_version_based_on_latest_version(
        self, app, db_session, test_user, test_base, document_version_service
    ):
        """版本判断应基于最新版本内容，而不是当前 document.content"""
        with app.app_context():
            doc = Document(
                base_id=test_base.id,
                name='测试文档',
                content='{"ops":[{"insert":"A\\n"}]}',
                content_format='delta',
                created_by=test_user.id
            )
            db.session.add(doc)
            db.session.commit()

            # 创建初始版本（内容 A）
            document_version_service.create_version(
                document_id=doc.id,
                name='版本 1',
                content='{"ops":[{"insert":"A\\n"}]}',
                content_format='delta',
                user_id=test_user.id,
                change_summary='创建文档'
            )

            # 当前文档内容被外部修改为 B（但没有创建版本）
            doc.content = '{"ops":[{"insert":"B\\n"}]}'
            db.session.commit()

            # 再次保存内容 A，与最新版本 A 比较，差异很小，不应创建版本
            should_create, _ = document_version_service.should_create_version(
                document_id=doc.id,
                new_content='{"ops":[{"insert":"A\\n"}]}'
            )
            assert not should_create

            # 保存内容 C（与最新版本 A 差异 >100 字符），应创建版本
            long_text = 'c' * 150
            should_create, _ = document_version_service.should_create_version(
                document_id=doc.id,
                new_content=f'{{"ops":[{{"insert":"{long_text}\\n"}}]}}'
            )
            assert should_create
