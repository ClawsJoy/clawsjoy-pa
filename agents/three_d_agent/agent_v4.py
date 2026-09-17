#!/usr/bin/env python3
"""ThreeDAgent v4.2 - 精简稳定版（3D 助手）"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import re
from typing import Dict, Optional, Tuple

from core.agents.business.business_agent import BusinessAgent


class ThreeDAgentV4(BusinessAgent):
    """3D Agent - 精简稳定版"""

    name = "three_d_agent_v4"
    description = "智慧 3D 助手"
    version = "5.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        print(f"🎨 ThreeDAgent v{self.version} 启动")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.85)

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        t = user_input.lower()
        
        if any(kw in t for kw in ["生成模型", "创建模型", "3d模型"]):
            return self._generate_model(user_input)
        
        if any(kw in t for kw in ["渲染", "场景"]):
            return self._render_scene(user_input)
        
        return self._resp("🎨 输入「生成模型 椅子」或「渲染 场景」")

    # ================================================================
    #  生成模型
    # ================================================================

    def _generate_model(self, user_input: str) -> Dict:
        desc = re.sub(r'(生成模型|创建模型|3d模型)', '', user_input).strip()
        if not desc:
            desc = "椅子"
        
        result = self._call_llm(f"""
为「{desc}」生成 3D 模型创建指南（Blender）：

1. 建模步骤（3-5步）
2. 材质建议
3. 渲染设置
""")
        return self._resp(f"🎨 3D 模型指南\n\n{result or self._model_template(desc)}")

    def _model_template(self, desc: str) -> str:
        return f"""
模型：{desc}

📌 软件：Blender

步骤：
1. 收集参考图
2. 使用基础形状建模
3. 添加细节
4. 材质：金属/塑料
5. 渲染输出
"""

    # ================================================================
    #  渲染场景
    # ================================================================

    def _render_scene(self, user_input: str) -> Dict:
        scene = re.sub(r'渲染', '', user_input).strip()
        if not scene:
            scene = "场景"
        
        result = self._call_llm(f"""
为「{scene}」提供 3D 渲染建议：

1. 推荐渲染器
2. 灯光设置
3. 相机角度
4. 输出设置
""")
        return self._resp(f"🎬 渲染建议\n\n{result or self._render_template(scene)}")

    def _render_template(self, scene: str) -> str:
        return f"""
场景：{scene}

🖥 渲染器：Cycles
💡 灯光：三点布光法
🎥 相机：50mm, f/2.8
⚙ 输出：1920x1080, 512采样
"""

    # ================================================================
    #  辅助
    # ================================================================

    def _resp(self, content: str, **kwargs) -> Dict:
        return {"success": True, "response": content, "output_content": content, **kwargs}


if __name__ == "__main__":
    agent = ThreeDAgentV4("test")
    print(agent.process("生成模型 椅子")["response"])   
