"""
数据表文件夹（TableFolder）功能测试
覆盖：文件夹 CRUD、单层结构限制、删除空校验、table.folder_id 归属校验
"""
import uuid

from app.extensions import db
from app.models import Table, TableFolder


class TestTableFolderAPI:
    """文件夹 API 测试"""

    def test_create_folder_success(self, client, auth_headers, test_base):
        """创建文件夹成功"""
        response = client.post(
            f'/api/bases/{test_base.id}/table-folders',
            json={'name': '项目文件夹'},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.get_json()['data']
        assert data['name'] == '项目文件夹'
        assert data['base_id'] == str(test_base.id)
        assert 'id' in data

    def test_create_folder_empty_name(self, client, auth_headers, test_base):
        """空名称创建文件夹返回 400"""
        response = client.post(
            f'/api/bases/{test_base.id}/table-folders',
            json={'name': '   '},
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_get_folders_sorted_by_order(self, client, auth_headers, test_base):
        """文件夹列表按 order 排序"""
        f1 = client.post(
            f'/api/bases/{test_base.id}/table-folders',
            json={'name': 'A'},
            headers=auth_headers,
        ).get_json()['data']
        f2 = client.post(
            f'/api/bases/{test_base.id}/table-folders',
            json={'name': 'B'},
            headers=auth_headers,
        ).get_json()['data']

        response = client.get(
            f'/api/bases/{test_base.id}/table-folders',
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.get_json()['data']
        ids = [f['id'] for f in data]
        assert ids.index(f1['id']) < ids.index(f2['id'])

    def test_rename_folder(self, client, auth_headers, test_base):
        """重命名文件夹"""
        folder = client.post(
            f'/api/bases/{test_base.id}/table-folders',
            json={'name': '旧名'},
            headers=auth_headers,
        ).get_json()['data']

        response = client.put(
            f"/api/table-folders/{folder['id']}",
            json={'name': '新名'},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.get_json()['data']['name'] == '新名'

    def test_delete_empty_folder_success(self, client, auth_headers, test_base):
        """空文件夹可删除"""
        folder = client.post(
            f'/api/bases/{test_base.id}/table-folders',
            json={'name': '待删'},
            headers=auth_headers,
        ).get_json()['data']

        response = client.delete(
            f"/api/table-folders/{folder['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert TableFolder.query.get(folder['id']) is None

    def test_delete_nonempty_folder_conflict(self, client, auth_headers, test_base, test_table):
        """非空文件夹删除返回 409"""
        folder = client.post(
            f'/api/bases/{test_base.id}/table-folders',
            json={'name': '非空'},
            headers=auth_headers,
        ).get_json()['data']

        # 将表格放入文件夹
        resp = client.put(
            f'/api/tables/{test_table.id}',
            json={'folder_id': folder['id']},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()['data']['folder_id'] == folder['id']

        # 删除非空文件夹 → 409
        response = client.delete(
            f"/api/table-folders/{folder['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 409
        assert TableFolder.query.get(folder['id']) is not None

    def test_move_table_out_of_folder(self, client, auth_headers, test_base, test_table):
        """移出文件夹（folder_id 置 null/空串）"""
        folder = client.post(
            f'/api/bases/{test_base.id}/table-folders',
            json={'name': 'F'},
            headers=auth_headers,
        ).get_json()['data']

        client.put(
            f'/api/tables/{test_table.id}',
            json={'folder_id': folder['id']},
            headers=auth_headers,
        )
        response = client.put(
            f'/api/tables/{test_table.id}',
            json={'folder_id': None},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.get_json()['data']['folder_id'] is None

    def test_move_table_to_foreign_folder_rejected(self, client, auth_headers, test_base, test_table):
        """folder_id 不属于该 Base 时返回 400"""
        # 在另一个 Base 下创建文件夹
        other_base_resp = client.post(
            '/api/bases',
            json={'name': '其他Base'},
            headers=auth_headers,
        )
        other_base_id = other_base_resp.get_json()['data']['id']

        folder = client.post(
            f'/api/bases/{other_base_id}/table-folders',
            json={'name': '外部文件夹'},
            headers=auth_headers,
        ).get_json()['data']

        response = client.put(
            f'/api/tables/{test_table.id}',
            json={'folder_id': folder['id']},
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_folder_not_found(self, client, auth_headers):
        """不存在的文件夹返回 404"""
        fake_id = uuid.uuid4()
        response = client.put(
            f'/api/table-folders/{fake_id}',
            json={'name': 'X'},
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestTableFolderService:
    """文件夹服务层测试"""

    def test_service_delete_empty_only(self, app, test_base, test_table):
        """服务层删除校验：非空拒绝、空允许"""
        from app.services.table_folder_service import TableFolderService

        folder = TableFolderService.create_folder(str(test_base.id), {'name': 'S'})
        test_table.folder_id = folder.id
        db.session.commit()

        success, error = TableFolderService.delete_folder(str(folder.id))
        assert success is False
        assert error == 'folder_not_empty'

        test_table.folder_id = None
        db.session.commit()

        success, error = TableFolderService.delete_folder(str(folder.id))
        assert success is True
        assert not error

    def test_service_count_tables(self, app, test_base, test_table):
        """文件夹内表格计数"""
        from app.services.table_folder_service import TableFolderService

        folder = TableFolderService.create_folder(str(test_base.id), {'name': 'C'})
        test_table.folder_id = folder.id
        db.session.commit()

        assert TableFolderService.count_tables_in_folder(str(folder.id)) == 1
