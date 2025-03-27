"""
安全工具 - 提供MCP通信的安全功能
"""

import hmac
import hashlib
import base64
import secrets
import time
from typing import Dict, Any, Optional

from ..protocol import MCPMessage

def generate_auth_token(length: int = 32) -> str:
    """
    生成认证令牌
    
    Args:
        length: 令牌长度
        
    Returns:
        生成的令牌
    """
    return secrets.token_hex(length // 2)

def sign_message(message: MCPMessage, secret_key: str) -> str:
    """
    对消息进行签名
    
    Args:
        message: 要签名的消息
        secret_key: 密钥
        
    Returns:
        消息签名
    """
    # 创建消息摘要
    message_dict = message.to_dict()
    
    # 移除现有签名
    message_dict.pop("signature", None)
    
    # 序列化消息
    message_str = str(sorted(message_dict.items()))
    
    # 计算HMAC
    h = hmac.new(secret_key.encode(), message_str.encode(), hashlib.sha256)
    return base64.b64encode(h.digest()).decode()

def verify_signature(message: MCPMessage, secret_key: str) -> bool:
    """
    验证消息签名
    
    Args:
        message: 要验证的消息
        secret_key: 密钥
        
    Returns:
        签名是否有效
    """
    if not message.signature:
        return False
    
    # 获取现有签名
    original_signature = message.signature
    
    # 计算新签名
    calculated_signature = sign_message(message, secret_key)
    
    # 比较签名
    return hmac.compare_digest(original_signature, calculated_signature)

def generate_expiring_token(user_id: str, secret_key: str, expiry: int = 3600) -> str:
    """
    生成带过期时间的令牌
    
    Args:
        user_id: 用户ID
        secret_key: 密钥
        expiry: 过期时间(秒)
        
    Returns:
        生成的令牌
    """
    # 创建令牌数据
    now = int(time.time())
    expiry_time = now + expiry
    
    token_data = f"{user_id}:{expiry_time}"
    
    # 计算签名
    h = hmac.new(secret_key.encode(), token_data.encode(), hashlib.sha256)
    signature = base64.b64encode(h.digest()).decode()
    
    # 组合令牌
    token = f"{token_data}:{signature}"
    return base64.b64encode(token.encode()).decode()

def verify_expiring_token(token: str, secret_key: str) -> Optional[str]:
    """
    验证带过期时间的令牌
    
    Args:
        token: 要验证的令牌
        secret_key: 密钥
        
    Returns:
        令牌有效时返回用户ID，否则返回None
    """
    try:
        # 解码令牌
        decoded = base64.b64decode(token.encode()).decode()
        parts = decoded.split(":")
        
        if len(parts) != 3:
            return None
        
        user_id, expiry_time, signature = parts
        
        # 检查过期时间
        now = int(time.time())
        if int(expiry_time) < now:
            return None
        
        # 验证签名
        token_data = f"{user_id}:{expiry_time}"
        h = hmac.new(secret_key.encode(), token_data.encode(), hashlib.sha256)
        expected_signature = base64.b64encode(h.digest()).decode()
        
        if not hmac.compare_digest(signature, expected_signature):
            return None
        
        return user_id
    except Exception:
        return None

def encrypt_payload(payload: Dict[str, Any], secret_key: str) -> str:
    """
    加密消息负载
    
    Args:
        payload: 要加密的负载
        secret_key: 密钥
        
    Returns:
        加密后的负载
    """
    # 注意：这是一个简化的实现，实际应用中应使用更安全的加密方法
    # 如AES加密
    
    # 序列化负载
    payload_str = str(sorted(payload.items()))
    
    # 计算密钥的SHA-256哈希
    key_hash = hashlib.sha256(secret_key.encode()).digest()
    
    # 简单的XOR加密(仅用于演示)
    encrypted = bytearray()
    for i, char in enumerate(payload_str.encode()):
        key_byte = key_hash[i % len(key_hash)]
        encrypted.append(char ^ key_byte)
    
    return base64.b64encode(encrypted).decode()

def decrypt_payload(encrypted: str, secret_key: str) -> Dict[str, Any]:
    """
    解密消息负载
    
    Args:
        encrypted: 加密的负载
        secret_key: 密钥
        
    Returns:
        解密后的负载
    """
    # 注意：这是一个简化的实现，实际应用中应使用更安全的解密方法
    
    # 解码加密数据
    encrypted_bytes = base64.b64decode(encrypted.encode())
    
    # 计算密钥的SHA-256哈希
    key_hash = hashlib.sha256(secret_key.encode()).digest()
    
    # 简单的XOR解密(仅用于演示)
    decrypted = bytearray()
    for i, byte in enumerate(encrypted_bytes):
        key_byte = key_hash[i % len(key_hash)]
        decrypted.append(byte ^ key_byte)
    
    # 解析负载
    # 注意：这里需要更健壮的实现来处理字符串到字典的转换
    # 这只是一个简化示例
    decrypted_str = decrypted.decode()
    
    # 简单解析(仅用于演示)
    # 实际应用中应使用JSON或其他序列化格式
    result = {}
    try:
        # 尝试将字符串转换回字典
        # 这种方法不安全，仅用于演示
        import ast
        result = ast.literal_eval(decrypted_str)
    except:
        pass
    
    return result
