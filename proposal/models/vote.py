from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import json


@dataclass
class Vote:
    """
    投票数据模型
    
    表示对提案的一次投票，包含投票类型、投票人和元数据
    """
    
    # 关联信息
    proposal_id: str
    voter_id: str
    
    # 投票内容
    vote_type: str  # "support", "oppose", "abstain"
    
    # 可选的投票理由
    reason: Optional[str] = None
    
    # 系统字段
    vote_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    
    # 附加信息
    weight: float = 1.0  # 投票权重，默认为1
    is_official: bool = False  # 标记是否为官方投票
    
    # 附加数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_support(self) -> bool:
        """检查是否为支持票"""
        return self.vote_type.lower() == "support"
    
    def is_oppose(self) -> bool:
        """检查是否为反对票"""
        return self.vote_type.lower() == "oppose"
    
    def is_abstain(self) -> bool:
        """检查是否为弃权票"""
        return self.vote_type.lower() == "abstain"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典表示
        
        Returns:
            包含所有投票数据的字典
        """
        return {
            "vote_id": self.vote_id,
            "proposal_id": self.proposal_id,
            "voter_id": self.voter_id,
            "vote_type": self.vote_type,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
            "weight": self.weight,
            "is_official": self.is_official,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """
        转换为JSON字符串
        
        Returns:
            JSON格式的投票数据
        """
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Vote':
        """
        从字典创建投票实例
        
        Args:
            data: 包含投票数据的字典
            
        Returns:
            投票实例
        """
        # 处理日期时间字段
        created_at = datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"]
        
        return cls(
            vote_id=data["vote_id"],
            proposal_id=data["proposal_id"],
            voter_id=data["voter_id"],
            vote_type=data["vote_type"],
            reason=data.get("reason"),
            created_at=created_at,
            weight=data.get("weight", 1.0),
            is_official=data.get("is_official", False),
            metadata=data.get("metadata", {})
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Vote':
        """
        从JSON字符串创建投票实例
        
        Args:
            json_str: JSON格式的投票数据
            
        Returns:
            投票实例
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @staticmethod
    def validate_vote_type(vote_type: str) -> bool:
        """
        验证投票类型是否有效
        
        Args:
            vote_type: 投票类型
            
        Returns:
            是否有效
        """
        valid_vote_types = ["support", "oppose", "abstain"]
        return vote_type.lower() in valid_vote_types