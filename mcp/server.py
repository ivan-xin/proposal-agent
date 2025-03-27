"""
MCP服务器 - 接收和处理来自其他代理的请求
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable, Awaitable, Union
import json
import time
from datetime import datetime
from aiohttp import web
import uuid

from .protocol import MCPMessage, MessageType, validate_message
from .registry import AgentRegistry

logger = logging.getLogger(__name__)

# 消息处理器类型
MessageHandler = Callable[[MCPMessage], Awaitable[MCPMessage]]

class MCPServer:
    """MCP服务器，用于接收和处理来自其他代理的请求"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化MCP服务器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.handlers: Dict[str, MessageHandler] = {}
        self.registry = AgentRegistry()
        
        # 创建应用
        self.app = web.Application()
        self.setup_routes()
        
        # 消息统计
        self.message_count = 0
        self.start_time = datetime.now()
        
        # 安全配置
        self.require_auth = self.config.get("require_auth", False)
        self.auth_tokens = self.config.get("auth_tokens", {})
    
    def setup_routes(self):
        """设置路由"""
        self.app.router.add_post("/mcp/message", self.handle_message_request)
        self.app.router.add_post("/mcp/broadcast", self.handle_broadcast_request)
        self.app.router.add_get("/mcp/status", self.handle_status_request)
    
    def register_handler(self, message_type: Union[str, MessageType], handler: MessageHandler):
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
    
    def register_default_handlers(self):
        """注册默认的系统消息处理器"""
        self.register_handler(MessageType.REGISTER, self.handle_register)
        self.register_handler(MessageType.HEARTBEAT, self.handle_heartbeat)
    
    async def handle_register(self, message: MCPMessage) -> MCPMessage:
        """处理代理注册消息"""
        payload = message.payload
        agent_id = payload.get("agent_id")
        capabilities = payload.get("capabilities", [])
        metadata = payload.get("metadata", {})
        
        if not agent_id:
            return message.create_error_response(
                "invalid_request", 
                "Missing agent_id in registration request"
            )
        
        # 注册代理
        self.registry.register_agent(agent_id, capabilities, metadata)
        
        return message.create_response({
            "status": "registered",
            "agent_id": agent_id,
            "registered_at": datetime.now().isoformat()
        })
    
    async def handle_heartbeat(self, message: MCPMessage) -> MCPMessage:
        """处理心跳检测消息"""
        agent_id = message.payload.get("agent_id")
        
        if agent_id:
            # 查询特定代理
            agent_info = self.registry.get_agent(agent_id)
            if not agent_info:
                return message.create_error_response(
                    "agent_not_found", 
                    f"Agent {agent_id} not found"
                )
            
            return message.create_response({
                "agent_id": agent_id,
                "status": "active" if agent_info.get("active", False) else "inactive",
                "last_seen": agent_info.get("last_seen"),
                "capabilities": agent_info.get("capabilities", [])
            })
        else:
            # 查询所有代理
            agents = self.registry.list_agents()
            return message.create_response({
                "agents": agents,
                "count": len(agents),
                "server_uptime": (datetime.now() - self.start_time).total_seconds()
            })
    
    async def process_message(self, message: MCPMessage) -> MCPMessage:
        """
        处理接收到的消息
        
        Args:
            message: 接收到的MCP消息
            
        Returns:
            处理结果
        """
        # 验证消息
        if not validate_message(message):
            return MCPMessage(
                message_type=MessageType.ERROR.value,
                source_agent="system",
                target_agent=message.source_agent,
                payload={
                    "error_code": "invalid_message",
                    "error_message": "Message validation failed"
                }
            )
        
        # 验证认证
        if self.require_auth and message.message_type != MessageType.REGISTER.value:
            if not message.auth_token or message.auth_token not in self.auth_tokens.values():
                return message.create_error_response(
                    "unauthorized", 
                    "Invalid or missing authentication token"
                )
        
        # 更新消息计数
        self.message_count += 1
        
        # 查找处理器
        handler = self.handlers.get(message.message_type)
        if handler:
            try:
                # 调用处理器
                response = await handler(message)
                return response
            except Exception as e:
                logger.exception(f"Error processing message: {str(e)}")
                return message.create_error_response(
                    "handler_error", 
                    f"Error processing message: {str(e)}"
                )
        else:
            # 如果没有找到处理器，返回错误
            return message.create_error_response(
                "unknown_message_type", 
                f"No handler registered for message type: {message.message_type}"
            )
    
    async def handle_message_request(self, request: web.Request) -> web.Response:
        """处理HTTP消息请求"""
        try:
            # 解析请求
            data = await request.json()
            message = MCPMessage.from_dict(data)
            
            # 处理消息
            response = await self.process_message(message)
            
            # 返回响应
            return web.json_response(response.to_dict())
        except json.JSONDecodeError:
            return web.json_response({
                "error": "Invalid JSON format"
            }, status=400)
        except Exception as e:
            logger.exception(f"Error handling message request: {str(e)}")
            return web.json_response({
                "error": f"Server error: {str(e)}"
            }, status=500)
    
    async def handle_broadcast_request(self, request: web.Request) -> web.Response:
        """处理广播请求"""
        try:
            # 解析请求
            data = await request.json()
            message_data = data.get("message", {})
            agent_filter = data.get("filter")
            
            message = MCPMessage.from_dict(message_data)
            
            # 获取目标代理列表
            if agent_filter:
                target_agents = [
                    agent_id for agent_id in agent_filter 
                    if self.registry.get_agent(agent_id)
                ]
            else:
                # 获取所有活跃代理
                agents = self.registry.list_agents()
                target_agents = [
                    agent["agent_id"] for agent in agents 
                    if agent.get("active", False)
                ]
            
            # 向每个代理发送消息
            results = {}
            for agent_id in target_agents:
                # 创建针对特定代理的消息
                agent_message = MCPMessage(
                    message_id=str(uuid.uuid4()),
                    message_type=message.message_type,
                    source_agent=message.source_agent,
                    target_agent=agent_id,
                    payload=message.payload,
                    correlation_id=message.correlation_id
                )
                
                # 处理消息
                response = await self.process_message(agent_message)
                results[agent_id] = response.to_dict()
            
            # 返回所有响应
            return web.json_response(results)
        except json.JSONDecodeError:
            return web.json_response({
                "error": "Invalid JSON format"
            }, status=400)
        except Exception as e:
            logger.exception(f"Error handling broadcast request: {str(e)}")
            return web.json_response({
                "error": f"Server error: {str(e)}"
            }, status=500)
    
    async def handle_status_request(self, request: web.Request) -> web.Response:
        """处理状态请求"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        agents = self.registry.list_agents()
        
        status = {
            "status": "running",
            "uptime": uptime,
            "message_count": self.message_count,
            "registered_agents": len(agents),
            "active_agents": sum(1 for agent in agents if agent.get("active", False)),
            "server_time": datetime.now().isoformat()
        }
        
        return web.json_response(status)
    
    async def start(self, host: str = '0.0.0.0', port: int = 8000):
        """
        启动MCP服务器
        
        Args:
            host: 监听地址
            port: 监听端口
        """
        # 注册默认处理器
        self.register_default_handlers()
        
        # 启动服务器
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        
        logger.info(f"Starting MCP server on {host}:{port}")
        await site.start()
        
        # 保持服务器运行
        while True:
            await asyncio.sleep(3600)  # 每小时检查一次
