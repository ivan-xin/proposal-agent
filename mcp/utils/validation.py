"""
消息验证工具 - 提供MCP消息的验证功能
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import re
import json

from ..protocol import MCPMessage, MessageType

def is_valid_agent_id(agent_id: str) -> bool:
    """
    验证代理ID是否有效
    
    Args:
        agent_id: 要验证的代理ID
        
    Returns:
        ID是否有效
    """
    # 代理ID应为字母、数字、下划线和连字符组成的字符串
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', agent_id))

def is_valid_message_type(message_type: str) -> bool:
    """
    验证消息类型是否有效
    
    Args:
        message_type: 要验证的消息类型
        
    Returns:
        类型是否有效
    """
    # 检查是否是预定义的消息类型
    try:
        MessageType(message_type)
        return True
    except ValueError:
        # 如果不是预定义类型，检查是否符合自定义类型格式
        # 自定义类型应为"domain.action"格式
        return bool(re.match(r'^[a-z0-9_]+\.[a-z0-9_]+$', message_type)) or \
               message_type.endswith('.response')

def is_expired(message: MCPMessage, max_age_seconds: int = 300) -> bool:
    """
    检查消息是否已过期
    
    Args:
        message: 要检查的消息
        max_age_seconds: 最大有效期(秒)
        
    Returns:
        消息是否已过期
    """
    try:
        # 解析时间戳
        timestamp = datetime.fromisoformat(message.timestamp)
        
        # 计算消息年龄
        age = datetime.now() - timestamp
        
        # 检查是否超过最大年龄
        return age > timedelta(seconds=max_age_seconds)
    except (ValueError, TypeError):
        # 如果时间戳无效，视为已过期
        return True

def validate_payload_schema(payload: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """
    验证负载是否符合指定的模式
    
    Args:
        payload: 要验证的负载
        schema: 模式定义
        
    Returns:
        错误列表，如果为空则表示验证通过
    """
    errors = []
    
    # 检查必需字段
    for field, field_schema in schema.items():
        if field_schema.get("required", False) and field not in payload:
            errors.append(f"Missing required field: {field}")
    
    # 检查字段类型
    for field, value in payload.items():
        if field in schema:
            field_schema = schema[field]
            expected_type = field_schema.get("type")
            
            if expected_type == "string" and not isinstance(value, str):
                errors.append(f"Field {field} should be a string")
            elif expected_type == "number" and not isinstance(value, (int, float)):
                errors.append(f"Field {field} should be a number")
            elif expected_type == "boolean" and not isinstance(value, bool):
                errors.append(f"Field {field} should be a boolean")
            elif expected_type == "array" and not isinstance(value, list):
                errors.append(f"Field {field} should be an array")
            elif expected_type == "object" and not isinstance(value, dict):
                errors.append(f"Field {field} should be an object")
    
    return errors

def validate_message(message: MCPMessage, schemas: Dict[str, Dict[str, Any]] = None) -> List[str]:
    """
    全面验证MCP消息
    
    Args:
        message: 要验证的消息
        schemas: 不同消息类型的负载模式
        
    Returns:
        错误列表，如果为空则表示验证通过
    """
    errors = []
    
    # 基本验证
    if not message.message_id:
        errors.append("Missing message_id")
    
    if not message.message_type:
        errors.append("Missing message_type")
    elif not is_valid_message_type(message.message_type):
        errors.append(f"Invalid message_type: {message.message_type}")
    
    if not message.source_agent:
        errors.append("Missing source_agent")
    elif not is_valid_agent_id(message.source_agent):
        errors.append(f"Invalid source_agent: {message.source_agent}")
    
    if message.target_agent and not is_valid_agent_id(message.target_agent):
        errors.append(f"Invalid target_agent: {message.target_agent}")
    
    # 验证时间戳
    try:
        datetime.fromisoformat(message.timestamp)
    except ValueError:
        errors.append(f"Invalid timestamp format: {message.timestamp}")
    
    # 验证TTL
    if not isinstance(message.ttl, int) or message.ttl <= 0:
        errors.append(f"Invalid TTL: {message.ttl}")
    
    # 检查过期
    if is_expired(message):
        errors.append("Message has expired")
    
    # 验证负载模式(如果提供)
    if schemas and message.message_type in schemas:
        schema = schemas[message.message_type]
        payload_errors = validate_payload_schema(message.payload, schema)
        errors.extend(payload_errors)
    
    return errors
