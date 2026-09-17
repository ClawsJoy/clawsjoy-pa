#!/usr/bin/env python3
"""
工具系统 - 2.5 层 JSON 标准
"""

from typing import Dict, Any

class ToolSystem:
    """工具系统"""
    
    VERSION = "2.5"
    
    TOOLS = {
        "calculate": {
            "description": "数学计算",
            "params": {
                "expression": {"type": "string", "required": True}
            }
        },
        "translate": {
            "description": "翻译文本",
            "params": {
                "text": {"type": "string", "required": True},
                "target_lang": {"type": "string", "required": True}
            }
        }
    }
    
    @classmethod
    def execute(cls, tool_name: str, params: Dict, user_id: str = "default") -> Dict:
        """执行工具"""
        tool = cls.TOOLS.get(tool_name)
        if not tool:
            return {
                "version": cls.VERSION,
                "success": False,
                "error": f"未知工具: {tool_name}",
                "available": list(cls.TOOLS.keys())
            }
        
        # 验证参数
        for key, spec in tool.get("params", {}).items():
            if spec.get("required") and key not in params:
                return {
                    "version": cls.VERSION,
                    "success": False,
                    "error": f"缺少必要参数: {key}"
                }
        
        # 执行
        if tool_name == "calculate":
            try:
                expression = params.get("expression", "")
                allowed = set("0123456789+-*/(). ")
                if all(c in allowed for c in expression):
                    result = eval(expression)
                    return {
                        "version": cls.VERSION,
                        "success": True,
                        "result": str(result)
                    }
                else:
                    return {
                        "version": cls.VERSION,
                        "success": False,
                        "error": "表达式包含不允许的字符"
                    }
            except Exception as e:
                return {
                    "version": cls.VERSION,
                    "success": False,
                    "error": f"计算错误: {str(e)}"
                }
        
        if tool_name == "translate":
            try:
                text = params.get("text", "")
                target_lang = params.get("target_lang", "中文")
                # 简单翻译：调用 translate_agent
                from agents.translate_agent.agent_v4 import TranslateAgentV4
                agent = TranslateAgentV4(user_id)
                result = agent.process(f"翻译 {text} 成 {target_lang}")
                return {
                    "version": cls.VERSION,
                    "success": True,
                    "result": result.get("output_content", result.get("response", text))
                }
            except Exception as e:
                return {
                    "version": cls.VERSION,
                    "success": False,
                    "error": f"翻译错误: {str(e)}"
                }
        
        return {
            "version": cls.VERSION,
            "success": False,
            "error": f"工具 {tool_name} 未实现"
        }
    
    @classmethod
    def get_tool_declaration(cls) -> Dict:
        return {
            "version": cls.VERSION,
            "tools": cls.TOOLS
        }

# 全局实例
tool_system = ToolSystem()
