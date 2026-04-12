"""
表单提交记录模型
用于存储通过表单分享提交的数据记录
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class FormSubmission(db.Model):
    """
    表单提交记录表
    
    属性:
        id: UUID 主键
        form_share_id: 关联的表单分享 ID
        record_id: 创建的记录 ID
        submitter_ip: 提交者 IP 地址
        submitter_user_agent: 提交者 User-Agent
        submitter_info: 提交者信息（如邮箱、姓名等，JSON）
        submitted_at: 提交时间
    """
    
    __tablename__ = 'form_submissions'
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    
    # 关联的表单分享 ID
    form_share_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey('form_shares.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # 创建的记录 ID
    record_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey('records.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    
    # 提交者 IP 地址
    submitter_ip: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        comment='支持 IPv6 地址'
    )
    
    # 提交者 User-Agent
    submitter_user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # 提交者信息（如邮箱、姓名等）
    submitter_info: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment='JSON格式，包含邮箱、姓名等提交者信息'
    )
    
    # 提交时间
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    
    # 关联关系
    form_share = relationship('FormShare', back_populates='submissions')
    record = relationship('Record')
    
    def get_submitter_info_dict(self) -> Dict[str, Any]:
        """获取提交者信息字典"""
        if not self.submitter_info:
            return {}
        import json
        try:
            return json.loads(self.submitter_info)
        except json.JSONDecodeError:
            return {}
    
    def set_submitter_info_dict(self, info: Dict[str, Any]) -> None:
        """设置提交者信息"""
        import json
        self.submitter_info = json.dumps(info)
    
    def to_dict(self, include_record: bool = False) -> dict:
        """转换为字典"""
        data = {
            'id': str(self.id),
            'form_share_id': str(self.form_share_id),
            'record_id': str(self.record_id) if self.record_id else None,
            'submitter_ip': self.submitter_ip,
            'submitter_user_agent': self.submitter_user_agent,
            'submitter_info': self.get_submitter_info_dict(),
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None
        }
        
        if include_record and self.record:
            data['record'] = self.record.to_dict()
        
        return data
    
    def __repr__(self) -> str:
        return f'<FormSubmission {self.id}>'
