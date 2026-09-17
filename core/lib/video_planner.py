#!/usr/bin/env python3
"""Video Planner - Video Planner 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""视频规划集成 - 使用 video-director 技能"""
import json
import subprocess

from core.lib.memory_simple import memory


class VideoPlanner:
    def __init__(self, skill_path="skills/video-director"):
        self.skill_path = skill_path

    def create_plan(self, topic, segments):
        """调用 video-director 生成分镜规划"""
        try:
            result = subprocess.run(
                [
                    "node",
                    f"{self.skill_path}/scripts/plan.js",
                    topic,
                    json.dumps(segments),
                ],
                capture_output=True,
                text=True,
                timeout=unified_config.get("timeouts.default", 30),
            )

            # 提取 JSON（输出中可能包含日志前缀）
            output = result.stdout
            start = output.find("{")
            end = output.rfind("}") + 1

            if start != -1 and end > start:
                plan = json.loads(output[start:end])
                return {"success": True, "plan": plan}
            else:
                return {"success": False, "error": "未找到 JSON 输出"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def plan_with_memory(self, topic, base_segments):
        """基于记忆生成规划"""
        # 从记忆获取偏好
        prefs = memory.recall("preference")
        style = memory.recall("style")

        # 增强 segments
        enhanced_segments = []
        for seg in base_segments:
            enhanced_seg = seg.copy()
            if prefs:
                enhanced_seg["text"] = f"{prefs[0]}，{seg.get('text', '')}"
            enhanced_segments.append(enhanced_seg)

        return self.create_plan(topic, enhanced_segments)

    def save_plan(self, plan, filename="output/video_plan.json"):
        """保存规划到文件"""
        import json

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)
        return filename


# 全局实例
planner = VideoPlanner()

if __name__ == "__main__":
    # 测试
    test_segments = [{"text": "李浩的优才计划", "emoji": "🌊", "title": "追梦香港"}]

    result = planner.create_plan("香港故事", test_segments)
    if result["success"]:
        print(f"✅ 规划成功，{len(result['plan']['scenes'])} 个场景")
        print(f"   总时长: {result['plan']['totalDuration']} 秒")
    else:
        print(f"❌ 失败: {result['error']}")
