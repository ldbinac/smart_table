"""
文档业务服务模块
提供文档的 CRUD 操作
"""
from app.extensions import db
from app.models.document import Document
from app.services.document_version_service import DocumentVersionService


document_version_service = DocumentVersionService()


class DocumentService:
    """文档服务类"""

    def get_by_id(self, doc_id: str) -> Document | None:
        """根据 ID 获取文档"""
        return db.session.query(Document).filter_by(id=doc_id).first()

    def get_list_by_base(self, base_id: str) -> list[Document]:
        """获取 Base 下的所有文档"""
        return db.session.query(Document).filter_by(base_id=base_id).order_by(Document.order.asc()).all()

    def get_count_by_base(self, base_id: str) -> int:
        """获取 Base 下的文档数量"""
        return db.session.query(Document).filter_by(base_id=base_id).count()

    def create(self, base_id: str, name: str, content: str = '', content_format: str = 'delta',
               created_by: str | None = None) -> Document:
        """创建新文档"""
        count = self.get_count_by_base(base_id)
        doc = Document(
            base_id=base_id,
            name=name,
            content=content,
            content_format=content_format,
            order=count,
            created_by=created_by,
            updated_by=created_by
        )
        db.session.add(doc)
        db.session.commit()

        # 创建初始版本
        document_version_service.create_version(
            document_id=doc.id,
            name='初始版本',
            content=content,
            content_format=content_format,
            user_id=created_by,
            change_summary='创建文档'
        )

        return doc

    def update(self, doc_id: str, user_id: str | None = None, **kwargs) -> Document:
        """更新文档"""
        doc = self.get_by_id(doc_id)
        if not doc:
            raise ValueError('Document not found')

        # 记录旧值用于版本判断
        old_name = doc.name
        old_content = doc.content

        for key, value in kwargs.items():
            if hasattr(doc, key):
                setattr(doc, key, value)

        if user_id:
            doc.updated_by = user_id

        db.session.commit()

        # 检查是否需要创建新版本
        new_name = kwargs.get('name', old_name)
        new_content = kwargs.get('content', old_content)

        should_version, change_summary = document_version_service.should_create_version(
            document_id=doc_id,
            new_content=new_content,
            old_content=old_content,
            new_name=new_name,
            old_name=old_name
        )

        if should_version:
            document_version_service.create_version(
                document_id=doc_id,
                name=f'版本 {new_name}',
                content=new_content,
                content_format=doc.content_format,
                user_id=user_id,
                change_summary=change_summary
            )

        return doc

    def delete(self, doc_id: str) -> None:
        """删除文档"""
        doc = self.get_by_id(doc_id)
        if not doc:
            raise ValueError('Document not found')
        db.session.delete(doc)
        db.session.commit()
