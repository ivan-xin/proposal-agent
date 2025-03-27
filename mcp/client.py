"""
MCP客户端 - 用于向其他代理发送消息
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional, List, Union
import json
import time

from .protocol import MCPMessage, MessageType, validate_message

logger = logging.getLogger(__name__)

class MCPClient:
    """MCP客户端，用于向其他代理发送请求"""
    
    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None):
        """
        初始化MCP客户端
        
        Args:
            agent_id: 当前代理的ID
            config: 配置字典
        """
        self.agent_id = agent_id
        self.config = config or {}
        
        # 配置HTTP会话
        self.session = None
        self.base_url = self.config.get("base_url", "http://localhost:8000/mcp")
        
        # 响应缓存
        self.response_cache = {}
        
        # 认证信息
        self.auth_token = self.config.get("auth_token")
        
        # 重试配置
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 1.0)
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def ensure_session(self):
        """确保HTTP会话已创建"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def send_message(self, 
                          message_type: Union[str, MessageType], 
                          payload: Dict[str, Any],
                          target_agent: Optional[str] = None,
                          timeout: float = 30.0) -> MCPMessage:
        """
        向目标代理发送消息
        
        Args:
            message_type: 消息类型
            payload: 消息内容
            target_agent: 目标代理ID
            timeout: 超时时间(秒)
            
        Returns:
            目标代理的响应消息
        """
        # 确保会话已创建
        await self.ensure_session()
        
        # 创建消息
        if isinstance(message_type, MessageType):
            message_type = message_type.value
            
        message = MCPMessage(
            message_type=message_type,
            source_agent=self.agent_id,
            target_agent=target_agent,
            payload=payload,
            auth_token=self.auth_token
        )
        
        # 验证消息
        if not validate_message(message):
            raise ValueError("Invalid message format")
        
        # 发送消息
        for attempt in range(self.max_retries):
            try:
                async with self.session.post(
                    f"{self.base_url}/message",
                    json=message.to_dict(),
                    timeout=timeout
                ) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        return MCPMessage.from_dict(response_data)
                    else:
                        error_text = await response.text()
                        logger.error(f"Error sending message: {response.status} - {error_text}")
                        
                        # 如果是最后一次尝试，创建错误响应
                        if attempt == self.max_retries - 1:
                            return message.create_error_response(
                                f"http_{response.status}", 
                                f"HTTP error: {response.status} - {error_text}"
                            )
            except asyncio.TimeoutError:
                logger.warning(f"Timeout sending message (attempt {attempt+1}/{self.max_retries})")
                # 如果是最后一次尝试，创建超时错误响应
                if attempt == self.max_retries - 1:
                    return message.create_error_response(
                        "timeout", 
                        f"Request timed out after {timeout} seconds"
                    )
            except Exception as e:
                logger.error(f"Error sending message: {str(e)}")
                # 如果是最后一次尝试，创建一般错误响应
                if attempt == self.max_retries - 1:
                    return message.create_error_response(
                        "client_error", 
                        f"Client error: {str(e)}"
                    )
            
            # 重试前等待
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))
    
    async def broadcast(self, 
                       message_type: Union[str, MessageType], 
                       payload: Dict[str, Any],
                       agent_filter: Optional[List[str]] = None,
                       timeout: float = 30.0) -> Dict[str, MCPMessage]:
        """
        向多个代理广播消息
        
        Args:
            message_type: 消息类型
            payload: 消息内容
            agent_filter: 代理ID列表，None表示所有已注册的代理
            timeout: 超时时间(秒)
            
        Returns:
            各代理响应的字典，键为代理ID
        """
        # 确保会话已创建
        await self.ensure_session()
        
        # 创建广播消息
        if isinstance(message_type, MessageType):
            message_type = message_type.value
            
        message = MCPMessage(
            message_type=message_type,
            source_agent=self.agent_id,
            target_agent=None,  # 广播消息
            payload=payload,
            auth_token=self.auth_token
        )
        
        # 验证消息
        if not validate_message(message):
            raise ValueError("Invalid message format")
        
        # 发送广播请求
        try:
            request_data = {
                "message": message.to_dict(),
                "filter": agent_filter
            }
            
            async with self.session.post(
                f"{self.base_url}/broadcast",
                json=request_data,
                timeout=timeout
            ) as response:
                if response.status == 200:
                    response_data = await response.json()
                    
                    # 解析各代理的响应
                    results = {}
                    for agent_id, msg_data in response_data.items():
                        results[agent_id] = MCPMessage.from_dict(msg_data)
                    
                    return results
                else:
                    error_text = await response.text()
                    logger.error(f"Error broadcasting message: {response.status} - {error_text}")
                    
                    # 返回错误响应
                    return {
                        "error": message.create_error_response(
                            f"http_{response.status}", 
                            f"HTTP error: {response.status} - {error_text}"
                        )
                    }
        except Exception as e:
                logger.error(f"Error broadcasting message: {str(e)}")
                return {
                    "error": message.create_error_response(
                        "client_error", 
                        f"Client error: {str(e)}"
                    )
                }
                    
    async def query_agent_status(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        查询代理状态
        
        Args:
            agent_id: 要查询的代理ID，None表示查询所有代理
            
        Returns:
            代理状态信息
        """
        payload = {}
        if agent_id:
            payload["agent_id"] = agent_id
        
        response = await self.send_message(
            MessageType.HEARTBEAT,
            payload=payload
        )
        
        return response.payload
                    
    async def register_agent(self, capabilities: List[str], metadata: Dict[str, Any] = None) -> bool:
        """
        注册当前代理到MCP系统
        
        Args:
            capabilities: 代理能力列表
            metadata: 代理元数据
            
        Returns:
            注册是否成功
        """
        payload = {
            "agent_id": self.agent_id,
            "capabilities": capabilities,
            "metadata": metadata or {}
        }
        
        response = await self.send_message(
            MessageType.REGISTER,
            payload=payload
        )
        
        return response.payload.get("success", False)
