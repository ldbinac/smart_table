"""
文档模块 API 测试
"""
import pytest
import json


class TestDocumentAPI:
    """文档 API 功能测试类"""

    def test_create_document(self, client, auth_headers, test_base):
        """测试创建文档"""
        response = client.post(
            f'/api/bases/{test_base.id}/documents',
            json={
                'name': '测试文档',
                'content': '{"ops":[{"insert":"测试内容\\n"}]}',
                'content_format': 'delta'
            },
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['code'] == 201
        assert data['data']['name'] == '测试文档'
        assert data['data']['content_format'] == 'delta'

    def test_create_document_without_auth(self, client, test_base):
        """测试无认证创建文档"""
        response = client.post(
            f'/api/bases/{test_base.id}/documents',
            json={
                'name': '未授权文档'
            }
        )

        assert response.status_code == 401

    def test_create_document_exceed_limit(self, client, auth_headers, test_base):
        """测试文档数量限制"""
        # 创建 10 个文档
        for i in range(10):
            client.post(
                f'/api/bases/{test_base.id}/documents',
                json={'name': f'文档{i}'},
                headers=auth_headers
            )

        # 第 11 个应该失败
        response = client.post(
            f'/api/bases/{test_base.id}/documents',
            json={'name': '超出限制的文档'},
            headers=auth_headers
        )

        assert response.status_code == 400
        data = response.get_json()
        assert '最多创建 10 个文档' in data['message']

    def test_get_document_list(self, client, auth_headers, test_base):
        """测试获取文档列表"""
        # 先创建一个文档
        client.post(
            f'/api/bases/{test_base.id}/documents',
            json={'name': '列表测试文档'},
            headers=auth_headers
        )

        response = client.get(
            f'/api/bases/{test_base.id}/documents',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert 'items' in data['data']
        assert len(data['data']['items']) >= 1

    def test_get_document_detail(self, client, auth_headers, test_base):
        """测试获取文档详情"""
        create_resp = client.post(
            f'/api/bases/{test_base.id}/documents',
            json={'name': '详情测试文档', 'content': '{"ops":[]}'},
            headers=auth_headers
        )
        doc_id = create_resp.get_json()['data']['id']

        response = client.get(
            f'/api/documents/{doc_id}',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert data['data']['name'] == '详情测试文档'
        assert 'content' in data['data']

    def test_get_nonexistent_document(self, client, auth_headers):
        """测试获取不存在的文档"""
        response = client.get(
            '/api/documents/nonexistent-id',
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_update_document(self, client, auth_headers, test_base):
        """测试更新文档"""
        create_resp = client.post(
            f'/api/bases/{test_base.id}/documents',
            json={'name': '待更新文档'},
            headers=auth_headers
        )
        doc_id = create_resp.get_json()['data']['id']

        response = client.put(
            f'/api/documents/{doc_id}',
            json={'name': '更新后的文档名'},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert data['data']['name'] == '更新后的文档名'

    def test_delete_document(self, client, auth_headers, test_base):
        """测试删除文档"""
        create_resp = client.post(
            f'/api/bases/{test_base.id}/documents',
            json={'name': '可删除的文档'},
            headers=auth_headers
        )
        doc_id = create_resp.get_json()['data']['id']

        response = client.delete(
            f'/api/documents/{doc_id}',
            headers=auth_headers
        )

        assert response.status_code == 204

    def test_delete_nonexistent_document(self, client, auth_headers):
        """测试删除不存在的文档"""
        response = client.delete(
            '/api/documents/nonexistent-id',
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_permission_check_viewer_cannot_create(self, client, test_base, test_user):
        """测试 Viewer 角色不能创建文档"""
        # 先创建 Viewer 用户
        from app.models import MemberRole
        from app.extensions import db

        # 添加 test_user 为 viewer
        from app.models import BaseMember
        member = BaseMember(
            base_id=test_base.id,
            user_id=test_user.id,
            role=MemberRole.VIEWER
        )
        db.session.add(member)
        db.session.commit()

        # 登录获取 token
        login_resp = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'Test1234!'
        })
        tokens = login_resp.get_json()['data']['tokens']
        viewer_headers = {'Authorization': f'Bearer {tokens["access_token"]}'}

        response = client.post(
            f'/api/bases/{test_base.id}/documents',
            json={'name': 'Viewer 创建的文档'},
            headers=viewer_headers
        )

        assert response.status_code == 403

    def test_export_pdf_frontend(self, client, auth_headers, test_base):
        """测试前端导出 PDF"""
        create_resp = client.post(
            f'/api/bases/{test_base.id}/documents',
            json={'name': 'PDF 测试文档', 'content': '{"ops":[]}'},
            headers=auth_headers
        )
        doc_id = create_resp.get_json()['data']['id']

        response = client.post(
            f'/api/documents/{doc_id}/export-pdf',
            json={'export_type': 'frontend'},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert data['data']['type'] == 'frontend'


class TestDocumentModel:
    """文档模型测试类"""

    def test_document_creation(self, app, db_session, test_base, test_user):
        """测试文档模型创建"""
        from app.models.document import Document

        with app.app_context():
            doc = Document(
                base_id=test_base.id,
                name='模型测试文档',
                content='{"ops":[]}',
                created_by=test_user.id
            )
            db_session.add(doc)
            db_session.commit()

            assert doc.id is not None
            assert doc.name == '模型测试文档'
            assert doc.order == 0
            assert doc.content_format == 'delta'

    def test_document_to_dict(self, app, db_session, test_base, test_user):
        """测试文档序列化"""
        from app.models.document import Document

        with app.app_context():
            doc = Document(
                base_id=test_base.id,
                name='序列化测试',
                content='{"ops":[{"insert":"test\\n"}]}',
                created_by=test_user.id
            )
            db_session.add(doc)
            db_session.commit()

            # 默认不包含 content
            data = doc.to_dict()
            assert 'id' in data
            assert 'name' in data
            assert 'content' not in data

            # 包含 content
            data_with_content = doc.to_dict(include_content=True)
            assert 'content' in data_with_content
            assert data_with_content['content'] == '{"ops":[{"insert":"test\\n"}]}'

    def test_document_base_relationship(self, app, db_session, test_base, test_user):
        """测试文档与 Base 的关系"""
        from app.models.document import Document

        with app.app_context():
            doc = Document(
                base_id=test_base.id,
                name='关系测试',
                created_by=test_user.id
            )
            db_session.add(doc)
            db_session.commit()

            # 验证可以通过 base 访问 documents
            base_docs = test_base.documents.all()
            assert len(base_docs) >= 1
            assert any(d.name == '关系测试' for d in base_docs)
