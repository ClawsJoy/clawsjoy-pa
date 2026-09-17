"""可配置引擎基类 - 支持硬编码和配置驱动"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigurableEngine:
    """可配置引擎基类"""
    
    def __init__(self, name: str, config_path: Optional[str] = None):
        self.name = name
        self.config = self._load_config(config_path)
        self._hardcoded_rules = self._init_hardcoded()
        print(f"🔧 {name} 引擎已初始化 (配置:{bool(self.config)}, 硬编码: {len(self._hardcoded_rules)})")
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """加载配置文件"""
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        
        # 默认配置路径
        default_path = Path(f"config/engines/{self.name}.yaml")
        if default_path.exists():
            with open(default_path, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def _init_hardcoded(self) -> Dict:
        """初始化硬编码规则（子类覆盖）"""
        return {}
    
    def get_rule(self, key: str, default: Any = None) -> Any:
        """获取规则（配置优先，硬编码兜底）"""
        if self.config and key in self.config:
            return self.config[key]
        return self._hardcoded_rules.get(key, default)
    
    def reload(self):
        """热重载配置"""
        self.config = self._load_config(None)
        print(f"🔄 {self.name} 引擎配置已重载")
    
    def get_stats(self) -> Dict:
        return {
            "name": self.name,
            "has_config": bool(self.config),
            "hardcoded_rules": len(self._hardcoded_rules)
        }
