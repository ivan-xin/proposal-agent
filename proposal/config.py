import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Settings:
    # API配置
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    
    # OpenAI配置
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "o3-mini")
    BASE_URL = os.getenv("BASE_URL", "")

    # 默认参数
    default_temperature: float = 0.7
    max_tokens: int = 4000

    # 应用配置
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # 验证OpenAI API密钥是否存在
    def validate(self):
        missing_keys = []
        if not self.OPENAI_API_KEY:
            missing_keys.append("OPENAI_API_KEY")
        
        if missing_keys:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_keys)}")
        
        return True

    def setup_environment(self):
        """设置环境变量用于LangChain"""
        os.environ["OPENAI_API_BASE"] = self.BASE_URL
        os.environ["OPENAI_API_KEY"] = self.OPENAI_API_KEY
# 创建设置实例
settings = Settings()