"""视频反馈智能链"""

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/home/flybo/clawsjoy_v5")
from engine.semantic_params.mapper import FeedbackLearner, SemanticParamMapper


class VideoFeedbackChain:
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.mapper = SemanticParamMapper()
        self.learner = FeedbackLearner(user_id)

    def process(self, video_path: str, feedback: str) -> dict:
        adjustments = self.mapper.parse(feedback)

        for param in adjustments:
            history_pref = self.learner.get_preference(param)
            if history_pref != 0:
                adjustments[param] = (adjustments[param] + history_pref) / 2

        result = self._apply_adjustments(video_path, adjustments)
        self.learner.record(feedback, adjustments, result.get("success", False))

        return {
            "success": result.get("success", False),
            "original": video_path,
            "adjusted": result.get("adjusted"),
            "understood": adjustments,
        }

    def _apply_adjustments(self, video_path, adjustments):
        if not adjustments:
            return {"success": True, "adjusted": video_path}

        path = Path(video_path)
        if not path.exists():
            return {"success": False, "error": f"文件不存在: {video_path}"}

        output_path = (
            path.parent / f"{path.stem}_adjusted_{int(__import__('time').time())}.mp4"
        )

        # 构建亮度/对比度调整
        brightness = adjustments.get("brightness", 0)
        contrast = adjustments.get("contrast", 0)
        saturation = adjustments.get("saturation", 0)

        # 转换参数
        brightness_val = 1 + brightness
        contrast_val = 1 + contrast
        saturation_val = 1 + saturation

        # ffmpeg eq 滤镜: brightness, contrast, saturation
        filters = f"eq=brightness={brightness_val:.2f}:contrast={contrast_val:.2f}:saturation={saturation_val:.2f}"

        cmd = [
            "ffmpeg",
            "-i",
            str(path),
            "-vf",
            filters,
            "-c:a",
            "copy",
            "-y",
            str(output_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and output_path.exists():
                return {"success": True, "adjusted": str(output_path)}
            else:
                return {"success": False, "error": result.stderr[:200]}
        except Exception as e:
            return {"success": False, "error": str(e)}


class VideoFeedbackAgent:
    def __init__(self):
        self.chain = VideoFeedbackChain()

    def handle(self, message: str, context: dict = None) -> dict:
        video_match = re.search(r"([^\s]+\.mp4)", message)
        if not video_match:
            return {
                "success": False,
                "response": "请指定视频文件，如: video.mp4 画面太暗",
            }

        video_path = video_match.group(1)
        feedback = message.replace(video_path, "").strip()

        if not feedback:
            return {"success": False, "response": "请说明调整需求，如: 画面太暗"}

        result = self.chain.process(video_path, feedback)

        if result["success"]:
            return {
                "success": True,
                "response": f"已调整: {result['understood']}",
                "adjusted_video": result["adjusted"],
            }
        return {
            "success": False,
            "response": f"调整失败: {result.get('error', '未知错误')}",
        }


if __name__ == "__main__":
    agent = VideoFeedbackAgent()
    result = agent.handle("downloads/video_1780781826.mp4 画面太暗")
    print(result)
