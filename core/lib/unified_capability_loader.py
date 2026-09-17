#!/usr/bin/env python3
"""统一能力加载器 - 管理 Agent/Skill/Tool/Plugin"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any


class UnifiedCapabilityLoader:
    """统一加载所有能力（Agent/Skill/Tool/Plugin）"""

    def __init__(self, config_dir: str = "config/capabilities"):
        self.config_dir = Path(config_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def load_all(self) -> Dict[str, Dict[str, Any]]:
        """加载所有能力"""
        if self._cache:
            return self._cache

        # 加载各类型能力
        types = ["agents", "skills", "tools", "plugins"]
        for t in types:
            type_dir = self.config_dir / t
            if type_dir.exists():
                for file_path in type_dir.glob("*.yaml"):
                    try:
                        with open(file_path, 'r') as f:
                            data = yaml.safe_load(f)
                            if data:
                                data['_type'] = t[:-1]  # agent/skill/tool/plugin
                                name = data.get('name', file_path.stem)
                                self._cache[name] = data
                    except Exception as e:
                        print(f"加载 {file_path} 失败: {e}")

        return self._cache

    def get_capability_prompt(self, user_input: str, types: List[str] = None) -> str:
        """生成 LLM 推荐提示词"""
        all_caps = self.load_all()

        # 过滤类型
        if types:
            all_caps = {k: v for k, v in all_caps.items() if v.get('_type') in types}

        prompt = f"""用户请求: {user_input}

请从以下能力中选择最合适的 3 个，按优先级排序。

可用能力（必须从以下列表中选择，使用精确名称）:
"""
        for name, cap in all_caps.items():
            prompt += f"- {name}: {cap.get('description', '')}\n"

        prompt += """
请只输出能力名称，用逗号分隔，最多 3 个。
必须使用上面列表中的精确名称，不要编造新名称。
例如: youtube_agent, video_download, file_agent

推荐结果:"""
        return prompt


# 全局实例
unified_capability_loader = UnifiedCapabilityLoader()
