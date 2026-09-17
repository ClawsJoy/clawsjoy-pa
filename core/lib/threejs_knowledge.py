#!/usr/bin/env python3
"""Threejs Knowledge - Threejs Knowledge 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""Three.js 知识库 - RAG 检索"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List


class ThreeJSKnowledgeBase:
    """Three.js 知识库管理器"""

    def __init__(self):
        self.knowledge_dir = Path(__file__).parent.parent / "knowledge" / "threejs"
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self._load_index()
        self._init_knowledge()

    def _load_index(self):
        """加载知识索引"""
        index_file = self.knowledge_dir / "index.json"
        if index_file.exists():
            with open(index_file, "r") as f:
                self.index = json.load(f)
        else:
            self.index = {}

    def _save_index(self):
        index_file = self.knowledge_dir / "index.json"
        with open(index_file, "w") as f:
            json.dump(self.index, f, indent=2)

    def _init_knowledge(self):
        """初始化 Three.js 知识"""
        knowledge_items = [
            {
                "topic": "Three.js 基础场景",
                "content": """
创建 Three.js 场景需要四个核心元素：
1. Scene - 场景容器
2. Camera - 相机（透视相机 PerspectiveCamera）
3. Renderer - 渲染器（WebGLRenderer）
4. 物体 - 添加到场景的几何体

示例代码：
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer();
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);
                """,
                "tags": ["基础", "scene", "camera", "renderer"],
            },
            {
                "topic": "环抱座舱 - 穹顶弧形",
                "content": """
实现弧形穹顶的方法：
1. 使用 SphereGeometry 取上半部分
2. 使用 TorusGeometry 做环形边框
3. 使用 CSS 3D 实现平面弧形

代码示例（CSS 3D）：
.dome {
    position: absolute;
    top: 20px;
    left: 10%;
    right: 10%;
    height: 180px;
    border-radius: 50% 50% 0 0;
    border-top: 2px solid rgba(0,243,255,0.4);
    transform: rotateX(-5deg);
    background: radial-gradient(ellipse, rgba(0,243,255,0.06), transparent);
}
                """,
                "tags": ["座舱", "穹顶", "弧形"],
            },
            {
                "topic": "环抱座舱 - 左右舱壁",
                "content": """
左右舱壁的 3D 内收效果：
左舱壁：transform: rotateY(15deg) translateZ(30px);
右舱壁：transform: rotateY(-15deg) translateZ(30px);

配合渐变增强纵深感：
background: linear-gradient(90deg, rgba(0,0,0,0.8), rgba(0,243,255,0.05));
                """,
                "tags": ["座舱", "舱壁", "3D变换"],
            },
            {
                "topic": "环抱座舱 - 中央曲面巨幕",
                "content": """
中央巨幕的曲面效果：
.screen {
    transform: rotateY(3deg) rotateX(1deg);
    background: rgba(0,50,80,0.3);
    backdrop-filter: blur(10px);
    border-radius: 30px;
    border: 1px solid rgba(0,243,255,0.4);
}

使用 CSS perspective 增强 3D 感：
.cockpit {
    perspective: 1200px;
    perspective-origin: 50% 35%;
}
                """,
                "tags": ["座舱", "巨幕", "曲面"],
            },
            {
                "topic": "全息扫描线动画",
                "content": """
全息扫描线的 CSS 动画：
.scan-line {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 100%;
    background: linear-gradient(180deg, transparent, rgba(0,243,255,0.1), transparent);
    animation: scan 3s linear infinite;
    pointer-events: none;
}
@keyframes scan {
    0% { transform: translateY(-100%); }
    100% { transform: translateY(100%); }
}
                """,
                "tags": ["动画", "全息", "扫描线"],
            },
            {
                "topic": "Three.js 环抱座舱完整示例",
                "content": """
Three.js 实现环抱座舱的完整思路：
1. 创建场景、透视相机、WebGL渲染器
2. 添加弧形穹顶（使用 SphereGeometry 或 TorusGeometry）
3. 添加左右舱壁（使用 BoxGeometry 并旋转）
4. 添加中央曲面屏幕（使用 PlaneGeometry 或自定义曲面）
5. 添加星空粒子系统
6. 添加全息扫描线效果

相机位置：camera.position.set(0, 2, 5); camera.lookAt(0, 0, 0);
                """,
                "tags": ["three.js", "完整示例", "座舱"],
            },
        ]

        for item in knowledge_items:
            doc_id = hashlib.md5(item["topic"].encode()).hexdigest()[:16]
            if doc_id not in self.index:
                self.index[doc_id] = item
                print(f"📚 加载知识: {item['topic']}")

        self._save_index()

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        """检索相关知识"""
        query_lower = query.lower()
        scored = []

        for doc_id, doc in self.index.items():
            score = 0
            # 关键词匹配
            for word in query_lower.split():
                if word in doc["topic"].lower():
                    score += 5
                if word in doc["content"].lower():
                    score += 2
                if doc.get("tags"):
                    for tag in doc["tags"]:
                        if word in tag.lower():
                            score += 3

            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]

    def get_all(self) -> List[Dict]:
        return list(self.index.values())


# 全局实例
threejs_kb = ThreeJSKnowledgeBase()
