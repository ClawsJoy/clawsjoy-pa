#!/usr/bin/env python3
"""Workflow Executor - Workflow Executor 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.lib.skill_chain_executor import skill_chain


class WorkflowExecutor:
    """工作流执行器"""

    name = "workflow_executor"

    def __init__(self):
        self.chain_executor = skill_chain

    def execute(self, goal: str, params: dict = None) -> dict:
        """执行工作流"""
        print(f"[WorkflowExecutor] 处理目标: {goal[:50]}")

        workflow_name = self._match_workflow(goal)
        if not workflow_name:
            return {"success": False, "error": "未匹配到工作流"}

        print(f"[WorkflowExecutor] 匹配到工作流: {workflow_name}")

        exec_params = {"goal": goal}
        if params and isinstance(params, dict):
            exec_params.update(params)

        # 提取图片路径
        path_match = re.search(r"[/\w\-\.]+\.(jpg|png|jpeg|gif)", goal, re.IGNORECASE)
        if path_match:
            exec_params["input_image"] = path_match.group()
        else:
            path_match = re.search(r"(/tmp/[^\s]+)", goal)
            if path_match:
                exec_params["input_image"] = path_match.group()

        # 如果没有找到图片路径，使用默认
        if "input_image" not in exec_params:
            exec_params["input_image"] = "/tmp/valid_image.jpg"

        print(f"[WorkflowExecutor] 参数: {exec_params}")

        result = self.chain_executor.execute_workflow(workflow_name, exec_params)
        print(f"[WorkflowExecutor] 结果: {result.get('success')}")

        return result

    def _match_workflow(self, goal: str) -> str:
        """匹配工作流"""
        goal_lower = goal.lower()

        # 图片相关工作流
        image_keywords = [
            "图片",
            "识别",
            "图像",
            "描述",
            "看图",
            "image",
            "picture",
            "识别图片",
        ]
        for kw in image_keywords:
            if kw in goal_lower:
                return "image_to_text"

        # 视频相关工作流
        video_keywords = ["视频", "制作", "生成", "video"]
        for kw in video_keywords:
            if kw in goal_lower:
                return "video_maker"

        return None


workflow_executor = WorkflowExecutor()
