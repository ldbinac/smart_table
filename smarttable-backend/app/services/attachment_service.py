"""
附件服务模块
处理文件上传、存储、缩略图生成和元数据管理
支持本地文件系统和 MinIO 对象存储
"""
import os
import uuid
import shutil
import mimetypes
from datetime import datetime, timezone
from typing import Optional, BinaryIO, Dict, Any, Tuple, Set
from pathlib import Path

from werkzeug.utils import secure_filename
from flask import current_app

from app.extensions import db
from app.models.attachment import Attachment, AttachmentType


# 文件 Magic Number 签名
# 格式: {文件类型: [(签名字节, 偏移量), ...]}
FILE_SIGNATURES = {
    # 图片类型
    'image/jpeg': [(b'\xff\xd8\xff', 0)],
    'image/png': [(b'\x89PNG\r\n\x1a\n', 0)],
    'image/gif': [(b'GIF87a', 0), (b'GIF89a', 0)],
    'image/webp': [(b'RIFF', 0), (b'WEBP', 8)],
    'image/bmp': [(b'BM', 0)],
    'image/tiff': [(b'II*\x00', 0), (b'MM\x00*', 0)],
    
    # 文档类型
    'application/pdf': [(b'%PDF', 0)],
    
    # Office 文档
    'application/zip': [(b'PK\x03\x04', 0)],  # DOCX, XLSX, PPTX 都是 ZIP 格式
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': [(b'PK\x03\x04', 0)],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': [(b'PK\x03\x04', 0)],
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': [(b'PK\x03\x04', 0)],
    
    # 压缩文件
    'application/x-rar-compressed': [(b'Rar!\x1a\x07', 0)],
    'application/x-7z-compressed': [(b'7z\xbc\xaf\x27\x1c', 0)],
    'application/x-tar': [(b'ustar', 257)],
    'application/gzip': [(b'\x1f\x8b', 0)],
    
    # 视频类型
    'video/mp4': [(b'\x00\x00\x00\x18ftypmp42', 0), (b'\x00\x00\x00\x1cftypmp42', 0), (b'ftyp', 4)],
    'video/avi': [(b'RIFF', 0), (b'AVI', 8)],
    'video/quicktime': [(b'moov', 4), (b'mdat', 4)],
    'video/x-matroska': [(b'\x1a\x45\xdf\xa3', 0)],
    'video/webm': [(b'\x1a\x45\xdf\xa3', 0)],
    'video/x-flv': [(b'FLV', 0)],
    
    # 音频类型
    'audio/mpeg': [(b'\xff\xfb', 0), (b'\xff\xfa', 0), (b'ID3', 0)],
    'audio/wav': [(b'RIFF', 0), (b'WAVE', 8)],
    'audio/ogg': [(b'OggS', 0)],
    'audio/flac': [(b'fLaC', 0)],
    'audio/x-m4a': [(b'ftypM4A', 4)],
}


class AttachmentService:
    """附件服务类"""
    
    # 允许的文件扩展名（移除 SVG）
    ALLOWED_EXTENSIONS = {
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'],
        'document': ['.doc', '.docx', '.odt', '.rtf', '.txt', '.md'],
        'spreadsheet': ['.xls', '.xlsx', '.ods', '.csv'],
        'presentation': ['.ppt', '.pptx', '.odp'],
        'pdf': ['.pdf'],
        'video': ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm'],
        'audio': ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.wma'],
        'archive': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
        'code': ['.py', '.js', '.ts', '.html', '.css', '.java', '.cpp', '.c',
                '.go', '.rs', '.rb', '.php', '.json', '.xml', '.yaml', '.yml', '.sql']
    }
    
    # 危险文件类型（禁止上传）
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js', '.jar',
        '.msi', '.msp', '.cpl', '.gadget', '.hta', '.inf', '.reg', '.msh',
        '.msh1', '.msh2', '.mshxml', '.msh1xml', '.msh2xml', '.ps1', '.ps1xml',
        '.ps2', '.ps2xml', '.psc1', '.psc2', '.msh', '.svg', '.svgz'
    }
    
    # 最大文件大小（50MB）
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    # 缩略图尺寸
    THUMBNAIL_SIZE = (300, 300)
    
    @classmethod
    def is_allowed_file(cls, filename: str) -> bool:
        """
        检查文件类型是否允许
        
        参数:
            filename: 文件名
            
        返回:
            是否允许
        """
        ext = os.path.splitext(filename.lower())[1]
        
        # 检查是否是危险文件类型
        if ext in cls.DANGEROUS_EXTENSIONS:
            return False
        
        return any(ext in exts for exts in cls.ALLOWED_EXTENSIONS.values())
    
    @classmethod
    def verify_file_content(cls, file: BinaryIO, filename: str) -> Tuple[bool, str]:
        """
        验证文件内容（Magic Number 检查）
        
        参数:
            file: 文件对象
            filename: 文件名
            
        返回:
            (是否验证通过, 错误消息或 MIME 类型)
        """
        ext = os.path.splitext(filename.lower())[1]
        
        # 获取预期的 MIME 类型
        expected_mime = cls.get_mime_type(filename)
        
        # 读取文件头部（最多 512 字节用于签名检测）
        file.seek(0)
        header = file.read(512)
        file.seek(0)
        
        if len(header) == 0:
            return False, '文件内容为空'
        
        # 对于文本文件（代码、文本等），跳过 Magic Number 检查
        text_extensions = {
            '.txt', '.md', '.json', '.xml', '.yaml', '.yml',
            '.py', '.js', '.ts', '.html', '.css', '.java', '.cpp', '.c',
            '.go', '.rs', '.rb', '.php', '.sql', '.csv'
        }
        if ext in text_extensions:
            # 尝试解码为文本，验证是否为有效文本
            try:
                header.decode('utf-8')
                return True, expected_mime
            except UnicodeDecodeError:
                try:
                    header.decode('latin-1')
                    return True, expected_mime
                except:
                    return False, '文件内容不是有效的文本格式'
        
        # 检查文件签名
        detected_mime = None
        for mime_type, signatures in FILE_SIGNATURES.items():
            for signature, offset in signatures:
                if len(header) >= offset + len(signature):
                    if header[offset:offset + len(signature)] == signature:
                        detected_mime = mime_type
                        break
            if detected_mime:
                break
        
        # 如果检测到 MIME 类型，验证是否与扩展名匹配
        if detected_mime:
            # 对于 ZIP 格式的文件（Office 文档），需要额外检查
            if detected_mime in ('application/zip', 
                                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                'application/vnd.openxmlformats-officedocument.presentationml.presentation'):
                # Office 文档扩展名
                office_extensions = {'.docx', '.xlsx', '.pptx', '.doc', '.xls', '.ppt', '.odt', '.ods', '.odp'}
                if ext in office_extensions:
                    return True, expected_mime
                # ZIP 压缩包
                if ext in {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'}:
                    return True, expected_mime
            
            # 检查 MIME 类型是否匹配
            # 图片类型
            if expected_mime.startswith('image/') and detected_mime.startswith('image/'):
                return True, expected_mime
            # 视频类型
            if expected_mime.startswith('video/') and detected_mime.startswith('video/'):
                return True, expected_mime
            # 音频类型
            if expected_mime.startswith('audio/') and detected_mime.startswith('audio/'):
                return True, expected_mime
            # PDF
            if expected_mime == 'application/pdf' and detected_mime == 'application/pdf':
                return True, expected_mime
            
            # MIME 类型不匹配
            return False, f'文件内容与扩展名不匹配（检测到: {detected_mime}）'
        
        # 无法识别的文件格式
        # 对于一些不常见的格式，允许通过但记录警告
        current_app.logger.warning(f'无法识别的文件格式: {filename}, MIME: {expected_mime}')
        return True, expected_mime
    
    @classmethod
    def get_file_type(cls, filename: str) -> str:
        """
        根据文件名获取文件类型
        
        参数:
            filename: 文件名
            
        返回:
            文件类型
        """
        ext = os.path.splitext(filename.lower())[1]
        
        for file_type, extensions in cls.ALLOWED_EXTENSIONS.items():
            if ext in extensions:
                return file_type
        
        return 'other'
    
    @classmethod
    def get_mime_type(cls, filename: str) -> str:
        """
        根据文件名获取 MIME 类型
        
        参数:
            filename: 文件名
            
        返回:
            MIME 类型
        """
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or 'application/octet-stream'
    
    @staticmethod
    def generate_stored_filename(original_filename: str) -> str:
        """
        生成唯一的存储文件名
        
        参数:
            original_filename: 原始文件名
            
        返回:
            生成的文件名
        """
        ext = os.path.splitext(original_filename)[1]
        unique_id = uuid.uuid4().hex[:16]
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        return f"{timestamp}_{unique_id}{ext}"
    
    @staticmethod
    def get_upload_path() -> str:
        """
        获取上传文件存储路径
        
        返回:
            上传目录绝对路径
        """
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        # 确保是绝对路径
        if not os.path.isabs(upload_folder):
            upload_folder = os.path.join(current_app.root_path, '..', upload_folder)
            upload_folder = os.path.abspath(upload_folder)
        return upload_folder
    
    @classmethod
    def ensure_upload_dir(cls) -> str:
        """
        确保上传目录存在
        
        返回:
            上传目录路径
        """
        upload_path = cls.get_upload_path()
        # 按日期创建子目录
        today = datetime.now(timezone.utc).strftime('%Y/%m/%d')
        upload_dir = os.path.join(upload_path, today)
        os.makedirs(upload_dir, exist_ok=True)
        return upload_dir
    
    @classmethod
    def get_file_path(cls, stored_filename: str) -> str:
        """
        根据存储文件名获取完整路径
        
        参数:
            stored_filename: 存储文件名
            
        返回:
            完整文件路径
        """
        upload_path = cls.get_upload_path()
        # 尝试在日期子目录中查找
        for root, dirs, files in os.walk(upload_path):
            if stored_filename in files:
                return os.path.join(root, stored_filename)
        # 如果找不到，返回默认路径
        return os.path.join(upload_path, stored_filename)
    
    @classmethod
    def get_file_url(cls, stored_filename: str) -> str:
        """
        获取文件访问 URL
        
        参数:
            stored_filename: 存储文件名
            
        返回:
            文件访问 URL
        """
        # 查找文件实际路径
        upload_path = cls.get_upload_path()
        for root, dirs, files in os.walk(upload_path):
            if stored_filename in files:
                # 计算相对路径
                rel_path = os.path.relpath(os.path.join(root, stored_filename), upload_path)
                return f"/uploads/{rel_path.replace(os.sep, '/')}"
        return f"/uploads/{stored_filename}"
    
    @classmethod
    def upload_attachment(cls, file: BinaryIO, data: Dict[str, Any], 
                         user_id: str) -> Optional[Attachment]:
        """
        上传附件
        
        参数:
            file: 文件对象（FileStorage 或 BinaryIO）
            data: 附件元数据，包含 filename, base_id 等
            user_id: 上传用户 ID
            
        返回:
            创建的附件对象，失败返回 None
        """
        # 获取文件信息
        original_filename = data.get('filename') or getattr(file, 'filename', 'unnamed')
        
        # 检查文件类型（扩展名）
        if not cls.is_allowed_file(original_filename):
            raise ValueError(f'不支持的文件类型: {original_filename}')
        
        # 验证文件内容（Magic Number 检查）
        is_valid, message = cls.verify_file_content(file, original_filename)
        if not is_valid:
            raise ValueError(f'文件验证失败: {message}')
        
        # 获取文件大小
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()
        file.seek(0)  # 重置到开头
        
        # 检查文件大小
        if file_size > cls.MAX_FILE_SIZE:
            raise ValueError(f'文件大小超过限制 ({cls.MAX_FILE_SIZE / 1024 / 1024}MB)')
        
        # 生成存储文件名
        stored_filename = cls.generate_stored_filename(original_filename)
        
        # 确保上传目录存在
        upload_dir = cls.ensure_upload_dir()
        file_path = os.path.join(upload_dir, stored_filename)
        
        # 保存文件
        try:
            file.save(file_path)
        except Exception as e:
            raise ValueError(f'文件保存失败: {str(e)}')
        
        # 获取 MIME 类型
        mime_type = cls.get_mime_type(original_filename)
        
        # 检测附件类型
        attachment_type = Attachment.detect_type(mime_type, original_filename)
        
        # 获取图片尺寸（如果是图片）
        width, height = None, None
        if attachment_type == AttachmentType.IMAGE.value:
            width, height = cls.get_image_dimensions(file_path)
        
        # 生成缩略图（如果是图片）
        thumbnail_url = None
        if attachment_type == AttachmentType.IMAGE.value:
            thumbnail_url = cls.generate_thumbnail(file_path, stored_filename)
        
        # 创建附件记录
        attachment = Attachment(
            filename=secure_filename(original_filename),
            stored_filename=stored_filename,
            original_name=original_filename,
            mime_type=mime_type,
            size=file_size,
            type=attachment_type,
            url=cls.get_file_url(stored_filename),
            thumbnail_url=thumbnail_url,
            width=width,
            height=height,
            uploaded_by=user_id,
            base_id=data.get('base_id')
        )
        
        db.session.add(attachment)
        db.session.commit()
        
        return attachment
    
    @staticmethod
    def get_image_dimensions(file_path: str) -> Tuple[Optional[int], Optional[int]]:
        """
        获取图片尺寸
        
        参数:
            file_path: 图片文件路径
            
        返回:
            (宽度, 高度)，如果不是图片返回 (None, None)
        """
        try:
            with Image.open(file_path) as img:
                return img.width, img.height
        except Exception:
            return None, None
    
    @classmethod
    def generate_thumbnail(cls, file_path: str, stored_filename: str) -> Optional[str]:
        """
        生成图片缩略图
        
        参数:
            file_path: 原图文件路径
            stored_filename: 存储文件名
            
        返回:
            缩略图 URL，失败返回 None
        """
        try:
            
            # 打开图片
            with Image.open(file_path) as img:
                # 转换为 RGB（处理 PNG 等带透明通道的图片）
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # 生成缩略图
                img.thumbnail(cls.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                
                # 生成缩略图文件名
                name, ext = os.path.splitext(stored_filename)
                thumbnail_filename = f"{name}_thumb.jpg"
                
                # 保存缩略图
                thumbnail_dir = os.path.join(os.path.dirname(file_path), 'thumbnails')
                os.makedirs(thumbnail_dir, exist_ok=True)
                thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)
                
                img.save(thumbnail_path, 'JPEG', quality=85)
                
                # 返回缩略图 URL
                rel_path = os.path.relpath(thumbnail_path, cls.get_upload_path())
                return f"/uploads/{rel_path.replace(os.sep, '/')}"
                
        except Exception as e:
            # 缩略图生成失败不影响主流程
            current_app.logger.warning(f'缩略图生成失败: {str(e)}')
            return None
    
    @staticmethod
    def get_attachment(attachment_id: str) -> Optional[Attachment]:
        """
        根据 ID 获取附件
        
        参数:
            attachment_id: 附件 ID
            
        返回:
            附件对象或 None
        """
        return Attachment.query.get(attachment_id)
    
    @classmethod
    def delete_attachment(cls, attachment_id: str) -> bool:
        """
        删除附件
        
        参数:
            attachment_id: 附件 ID
            
        返回:
            是否删除成功
        """
        attachment = Attachment.query.get(attachment_id)
        if not attachment:
            return False
        
        try:
            # 删除物理文件
            file_path = cls.get_file_path(attachment.stored_filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # 删除缩略图（如果存在）
            if attachment.thumbnail_url:
                thumbnail_path = cls.get_file_path(
                    os.path.basename(attachment.thumbnail_url)
                )
                if os.path.exists(thumbnail_path):
                    os.remove(thumbnail_path)
            
            # 删除数据库记录
            db.session.delete(attachment)
            db.session.commit()
            
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'删除附件失败: {str(e)}')
            return False
    
    @classmethod
    def get_attachment_file(cls, attachment_id: str) -> Optional[Tuple[str, str]]:
        """
        获取附件文件路径和文件名
        
        参数:
            attachment_id: 附件 ID
            
        返回:
            (文件路径, 原始文件名) 或 None
        """
        attachment = Attachment.query.get(attachment_id)
        if not attachment:
            return None
        
        file_path = cls.get_file_path(attachment.stored_filename)
        if not os.path.exists(file_path):
            return None
        
        return file_path, attachment.original_name
    
    @classmethod
    def get_base_attachments(cls, base_id: str, file_type: str = None,
                            page: int = 1, per_page: int = 20) -> Tuple[list, int]:
        """
        获取基础数据下的附件列表
        
        参数:
            base_id: 基础数据 ID
            file_type: 文件类型筛选（可选）
            page: 页码
            per_page: 每页数量
            
        返回:
            (附件列表, 总数量)
        """
        query = Attachment.query.filter_by(base_id=base_id)
        
        if file_type:
            query = query.filter_by(type=file_type)
        
        total = query.count()
        attachments = query.order_by(Attachment.created_at.desc()).offset(
            (page - 1) * per_page
        ).limit(per_page).all()
        
        return attachments, total
    
    @classmethod
    def update_attachment(cls, attachment_id: str, data: Dict[str, Any]) -> Optional[Attachment]:
        """
        更新附件元数据
        
        参数:
            attachment_id: 附件 ID
            data: 更新数据
            
        返回:
            更新后的附件对象，不存在返回 None
        """
        attachment = Attachment.query.get(attachment_id)
        if not attachment:
            return None
        
        # 允许更新的字段
        allowed_fields = ['filename', 'base_id']
        
        for field in allowed_fields:
            if field in data:
                setattr(attachment, field, data[field])
        
        db.session.commit()
        
        return attachment
    
    # ==================== MinIO 支持（未来扩展）====================
    
    @classmethod
    def upload_to_minio(cls, file: BinaryIO, data: Dict[str, Any],
                       user_id: str) -> Optional[Attachment]:
        """
        上传附件到 MinIO 对象存储
        
        参数:
            file: 文件对象
            data: 附件元数据
            user_id: 上传用户 ID
            
        返回:
            创建的附件对象，失败返回 None
            
        注意:
            此方法需要安装 minio 库: pip install minio
        """
        # TODO: 实现 MinIO 上传逻辑
        # from minio import Minio
        # minio_client = Minio(
        #     current_app.config['MINIO_ENDPOINT'],
        #     access_key=current_app.config['MINIO_ACCESS_KEY'],
        #     secret_key=current_app.config['MINIO_SECRET_KEY'],
        #     secure=current_app.config['MINIO_SECURE']
        # )
        # bucket_name = current_app.config['MINIO_BUCKET_NAME']
        # ...
        raise NotImplementedError('MinIO 上传功能尚未实现')
    
    @classmethod
    def get_minio_url(cls, stored_filename: str, expires: int = 3600) -> str:
        """
        获取 MinIO 预签名 URL
        
        参数:
            stored_filename: 存储文件名
            expires: URL 过期时间（秒）
            
        返回:
            预签名 URL
            
        注意:
            此方法需要安装 minio 库
        """
        # TODO: 实现 MinIO 预签名 URL 生成
        raise NotImplementedError('MinIO 功能尚未实现')
