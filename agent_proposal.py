from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.messages import SystemMessage
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from typing import List, Optional, Dict, Any

from app.config import settings
from app.core.llm import get_chat_llm_instance
from proposal_plugin.prompts.proposal_prompts import PROPOSAL_SYSTEM_PROMPT, PROPOSAL_EXAMPLES
from proposal_plugin.tools import ProposalTool

class ProposalAgent:
    """用于生成和评估proposal的Agent"""
    
    def __init__(self):
        # 使用工厂方法获取LLM
        self.llm = get_chat_llm_instance(temperature=0.3)
        
        # 初始化工具
        self.tools = [
            ProposalTool()
        ]
        
        # 创建系统消息
        self.system_message = SystemMessage(content=PROPOSAL_SYSTEM_PROMPT)
        
        # 创建Agent
        self.agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            system_message=self.system_message
        )
        
        # 创建Agent执行器
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True
        )
    
    def _create_scene_classifier(self) -> LLMChain:
        """创建用于识别请求类型的LLM链"""
        prompt_template = """
        识别以下用户消息与提案系统相关的意图。
        
        用户消息: {message}
        
        请从以下选项中选择最匹配的一项:
        1. CREATE_PROPOSAL - 用户想要创建一个新提案
        2. EVALUATE_PROPOSAL - 用户发送了一个提案，希望获得评估
        3. NOT_PROPOSAL_RELATED - 与提案无关的消息
        
        只需返回对应的代码(如CREATE_PROPOSAL)，无需解释。
        """
        
        return LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                input_variables=["message"],
                template=prompt_template
            )
        )

    def _create_proposal_formatter(self) -> LLMChain:
        """创建用于格式化提案内容的LLM链"""
        prompt_template = """
        你是一个专业的提案格式化助手。请将用户的提案内容转换为标准格式。
        
        用户提交的提案内容: {content}
        
        请提取或创建一个简洁明了的标题，并整理描述内容。
        
        返回格式:
        标题: [提案标题]
        描述: [提案详细描述]
        """
        
        return LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                input_variables=["content"],
                template=prompt_template
            )
        )
    
    def _create_proposal_evaluator(self) -> LLMChain:
        """创建用于评估提案的LLM链"""
        prompt_template = """
        作为提案评估专家，分析以下提案并给出你的专业评估。
        
        提案标题: {title}
        提案描述: {description}
        
        请从以下方面分析:
        1. 提案目标和价值
        2. 可行性评估
        3. 潜在影响和效益
        4. 可能的风险或问题
        5. 长期前景
        
        最后，明确表明你的立场(支持或反对)并提供理由。
        
        评估格式:
        立场: [支持/反对]
        理由: [简明扼要的主要理由]
        详细分析:
        [提供完整分析和建议]
        """
        
        return LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                input_variables=["title", "description"],
                template=prompt_template
            )
        )
    
     async def process(self, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        统一处理入口 - 自动识别并处理消息
        
        Args:
            message: 用户消息
            context: 可选上下文信息
            
        Returns:
            处理结果字典
        """
        # 首先识别消息类型
        message_type = await self._identify_message_type(message)
        
        # 根据消息类型处理
        if message_type == "CREATE_PROPOSAL":
            return await self._handle_proposal_creation(message)
        elif message_type == "EVALUATE_PROPOSAL":
            return await self._handle_proposal_evaluation(message)
        else:
            # 非提案相关消息
            return {
                "handled": False,
                "type": "not_proposal_related",
                "message": "此消息与提案系统无关"
            }
    
    async def _identify_message_type(self, message: str) -> str:
        """
        识别消息类型
        
        Args:
            message: 用户消息
            
        Returns:
            消息类型代码
        """
        # 检查明确的关键词模式
        if re.search(r"创建提案|新提案|提交提案|我有个提案|我想提议|create proposal", message.lower()):
            return "CREATE_PROPOSAL"
        
        if re.search(r"评估提案|评价提案|analyze proposal|请对.*?提案", message.lower()):
            # 如果消息中包含已有提案ID或明确要求评估，则视为评估请求
            return "EVALUATE_PROPOSAL"
        
        # 使用LLM进行更复杂的意图识别
        try:
            result = await self.scene_classifier.arun(message=message)
            return result.strip()
        except Exception as e:
            # 如果LLM识别失败，默认为非提案相关
            print(f"Scene classification error: {e}")
            return "NOT_PROPOSAL_RELATED"
    
    async def _handle_proposal_creation(self, message: str) -> Dict[str, Any]:
        """
        处理提案创建请求
        
        Args:
            message: 包含提案内容的消息
            
        Returns:
            创建结果
        """
        try:
            # 格式化提案内容
            formatted_proposal = await self.proposal_formatter.arun(content=message)
            
            # 解析格式化结果
            title_match = re.search(r"标题:\s*(.*?)(?:\n描述:|$)", formatted_proposal)
            desc_match = re.search(r"描述:\s*(.*?)$", formatted_proposal, re.DOTALL)
            
            if not title_match:
                return {
                    "handled": True,
                    "type": "proposal_creation_failed",
                    "success": False,
                    "message": "无法提取提案标题，请更清晰地描述您的提案"
                }
            
            title = title_match.group(1).strip()
            description = desc_match.group(1).strip() if desc_match else ""
            
            # 创建提案对象
            proposal = {
                "title": title,
                "description": description,
                "status": "active"
            }
            
            # 如果提供了存储接口，保存提案
            proposal_id = None
            if self.proposal_storage:
                proposal_id = self.proposal_storage.save_proposal(proposal)
                proposal["id"] = proposal_id
            
            # 返回成功结果
            return {
                "handled": True,
                "type": "proposal_created",
                "success": True,
                "proposal": proposal,
                "message": f"成功创建提案: {title}"
            }
            
        except Exception as e:
            return {
                "handled": True,
                "type": "proposal_creation_failed",
                "success": False,
                "message": f"创建提案时出错: {str(e)}"
            }
    
    async def _handle_proposal_evaluation(self, message: str) -> Dict[str, Any]:
        """
        处理提案评估请求
        
        Args:
            message: 包含待评估提案的消息
            
        Returns:
            评估结果
        """
        try:
            # 从消息中提取提案内容
            # 这里假设消息就是提案内容，或者我们从消息中解析出提案ID并获取内容
            proposal = await self._extract_proposal(message)
            
            if not proposal:
                return {
                    "handled": True,
                    "type": "proposal_evaluation_failed",
                    "success": False,
                    "message": "无法识别需要评估的提案内容"
                }
            
            # 评估提案
            evaluation = await self.proposal_evaluator.arun(
                title=proposal.get("title", "未命名提案"),
                description=proposal.get("description", "")
            )
            
            # 解析评估结果
            stance_match = re.search(r"立场:\s*(支持|反对)", evaluation)
            reason_match = re.search(r"理由:\s*(.*?)(?:\n详细分析:|$)", evaluation, re.DOTALL)
            analysis_match = re.search(r"详细分析:\s*(.*?)$", evaluation, re.DOTALL)
            
            stance = stance_match.group(1) if stance_match else "未明确表态"
            reason = reason_match.group(1).strip() if reason_match else ""
            analysis = analysis_match.group(1).strip() if analysis_match else evaluation
            
            # 如果提供了存储接口，保存评估结果
            if self.proposal_storage and "id" in proposal:
                self.proposal_storage.save_vote(
                    proposal_id=proposal["id"],
                    voter_id="ai_agent",
                    stance=stance,
                    comment=analysis
                )
            
            # 返回评估结果
            return {
                "handled": True,
                "type": "proposal_evaluated",
                "success": True,
                "proposal": proposal,
                "evaluation": {
                    "stance": stance,
                    "reason": reason,
                    "analysis": analysis
                },
                "message": self._format_evaluation_feedback(proposal, stance, reason, analysis)
            }
            
        except Exception as e:
            return {
                "handled": True,
                "type": "proposal_evaluation_failed",
                "success": False,
                "message": f"评估提案时出错: {str(e)}"
            }

    async def _extract_proposal(self, message: str) -> Optional[Dict[str, str]]:
        """
        从消息中提取提案内容
        
        这个方法可以提取以下几种格式:
        1. 直接包含完整提案内容的消息
        2. 包含提案ID的消息，需要从存储中获取
        3. 格式化的提案文本
        
        Args:
            message: 用户消息
            
        Returns:
            提案字典或None
        """
        # 检查是否包含提案ID
        id_match = re.search(r"提案\s*#?(\w+)|proposal\s*#?(\w+)", message, re.IGNORECASE)
        if id_match and self.proposal_storage:
            # 从提案ID获取提案
            proposal_id = id_match.group(1) or id_match.group(2)
            proposal = self.proposal_storage.get_proposal(proposal_id)
            if proposal:
                return proposal
        
        # 尝试直接从消息中提取提案内容
        title_match = re.search(r"标题[:：]\s*(.*?)(?:\n|$)", message)
        desc_match = re.search(r"(?:描述|内容|详情)[:：]\s*(.*?)$", message, re.DOTALL)
        
        if title_match:
            # 消息中已包含格式化的提案
            title = title_match.group(1).strip()
            description = desc_match.group(1).strip() if desc_match else ""
            return {"title": title, "description": description}
        
        # 如果以上方法都失败，尝试将整个消息作为提案内容进行格式化
        formatted = await self.proposal_formatter.arun(content=message)
        
        # 从格式化结果中提取提案
        title_match = re.search(r"标题:\s*(.*?)(?:\n描述:|$)", formatted)
        desc_match = re.search(r"描述:\s*(.*?)$", formatted, re.DOTALL)
        
        if title_match:
            title = title_match.group(1).strip()
            description = desc_match.group(1).strip() if desc_match else ""
            return {"title": title, "description": description}
        
        # 无法提取提案，返回None
        return None



    

    async def generate_proposal(self,
                              user_input: str,
                              chat_history: Optional[List] = None) -> Dict[str, Any]:
        """生成新的proposal"""
        
        if chat_history is None:
            chat_history = []
            
        response = await self.agent_executor.ainvoke(
            {
                "input": f"创建新提案: {user_input}",
                "chat_history": chat_history,
                "examples": PROPOSAL_EXAMPLES
            }
        )
        
        return {
            "proposal": response["output"],
            "intermediate_steps": response.get("intermediate_steps", [])
        }
    
    async def evaluate_proposal(self,
                              proposal_content: str,
                              chat_history: Optional[List] = None) -> Dict[str, Any]:
        """评估已有的proposal并提供反馈"""
        
        if chat_history is None:
            chat_history = []
            
        response = await self.agent_executor.ainvoke(
            {
                "input": f"评估提案: {proposal_content}",
                "chat_history": chat_history,
                "examples": PROPOSAL_EXAMPLES
            }
        )
        
        evaluation = response["output"]
        # 解析评估结果
        return {
            "vote": "support" if "支持" in evaluation else "oppose",
            "feedback": evaluation,
            "intermediate_steps": response.get("intermediate_steps", [])
        }
    
    def generate_proposal_sync(self,
                              user_input: str,
                              chat_history: Optional[List] = None) -> Dict[str, Any]:
        """同步版本的proposal生成"""
        
        if chat_history is None:
            chat_history = []
            
        response = self.agent_executor.invoke(
            {
                "input": f"创建新提案: {user_input}",
                "chat_history": chat_history,
                "examples": PROPOSAL_EXAMPLES
            }
        )
        
        return {
            "proposal": response["output"],
            "intermediate_steps": response.get("intermediate_steps", [])
        }
        
    def evaluate_proposal_sync(self,
                              proposal_content: str,
                              chat_history: Optional[List] = None) -> Dict[str, Any]:
        """同步版本的proposal评估"""
        
        if chat_history is None:
            chat_history = []
            
        response = self.agent_executor.invoke(
            {
                "input": f"评估提案: {proposal_content}",
                "chat_history": chat_history,
                "examples": PROPOSAL_EXAMPLES
            }
        )
        
        evaluation = response["output"]
        return {
            "vote": "support" if "支持" in evaluation else "oppose",
            "feedback": evaluation,
            "intermediate_steps": response.get("intermediate_steps", [])
        }
