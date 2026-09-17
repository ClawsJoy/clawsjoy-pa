#!/usr/bin/env python3
"""DirectorAgent v6.0 - 电影制作导演"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from core.agents.business.business_agent import BusinessAgent


@dataclass
class FilmProject:
    title: str = ""
    genre: str = "剧情"
    status: str = "concept"
    progress: int = 0
    script: str = ""
    characters: list = field(default_factory=list)
    scenes: list = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: int = 1


class DirectorAgentV4(BusinessAgent):
    name = "director_agent_v4"
    description = "电影制作导演"
    version = "6.0.0"

    GENRES = ["动作", "喜剧", "剧情", "科幻", "奇幻", "悬疑", "爱情", "动画", "纪录片", "恐怖", "冒险"]

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self._project: Optional[FilmProject] = None
        print(f"🎬 DirectorAgent v{self.version}")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.85)

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        t = user_input.lower()

        if "创建" in t or "新项目" in t:
            return self._create(user_input)
        if "导演" in t or "出片" in t:
            return self._comic_direct()
        if not self._project:
            return self._resp("请先创建项目。输入「创建 电影名 类型」开始。\n\n示例：创建 星际迷航 科幻")

        if "剧本" in t or "写" in t:
            return self._script(user_input)
        elif "角色" in t:
            return self._characters(user_input)
        elif "场景" in t or "分镜" in t:
            return self._scenes(user_input)
        elif "审查" in t or "评估" in t:
            return self._review()
        elif "修改" in t or "精炼" in t or "优化" in t:
            return self._refine(user_input)
        elif "发布" in t or "完成" in t:
            return self._release()
        elif "导出" in t:
            return self._export()
        elif "状态" in t or "进度" in t:
            return self._status()
        else:
            return self._status()

    def _create(self, user_input: str) -> Dict:
        title = self._extract_title(user_input)
        genre = "剧情"
        for g in self.GENRES:
            if g in user_input:
                genre = g
                break
        self._project = FilmProject(title=title, genre=genre)
        return self._resp(f"## 🎬 项目创建成功\n\n**{title}** | {genre} | 概念阶段\n\n💡 输入「写剧本」开始创作")

    def _script(self, user_input: str) -> Dict:
        prompt = f"为电影《{self._project.title}》创作完整剧本。类型：{self._project.genre}。要求：三幕结构、场景标题、动作描述、角色对白、2000-4000字。"
        result = self._call_llm(prompt, task_type="script", max_tokens=4096)
        if result:
            self._project.script = result
            self._project.progress = 25
            self._project.version += 1
            self._project.updated_at = datetime.now().isoformat()
            return self._resp(f"## ✍️ 剧本完成\n\n进度25% | {len(result)}字 | v{self._project.version}\n\n{result[:800]}...")
        return self._resp("剧本生成失败")

    def _characters(self, user_input: str) -> Dict:
        prompt = f"为《{self._project.title}》设计主要角色。类型：{self._project.genre}。要求：主角(姓名/年龄/性格/动机/弧光)、配角2-3个、反派、角色关系网。"
        result = self._call_llm(prompt, task_type="character")
        if result:
            self._project.characters.append({"content": result})
            self._project.progress = max(self._project.progress, 35)
            return self._resp(f"## 🎭 角色设定\n\n{result}")
        return self._resp("角色设定失败")

    def _scenes(self, user_input: str) -> Dict:
        prompt = f"为《{self._project.title}》设计5-8个关键场景。每个场景：地点/时间/事件/角色/情绪基调/冲突密度(1-10)。"
        result = self._call_llm(prompt, task_type="scene")
        if result:
            self._project.scenes.append({"content": result})
            self._project.progress = max(self._project.progress, 45)
            return self._resp(f"## 🎨 场景设计\n\n{result}")
        return self._resp("场景设计失败")

    def _review(self) -> Dict:
        if not self._project.script:
            return self._resp("请先生成剧本")
        prompt = f"审查以下剧本，从结构/角色/对白/节奏/主题五个维度评分(1-10)并给出改进建议：\n\n{self._project.script[:3000]}"
        result = self._call_llm(prompt, task_type="review")
        return self._resp(f"## 📊 剧本审查\n\n{result}" if result else "审查失败")

    def _refine(self, user_input: str) -> Dict:
        feedback = re.sub(r"^(修改|精炼|优化)", "", user_input).strip()
        if not feedback:
            return self._resp("请说明修改意见。例如：精炼 主角对话更幽默")
        prompt = f"根据反馈修改剧本，保持整体结构不变：\n\n反馈：{feedback}\n\n剧本：{self._project.script[:3000]}"
        result = self._call_llm(prompt, task_type="refine")
        if result:
            self._project.script = result
            self._project.version += 1
            self._project.updated_at = datetime.now().isoformat()
            return self._resp(f"## ✅ 精炼完成 v{self._project.version}\n\n{result[:800]}...")
        return self._resp("精炼失败")

    def _release(self) -> Dict:
        self._project.status = "released"
        self._project.progress = 100
        self._project.updated_at = datetime.now().isoformat()
        return self._resp(
            f"## 🚀 发布完成\n\n**{self._project.title}** | {self._project.genre} | {len(self._project.script)}字"
        )

    def _export(self) -> Dict:
        path = f"/tmp/{self._project.title}_剧本.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(self._project.script)
        return self._resp(f"✅ 已导出到 {path}（{len(self._project.script)}字）")

    def _status(self) -> Dict:
        p = self._project
        return self._resp(f"**{p.title}** | {p.genre} | {p.status} | {p.progress}% | {len(p.script)}字 | v{p.version}")

    def _extract_title(self, text: str) -> str:
        for g in self.GENRES:
            text = text.replace(g, "")
        text = re.sub(r"(创建|新项目|电影|项目|一部)", "", text).strip()
        return text[:30] if text else "未命名作品"

    def _resp(self, content: str, **kwargs) -> Dict:
        return {"success": True, "response": content, "output_content": content, **kwargs}

    # ================================================================
    #  漫剧导演（新增能力）
    # ================================================================

    def _comic_direct(self, episode="EP01", frame_duration=5):
        """导演一集漫剧：llava描述 → qwen审片 → zoompan出视频"""
        import base64
        import glob as g
        import os as os_
        import shutil
        import subprocess
        import tempfile

        import requests

        storyboard_dir = f"data/assets/novels/{self._project.title}/storyboard"
        os_.makedirs(storyboard_dir, exist_ok=True)
        output = f"{storyboard_dir}/{episode}.mp4"

        # 收集分镜帧
        frames = sorted(g.glob(f"{storyboard_dir}/{episode}_分镜*.png"))
        final = {}
        for f in frames:
            num = re.search(r"分镜(\d+)", os_.path.basename(f))
            if num:
                final[num.group(1)] = f
        frames = (
            ["data/assets/novels/AI觉醒/storyboard/片头.png"]
            + [final[k] for k in sorted(final.keys())]
            + ["data/assets/novels/AI觉醒/storyboard/片尾.png"]
        )

        # 预热 llava
        try:
            requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "llava:latest", "prompt": "warmup", "stream": False},
                timeout=120,
            )
            print("llava 就绪")
        except Exception:
            pass

        # llava 逐帧描述
        print(f"llava 审片中 ({len(frames)} 帧)...")
        descriptions = []
        for i, frame in enumerate(frames):
            with open(frame, "rb") as fp:
                img = base64.b64encode(fp.read()).decode()
            try:
                r = requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "llava:latest", "prompt": "描述画面：角色、场景、光影。20字。", "images": [img], "stream": False},
                    timeout=30,
                )
                desc = r.json().get("response", "")
            except Exception:
                desc = ""
            descriptions.append("帧{}: {}".format(i, desc[:30]))  # 截断到50字
            print(f"  帧{i}: {desc[:60]}")

        # qwen 导演审片 + 镜头运动
        director_prompt = "你是漫剧导演。以下是{}个分镜的画面描述：\n{}\n\n请输出：\n1. 综合评分(1-5)与理由\n2. 缺失素材清单\n3. 每个分镜的镜头运动指令，格式：分镜N:运动类型\n   选型：zoom_in(强调情感) zoom_out(展示环境) pan_right/left(跟随视线) static(对话思考)\n4. 优先改进项".format(
            len(frames), "\n".join(descriptions)
        )

        try:
            r = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "qwen2.5:7b-instruct-q4_0", "prompt": director_prompt, "stream": False},
                timeout=120,
            )
            director_advice = r.json().get("response", "")
        except Exception as _e:
            director_advice = "导演建议生成失败"
            print(f"qwen 调用失败: {_e}")

        # 解析镜头运动
        import re as _re

        camera_moves = {0: "zoom_in"}
        for _line in director_advice.split(chr(10)):
            _m = _re.search(r"分镜\s*(\d+)\s*[:：]\s*(zoom_in|zoom_out|pan_left|pan_right|static)", _line)
            if _m:
                camera_moves[int(_m.group(1))] = _m.group(2)
        for i in range(1, len(frames)):
            if i not in camera_moves:
                camera_moves[i] = "static"

        # 逐帧 zoompan 出视频
        _tmpdir = tempfile.mkdtemp()
        processed = []
        for i, frame in enumerate(frames):
            move = camera_moves.get(i, "static")
            out_frame = "{}/f_{:03d}.mp4".format(_tmpdir, i)
            if move == "zoom_in":
                vf = "zoompan=z='min(zoom+0.001,1.1)':d=100:s=768x512"
            elif move == "zoom_out":
                vf = "zoompan=z='max(zoom-0.001,0.9)':d=100:s=768x512"
            elif move == "pan_right":
                vf = "zoompan=z=1.05:x='iw/2+10*on':y='ih/2':d=100:s=768x512"
            elif move == "pan_left":
                vf = "zoompan=z=1.05:x='iw/2-10*on':y='ih/2':d=100:s=768x512"
            else:
                vf = "zoompan=z=1.02:d=100:s=768x512"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-loop",
                    "1",
                    "-i",
                    frame,
                    "-vf",
                    vf,
                    "-t",
                    str(frame_duration),
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    out_frame,
                ],
                capture_output=True,
            )
            processed.append(out_frame)

        with open("/tmp/processed_frames.txt", "w") as f:
            for p in processed:
                f.write("file '{}'\n".format(p))
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                "/tmp/processed_frames.txt",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                output,
            ],
            capture_output=True,
        )
        shutil.rmtree(_tmpdir, ignore_errors=True)

        # 日志
        self._comic_log(
            episode, 1, {"frames": len(frames), "camera": str(camera_moves), "advice": director_advice[:500]}
        )

        return self._resp(
            "## 🎬 {} 完成\n\n帧数: {}\n镜头: {}\n\n### 🎯 导演建议\n{}\n\n文件: {}".format(
                episode, len(frames), camera_moves, director_advice, output
            )
        )

    def _comic_log(self, episode, version, data):
        """记录漫剧导演日志"""
        log_file = f"data/assets/novels/{self._project.title}/director_log.jsonl"
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        log = {"time": datetime.now().isoformat(), "episode": episode, "version": version, **data}
        with open(log_file, "a") as f:
            f.write(json.dumps(log, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    agent = DirectorAgentV4("test")
    print(agent.process("创建 星际迷航 科幻")["response"][:200])
