#!/usr/bin/env python3
"""3D 虚拟空间 Agent - 独立处理3D场景、虚拟空间、三维可视化"""

import importlib
import json
import re
from pathlib import Path
from typing import Dict, Optional

from core.agents.business.business_agent_v2 import BusinessAgentV2


class ThreeDAgent(BusinessAgentV2):
    name = "three_d_agent"
    description = "3D虚拟空间构建与三维可视化"
    version = "1.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self._init_skills()
        self.scene_memory = {}
        print(f"🎮 3D虚拟空间Agent v{self.version} 已上线")

    def _init_skills(self):
        """初始化3D技能"""
        self.skills = {}

        # Three.js 场景生成
        try:
            module = importlib.import_module("skills.threejs.scripts.main")
            self.skills["threejs"] = getattr(module, "execute")
            print("   ✅ Three.js 场景生成技能已加载")
        except Exception:
            pass

    def _execute_business(self, user_input: str, context: dict = None) -> dict:
        """处理3D请求"""

        # 1. 生成3D场景
        if any(kw in user_input for kw in ["生成", "创建", "构建"]) and any(
            kw in user_input for kw in ["3d", "3D", "三维", "场景", "空间"]
        ):
            return self._generate_3d_scene(user_input)

        # 2. 虚拟空间描述
        if any(kw in user_input for kw in ["虚拟空间", "元宇宙", "虚拟世界"]):
            return self._create_virtual_space(user_input)

        # 3. 3D可视化
        if "可视化" in user_input or "展示" in user_input:
            return self._visualize_3d(user_input)

        # 4. 空间语义控制
        if any(kw in user_input for kw in ["往上", "往下", "往左", "往右", "拉近", "拉远"]):
            return self._control_scene(user_input)

        # 5. 帮助
        return self._help()

    def _generate_3d_scene(self, user_input: str) -> dict:
        """生成3D场景"""
        # 解析场景描述
        scene_desc = self._parse_scene_desc(user_input)

        # 调用 Three.js 生成
        if "threejs" in self.skills:
            result = self.skills["threejs"](
                {
                    "scene_type": scene_desc.get("type", "basic"),
                    "objects": scene_desc.get("objects", []),
                    "lighting": scene_desc.get("lighting", {}),
                    "camera": scene_desc.get("camera", {}),
                }
            )

            return {
                "success": True,
                "response": self._format_scene_response(scene_desc),
                "scene_code": result.get("code", ""),
                "scene_data": scene_desc,
                "agent": self.name,
            }

        # 降级：返回场景描述
        return {
            "success": True,
            "response": f"🎮 3D场景请求\n场景类型: {scene_desc.get('type', '默认')}\n对象: {', '.join(scene_desc.get('objects', []))}\n\n💡 Three.js 技能可生成实际HTML",
            "scene_data": scene_desc,
            "agent": self.name,
        }

    def _create_virtual_space(self, user_input: str) -> dict:
        """创建虚拟空间"""
        space_desc = self._parse_space_desc(user_input)

        return {
            "success": True,
            "response": f"🌌 虚拟空间已创建\n\n空间名称: {space_desc.get('name', '未命名')}\n环境: {space_desc.get('environment', '默认')}\n尺寸: {space_desc.get('size', '100x100')}\n\n可在此空间中进行3D交互",
            "space_data": space_desc,
            "agent": self.name,
        }

    def _visualize_3d(self, user_input: str) -> dict:
        """3D可视化"""
        viz_data = self._parse_viz_desc(user_input)

        return {
            "success": True,
            "response": f"📊 3D可视化请求\n数据类型: {viz_data.get('data_type', '通用')}\n渲染方式: {viz_data.get('render', '标准')}",
            "agent": self.name,
        }

    def _control_scene(self, user_input: str) -> dict:
        """空间语义控制"""
        from engine.semantic_params.spatial_mapper import spatial_mapper

        params = spatial_mapper.parse(user_input)

        return {
            "success": True,
            "response": f"🎮 场景控制\n位置偏移: x:{params['position']['x']:.2f} y:{params['position']['y']:.2f}\n缩放: {params['scale']:.2f}\n相机: {params['camera']['angle']}",
            "control_params": params,
            "agent": self.name,
        }

    def _parse_scene_desc(self, user_input: str) -> dict:
        """解析场景描述"""
        desc = {"type": "basic", "objects": [], "lighting": {}, "camera": {}}

        # 场景类型
        if "室内" in user_input:
            desc["type"] = "interior"
        elif "室外" in user_input:
            desc["type"] = "exterior"
        elif "科幻" in user_input:
            desc["type"] = "scifi"
        elif "自然" in user_input:
            desc["type"] = "nature"

        # 对象检测
        objects = []
        if "立方体" in user_input or "cube" in user_input.lower():
            objects.append("cube")
        if "球体" in user_input or "sphere" in user_input.lower():
            objects.append("sphere")
        if "圆柱" in user_input:
            objects.append("cylinder")
        if "人物" in user_input:
            objects.append("character")
        if "建筑" in user_input:
            objects.append("building")

        desc["objects"] = objects

        # 光照
        if "暗" in user_input:
            desc["lighting"]["intensity"] = 0.5
        elif "亮" in user_input:
            desc["lighting"]["intensity"] = 1.2

        return desc

    def _parse_space_desc(self, user_input: str) -> dict:
        """解析虚拟空间描述"""
        return {
            "name": self._extract_name(user_input),
            "environment": "default",
            "size": "100x100",
        }

    def _parse_viz_desc(self, user_input: str) -> dict:
        """解析可视化描述"""
        return {"data_type": "generic", "render": "standard"}

    def _extract_name(self, text: str) -> str:
        """提取名称"""
        import re

        match = re.search(r"[名称叫]([\u4e00-\u9fa5a-zA-Z0-9]+)", text)
        return match.group(1) if match else "未命名"

    def _format_scene_response(self, desc: dict) -> str:
        """格式化场景响应"""
        lines = ["🎮 3D场景已生成"]
        lines.append(f"场景类型: {desc.get('type', '默认')}")
        if desc.get("objects"):
            lines.append(f"包含对象: {', '.join(desc['objects'])}")
        if desc.get("lighting"):
            lines.append(f"光照强度: {desc.get('lighting', {}).get('intensity', '默认')}")
        return "\n".join(lines)

    def _help(self) -> dict:
        return {
            "success": True,
            "response": """🎮 我能做什么：

🎨 **3D场景生成**
• 生成一个3D场景，包含立方体和球体
• 创建科幻风格的室内场景

🌌 **虚拟空间**
• 创建名为"我的世界"的虚拟空间
• 构建元宇宙空间

📊 **3D可视化**
• 可视化数据点云
• 展示3D模型

🎮 **空间控制**
• 往上一点，往右一点
• 拉近，放大，旋转""",
            "agent": self.name,
        }


def get_three_d_agent(user_id: str = "default"):
    return ThreeDAgent(user_id)
