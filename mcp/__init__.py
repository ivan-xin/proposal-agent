"""
MCP (Message Control Protocol) - 代理系统间通信框架

提供标准化的消息传递机制，用于连接不同的AI代理系统。
"""

from .protocol import MCPMessage, MessageType
from .client import MCPClient
from .server import MCPServer
from .registry import AgentRegistry
from .adapter import MCPAdapter

__version__ = "0.1.0"
