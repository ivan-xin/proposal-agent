from langchain.tools import BaseTool
from langchain_core.prompts import PromptTemplate
from typing import Dict, List, Optional, Any
import json

from app.config import settings
from app.core.llm import get_chat_llm_instance
from app.plugins.proposal_plugin.models.proposal import ProposalManager

# 全局提案管理器
proposal_manager = ProposalManager()

# 提案评估提示
PROPOSAL_ANALYSIS_PROMPT = """
你需要评估一个社区治理提案，并决定是支持还是反对。保持客观理性，既关注社区利益也关注个人权益。

提案标题: {title}
提案内容: {description}

请分析这个提案:
1. 提案的目的和潜在影响
2. 提案的优点和缺点
3. 考虑提案对不同群体的影响
4. 提案是否符合基本伦理和价值观

最后，明确给出你的投票决定(支持或反对)并解释理由。

你的分析:
"""

class ProposalTool(BaseTool):
    name: str = "proposal_tool"
    description: str = "管理社区治理提案和投票。可用于创建提案、查看提案、进行投票和获取结果。"
    
    def _run(self, action: str, **kwargs: Any) -> str:
        """
        运行提案工具
        
        Args:
            action: 要执行的操作，可以是 'create', 'list', 'view', 'vote', 'analyze'
            **kwargs: 其他参数
        """
        if action == "create":
            title = kwargs.get("title", "")
            description = kwargs.get("description", "")
            
            if not title or not description:
                return "创建提案失败：标题和描述不能为空"
            
            proposal = proposal_manager.create_proposal(title, description)
            
            return f"""已创建提案 #{proposal.proposal_id}
            
                    标题: {proposal.title}

                    内容: {proposal.description}

                    用户可以使用"支持"或"反对"进行投票。
                    """
            
        elif action == "list":
            status = kwargs.get("status")
            
            proposals = proposal_manager.list_proposals(status)
            
            if not proposals:
                return "当前没有提案"
            
            proposals_text = "\n\n".join([
                f"#{p['proposal_id']} - {p['title']} (状态: {p['status']}, 投票数: {p['vote_count']})"
                for p in proposals
            ])
            
            return f"提案列表:\n\n{proposals_text}"
            
        elif action == "view":
            proposal_id = kwargs.get("proposal_id", "")
            
            if not proposal_id:
                return "查看提案失败：缺少提案ID"
            
            proposal = proposal_manager.get_proposal(proposal_id)
            if not proposal:
                return f"查看提案失败：找不到ID为 {proposal_id} 的提案"
            
            results = proposal.get_results()
            
            return f"""提案 #{results['proposal_id']}
            
                    标题: {results['title']}

                    内容: {results['description']}

                    投票情况:
                    - 支持: {results['votes']['support']} ({results['support_percentage']:.1f}%)
                    - 反对: {results['votes']['oppose']} ({results['oppose_percentage']:.1f}%)

                    总投票数: {results['total_votes']}
                    状态: {results['status']}
                    """
            
        elif action == "vote":
            proposal_id = kwargs.get("proposal_id", "")
            voter_id = kwargs.get("voter_id", "default_user")
            vote = kwargs.get("vote", "").lower()
            
            if not proposal_id or not vote:
                return "投票失败：缺少提案ID或投票选项"
            
            # 标准化投票选项
            if vote in ["支持", "赞成", "同意", "yes", "support"]:
                vote = "support"
            elif vote in ["反对", "不赞成", "不同意", "no", "oppose"]:
                vote = "oppose"
            else:
                return f"投票失败：'{vote}' 不是有效的投票选项，请使用'支持'或'反对'"
            
            proposal = proposal_manager.get_proposal(proposal_id)
            if not proposal:
                return f"投票失败：找不到ID为 {proposal_id} 的提案"
            
            success = proposal.add_vote(voter_id, vote)
            if not success:
                return "投票失败：您可能已经投过票或提案已关闭"
            
            return f"您已成功对提案 #{proposal_id} 投票: {vote}"
            
        elif action == "analyze":
            proposal_id = kwargs.get("proposal_id", "")
            
            if not proposal_id:
                return "分析提案失败：缺少提案ID"
            
            proposal = proposal_manager.get_proposal(proposal_id)
            if not proposal:
                return f"分析提案失败：找不到ID为 {proposal_id} 的提案"
            
            # 使用LLM进行分析
            prompt = PromptTemplate(
                template=PROPOSAL_ANALYSIS_PROMPT,
                input_variables=["title", "description"]
            )
            
            llm = get_chat_llm_instance(temperature=0.3)
            analysis_prompt = prompt.format(
                title=proposal.title,
                description=proposal.description
            )
            
            analysis_result = ""
            
            return f"提案 #{proposal_id} 的分析:\n\n{analysis_result.content}"
            
        else:
            return f"未知操作：{action}。支持的操作有：create, list, view, vote, analyze。"