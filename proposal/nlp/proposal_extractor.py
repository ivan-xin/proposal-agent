from typing import Dict, Any, Optional, List
import os
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
import json

class ProposalExtractor:
    """从用户文本中提取提案内容"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化提案提取器
        
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
        
        # 创建意图识别和内容提取的提示模板
        self.extraction_prompt_template = PromptTemplate(
            input_variables=["input_text"],
            template="""
            请分析以下文本，判断是否包含创建提案的意图，并提取相关内容。
            
            用户文本:
            {input_text}
            
            请执行两项任务:
            1. 判断用户是否有创建新提案的意图
            2. 如果有，请从文本中提取提案的关键要素
            
            以JSON格式返回以下内容:
            {{
              "has_proposal": true/false,  // 是否包含提案意图
              "title": "提案标题",  // 提取或生成适当的标题
              "main_points": ["要点1", "要点2", ...],  // 提案的主要观点
              "background": "背景或动机",  // 提案的背景说明
              "suggestions": ["建议1", "建议2", ...],  // 具体建议或行动项
              "categories": ["类别1", "类别2", ...]  // 提案可能属于的类别
            }}
            
            如果文本不包含提案意图，只需返回 {{"has_proposal": false}} 即可。
            
            仅返回JSON格式，不要有其他解释文字。
            """
        )
        
        # 创建LLM链
        self.extraction_chain = LLMChain(llm=self.llm, prompt=self.extraction_prompt_template)
    
    def has_proposal_intent(self, text: str) -> bool:
        """
        判断文本是否包含创建提案的意图
        
        Args:
            text: 用户输入文本
            
        Returns:
            是否有创建提案的意图
        """
        try:
            result = self.extract_content(text)
            return result.get("has_proposal", False)
        except Exception:
            return False
    
    def extract_content(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取提案相关内容
        
        Args:
            text: 用户输入文本
            
        Returns:
            提取的提案内容
        """
        try:
            # 运行提取链
            response = self.extraction_chain.run(input_text=text)
            
            # 解析JSON结果
            content = json.loads(response)
            return content
            
        except Exception as e:
            print(f"提案内容提取错误: {str(e)}")
            return {
                "has_proposal": False,
                "title": None,
                "main_points": None,
                "background": None,
                "suggestions": None,
                "categories": None
            }
    
    def extract_and_format(self, text: str) -> Dict[str, Any]:
        """
        提取并格式化提案内容，适用于直接创建提案
        
        Args:
            text: 用户输入文本
            
        Returns:
            格式化的提案内容，可直接用于创建提案
        """
        content = self.extract_content(text)
        
        if not content.get("has_proposal", False):
            return None
        
        # 构建格式化的提案内容
        formatted_content = {
            "title": content.get("title", "未命名提案"),
            "content": self._format_proposal_content(content),
            "tags": content.get("categories", []),
        }
        
        return formatted_content
    
    def _format_proposal_content(self, extracted_data: Dict[str, Any]) -> str:
        """
        将提取的数据格式化为结构化的提案内容
        
        Args:
            extracted_data: 提取的提案数据
            
        Returns:
            格式化的提案内容文本
        """
        content_parts = []
        
        # 添加背景部分
        if extracted_data.get("background"):
            content_parts.append(f"## 背景\n\n{extracted_data['background']}\n")
        
        # 添加主要观点
        if extracted_data.get("main_points"):
            content_parts.append("## 主要观点\n")
            for point in extracted_data["main_points"]:
                content_parts.append(f"- {point}")
            content_parts.append("\n")
        
        # 添加具体建议
        if extracted_data.get("suggestions"):
            content_parts.append("## 具体建议\n")
            for suggestion in extracted_data["suggestions"]:
                content_parts.append(f"- {suggestion}")
            content_parts.append("\n")
        
        # 如果没有获取到有效内容，添加原始文本
        if not content_parts and "input_text" in self.config:
            content_parts.append(self.config["input_text"])
        
        return "\n".join(content_parts)