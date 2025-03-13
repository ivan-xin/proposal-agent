from langchain.tools import BaseTool
from typing import Dict, List, Optional, Any
import json

from proposal.services.proposal_service import ProposalService
from proposal.nlp.proposal_analyzer import ProposalAnalyzer

class ProposalTool(BaseTool):
    name: str = "proposal_tool"
    description: str = "管理社区治理提案和投票。可用于创建提案、查看提案、进行投票和分析提案。"
    
    def __init__(self):
        """初始化提案工具，设置所需服务"""
        super().__init__()
        self.proposal_service = ProposalService()
        self.proposal_analyzer = ProposalAnalyzer()
    
    def _run(self, action: str, **kwargs: Any) -> str:
        """
        执行提案工具操作
        
        Args:
            action: 要执行的操作 ('create', 'list', 'view', 'vote', 'analyze')
            **kwargs: 操作所需参数
        
        Returns:
            字符串形式的操作结果
        """
        actions = {
            "create": self._create_proposal,
            "list": self._list_proposals,
            "view": self._view_proposal,
            "vote": self._vote_proposal,
            "analyze": self._analyze_proposal
        }
        
        if action in actions:
            return actions[action](**kwargs)
        else:
            return f"未知操作：{action}。支持的操作有：create, list, view, vote, analyze。"
    
    def _create_proposal(self, title: str = "", description: str = "", **kwargs) -> str:
        """创建新提案"""
        if not title or not description:
            return "创建提案失败：标题和描述不能为空"
        
        proposal = self.proposal_service.create_proposal(title, description)
        
        return f"""已创建提案 #{proposal['proposal_id']}
        
                标题: {proposal['title']}

                内容: {proposal['description']}

                用户可以使用"支持"或"反对"进行投票。
                        """
    
    def _list_proposals(self, status: str = None, **kwargs) -> str:
        """列出所有提案或指定状态的提案"""
        proposals = self.proposal_service.list_proposals(status)
        
        if not proposals:
            return "当前没有提案"
        
        proposals_text = "\n\n".join([
            f"#{p['proposal_id']} - {p['title']} (状态: {p['status']}, 投票数: {p['vote_count']})"
            for p in proposals
        ])
        
        return f"提案列表:\n\n{proposals_text}"
    
    def _view_proposal(self, proposal_id: str = "", **kwargs) -> str:
        """查看特定提案详情"""
        if not proposal_id:
            return "查看提案失败：缺少提案ID"
        
        proposal = self.proposal_service.get_proposal(proposal_id)
        if not proposal:
            return f"查看提案失败：找不到ID为 {proposal_id} 的提案"
        
        results = proposal.get('results', {})
        
        return f"""提案 #{proposal_id}
        
                标题: {proposal['title']}

                内容: {proposal['description']}

                投票情况:
                - 支持: {results.get('votes', {}).get('support', 0)} ({results.get('support_percentage', 0):.1f}%)
                - 反对: {results.get('votes', {}).get('oppose', 0)} ({results.get('oppose_percentage', 0):.1f}%)

                总投票数: {results.get('total_votes', 0)}
                状态: {proposal['status']}
            """
    
    def _vote_proposal(self, proposal_id: str = "", voter_id: str = "default_user", 
                      vote: str = "", **kwargs) -> str:
        """对提案进行投票"""
        if not proposal_id or not vote:
            return "投票失败：缺少提案ID或投票选项"
        
        # 标准化投票选项
        vote_map = {
            "支持": "support", "赞成": "support", "同意": "support", "yes": "support", "support": "support",
            "反对": "oppose", "不赞成": "oppose", "不同意": "oppose", "no": "oppose", "oppose": "oppose"
        }
        
        normalized_vote = vote_map.get(vote.lower())
        if not normalized_vote:
            return f"投票失败：'{vote}' 不是有效的投票选项，请使用'支持'或'反对'"
        
        success = self.proposal_service.add_vote(proposal_id, voter_id, normalized_vote)
        if not success:
            return "投票失败：您可能已经投过票或提案已关闭"
        
        return f"您已成功对提案 #{proposal_id} 投票: {normalized_vote}"
    
    def _analyze_proposal(self, proposal_id: str = "", **kwargs) -> str:
        """分析提案并提供建议"""
        if not proposal_id:
            return "分析提案失败：缺少提案ID"
        
        proposal = self.proposal_service.get_proposal(proposal_id)
        if not proposal:
            return f"分析提案失败：找不到ID为 {proposal_id} 的提案"
        
        # 使用专门的分析器
        analysis_result = self.proposal_analyzer.analyze_proposal(proposal)
        vote_decision = self.proposal_analyzer.generate_vote_decision(analysis_result)
        
        return f"""提案 #{proposal_id} 的分析:

                    总体评分: {analysis_result.get('overall_score', 5)}/10

                    优势:
                    - {'\n- '.join(analysis_result.get('strengths', ['未找到明显优势']))}

                    弱点:
                    - {'\n- '.join(analysis_result.get('weaknesses', ['未找到明显弱点']))}

                    建议投票: {vote_decision.get('vote_type', '未决定')}
                    理由: {vote_decision.get('reason', '无详细理由')}
                """