"""
文档版本历史服务模块
提供文档版本的创建、查询、恢复、清理功能
"""
from datetime import datetime, timezone, timedelta

from app.extensions import db
from app.models.document_version import DocumentVersion


class DocumentVersionService:
    """文档版本服务类"""

    # 版本保留配置
    MAX_VERSIONS = 50  # 最多保留 50 个版本
    RETENTION_DAYS = 30  # 保留最近 30 天

    # 重大变更阈值
    CONTENT_CHANGE_THRESHOLD = 100  # 内容变化超过 100 个字符
    CONTENT_CHANGE_RATIO = 0.2  # 内容变化超过 20%
    MIN_INTERVAL_MINUTES = 60  # 两次版本创建间隔至少 60 分钟

    def get_list_by_document(self, document_id: str) -> list[DocumentVersion]:
        """获取文档的版本列表"""
        return db.session.query(DocumentVersion).filter_by(
            document_id=document_id
        ).order_by(DocumentVersion.version_number.desc()).all()

    def get_by_id(self, version_id: str) -> DocumentVersion | None:
        """根据 ID 获取版本"""
        return db.session.query(DocumentVersion).filter_by(id=version_id).first()

    def get_latest_version(self, document_id: str) -> DocumentVersion | None:
        """获取文档的最新版本"""
        return db.session.query(DocumentVersion).filter_by(
            document_id=document_id
        ).order_by(DocumentVersion.version_number.desc()).first()

    def get_version_count(self, document_id: str) -> int:
        """获取文档的版本数量"""
        return db.session.query(DocumentVersion).filter_by(document_id=document_id).count()

    def create_version(self, document_id: str, name: str, content: str,
                       content_format: str = 'delta', user_id: str | None = None,
                       change_summary: str | None = None) -> DocumentVersion:
        """创建新版本"""
        # 获取下一个版本号
        latest = self.get_latest_version(document_id)
        version_number = (latest.version_number + 1) if latest else 1

        version = DocumentVersion(
            document_id=document_id,
            name=name,
            content=content,
            content_format=content_format,
            version_number=version_number,
            change_summary=change_summary,
            created_by=user_id
        )
        db.session.add(version)
        db.session.commit()

        # 清理旧版本
        self._cleanup_old_versions(document_id)

        return version

    def should_create_version(self, document_id: str, new_content: str,
                               old_content: str = '', new_name: str = '',
                               old_name: str = '') -> tuple[bool, str]:
        """
        判断是否应该创建新版本

        返回: (是否应该创建, 变更摘要)
        """
        # 名称变更
        if new_name != old_name and old_name:
            return True, f'文档名称从 "{old_name}" 改为 "{new_name}"'

        # 内容长度变化
        old_len = len(old_content)
        new_len = len(new_content)

        if old_len == 0:
            # 首次保存
            return True, '创建文档'

        # 计算变化量
        change_size = abs(new_len - old_len)
        change_ratio = change_size / old_len if old_len > 0 else 1.0

        # 检查是否超过阈值
        if change_size >= self.CONTENT_CHANGE_THRESHOLD:
            return True, f'内容变化 {change_size} 个字符'

        if change_ratio >= self.CONTENT_CHANGE_RATIO:
            return True, f'内容变化 {change_ratio:.0%}'

        # 检查时间间隔
        latest = self.get_latest_version(document_id)
        if latest:
            time_diff = datetime.now(timezone.utc) - latest.created_at
            if time_diff >= timedelta(minutes=self.MIN_INTERVAL_MINUTES):
                return True, '定时自动保存'

        return False, ''

    def restore_version(self, version_id: str, user_id: str | None = None) -> DocumentVersion:
        """
        恢复到指定版本

        恢复时会创建一个新版本，内容为被恢复版本的内容
        """
        version = self.get_by_id(version_id)
        if not version:
            raise ValueError('Version not found')

        # 创建恢复版本
        restored = self.create_version(
            document_id=version.document_id,
            name=f'恢复到版本 #{version.version_number}',
            content=version.content,
            content_format=version.content_format,
            user_id=user_id,
            change_summary=f'从版本 #{version.version_number} 恢复'
        )

        return restored

    def delete_version(self, version_id: str) -> None:
        """删除版本"""
        version = self.get_by_id(version_id)
        if not version:
            raise ValueError('Version not found')
        db.session.delete(version)
        db.session.commit()

    def _cleanup_old_versions(self, document_id: str) -> None:
        """清理旧版本"""
        versions = db.session.query(DocumentVersion).filter_by(
            document_id=document_id
        ).order_by(DocumentVersion.version_number.desc()).all()

        if len(versions) <= self.MAX_VERSIONS:
            return

        # 计算保留截止日期
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.RETENTION_DAYS)

        # 保留策略：
        # 1. 保留最近 MAX_VERSIONS 个版本
        # 2. 保留最近 RETENTION_DAYS 天内的版本
        versions_to_keep = set()

        # 保留最近的 MAX_VERSIONS 个
        for v in versions[:self.MAX_VERSIONS]:
            versions_to_keep.add(v.id)

        # 保留最近 RETENTION_DAYS 天内的
        for v in versions:
            if v.created_at >= cutoff_date:
                versions_to_keep.add(v.id)

        # 删除不需要保留的版本
        for v in versions:
            if v.id not in versions_to_keep:
                db.session.delete(v)

        db.session.commit()
