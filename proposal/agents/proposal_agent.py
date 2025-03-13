from typing import Dict, Any, Optional
import logging

from proposal.nlp.proposal_extractor import ProposalExtractor
from proposal.nlp.proposal_analyzer import ProposalAnalyzer
from proposal.nlp.proposal_formatter import ProposalFormatter
from proposal.services.proposal_service import ProposalService
from proposal.services.vote_service import VoteService

logger = logging.getLogger(__name__)

class ProposalAgent:
    """提案AI代理：处理提案相关的用户请求和自动化任务"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化提案代理"""
        self.config = config or {}
        
        # 初始化各个组件
        self.extractor = ProposalExtractor(config.get("extractor_config"))
        self.formatter = ProposalFormatter(config.get("formatter_config"))
        self.analyzer = ProposalAnalyzer(config.get("analyzer_config"))
        self.proposal_service = ProposalService()
        self.vote_service = VoteService()
    
    def process_message(self, message: str, user_id: str) -> Dict[str, Any]:
        """处理用户消息，执行相应的提案操作"""
        # 尝试识别提案创建意图
        if self.extractor.has_proposal_intent(message):
            return self._handle_proposal_creation(message, user_id)
            
        # 其他意图处理...
        
        return {"type": "default", "content": "我可以帮您创建提案、投票或查询提案信息。"}
    
    def _handle_proposal_creation(self, message: str, user_id: str) -> Dict[str, Any]:
        """处理提案创建请求"""
        # 步骤1: 从消息中提取提案基本内容
        raw_proposal_data = self.extractor.extract_and_format(message)
        
        if not raw_proposal_data:
            return {
                "type": "error",
                "content": "无法从您的消息中提取有效的提案内容，请提供更多细节。"
            }
        
        # 步骤2: 格式化提案内容
        formatted_proposal = self.formatter.format_proposal(raw_proposal_data)
        
        # 步骤3: 添加创建者信息
        formatted_proposal["creator_id"] = user_id
        
        # 步骤4: 分析提案质量 (可选)
        analysis = self.analyzer.analyze_proposal(formatted_proposal)
        if analysis.get("overall_score", 7) < self.config.get("quality_threshold", 4):
            # 提案质量不足，返回反馈
            return {
                "type": "quality_feedback",
                "content": "您的提案需要更多细节和论证。请考虑以下几点：",
                "weaknesses": analysis.get("weaknesses", []),
                "proposal_draft": formatted_proposal
            }
        
        # 步骤5: 创建提案
        proposal = self.proposal_service.create_proposal(**formatted_proposal)
        
        # 步骤6: 返回成功响应
        return {
            "type": "proposal_created",
            "proposal_id": proposal.get("proposal_id"),
            "title": proposal.get("title"),
            "content": "您的提案已成功创建！其他成员现在可以对它进行投票和评论。",
            "formatted_content": formatted_proposal.get("content")
        }