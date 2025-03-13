from typing import Dict, Any, Optional, List
import re

class ProposalFormatter:
    """格式化和优化提案内容的简单工具"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化提案格式化器"""
        self.config = config or {}
    
    def format_proposal(self, proposal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化提案内容
        
        Args:
            proposal_data: 包含提案信息的字典
            
        Returns:
            包含格式化内容的更新提案数据
        """
        # 创建提案数据的副本
        formatted_proposal = proposal_data.copy()
        
        # 格式化内容
        content = proposal_data.get("content", "")
        title = proposal_data.get("title", "")
        
        # 格式化并更新内容
        formatted_content = self._format_content(content, title)
        formatted_proposal["content"] = formatted_content
        
        # 如果标题缺失，从内容生成
        if not title:
            formatted_proposal["title"] = self._extract_title(formatted_content)
        
        # 确保有标签
        if "tags" not in formatted_proposal or not formatted_proposal["tags"]:
            formatted_proposal["tags"] = self._extract_tags(formatted_content)
        
        return formatted_proposal
    
    def _format_content(self, content: str, title: str) -> str:
        """
        格式化提案内容
        
        Args:
            content: 原始内容
            title: 提案标题
            
        Returns:
            格式化后的内容
        """
        # 如果内容为空，返回空字符串
        if not content:
            return ""
        
        lines = content.strip().split('\n')
        formatted_parts = []
        
        # 添加标题(如果内容中没有)
        has_title = any(line.startswith('#') for line in lines[:3])
        if title and not has_title:
            formatted_parts.append(f"# {title}\n")
        
        # 添加正文内容
        sections = self._identify_sections(content)
        if sections:
            formatted_parts.append(self._format_sections(sections))
        else:
            formatted_parts.append(content)
        
        # 合并所有部分
        return "\n\n".join(formatted_parts).strip()
    
    def _identify_sections(self, content: str) -> Dict[str, str]:
        """
        尝试识别内容中的不同部分
        
        Args:
            content: 提案内容
            
        Returns:
            各个部分的映射
        """
        sections = {}
        current_section = "main"
        current_content = []
        
        # 简单的正则匹配寻找章节标题
        for line in content.split('\n'):
            # 检查是否是标题行
            if re.match(r'^#{1,3}\s+', line):
                # 如果已有内容，保存之前的章节
                if current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                    current_content = []
                
                # 提取标题并作为章节名
                section_name = re.sub(r'^#{1,3}\s+', '', line).lower()
                current_section = section_name
            else:
                current_content.append(line)
        
        # 保存最后一个章节
        if current_content:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections
    
    def _format_sections(self, sections: Dict[str, str]) -> str:
        """
        格式化已识别的章节
        
        Args:
            sections: 章节映射
            
        Returns:
            格式化后的内容
        """
        formatted_content = []
        
        # 首先处理主要内容
        if "main" in sections:
            formatted_content.append(sections["main"])
            del sections["main"]
        
        # 按照理想顺序添加其他章节
        priority_sections = [
            ("背景", "background", "背景"),
            ("目标", "goals", "目标"),
            ("内容", "content", "主要内容"),
            ("建议", "suggestions", "建议"),
            ("分析", "analysis", "分析"),
            ("结论", "conclusion", "结论")
        ]
        
        for keywords, section_key, title in priority_sections:
            # 尝试找到匹配的章节
            section_content = None
            for key in sections:
                if any(kw in key for kw in keywords.split('|')):
                    section_content = sections[key]
                    del sections[key]
                    break
            
            # 如果找到了匹配的章节，添加它
            if section_content:
                formatted_content.append(f"## {title}\n\n{section_content}")
        
        # 添加剩余的章节
        for title, content in sections.items():
            # 规范化标题
            proper_title = title.capitalize()
            formatted_content.append(f"## {proper_title}\n\n{content}")
        
        return "\n\n".join(formatted_content)
    
    def _extract_title(self, content: str) -> str:
        """
        从内容中提取标题
        
        Args:
            content: 提案内容
            
        Returns:
            提取的标题
        """
        # 尝试从内容中提取标题
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip()
        
        # 使用内容的第一行作为标题
        lines = content.strip().split('\n')
        if lines:
            return lines[0].strip()[:50]  # 限制长度
        
        return "提案"
    
    def _extract_tags(self, content: str) -> List[str]:
        """
        从内容中提取可能的标签
        
        Args:
            content: 提案内容
            
        Returns:
            提取的标签列表
        """
        # 关键词到标签的简化映射
        keywords = {
            "预算|资金|费用": "财务",
            "社区|居民": "社区",
            "环境|绿色": "环保",
            "教育|学习": "教育",
            "安全|保障": "安全",
            "设施|建设": "基础设施",
            "活动|文化": "活动"
        }
        
        found_tags = set()
        content_lower = content.lower()
        
        # 检查内容中是否包含关键词
        for kw_group, tag in keywords.items():
            if any(kw in content_lower for kw in kw_group.split('|')):
                found_tags.add(tag)
        
        # 如果没有找到任何标签，添加一个默认标签
        if not found_tags:
            found_tags.add("一般")
        
        return list(found_tags)