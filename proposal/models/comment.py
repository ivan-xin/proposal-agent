from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import json

@dataclass
class Comment:
    """
    评论数据模型
    
    表示对提案的一条评论，包含评论内容、作者和元数据
    """
    
    # 关联信息
    proposal_id: str
    commenter_id: str
    
    # 评论内容
    content: str
    sentiment: str = "neutral"  # positive, negative, neutral, mixed
    
    # 系统字段
    comment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    
    # 附加信息
    parent_id: Optional[str] = None  # 用于回复其他评论
    is_official: bool = False  # 标记是否为官方评论
    
    # 附加数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_reply(self) -> bool:
        """检查是否为回复评论"""
        return self.parent_id is not None
    
    def is_positive(self) -> bool:
        """检查是否为积极评论"""
        return self.sentiment.lower() == "positive"
    
    def is_negative(self) -> bool:
        """检查是否为消极评论"""
        return self.sentiment.lower() == "negative"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典表示
        
        Returns:
            包含所有评论数据的字典
        """
        return {
            "comment_id": self.comment_id,
            "proposal_id": self.proposal_id,
            "commenter_id": self.commenter_id,
            "content": self.content,
            "sentiment": self.sentiment,
            "created_at": self.created_at.isoformat(),
            "parent_id": self.parent_id,
            "is_official": self.is_official,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """
        转换为JSON字符串
        
        Returns:
            JSON格式的评论数据
        """
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Comment':
        """
        从字典创建评论实例
        
        Args:
            data: 包含评论数据的字典
            
        Returns:
            评论实例
        """
        # 处理日期时间字段
        created_at = datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"]
        
        return cls(
            comment_id=data["comment_id"],
            proposal_id=data["proposal_id"],
            commenter_id=data["commenter_id"],
            content=data["content"],
            sentiment=data.get("sentiment", "neutral"),
            created_at=created_at,
            parent_id=data.get("parent_id"),
            is_official=data.get("is_official", False),
            metadata=data.get("metadata", {})
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Comment':
        """
        从JSON字符串创建评论实例
        
        Args:
            json_str: JSON格式的评论数据
            
        Returns:
            评论实例
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @staticmethod
    def validate_sentiment(sentiment: str) -> bool:
        """
        验证情感类型是否有效
        
        Args:
            sentiment: 情感类型
            
        Returns:
            是否有效
        """
        valid_sentiments = ["positive", "negative", "neutral", "mixed"]
        return sentiment.lower() in valid_sentiments