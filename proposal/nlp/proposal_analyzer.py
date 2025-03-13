from typing import Dict, Any, Optional, List
import os
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
import json

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
        
    def _initialize_llm(self):
        """初始化LLM组件和提示模板"""
        # 配置LLM
        model_name = self.config.get("model_name", "gpt-3.5-turbo")
        temperature = self.config.get("temperature", 0.0)
        api_key = self.config.get("api_key", os.getenv("OPENAI_API_KEY"))
        
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            openai_api_key=api_key
        )
        
        # 创建提案分析提示模板
        self.analysis_prompt_template = PromptTemplate(
            input_variables=["proposal_title", "proposal_content"],
            template="""
            请对以下提案进行分析评估:
            
            提案标题: {proposal_title}
            提案内容: {proposal_content}
            
            请分析以下方面并以JSON格式返回:
            1. 各维度评分(1-10分):
               - 可行性(feasibility)
               - 相关性(relevance)
               - 成本效益(cost_benefit)
               - 影响力(impact)
               - 风险(risk)
            2. 整体评分(overall_score)
            3. 优势(strengths)和弱点(weaknesses)
            4. 潜在风险(risks)
            
            仅返回JSON格式，不要有其他文字。
            """
        )
        
        # 创建投票决策提示模板
        self.vote_prompt_template = PromptTemplate(
            input_variables=["analysis_result"],
            template="""
            根据以下提案分析结果，决定是支持(support)还是反对(oppose)该提案:
            
            {analysis_result}
            
            请以JSON格式返回你的决定，包含以下字段:
            1. vote_type: "support"或"oppose"
            2. reason: 决定的详细理由
            3. confidence: 决策置信度(0-1)
            
            仅返回JSON格式，不要有其他文字。
            """
        )
        
        # 创建评论生成提示模板
        self.comment_prompt_template = PromptTemplate(
            input_variables=["analysis_result", "sentiment"],
            template="""
            根据以下提案分析结果，生成一段评论:
            
            {analysis_result}
            
            评论情感倾向: {sentiment} (positive/negative/neutral)
            
            请以JSON格式返回评论，包含以下字段:
            1. content: 评论正文
            2. highlights: 提案亮点
            3. suggestions: 改进建议
            
            仅返回JSON格式，不要有其他文字。
            """
        )
        
        # 创建LLM链
        self.analysis_chain = LLMChain(llm=self.llm, prompt=self.analysis_prompt_template)
        self.vote_chain = LLMChain(llm=self.llm, prompt=self.vote_prompt_template)
        self.comment_chain = LLMChain(llm=self.llm, prompt=self.comment_prompt_template)
    
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
            
            # 运行分析链
            response = self.analysis_chain.run(
                proposal_title=proposal_title,
                proposal_content=proposal_content
            )
            
            # 解析JSON结果
            analysis_result = json.loads(response)
            return analysis_result
            
        except Exception as e:
            print(f"提案分析错误: {str(e)}")
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
            print(f"投票决策错误: {str(e)}")
            return {
                "vote_type": "oppose" if analysis_result.get("overall_score", 5) < 6 else "support",
                "reason": "由于技术问题，无法生成详细理由",
                "confidence": 0.5
            }
    
    def generate_comment(self, analysis_result: Dict[str, Any], 
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
            print(f"评论生成错误: {str(e)}")
            return {
                "content": "这个提案有一些优点和需要改进的地方。",
                "highlights": ["提案内容完整"],
                "suggestions": ["可以提供更多细节"]
            }