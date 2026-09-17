#!/usr/bin/env python3
"""Function Calling 实现 - 工具调用"""

import json
from core.lib.safe_calculator import safe_calculator
import requests
from typing import Dict, List, Any, Callable
from dataclasses import dataclass

@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable

class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._register_builtin_tools()
    
    def _register_builtin_tools(self):
        """注册内置工具"""
        # 天气工具
        self.register(Tool(
            name="get_weather",
            description="获取城市天气",
            parameters={"city": {"type": "string", "description": "城市名称"}},
            handler=self._get_weather
        ))
        
        # 计算器工具
        self.register(Tool(
            name="calculate",
            description="计算数学表达式",
            parameters={"expression": {"type": "string", "description": "数学表达式"}},
            handler=self._calculate
        ))
        
        # 搜索工具
        self.register(Tool(
            name="search",
            description="搜索信息",
            parameters={"query": {"type": "string", "description": "搜索关键词"}},
            handler=self._search
        ))
    
    def register(self, tool: Tool):
        self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Tool:
        return self._tools.get(name)
    
    def list_tools(self) -> List[Dict]:
        return [{"name": t.name, "description": t.description} for t in self._tools.values()]
    
    def execute(self, name: str, arguments: Dict) -> Dict:
        tool = self.get_tool(name)
        if tool:
            try:
                result = tool.handler(arguments)
                return {"success": True, "result": result}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"工具 {name} 不存在"}
    
    def _get_weather(self, params: Dict) -> str:
        city = params.get("city", "北京")
        return f"{city}天气：晴，25°C"
    
    def _calculate(self, params: Dict) -> str:
        expr = params.get("expression", "")
        try:
            result = safe_calculator.calculate(expr)
            return str(result)
        except Exception as e:
            return "计算错误"
    
    def _search(self, params: Dict) -> str:
        query = params.get("query", "")
        return f"关于 '{query}' 的搜索结果..."

tool_registry = ToolRegistry()

class FunctionCallingHandler:
    """Function Calling 处理器"""
    
    def __init__(self):
        self.registry = tool_registry
    
    def parse_tool_calls(self, llm_response: str) -> List[Dict]:
        """从 LLM 响应中解析工具调用"""
        try:
            data = json.loads(llm_response)
            if "tool_calls" in data:
                return data["tool_calls"]
            elif "tool_call" in data:
                return [data["tool_call"]]
        except Exception as e:
            pass
        return []
    
    def execute_tool_calls(self, tool_calls: List[Dict]) -> List[Dict]:
        results = []
        for call in tool_calls:
            name = call.get("name")
            args = call.get("arguments", {})
            result = self.registry.execute(name, args)
            results.append({"tool": name, "result": result})
        return results

function_calling = FunctionCallingHandler()
