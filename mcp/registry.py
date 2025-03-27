"""
代理注册中心 - 管理已注册的代理系统
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import threading
import logging

logger = logging.getLogger(__name__)

class AgentRegistry:
    """代理注册中心，管理已注册的代理系统"""
    
    def __init__(self):
        """初始化代理注册中心"""
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.RLock()  # 使用可重入锁保护并发访问
    
    def register_agent(self, agent_id: str, capabilities: List[str], metadata: Dict[str, Any] = None) -> bool:
        """
        注册代理
        
        Args:
            agent_id: 代理ID
            capabilities: 代理能力列表
            metadata: 代理元数据
            
        Returns:
            注册是否成功
        """
        with self.lock:
            now = datetime.now().isoformat()
            
            # 检查代理是否已存在
            if agent_id in self.agents:
                # 更新现有代理
                self.agents[agent_id].update({
                    "capabilities": capabilities,
                    "metadata": metadata or {},
                    "last_seen": now,
                    "active": True
                })
                logger.info(f"Updated agent: {agent_id}")
            else:
                # 注册新代理
                self.agents[agent_id] = {
                    "agent_id": agent_id,
                    "capabilities": capabilities,
                    "metadata": metadata or {},
                    "registered_at": now,
                    "last_seen": now,
                    "active": True
                }
                logger.info(f"Registered new agent: {agent_id}")
            
            return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        注销代理
        
        Args:
            agent_id: 代理ID
            
        Returns:
            注销是否成功
        """
        with self.lock:
            if agent_id in self.agents:
                # 标记为非活跃而不是删除
                self.agents[agent_id]["active"] = False
                self.agents[agent_id]["last_seen"] = datetime.now().isoformat()
                logger.info(f"Unregistered agent: {agent_id}")
                return True
            return False
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取代理信息
        
        Args:
            agent_id: 代理ID
            
        Returns:
            代理信息字典，不存在则返回None
        """
        with self.lock:
            return self.agents.get(agent_id)
    
    def update_agent_status(self, agent_id: str, active: bool = True) -> bool:
        """
        更新代理状态
        
        Args:
            agent_id: 代理ID
            active: 是否活跃
            
        Returns:
            更新是否成功
        """
        with self.lock:
            if agent_id in self.agents:
                self.agents[agent_id]["active"] = active
                self.agents[agent_id]["last_seen"] = datetime.now().isoformat()
                return True
            return False
    
    def list_agents(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """
        列出所有代理
        
        Args:
            include_inactive: 是否包含非活跃代理
            
        Returns:
            代理信息列表
        """
        with self.lock:
            if include_inactive:
                return list(self.agents.values())
            else:
                return [agent for agent in self.agents.values() if agent.get("active", False)]
    
    def find_agents_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """
        按能力查找代理
        
        Args:
            capability: 要查找的能力
            
        Returns:
            具有指定能力的代理列表
        """
        with self.lock:
            return [
                agent for agent in self.agents.values()
                if capability in agent.get("capabilities", []) and agent.get("active", False)
            ]
    
    def cleanup_inactive_agents(self, max_inactive_time: int = 3600) -> int:
        """
        清理长时间不活跃的代理
        
        Args:
            max_inactive_time: 最大不活跃时间(秒)
            
        Returns:
            清理的代理数量
        """
        with self.lock:
            now = datetime.now()
            count = 0
            
            for agent_id, agent in list(self.agents.items()):
                if not agent.get("active", True):
                    continue
                    
                last_seen = agent.get("last_seen")
                if not last_seen:
                    continue
                    
                try:
                    last_seen_time = datetime.fromisoformat(last_seen)
                    inactive_seconds = (now - last_seen_time).total_seconds()
                    
                    if inactive_seconds > max_inactive_time:
                        agent["active"] = False
                        count += 1
                        logger.info(f"Marked agent as inactive due to timeout: {agent_id}")
                except (ValueError, TypeError):
                    pass
            
            return count

