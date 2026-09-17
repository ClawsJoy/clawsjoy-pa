#!/usr/bin/env python3
"""Code Generator - Code Generator 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)
from core.lib.unified_config import unified_config

"""配置驱动的代码生成器"""

import json
from pathlib import Path
from typing import Any, Dict

import yaml


class CodeGenerator:
    """配置驱动的代码生成器"""

    def __init__(self):
        self.config = self._load_config()
        self.memory = self._load_memory()
        self.templates = self._load_templates()

    def _load_config(self) -> Dict:
        config_file = Path("config/code_agent.yaml")
        if config_file.exists():
            with open(config_file, "r") as f:
                return unified_config.get("code_generator", {})
        return {}

    def _load_memory(self) -> Dict:
        memory_file = Path(f"{get_data_root()}/code_agent_memory.json")
        if memory_file.exists():
            with open(memory_file, "r") as f:
                return json.load(f)
        return {"user_preferences": {}, "generation_count": 0}

    def _save_memory(self):
        memory_file = Path(f"{get_data_root()}/code_agent_memory.json")
        memory_file.parent.mkdir(parents=True, exist_ok=True)
        with open(memory_file, "w") as f:
            json.dump(self.memory, f, indent=2)

    def _load_templates(self) -> Dict:
        """加载模板（从配置读取模板路径）"""
        templates_config = self.config.get("templates", {})
        templates = {}

        for name, cfg in templates_config.items():
            template_file = Path(cfg.get("file", ""))
            if template_file.exists():
                with open(template_file, "r") as f:
                    templates[name] = f.read()
            else:
                # 使用内置模板
                templates[name] = self._get_builtin_template(name)

        return templates

    def _get_builtin_template(self, name: str) -> str:
        """获取内置模板"""
        if name == "threejs_cockpit":
            return self._get_cockpit_template()
        return "<html><body>模板不存在</body></html>"

    def _get_cockpit_template(self) -> str:
        """获取座舱模板"""
        color = (
            self.config.get("preferences", {})
            .get("colors", {})
            .get("default", "#00f3f")
        )
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ClawsJoy 智能座舱</title>
    <style>
        body {{ margin: 0; overflow: hidden; background: #0a0a1a; }}
        #info {{ position: absolute; bottom: 20px; left: 20px; color: {color}; }}
    </style>
</head>
<body>
    <div id="info">✨ ClawsJoy 智能座舱</div>
    <script type="importmap">
        {{ "imports": {{ "three": "https://unpkg.com/three@0.128.0/build/three.module.js" }} }}
    </script>
    <script type="module">
        import * as THREE from 'three';

        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0a0a1a);

        const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.set(0, 2, 8);

        const renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        document.body.appendChild(renderer.domElement);

        // 穹顶
        const dome = new THREE.Mesh(
            new THREE.SphereGeometry(3.8, 64, 64, 0, Math.PI * 2, 0, Math.PI / 3),
            new THREE.MeshStandardMaterial({{ color: {color}, transparent: true, opacity: 0.15 }})
        );
        dome.position.y = 1.5;
        scene.add(dome);

        // 灯光
        const light = new THREE.PointLight(0x00f3ff, 0.5);
        light.position.set(0, 2, 2);
        scene.add(light);

        function animate() {{
            requestAnimationFrame(animate);
            renderer.render(scene, camera);
        }}
        animate();

        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }});
    </script>
</body>
</html>"""

    def generate(self, request: str, user_id: str = "default") -> Dict:
        """根据请求生成代码"""
        # 更新统计
        self.memory["generation_count"] = self.memory.get("generation_count", 0) + 1
        self._save_memory()

        # 识别请求类型
        if "座舱" in request or "cockpit" in request.lower():
            template = self.templates.get(
                "threejs_cockpit", self._get_cockpit_template()
            )

            # 应用用户偏好
            prefs = self.memory.get("user_preferences", {}).get(user_id, {})
            if prefs.get("color") == "purple":
                template = template.replace("#00f3f", "#9b59b6")

            return {
                "success": True,
                "code": template,
                "type": "threejs",
                "suggestions": ["调整穹顶颜色", "添加左右舱壁", "增加星空粒子"],
            }

        return {"success": False, "error": "无法识别的请求"}

    def modify(self, code: str, instruction: str) -> Dict:
        """根据指令修改代码"""
        modified = code
        if "紫色" in instruction or "purple" in instruction:
            modified = modified.replace("#00f3f", "#9b59b6")
            modified = modified.replace("0x00f3f", "0x9b59b6")

        return {"success": True, "code": modified}

    def record_feedback(self, user_id: str, feedback: str, accepted: bool):
        """记录用户反馈"""
        if user_id not in self.memory["user_preferences"]:
            self.memory["user_preferences"][user_id] = {}

        if "紫色" in feedback and accepted:
            self.memory["user_preferences"][user_id]["color"] = "purple"

        self._save_memory()
        return {"success": True}


code_generator = CodeGenerator()
