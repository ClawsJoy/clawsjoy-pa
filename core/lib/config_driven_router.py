"""配置驱动的意图路由器 - 集成语义引擎和规则引擎"""

import yaml
import re
from pathlib import Path
from typing import Dict, Optional, List


class ConfigDrivenRouter:
    """完全配置驱动的意图路由器（集成语义引擎）"""
    
    def __init__(self):
        self.intents_config = {}
        self.intent_map = {}
        self.semantic_engine = None
        self._load_configs()
        self._compile_patterns()
        self._init_semantic_engine()
        self._print_stats()
    
    def _load_configs(self):
        """加载配置文件"""
        # 1. 加载 intents.yaml
        intents_path = Path("config/intents.yaml")
        if intents_path.exists():
            with open(intents_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                self.intents_config = data.get("intents", {})
            print(f"✅ 加载意图配置: {len(self.intents_config)} 个意图")
        
        # 2. 加载 intent_agent_map.yaml
        map_path = Path("config/intent_agent_map.yaml")
        if map_path.exists():
            with open(map_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                self.intent_map = data.get("intent_to_agent", {})
            print(f"✅ 加载 Agent 映射: {len(self.intent_map)} 个映射")
    
    def _init_semantic_engine(self):
        """初始化语义引擎（可选）"""
        try:
            from engine.semantic import semantic_engine
            self.semantic_engine = semantic_engine
            print(f"✅ 语义引擎已集成")
        except ImportError:
            try:
                from engine.semantic.core import semantic_engine
                self.semantic_engine = semantic_engine
                print(f"✅ 语义引擎已集成 (core)")
            except ImportError as e:
                print(f"⚠️ 语义引擎不可用: {e}")
    
    def _compile_patterns(self):
        """预编译正则表达式"""
        self.compiled_patterns = []
        for intent, config in self.intents_config.items():
            patterns = config.get("patterns", [])
            for pattern in patterns:
                try:
                    self.compiled_patterns.append({
                        "intent": intent,
                        "pattern": re.compile(pattern, re.IGNORECASE),
                        "priority": config.get("priority", 5)
                    })
                except re.error:
                    pass
    
    def _semantic_route(self, message: str) -> Optional[Dict]:
        """使用语义引擎路由"""
        if not self.semantic_engine:
            return None
        
        try:
            result = self.semantic_engine.understand(message)
            intent = getattr(result, 'intent', None)
            confidence = getattr(result, 'confidence', 0.5)
            
            if intent and confidence > 0.6:
                return {
                    "intent": intent,
                    "confidence": confidence,
                    "agent": self.intent_map.get(intent, "chat_agent"),
                    "method": "semantic"
                }
        except Exception:
            pass
        return None
    
    def _rule_route(self, message: str) -> Optional[Dict]:
        """使用规则引擎路由"""
        try:
            from engine.semantic.engines.rule_engine import rule_engine
            result = rule_engine.match(message)
            if result and result.get('intent'):
                return {
                    "intent": result['intent'],
                    "confidence": result.get('confidence', 0.7),
                    "agent": self.intent_map.get(result['intent'], "chat_agent"),
                    "method": "rule"
                }
        except Exception:
            pass
        return None
    
    def _pattern_route(self, message: str) -> Optional[Dict]:
        """正则匹配路由"""
        for item in self.compiled_patterns:
            if item["pattern"].search(message):
                return {
                    "intent": item["intent"],
                    "confidence": 0.9,
                    "agent": self.intent_map.get(item["intent"], "chat_agent"),
                    "method": "pattern"
                }
        return None
    
    def _keyword_route(self, message: str) -> Optional[Dict]:
        """关键词匹配路由"""
        for intent, config in self.intents_config.items():
            keywords = config.get("keywords", [])
            for keyword in keywords:
                if keyword and keyword.lower() in message.lower():
                    return {
                        "intent": intent,
                        "confidence": 0.8,
                        "agent": self.intent_map.get(intent, "chat_agent"),
                        "method": "keyword"
                    }
        return None
    
    def route(self, message: str) -> Dict:
        """路由消息到意图（多级路由）"""
        
        # 1. 语义理解（优先级最高）
        result = self._semantic_route(message)
        if result:
            return result
        
        # 2. 规则引擎
        result = self._rule_route(message)
        if result:
            return result
        
        # 3. 正则匹配
        result = self._pattern_route(message)
        if result:
            return result
        
        # 4. 关键词匹配
        result = self._keyword_route(message)
        if result:
            return result
        
        # 5. 默认
        return {
            "intent": "chat",
            "confidence": 0.5,
            "agent": "chat_agent",
            "method": "default"
        }
    
    def reload(self):
        """热重载配置"""
        self._load_configs()
        self._compile_patterns()
        return True
    
    def _print_stats(self):
        """打印统计信息"""
        print(f"📊 路由器状态:")
        print(f"   - 意图数: {len(self.intents_config)}")
        print(f"   - 模式匹配: {len(self.compiled_patterns)}")
        print(f"   - Agent映射: {len(self.intent_map)}")
        print(f"   - 语义引擎: {'✅ 已启用' if self.semantic_engine else '⚠️ 未启用'}")


config_router = ConfigDrivenRouter()
