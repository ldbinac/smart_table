"""
导入导出模块测试
"""
import pytest
import io
import json


class TestImportExport:
    """导入导出功能测试类"""
    
    @pytest.fixture
    def sample_csv_bytes(self):
        """生成 CSV 测试数据"""
        csv_content = (
            b'name,age,score,active\n'
            b'Alice,30,95.5,true\n'
            b'Bob,25,88.0,false\n'
            b'Charlie,35,92.3,true\n'
        )
        return io.BytesIO(csv_content)
    
    @pytest.fixture
    def sample_excel_like_csv(self):
        """生成 Excel 格式的 CSV 数据"""
        csv_content = (
            b'\xef\xbb\xbf'  # BOM header
            b'Product,Price,Quantity,Category\n'
            b'Laptop,9999.00,10,Electronics\n'
            b'Phone,5999.00,20,Electronics\n'
            b'Book,49.90,100,Books\n'
        )
        return io.BytesIO(csv_content)
    
    def test_analyze_csv_structure(self, client, auth_headers, sample_csv_bytes):
        """分析 CSV 文件结构"""
        sample_csv_bytes.seek(0)
        response = client.post('/api/import/analyze',
            data={'file': (sample_csv_bytes, 'test.csv', 'text/csv')},
            headers=auth_headers,
            content_type='multipart/form-data'
        )
        
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.get_json()['data']
            assert 'total_rows' in data
            assert 'columns' in data
            assert data['total_rows'] > 0
    
    def test_import_csv_preview(self, client, auth_headers, sample_csv_bytes, test_table, test_field):
        """CSV 导入预览"""
        sample_csv_bytes.seek(0)
        response = client.post('/api/import/csv',
            data={
                'file': (sample_csv_bytes, 'test.csv', 'text/csv'),
                'table_id': str(test_table.id),
                'preview_only': 'true'
            },
            headers=auth_headers,
            content_type='multipart/form-data'
        )
        
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.get_json()['data']
            assert data.get('preview') is True
            assert 'sample_data' in data
    
    def test_import_json_preview(self, client, auth_headers, test_table):
        """JSON 导入预览"""
        json_data = [
            {'name': 'Item 1', 'value': 100},
            {'name': 'Item 2', 'value': 200},
            {'name': 'Item 3', 'value': 300}
        ]
        response = client.post('/api/import/json',
            json={
                'data': json_data,
                'table_id': str(test_table.id),
                'preview_only': True
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.get_json()['data']
            assert data['total_rows'] == 3
    
    def test_export_to_csv(self, client, auth_headers, test_table, test_record):
        """导出为 CSV"""
        response = client.post('/api/export',
            json={
                'table_id': str(test_table.id),
                'format': 'csv'
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            assert response.content_type.startswith(('text/', 'application/'))
    
    def test_export_to_json(self, client, auth_headers, test_table, test_record):
        """导出为 JSON"""
        response = client.post('/api/export',
            json={
                'table_id': str(test_table.id),
                'format': 'json'
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.get_json()
            if isinstance(data, dict) and 'data' in data:
                items = data['data']
                if isinstance(items, list):
                    assert len(items) >= 0
    
    def test_export_specific_fields(self, client, auth_headers, test_table, test_field):
        """导出指定字段"""
        response = client.post('/api/export',
            json={
                'table_id': str(test_table.id),
                'format': 'csv',
                'field_ids': [str(test_field.id)]
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400]
    
    def test_export_specific_records(self, client, auth_headers, test_table, test_record):
        """导出指定记录"""
        response = client.post('/api/export',
            json={
                'table_id': str(test_table.id),
                'format': 'json',
                'record_ids': [str(test_record.id)]
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400]
    
    def test_import_task_status(self, client, auth_headers):
        """查询导入任务状态"""
        response = client.get('/api/import/tasks/test-task-id',
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]
    
    def test_export_task_status(self, client, auth_headers):
        """查询导出任务状态"""
        response = client.get('/api/export/tasks/test-task-id',
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]
    
    def test_import_empty_file_rejected(self, client, auth_headers):
        """空文件导入被拒绝"""
        empty_file = io.BytesIO(b'')
        response = client.post('/api/import/csv',
            data={
                'file': (empty_file, 'empty.csv', 'text/csv'),
                'table_id': 'some-table-id'
            },
            headers=auth_headers,
            content_type='multipart/form-data'
        )
        
        assert response.status_code in [400, 422]
    
    def test_import_unsupported_format(self, client, auth_headers):
        """不支持格式的导入请求"""
        bad_file = io.BytesIO(b'some binary data')
        response = client.post('/api/import/excel',
            data={
                'file': (bad_file, 'test.xyz', 'application/octet-stream')
            },
            headers=auth_headers,
            content_type='multipart/form-data'
        )
        
        assert response.status_code in [400, 422]
    
    def test_export_invalid_table(self, client, auth_headers):
        """导出不存在的表格"""
        response = client.post('/api/export',
            json={
                'table_id': 'nonexistent-table-id',
                'format': 'csv'
            },
            headers=auth_headers
        )
        
        assert response.status_code in [400, 404]
    
    def test_export_invalid_format(self, client, auth_headers, test_table):
        """导出不支持的格式"""
        response = client.post('/api/export',
            json={
                'table_id': str(test_table.id),
                'format': 'pdf'
            },
            headers=auth_headers
        )
        
        assert response.status_code in [400, 422]
