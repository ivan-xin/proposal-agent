from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json

@dataclass
class Proposal:
    """
    提案数据模型
    
    表示一个完整的提案，包含标题、内容、创建者、状态、投票和元数据等信息
    """
    
    # 基本信息
    title: str
    content: str
    creator_id: str
    
    # 系统字段
    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    # 提案状态
    status: str = "open"  # open, closed, approved, rejected
    
    # 分类和标签
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    
    # 统计数据
    vote_count: Dict[str, int] = field(default_factory=lambda: {"support": 0, "oppose": 0})
    comment_count: int = 0
    
    # 附加数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update(self, **kwargs) -> None:
        """
        更新提案属性
        
        Args:
            **kwargs: 要更新的字段和值
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        self.updated_at = datetime.now()
    
    def add_vote(self, vote_type: str) -> None:
        """
        添加投票计数
        
        Args:
            vote_type: 投票类型 ('support' 或 'oppose')
        """
        if vote_type in self.vote_count:
            self.vote_count[vote_type] += 1
        else:
            self.vote_count[vote_type] = 1
    
    def increment_comment_count(self) -> None:
        """增加评论计数"""
        self.comment_count += 1
    
    def is_open(self) -> bool:
        """检查提案是否处于开放状态"""
        return self.status == "open"
    
    def close(self, final_status: str = "closed") -> None:
        """
        关闭提案
        
        Args:
            final_status: 最终状态 ('closed', 'approved', 'rejected')
        """
        valid_statuses = ["closed", "approved", "rejected"]
        self.status = final_status if final_status in valid_statuses else "closed"
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典表示
        
        Returns:
            包含所有提案数据的字典
        """
        return {
            "proposal_id": self.proposal_id,
            "title": self.title,
            "content": self.content,
            "creator_id": self.creator_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "status": self.status,
            "tags": self.tags,
            "categories": self.categories,
            "vote_count": self.vote_count,
            "comment_count": self.comment_count,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """
        转换为JSON字符串
        
        Returns:
            JSON格式的提案数据
        """
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Proposal':
        """
        从字典创建提案实例
        
        Args:
            data: 包含提案数据的字典
            
        Returns:
            提案实例
        """
        # 处理日期时间字段
        created_at = datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"]
        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"]) if isinstance(data["updated_at"], str) else data["updated_at"]
        
        return cls(
            proposal_id=data["proposal_id"],
            title=data["title"],
            content=data["content"],
            creator_id=data["creator_id"],
            created_at=created_at,
            updated_at=updated_at,
            status=data["status"],
            tags=data.get("tags", []),
            categories=data.get("categories", []),
            vote_count=data.get("vote_count", {"support": 0, "oppose": 0}),
            comment_count=data.get("comment_count", 0),
            metadata=data.get("metadata", {})
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Proposal':
        """
        从JSON字符串创建提案实例
        
        Args:
            json_str: JSON格式的提案数据
            
        Returns:
            提案实例
        """
        data = json.loads(json_str)
        return cls.from_dict(data)