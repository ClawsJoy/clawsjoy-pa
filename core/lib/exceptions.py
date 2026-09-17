"""自定义异常类"""

class ClawsJoyError(Exception):
    """基础异常类"""
    pass

class AgentError(ClawsJoyError):
    """Agent 相关异常"""
    pass

class CacheError(ClawsJoyError):
    """缓存相关异常"""
    pass

class ConfigError(ClawsJoyError):
    """配置相关异常"""
    pass

class LLMError(ClawsJoyError):
    """LLM 服务异常"""
    pass

class MemoryError(ClawsJoyError):
    """记忆存储异常"""
    pass

class ValidationError(ClawsJoyError):
    """验证异常"""
    pass
