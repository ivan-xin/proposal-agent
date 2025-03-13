from typing import Dict, Any, Optional, List, Union
import os
import logging
from functools import lru_cache
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
import json

# 导入提示词模板
# 导入提示词模板
from prompts.proposal_prompts import (
    ANALYSIS_TEMPLATE,
    VOTE_TEMPLATE,
    COMMENT_TEMPLATE
)

# 配置日志
logger = logging.getLogger(__name__)

class ProposalAnalyzer:
    """提案分析器：分析提案内容并提供投票和评论决策支持"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化提案分析器
        
        Args:
            config: 配置字典，包含模型设置、API密钥等
        """
        self.config = config or {}
        self._initialize_llm()
        # 添加结果缓存
        self._proposal_cache = {}
        
    def _initialize_llm(self) -> None:
        """初始化LLM组件和提示模板"""
        # 配置LLM
        model_name = self.config.get("model_name", "gpt-3.5-turbo")
        temperature = self.config.get("temperature", 0.0)
        api_key = self.config.get("api_key", os.getenv("OPENAI_API_KEY"))
        
        # 使用独立配置
        analysis_config = self.config.get("analysis", {})
        vote_config = self.config.get("vote", {})
        comment_config = self.config.get("comment", {})
        
        # 创建基础LLM
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            openai_api_key=api_key
        )
        
        # 各功能可能使用不同的模型配置
        self.analysis_llm = ChatOpenAI(
            model_name=analysis_config.get("model_name", model_name),
            temperature=analysis_config.get("temperature", temperature),
            openai_api_key=api_key
        )
        
        self.vote_llm = ChatOpenAI(
            model_name=vote_config.get("model_name", model_name),
            temperature=vote_config.get("temperature", temperature),
            openai_api_key=api_key
        )
        
        self.comment_llm = ChatOpenAI(
            model_name=comment_config.get("model_name", model_name),
            temperature=comment_config.get("temperature", 0.7),  # 评论可能需要更高的创造性
            openai_api_key=api_key
        )
        
        # 创建提示模板
        self.analysis_prompt_template = PromptTemplate(
            input_variables=["proposal_title", "proposal_content"],
            template=ANALYSIS_TEMPLATE
        )
        
        self.vote_prompt_template = PromptTemplate(
            input_variables=["analysis_result"],
            template=VOTE_TEMPLATE
        )
        
        self.comment_prompt_template = PromptTemplate(
            input_variables=["analysis_result", "sentiment"],
            template=COMMENT_TEMPLATE
        )
        
        # 创建LLM链
        self.analysis_chain = LLMChain(llm=self.analysis_llm, prompt=self.analysis_prompt_template)
        self.vote_chain = LLMChain(llm=self.vote_llm, prompt=self.vote_prompt_template)
        self.comment_chain = LLMChain(llm=self.comment_llm, prompt=self.comment_prompt_template)
    
    @lru_cache(maxsize=100)
    def _get_proposal_hash(self, title: str, content: str) -> str:
        """
        生成提案哈希用于缓存
        
        Args:
            title: 提案标题
            content: 提案内容
            
        Returns:
            哈希字符串
        """
        import hashlib
        # 创建提案内容的哈希，用于缓存
        combined = f"{title}|{content}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    async def analyze_proposal_async(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """
        异步分析提案
        
        Args:
            proposal: 提案数据字典
            
        Returns:
            多维度分析结果字典
        """
        # 异步版本实现
        # 这里需要使用LangChain的异步API
        pass
    
    def analyze_proposal(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """
        对提案进行全面分析
        
        Args:
            proposal: 提案数据字典，至少包含标题和内容
            
        Returns:
            多维度分析结果字典
        """
        try:
            # 提取提案信息
            proposal_title = proposal.get("title", "")
            proposal_content = proposal.get("content", "")
            
            # 检查缓存
            proposal_hash = self._get_proposal_hash(proposal_title, proposal_content)
            if proposal_hash in self._proposal_cache:
                logger.info(f"使用缓存的提案分析结果: {proposal_hash}")
                return self._proposal_cache[proposal_hash]
            
            # 运行分析链
            response = self.analysis_chain.run(
                proposal_title=proposal_title,
                proposal_content=proposal_content
            )
            
            # 解析JSON结果
            analysis_result = json.loads(response)
            
            # 存入缓存
            self._proposal_cache[proposal_hash] = analysis_result
            return analysis_result
            
        except Exception as e:
            logger.error(f"提案分析错误: {str(e)}", exc_info=True)
            return {
                "feasibility": 5,
                "relevance": 5,
                "cost_benefit": 5,
                "impact": 5,
                "risk": 5,
                "overall_score": 5.0,
                "strengths": ["无法完成分析"],
                "weaknesses": ["分析过程中发生错误"]
            }
    
    def generate_vote_decision(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于分析结果生成投票决定
        
        Args:
            analysis_result: 提案分析结果
            
        Returns:
            包含投票类型和理由的决定字典
        """
        try:
            # 将分析结果转为字符串
            analysis_str = json.dumps(analysis_result, ensure_ascii=False)
            
            # 运行投票决策链
            response = self.vote_chain.run(analysis_result=analysis_str)
            
            # 解析JSON结果
            vote_decision = json.loads(response)
            return vote_decision
        
        except Exception as e:
            logger.error(f"投票决策错误: {str(e)}", exc_info=True)
            # 基于整体分数提供默认决策
            threshold = self.config.get("vote_threshold", 6.0)
            return {
                "vote_type": "oppose" if analysis_result.get("overall_score", 5) < threshold else "support",
                "reason": "由于技术问题，无法生成详细理由",
                "confidence": 0.5
            }
    
    def generate_comment(self, 
                         analysis_result: Dict[str, Any], 
                         sentiment: str = "neutral") -> Dict[str, Any]:
        """
        基于分析结果生成评论
        
        Args:
            analysis_result: 提案分析结果
            sentiment: 期望的情感倾向("positive", "negative", "neutral")
            
        Returns:
            包含评论内容的字典
        """
        try:
            # 验证情感类型
            valid_sentiments = ["positive", "negative", "neutral"]
            if sentiment.lower() not in valid_sentiments:
                logger.warning(f"无效的情感类型: {sentiment}，使用neutral替代")
                sentiment = "neutral"
                
            # 将分析结果转为字符串
            analysis_str = json.dumps(analysis_result, ensure_ascii=False)
            
            # 运行评论生成链
            response = self.comment_chain.run(
                analysis_result=analysis_str,
                sentiment=sentiment
            )
            
            # 解析JSON结果
            comment_content = json.loads(response)
            return comment_content
        
        except Exception as e:
            logger.error(f"评论生成错误: {str(e)}", exc_info=True)
            return {
                "content": "这个提案有一些优点和需要改进的地方。",
                "highlights": ["提案内容完整"],
                "suggestions": ["可以提供更多细节"]
            }