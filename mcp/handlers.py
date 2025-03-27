"""
消息处理器 - 处理不同类型的MCP消息
"""

from typing import Dict, Any, Optional, List, Callable, Awaitable
import logging
import asyncio
import json

from .protocol import MCPMessage, MessageType

logger = logging.getLogger(__name__)

# 消息处理器类型
MessageHandler = Callable[[MCPMessage], Awaitable[MCPMessage]]

class MessageHandlerRegistry:
    """消息处理器注册中心"""
    
    def __init__(self):
        """初始化处理器注册中心"""
        self.handlers: Dict[str, MessageHandler] = {}
        self.default_handler: Optional[MessageHandler] = None
    
    def register(self, message_type: str, handler: MessageHandler):
        """
        注册消息处理器
        
        Args:
            message_type: 消息类型
            handler: 处理函数
        """
        self.handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type}")
    
    def register_default(self, handler: MessageHandler):
        """
        注册默认处理器
        
        Args:
            handler: 默认处理函数
        """
        self.default_handler = handler
        logger.info("Registered default message handler")
    
    async def handle(self, message: MCPMessage) -> MCPMessage:
        """
        处理消息
        
        Args:
            message: 要处理的消息
            
        Returns:
            处理结果
        """
        handler = self.handlers.get(message.message_type)
        
        if handler:
            try:
                return await handler(message)
            except Exception as e:
                logger.exception(f"Error in message handler: {str(e)}")
                return message.create_error_response(
                    "handler_error", 
                    f"Error in message handler: {str(e)}"
                )
        elif self.default_handler:
            try:
                return await self.default_handler(message)
            except Exception as e:
                logger.exception(f"Error in default handler: {str(e)}")
                return message.create_error_response(
                    "handler_error", 
                    f"Error in default handler: {str(e)}"
                )
        else:
            return message.create_error_response(
                "unknown_message_type", 
                f"No handler registered for message type: {message.message_type}"
            )


# 系统消息处理器
async def handle_system_error(message: MCPMessage) -> MCPMessage:
    """处理系统错误消息"""
    # 记录错误
    error_code = message.payload.get("error_code", "unknown_error")
    error_message = message.payload.get("error_message", "Unknown error")
    logger.error(f"System error: [{error_code}] {error_message}")
    
    # 返回确认
    return message.create_response({
        "status": "error_acknowledged",
        "error_code": error_code
    })

# 创建默认处理器
async def default_message_handler(message: MCPMessage) -> MCPMessage:
    """默认消息处理器"""
    logger.warning(f"Using default handler for message type: {message.message_type}")
    
    return message.create_response({
        "status": "received",
        "message": "Message received, but no specific handler available",
        "original_type": message.message_type
    })
