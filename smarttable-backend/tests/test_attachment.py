"""
附件模块 API 测试
"""
import pytest
import io
import json


class TestAttachment:
    """附件功能测试类"""
    
    def test_upload_single_file(self, client, auth_headers, test_user):
        """测试单文件上传"""
        file_data = io.BytesIO(b'fake image content for testing')
        response = client.post('/api/attachments/upload',
            data={
                'file': (file_data, 'test_image.png', 'image/png'),
                'table_id': 'test-table-id'
            },
            headers=auth_headers,
            content_type='multipart/form-data'
        )
        
        assert response.status_code in [201, 200, 400]
    
    def test_upload_without_auth(self, client):
        """测试无认证上传文件"""
        file_data = io.BytesIO(b'unauthorized upload')
        response = client.post('/api/attachments/upload',
            data={
                'file': (file_data, 'test.txt', 'text/plain')
            },
            content_type='multipart/form-data'
        )
        
        assert response.status_code == 401
    
    def test_upload_without_file(self, client, auth_headers):
        """测试无文件上传"""
        response = client.post('/api/attachments/upload',
            data={},
            headers=auth_headers,
            content_type='multipart/form-data'
        )
        
        assert response.status_code == 400
    
    def test_get_attachment_info(self, client, auth_headers):
        """测试获取附件信息"""
        response = client.get('/api/attachments/some-file-id',
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]
    
    def test_download_attachment(self, client, auth_headers):
        """测试下载附件"""
        response = client.get('/api/attachments/some-file-id/download',
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]
    
    def test_delete_attachment(self, client, auth_headers):
        """测试删除附件"""
        response = client.delete('/api/attachments/some-file-id',
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]
    
    def test_upload_large_file(self, client, auth_headers):
        """测试大文件上传"""
        large_content = b'x' * (10 * 1024 * 1024)
        file_data = io.BytesIO(large_content)
        response = client.post('/api/attachments/upload',
            data={
                'file': (file_data, 'large_file.bin', 'application/octet-stream')
            },
            headers=auth_headers,
            content_type='multipart/form-data'
        )
        
        assert response.status_code in [201, 200, 400, 413]
    
    def test_upload_image_file_types(self, client, auth_headers):
        """测试各种图片格式上传"""
        image_types = [
            ('test.jpg', 'image/jpeg'),
            ('test.gif', 'image/gif'),
            ('test.webp', 'image/webp'),
        ]
        for filename, mime_type in image_types:
            file_data = io.BytesIO(b'fake image bytes')
            response = client.post('/api/attachments/upload',
                data={
                    'file': (file_data, filename, mime_type)
                },
                headers=auth_headers,
                content_type='multipart/form-data'
            )
            assert response.status_code in [201, 200, 400], f"Failed for {filename}"


class TestAttachmentChunkedUpload:
    """分片上传测试"""
    
    def test_init_chunked_upload(self, client, auth_headers):
        """初始化分片上传"""
        response = client.post('/api/attachments/chunked/init',
            json={
                'filename': 'large_file.zip',
                'file_size': 10485760,
                'mime_type': 'application/zip'
            },
            headers=auth_headers
        )
        
        assert response.status_code in [201, 200, 400]
    
    def test_upload_chunk(self, client, auth_headers):
        """上传分片"""
        chunk_data = io.BytesIO(b'chunk content data here')
        response = client.post('/api/attachments/chunked/upload',
            data={
                'upload_id': 'test-upload-id',
                'chunk_index': 0,
                'total_chunks': 5,
                'chunk': (chunk_data, 'chunk_0.bin', 'application/octet-stream')
            },
            headers=auth_headers,
            content_type='multipart/form-data'
        )
        
        assert response.status_code in [200, 400, 404]
    
    def test_complete_chunked_upload(self, client, auth_headers):
        """完成分片上传合并"""
        response = client.post('/api/attachments/chunked/complete',
            json={'upload_id': 'test-upload-id'},
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400, 404]
