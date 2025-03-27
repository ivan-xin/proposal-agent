"""
MCP适配器 - 适配不同代理系统的接口
"""

from typing import Dict, Any, Optional, List, Callable, Awaitable, Union, TypeVar, Generic
import logging
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime 

from .protocol import MCPMessage, MessageType
from .client import MCPClient

logger = logging.getLogger(__name__)

# 定义泛型类型变量
T = TypeVar('T')
R = TypeVar('R')

class MCPAdapter(Generic[T, R], ABC):
    """
    MCP适配器基类
    
    用于将特定代理系统的请求转换为MCP消息，并将MCP响应转换回代理系统的格式
    """
    
    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None):
        """
        初始化MCP适配器
        
        Args:
            agent_id: 代理ID
            config: 配置字典
        """
        self.agent_id = agent_id
        self.config = config or {}
        self.client = MCPClient(agent_id, config)
        
        # 注册处理器映射
        self.handlers: Dict[str, Callable[[T], Awaitable[R]]] = {}
    
    @abstractmethod
    async def convert_to_mcp(self, request: T) -> MCPMessage:
        """
        将代理请求转换为MCP消息
        
        Args:
            request: 代理系统的请求
            
        Returns:
            转换后的MCP消息
        """
        pass
    
    @abstractmethod
    async def convert_from_mcp(self, message: MCPMessage) -> R:
        """
        将MCP消息转换为代理响应
        
        Args:
            message: MCP消息
            
        Returns:
            转换后的代理响应
        """
        pass
    
    async def process_request(self, request: T) -> R:
        """
        处理代理请求
        
        Args:
            request: 代理系统的请求
            
        Returns:
            处理结果
        """
        try:
            # 转换为MCP消息
            mcp_message = await self.convert_to_mcp(request)
            
            # 发送消息
            async with self.client:
                response = await self.client.send_message(
                    mcp_message.message_type,
                    mcp_message.payload,
                    mcp_message.target_agent
                )
            
            # 转换响应
            return await self.convert_from_mcp(response)
        except Exception as e:
            logger.exception(f"Error processing request: {str(e)}")
            # 创建错误响应
            return await self.create_error_response(str(e))
    
    @abstractmethod
    async def create_error_response(self, error_message: str) -> R:
        """
        创建错误响应
        
        Args:
            error_message: 错误消息
            
        Returns:
            错误响应
        """
        pass
    
    def register_handler(self, message_type: Union[str, MessageType], 
                        handler: Callable[[T], Awaitable[R]]):
        """
        注册消息处理器
        
        Args:
            message_type: 消息类型
            handler: 处理函数
        """
        if isinstance(message_type, MessageType):
            message_type = message_type.value
            
        self.handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type}")
    
    async def handle_message(self, message: MCPMessage) -> MCPMessage:
        """
        处理接收到的MCP消息
        
        Args:
            message: 接收到的MCP消息
            
        Returns:
            处理结果
        """
        # 查找处理器
        handler = self.handlers.get(message.message_type)
        if handler:
            try:
                # 转换为代理请求
                request = await self.convert_from_mcp(message)
                
                # 调用处理器
                response = await handler(request)
                
                # 转换为MCP响应
                return await self.convert_to_mcp(response)
            except Exception as e:
                logger.exception(f"Error handling message: {str(e)}")
                return message.create_error_response(
                    "handler_error", 
                    f"Error handling message: {str(e)}"
                )
        else:
            # 如果没有找到处理器，返回错误
            return message.create_error_response(
                "unknown_message_type", 
                f"No handler registered for message type: {message.message_type}"
            )


class JSONAdapter(MCPAdapter[Dict[str, Any], Dict[str, Any]]):
    """
    JSON适配器
    
    用于处理JSON格式的请求和响应
    """
    
    async def convert_to_mcp(self, request: Dict[str, Any]) -> MCPMessage:
        """将JSON请求转换为MCP消息"""
        message_type = request.get("type", MessageType.QUERY.value)
        target_agent = request.get("target")
        payload = request.get("data", {})
        
        return MCPMessage(
            message_type=message_type,
            source_agent=self.agent_id,
            target_agent=target_agent,
            payload=payload
        )
    
    async def convert_from_mcp(self, message: MCPMessage) -> Dict[str, Any]:
        """将MCP消息转换为JSON响应"""
        return {
            "type": message.message_type,
            "source": message.source_agent,
            "data": message.payload,
            "message_id": message.message_id,
            "timestamp": message.timestamp
        }
    
    async def create_error_response(self, error_message: str) -> Dict[str, Any]:
        """创建JSON错误响应"""
        return {
            "type": "error",
            "source": self.agent_id,
            "data": {
                "error": error_message
            },
            "timestamp": datetime.now().isoformat()
        }
