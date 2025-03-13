from langchain_openai import ChatOpenAI
from typing import Optional
from proposal.config import settings

        # self.llm = ChatOpenAI(
        #     temperature=0.5,
        #     model_name=settings.OPENAI_MODEL,
        #     openai_api_key=settings.OPENAI_API_KEY
        # )

def get_chat_llm_instance(
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    streaming: bool = False,
    max_tokens: Optional[int] = None
) -> ChatOpenAI:
    """
    创建并返回配置好的ChatOpenAI实例
    
    Args:
        model_name: 模型名称，如果不指定则使用配置中的默认模型
        temperature: 温度参数，控制输出随机性，0表示最确定性，1表示最创造性
        streaming: 是否使用流式输出
        max_tokens: 最大生成标记数
        
    Returns:
        配置好的ChatOpenAI实例
    """
    # 使用提供的参数或配置中的默认值
    model = model_name or settings.OPENAI_MODEL
    temp = temperature if temperature is not None else settings.default_temperature
    max_tokens = max_tokens or settings.max_tokens
    
    # 创建ChatOpenAI实例
    llm = ChatOpenAI(
        model=model,
        temperature=temp,
        streaming=streaming,
        max_tokens=max_tokens,
        api_key=settings.OPENAI_API_KEY
    )
    
    return llm