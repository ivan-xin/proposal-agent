"""
MCP协议定义 - 定义代理系统间通信的消息格式和协议规范
"""

from enum import Enum
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
import json
import uuid
from datetime import datetime

class MessageType(str, Enum):
    """MCP消息类型枚举"""
    # 系统消息
    REGISTER = "register"           # 代理注册
    HEARTBEAT = "heartbeat"         # 心跳检测
    ERROR = "error"                 # 错误消息
    
    # 提案相关消息
    PROPOSAL_CREATE = "proposal.create"     # 创建提案
    PROPOSAL_LIST = "proposal.list"         # 列出提案
    PROPOSAL_GET = "proposal.get"           # 获取提案详情
    PROPOSAL_UPDATE = "proposal.update"     # 更新提案
    PROPOSAL_CLOSE = "proposal.close"       # 关闭提案
    
    # 投票相关消息
    VOTE_CAST = "vote.cast"                 # 投票
    VOTE_LIST = "vote.list"                 # 获取投票列表
    
    # 评论相关消息
    COMMENT_ADD = "comment.add"             # 添加评论
    COMMENT_LIST = "comment.list"           # 获取评论列表
    
    # 分析相关消息
    ANALYZE_PROPOSAL = "analyze.proposal"   # 分析提案
    ANALYZE_VOTE = "analyze.vote"           # 分析投票决策
    
    # 通用查询消息
    QUERY = "query"                         # 通用查询
    
    # 通知消息
    NOTIFICATION = "notification"           # 通知消息


@dataclass
class MCPMessage:
    """MCP消息数据结构"""
    
    # 消息元数据
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: str = MessageType.QUERY.value
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # 消息来源和目标
    source_agent: str = "unknown"
    target_agent: Optional[str] = None  # None表示广播消息
    
    # 消息内容
    payload: Dict[str, Any] = field(default_factory=dict)
    
    # 消息控制
    correlation_id: Optional[str] = None  # 用于关联请求和响应
    reply_to: Optional[str] = None        # 回复地址
    ttl: int = 60                         # 生存时间(秒)
    
    # 安全相关
    auth_token: Optional[str] = None      # 认证令牌
    signature: Optional[str] = None       # 消息签名
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type,
            "timestamp": self.timestamp,
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
            "ttl": self.ttl,
            "auth_token": self.auth_token,
            "signature": self.signature
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPMessage':
        """从字典创建消息实例"""
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            message_type=data.get("message_type", MessageType.QUERY.value),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            source_agent=data.get("source_agent", "unknown"),
            target_agent=data.get("target_agent"),
            payload=data.get("payload", {}),
            correlation_id=data.get("correlation_id"),
            reply_to=data.get("reply_to"),
            ttl=data.get("ttl", 60),
            auth_token=data.get("auth_token"),
            signature=data.get("signature")
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MCPMessage':
        """从JSON字符串创建消息实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def create_response(self, payload: Dict[str, Any]) -> 'MCPMessage':
        """创建对此消息的响应消息"""
        return MCPMessage(
            message_type=f"{self.message_type}.response",
            source_agent=self.target_agent or "system",
            target_agent=self.source_agent,
            payload=payload,
            correlation_id=self.message_id,
            reply_to=self.reply_to
        )
    
    def create_error_response(self, error_code: str, error_message: str) -> 'MCPMessage':
        """创建错误响应消息"""
        return MCPMessage(
            message_type=MessageType.ERROR.value,
            source_agent=self.target_agent or "system",
            target_agent=self.source_agent,
            payload={
                "error_code": error_code,
                "error_message": error_message,
                "original_message_type": self.message_type
            },
            correlation_id=self.message_id,
            reply_to=self.reply_to
        )


def validate_message(message: MCPMessage) -> bool:
    """
    验证MCP消息是否有效
    
    Args:
        message: 要验证的消息
        
    Returns:
        消息是否有效
    """
    # 基本验证
    if not message.message_id or not message.message_type:
        return False
    
    # 验证消息类型
    try:
        MessageType(message.message_type)
    except ValueError:
        # 允许自定义消息类型，只要它们包含一个点(如"domain.action")
        if '.' not in message.message_type and not message.message_type.endswith('.response'):
            return False
    
    # 验证时间戳
    try:
        datetime.fromisoformat(message.timestamp)
    except ValueError:
        return False
    
    # 验证TTL
    if not isinstance(message.ttl, int) or message.ttl <= 0:
        return False
    
    return True
