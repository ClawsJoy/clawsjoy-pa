#!/usr/bin/env python3
"""VisionAgent v5.0 - 视觉创作与图像分析"""
import os
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from core.agents.business.business_agent import BusinessAgent
from core.lib.notify import notify as _notify
from core.lib.paths import runtime_tmp_path

_sketch_lock = threading.Lock()


def _subtitle_file() -> str:
    """字幕临时文件路径（两处调用共用，保证同值）"""
    return runtime_tmp_path("subtitles.txt")


class VisionAgentV4(BusinessAgent):
    name = "vision_agent_v4"
    description = "视觉创作与图像分析"
    version = "5.0.0"

    STYLES = ["写实", "动漫", "水彩", "油画", "素描", "像素", "3D渲染", "赛博朋克", "水墨", "浮世绘"]
    RATIOS = {"方形": "1:1", "横版": "16:9", "竖版": "9:16", "漫画": "3:4"}

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self.output_dir = Path(f"data/vision/{user_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"👁 VisionAgent v{self.version}")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.9)

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        t = user_input.lower()

        if context and context.get("skip_intent"):
            task_id = context.get("task_id", "")
            # 如果是图像生成任务，走 SD 出图
            if "图像生成" in user_input or "生成" in user_input or "画" in user_input:
                prompt = user_input.split("任务：")[-1].strip() if "任务：" in user_input else user_input
                path = self._generate_sketch(prompt, output_dir=f"{self.output_dir}/sketches")
                return {"success": True, "response": f"🎨 草图已生成: {path}"}
            from core.lib.llm_client import llm_client

            text = llm_client.generate(user_input, task_type="task_execute", timeout=120)
            return {"success": True, "response": text} if text else {"success": False, "response": ""}

        if any(kw in t for kw in ["分析视频", "视频分析", "视频内容"]):
            import threading

            path = self._extract_path(user_input)
            if not path:
                return self._resp("请提供视频文件路径")
            video_path = str(Path(path))
            if not Path(video_path).exists():
                return self._resp(f"视频不存在: {path}")

            import os

            from core.lib.v8.video_analyzer import VideoAnalyzer

            def _async_analyze(video_path, subtitle_path):
                try:
                    analyzer = VideoAnalyzer()
                    result = analyzer.analyze(video_path, subtitle_path)
                    import time

                    import requests as _r

                    for s in result.get("scenes", []):
                        msg = f"📹 场景{s['id']} [{s['start']:.0f}s-{s['end']:.0f}s]: {s.get('frame_analysis','')[:200]}"
                        _notify("视频分析", msg)
                        time.sleep(0.5)
                    report = result.get("report", "")
                    for i in range(0, len(report), 1900):
                        _notify("视频分析", report[i : i + 1900])
                        time.sleep(0.5)
                except Exception as e:
                    print(f"[Vision] 异步分析失败: {e}")

            threading.Thread(
                target=_async_analyze,
                args=(video_path, _subtitle_file() if os.path.exists(_subtitle_file()) else None),
                daemon=True,
            ).start()
            return self._resp("🔍 正在分析视频，请稍候...")

        if any(
            kw in t
            for kw in [
                "批量分析图片",
                "分析目录图片",
                "目录图片分析",
            ]
        ):
            import glob
            import os
            import threading

            path = self._extract_path(user_input)
            if not path:
                return self._resp("请提供目录路径")
            dir_path = path if os.path.isdir(path) else str(Path(path).parent)
            if not os.path.isdir(dir_path):
                return self._resp(f"目录不存在: {dir_path}")

            def _async_batch():
                import datetime
                import json

                try:
                    images = sorted(
                        glob.glob(f"{dir_path}/*.png")
                        + glob.glob(f"{dir_path}/*.jpg")
                        + glob.glob(f"{dir_path}/*.jpeg")
                    )
                    # 支持 006-021 范围过滤
                    import re

                    range_match = re.search(r"(\d+)[-–](\d+)", user_input)

                    if range_match:
                        start, end = int(range_match.group(1)), int(range_match.group(2))
                        filtered = []
                        for img in images:
                            m = re.search(r"(\d+)", os.path.basename(img))
                            if m and start <= int(m.group(1)) <= end:
                                filtered.append(img)
                        images = filtered
                    # 支持 6月份 过滤
                    month_match = re.search(r"(\d+)\s*月", user_input)
                    if month_match:
                        target_month = int(month_match.group(1))

                        filtered = []
                        for img in images:
                            mtime = os.path.getmtime(img)
                            dt = datetime.datetime.fromtimestamp(mtime)
                            if dt.month == target_month:
                                filtered.append(img)
                        images = filtered
                    # 续任务：跳过已分析的文件
                    analyzed_files = set()
                    results_file = f"{dir_path}/_batch_results.jsonl"
                    if os.path.exists(results_file):
                        with open(results_file, encoding="utf-8") as f:
                            for line in f:
                                try:
                                    item = json.loads(line)
                                    analyzed_files.add(item.get("file", ""))
                                except Exception:
                                    pass

                    images = [img for img in images if os.path.basename(img) not in analyzed_files]

                    if not images and analyzed_files:
                        _notify("图片分析", f"✅ 全部 {len(analyzed_files)} 张已分析，可直接导出报告")
                        return

                    if not images:
                        _notify("图片分析", f"📁 {dir_path}: 未找到图片")
                        return

                    from core.lib.llm_client import llm_client
                    from core.lib.v8.video_analyzer import VideoAnalyzer

                    analyzer = VideoAnalyzer()
                    results = []
                    for i, img in enumerate(images):
                        desc = analyzer._analyze_frame(img, mode="image")
                        results.append({"file": os.path.basename(img), "analysis": desc[:300]})
                        # 持久化到文件
                        results_file = f"{dir_path}/_batch_results.jsonl"
                        with open(results_file, "a", encoding="utf-8") as f:
                            f.write(
                                json.dumps({"file": os.path.basename(img), "analysis": desc[:300]}, ensure_ascii=False)
                                + "\n"
                            )
                        _notify("图片分析", f"🖼 [{i+1}/{len(images)}] {os.path.basename(img)}:\n{desc[:500]}")
                        time.sleep(0.3)

                    # 1. 去重
                    try:
                        import hashlib
                        from collections import defaultdict

                        hash_groups = defaultdict(list)
                        for img in images:
                            with open(img, "rb") as f:
                                file_hash = hashlib.md5(f.read()).hexdigest()
                            hash_groups[file_hash].append(img)
                        duplicates = {h: imgs for h, imgs in hash_groups.items() if len(imgs) > 1}
                        if duplicates:
                            dup_count = sum(len(imgs) - 1 for imgs in duplicates.values())
                            _notify("图片分析", f"🔍 发现 {dup_count} 张重复图片")
                            dup_dir = f"{dir_path}/_duplicates"
                            os.makedirs(dup_dir, exist_ok=True)
                            for h, imgs in duplicates.items():
                                for dup in imgs[1:]:
                                    shutil.move(dup, f"{dup_dir}/{os.path.basename(dup)}")
                            _notify("图片分析", f"✅ 重复图片已移至 _duplicates")
                            images = [img for img in images if os.path.exists(img)]
                        else:
                            _notify("图片分析", "✅ 未发现重复图片")
                    except Exception as e:
                        _notify("图片分析", f"⚠ 去重失败: {e}")

                    # 2. 打标签
                    try:
                        tags_file = f"{dir_path}/_tags.json"
                        tag_data = {}
                        for r in results:
                            if os.path.exists(f"{dir_path}/{r['file']}"):
                                tag_prompt = (
                                    f"根据以下图片分析，提取1-2个简短分类标签（如：科幻、人物、界面、数据图表、游戏、电影、聊天、代码）。只输出标签，用逗号分隔：{r['analysis']}"
                                )
                                tags = llm_client.generate(tag_prompt).strip()
                                tag_data[r["file"]] = {"tags": tags, "analysis": r["analysis"][:200]}
                        with open(tags_file, "w", encoding="utf-8") as f:
                            json.dump(tag_data, f, ensure_ascii=False, indent=2)
                        _notify("图片分析", f"🏷 标签已保存至 _tags.json")
                    except Exception as e:
                        _notify("图片分析", f"⚠ 打标签失败: {e}")

                    # 3. 生成缩略图
                    try:
                        thumb_dir = f"{dir_path}/_thumbnails"
                        os.makedirs(thumb_dir, exist_ok=True)
                        from PIL import Image

                        count = 0
                        for img in images[:50]:
                            if os.path.exists(img):
                                im = Image.open(img)
                                im.thumbnail((200, 200))
                                im.save(f"{thumb_dir}/thumb_{os.path.basename(img)}")
                                count += 1
                        _notify("图片分析", f"🖼 缩略图已生成 {count} 张")
                    except Exception as e:
                        _notify("图片分析", f"⚠ 缩略图失败: {e}")

                    # 4. 分类整理（从标签读取）
                    try:
                        import json as _json
                        import shutil

                        tags_file = f"{dir_path}/_tags.json"
                        if os.path.exists(tags_file):
                            with open(tags_file, encoding="utf-8") as f:
                                tag_data = _json.load(f)
                            mapping = {}
                            for fname, info in tag_data.items():
                                tags = info.get("tags", "")
                                # 清洗标签
                                clean_tags = []
                                for t in tags.split(","):
                                    t = t.strip().strip("：:").strip()
                                    if len(t) <= 8 and "关键词" not in t and "标签" not in t:
                                        clean_tags.append(t)
                                first_tag = clean_tags[0] if clean_tags else "未分类"
                                mapping[fname] = first_tag
                            count = 0
                            for fname, subdir in mapping.items():
                                src = f"{dir_path}/{fname}"
                                dst_dir = f"{dir_path}/{subdir}"
                                os.makedirs(dst_dir, exist_ok=True)
                                if os.path.exists(src):
                                    shutil.move(src, f"{dst_dir}/{fname}")
                                    count += 1
                            _notify("图片分析", f"✅ 整理完成，{count} 个文件已按标签分类移动到子目录")
                        else:
                            _notify("图片分析", "⚠ 未找到标签数据，跳过整理")
                    except Exception as e:
                        _notify("图片分析", f"⚠ 整理失败: {e}")
                    # 5. 导出报告
                    _notify("图片分析", f"📄 results示例: {results[0] if results else '空'}")
                    # 从文件加载 results（支持续任务）
                    results_file = f"{dir_path}/_batch_results.jsonl"
                    results = []
                    if os.path.exists(results_file):
                        with open(results_file, encoding="utf-8") as f:
                            for line in f:
                                results.append(json.loads(line))
                    _notify("图片分析", f"📄 results示例: {results[0] if results else '空'}")
                    if re.search(r"导出|报告|report", user_input) and results:
                        report_file = f"{dir_path}/_analysis_report.md"
                        with open(report_file, "w", encoding="utf-8") as f:
                            f.write(f"# 图片分析报告\n\n")
                            f.write(f"目录: {dir_path}\n")
                            f.write(f"图片数: {len(images)}\n")
                            f.write(f"分析时间: {datetime.datetime.now()}\n\n")
                            f.write(f"## 分类建议\n{suggestion}\n\n")
                            f.write(f"## 逐张分析\n")
                            for idx, r in enumerate(results):
                                try:
                                    line = f"- **{r['file']}**: {r['analysis'][:200]}\n"
                                    f.write(line)
                                except Exception as e:
                                    f.write(f"- **{r.get('file', f'item{idx}')}**: 写入失败: {e}\n")
                        _notify("图片分析", f"📄 报告已导出至 _analysis_report.md（{len(results)}条分析）")

                except Exception as e:
                    print(f"[Vision] 批量分析失败: {e}")

            import time

            import requests as _r

            threading.Thread(target=_async_batch, daemon=True).start()
            return self._resp(f"🔍 正在批量分析 {dir_path} 目录下的图片，请稍候...")

        if any(kw in t for kw in ["分析图片", "图片分析", "分析图像", "识别图片"]):
            path = self._extract_path(user_input)
            if not path:
                return self._resp("请提供图片路径")
            if not Path(path).exists():
                return self._resp(f"图片不存在: {path}")
            from core.lib.v8.video_analyzer import VideoAnalyzer

            analyzer = VideoAnalyzer()
            result = analyzer._analyze_frame(path, mode="image")
            return self._resp(f"🖼  图片分析:\n{result}")
        if any(kw in t for kw in ["导出报告", "导出分析报告"]):
            return self._export_report(user_input)
        if any(kw in t for kw in ["整理图片", "整理文件", "分类整理"]):
            return self._organize_images(user_input)
        if any(kw in t for kw in ["生成草图", "出草图", "文生图"]):
            prompt = re.sub(r"(生成草图|出草图|文生图)", "", user_input).strip()
            if not prompt:
                return self._resp("请提供草图描述")

            output_dir = f"{self.output_dir}/sketches"
            os.makedirs(output_dir, exist_ok=True)

            # 拿到包工头上下文
            task_id = context.get("task_id", "") if context else ""
            created_by = context.get("created_by", "") if context else ""
            server_id = context.get("server_id", "default") if context else "default"
            channel_id = context.get("channel_id", "") if context else ""

            import threading

            def _async_sketch():
                try:
                    with _sketch_lock:
                        path = self._generate_sketch(prompt, output_dir=output_dir)
                    # 通知 Discord
                    if channel_id:
                        import requests as _r

                        _r.post(
                            "http://localhost:5002/v8/discord/notify",
                            json={"channel_id": channel_id, "message": f"🎨 草图已生成: {path}", "username": "草图"},
                            timeout=10,
                        )
                    # 更新包工头任务状态
                    if task_id:
                        from core.lib.v8.task_engine import task_engine

                        task_data = task_engine.get(server_id, task_id)
                        if task_data:
                            task_data["output"] = path
                            task_engine.transition(server_id, task_id, "done", f"草图已生成: {path}")

                except Exception as e:
                    print(f"[Sketch] 生成失败: {e}")

            threading.Thread(target=_async_sketch, daemon=True).start()
            return self._resp("🎨 正在生成草图，请稍候...")
        if any(kw in t for kw in ["生成", "画", "创建", "绘制"]):
            return self._generate(user_input)
        elif any(kw in t for kw in ["分析", "识别", "描述图"]):
            return self._analyze(user_input)
        elif any(kw in t for kw in ["角色立绘", "人物图"]):
            return self._character_sheet(user_input)
        elif any(kw in t for kw in ["场景图", "背景"]):
            return self._scene_image(user_input)
        elif any(kw in t for kw in ["分镜画面", "漫剧画面"]):
            return self._storyboard_frame(user_input)
        elif any(kw in t for kw in ["风格", "画风"]):
            return self._list_styles()
        else:
            return self._help()

    def _generate(self, user_input: str) -> Dict:
        """通用图像生成 - 使用 DreamShaper 出图"""
        prompt = self._clean_prompt(user_input)
        style = self._detect_style(user_input)
        ratio = self._detect_ratio(user_input)

        enhanced = self._call_llm(
            f"作为AI绘画专家，将以下描述优化为Stable Diffusion英文提示词，包含画风、光照、构图、细节：\n\n{prompt}\n\n风格：{style}\n比例：{ratio}\n\n只输出英文提示词：",
            task_type="prompt_enhance",
        )
        final_prompt = enhanced or prompt

        try:
            with _sketch_lock:
                path = self._generate_sketch(final_prompt, output_dir=f"{self.output_dir}/sketches")
            return self._resp(f"🎨 图像已生成\n\n**提示词**: {prompt}\n**风格**: {style}\n**比例**: {ratio}\n**文件**: {path}")
        except Exception as e:
            return self._resp(
                f"🎨 图像生成失败: {e}\n\n**增强提示词**: `{final_prompt}`\n\n💡 可手动使用此提示词在 Stable Diffusion / Midjourney 生成"
            )

    def _generate_sketch(
        self,
        prompt: str,
        output_dir: str = "/tmp",
        negative_prompt: str = "low quality, blurry",
        steps: int = 15,
        width: int = 768,
        height: int = 768,
    ) -> str:
        """文生图草图 - DreamShaper XL"""
        import os

        import torch
        from diffusers import StableDiffusionXLPipeline

        pipe = StableDiffusionXLPipeline.from_pretrained(
            "/mnt/d/clawsjoy_clean/models/dreamshaper", torch_dtype=torch.float16, variant="fp16"
        )
        pipe.enable_model_cpu_offload()

        image = pipe(
            prompt=prompt, negative_prompt=negative_prompt, num_inference_steps=steps, width=width, height=height
        ).images[0]

        os.makedirs(output_dir, exist_ok=True)
        output_path = f"{output_dir}/{hash(prompt) & 0xFFFFFFFF}.png"
        image.save(output_path)
        return output_path

    def _character_sheet(self, user_input: str) -> Dict:
        """角色立绘生成"""
        prompt = self._clean_prompt(user_input)

        enhanced = self._call_llm(
            f"生成角色立绘提示词，包含：全身像、服装细节、发型、表情、三视图(front/side/back)、白色背景、高质量：\n\n{prompt}\n\n只输出英文提示词：",
            task_type="character_sheet",
        )

        return self._resp(
            f"## 👤 角色立绘\n\n"
            f"**角色**: {prompt}\n"
            f"**提示词**: `{enhanced or prompt}`\n\n"
            f"💡 建议搭配 ControlNet OpenPose 控制姿态"
        )

    def _scene_image(self, user_input: str) -> Dict:
        """场景图生成"""
        prompt = self._clean_prompt(user_input)

        enhanced = self._call_llm(
            f"生成场景概念图提示词，包含：环境、氛围、光照、景深、广角、高质量：\n\n{prompt}\n\n只输出英文提示词：", task_type="scene_image"
        )

        return self._resp(
            f"## 🏞 场景图\n\n" f"**场景**: {prompt}\n" f"**提示词**: `{enhanced or prompt}`\n\n" f"💡 建议使用 16:9 横版比例"
        )

    def _storyboard_frame(self, user_input: str) -> Dict:
        """漫剧分镜画面"""
        prompt = self._clean_prompt(user_input)

        enhanced = self._call_llm(
            f"生成漫剧分镜画面提示词，包含：角色动作、表情、场景、镜头角度、漫画风格、清晰线条：\n\n{prompt}\n\n只输出英文提示词：", task_type="storyboard_frame"
        )

        return self._resp(
            f"## 🎬 分镜画面\n\n" f"**画面**: {prompt}\n" f"**提示词**: `{enhanced or prompt}`\n\n" f"💡 建议使用 3:4 比例，配合分镜脚本使用"
        )

    def _analyze(self, user_input: str) -> Dict:
        """图像分析 - 使用 llava 模型"""
        path = self._extract_path(user_input)
        if not path:
            return self._resp("请提供图像路径。例如：分析 data/vision/demo/characters/林浩/01_素体_正面.png")

        img_path = Path(path)
        if not img_path.exists():
            return self._resp(f"图像不存在: {path}")

        # 提取问题（"分析 xxx 有什么问题" → question）
        question = user_input.replace(path, "").strip()
        if not question or len(question) < 3:
            question = "描述这张图片的内容、画风、质量，是否有手指/面部畸形？"

        try:
            import base64

            import requests

            with open(img_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()

            resp = requests.post(
                "http://localhost:11435/api/generate",
                json={"model": "llava:latest", "prompt": question, "images": [img_b64], "stream": False},
                timeout=60,
            )
            if resp.status_code == 200:
                description = resp.json().get("response", "无描述")
                return self._resp(
                    f"## 🖼 图像分析\n\n"
                    f"**文件**: {path}\n"
                    f"**大小**: {img_path.stat().st_size}B\n\n"
                    f"**llava 描述**:\n{description}"
                )
            else:
                return self._resp(f"llava 调用失败: {resp.status_code}")
        except Exception as e:
            return self._resp(f"分析失败: {e}")

    def _list_styles(self) -> Dict:
        return self._resp(
            f"## 🎨 可用风格\n\n"
            + "\n".join(f"• {s}" for s in self.STYLES)
            + f"\n\n## 📐 可用比例\n\n"
            + "\n".join(f"• {k} ({v})" for k, v in self.RATIOS.items())
        )

    def _help(self) -> Dict:
        return self._resp(
            "👁 **视觉助手**\n\n"
            "• 生成 海边日落 动漫风格\n"
            "• 角色立绘 年轻女科学家\n"
            "• 场景图 未来城市夜景\n"
            "• 分镜画面 主角震惊表情 特写\n"
            "• 分析 /path/to/image.png\n"
            "• 风格 查看所有画风"
        )

    def _clean_prompt(self, text: str) -> str:
        for kw in ["生成", "画", "创建", "绘制", "角色立绘", "场景图", "分镜画面", "图片"]:
            text = text.replace(kw, "")
        return text.strip() or "美丽风景"

    def _detect_style(self, text: str) -> str:
        for s in self.STYLES:
            if s in text:
                return s
        return "写实"

    def _detect_ratio(self, text: str) -> str:
        for k in self.RATIOS:
            if k in text:
                return k
        return "方形"

    def _extract_path(self, text: str) -> str:
        # 先匹配文件路径（带扩展名）
        m = re.search(r"(/[^\s]+\.\w{2,5})", text)
        if m:
            return m.group(1)
        # 再匹配目录路径（以/结尾或后面跟空格）
        m = re.search(r"(/[^\s]+/)", text)
        if m:
            return m.group(1)
        # 匹配不带扩展名的路径
        m = re.search(r"(/[^\s]+)", text)
        if m:
            path = m.group(1)
            if not any(path.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".mp4", ".txt"]):
                return path
        return ""

    def _resp(self, content: str, **kwargs) -> Dict:
        return {"success": True, "response": content, "output_content": content, **kwargs}

    def _analyze_video(self, user_input: str) -> Dict:
        """分析视频内容 - 逆向工程分析"""
        path = self._extract_path(user_input)
        if not path:
            return self._resp("请提供视频文件路径")

        video_path = Path(path)
        if not video_path.exists():
            return self._resp(f"视频不存在: {path}")

        import os

        from core.lib.v8.video_analyzer import VideoAnalyzer

        analyzer = VideoAnalyzer()
        subtitle_path = _subtitle_file()

        result = analyzer.analyze(str(video_path), subtitle_path if os.path.exists(subtitle_path) else None)

        if "error" in result:
            return self._resp(f"分析失败: {result['error']}")

        stats = result.get("stats", {})
        report = result.get("report", "")
        scenes_count = len(result.get("scenes", []))

        return self._resp(
            f"📹 **{result['file']}**\n\n"
            f"📊 场景数: {scenes_count} | 总时长: {stats.get('总时长', '?')}\n\n"
            f"📋 **制作分析报告**:\n{report}"
        )

    def _export_report(self, user_input: str) -> Dict:
        """从 jsonl 加载分析结果，导出报告"""
        path = self._extract_path(user_input)
        if not path:
            return self._resp("请提供目录路径")
        dir_path = path if os.path.isdir(path) else str(Path(path).parent)

        results_file = f"{dir_path}/_batch_results.jsonl"
        if not os.path.exists(results_file):
            return self._resp(f"未找到分析结果: {results_file}")

        import json

        results = []
        with open(results_file, encoding="utf-8") as f:
            for line in f:
                results.append(json.loads(line))

        if not results:
            return self._resp("分析结果为空")

        report_file = f"{dir_path}/_analysis_report.md"
        from datetime import datetime

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(f"# 图片分析报告\n\n")
            f.write(f"目录: {dir_path}\n")
            f.write(f"图片数: {len(results)}\n")
            f.write(f"分析时间: {datetime.now()}\n\n")
            f.write(f"## 逐张分析\n")
            for idx, r in enumerate(results):
                try:
                    line = f"- **{r['file']}**: {r['analysis'][:200]}\n"
                    f.write(line)
                except Exception as e:
                    f.write(f"- **{r.get('file', f'item{idx}')}**: 写入失败: {e}\n")

        return self._resp(f"📄 报告已导出至 _analysis_report.md（{len(results)}条分析）")

    def _organize_images(self, user_input: str) -> Dict:
        """从标签数据读取分类，整理文件"""
        path = self._extract_path(user_input)
        if not path:
            return self._resp("请提供目录路径")
        dir_path = path if os.path.isdir(path) else str(Path(path).parent)

        tags_file = f"{dir_path}/_tags.json"
        if not os.path.exists(tags_file):
            return self._resp(f"未找到标签数据，请先批量分析: {tags_file}")

        import json
        import shutil

        with open(tags_file, encoding="utf-8") as f:
            tag_data = json.load(f)

        mapping = {}
        for fname, info in tag_data.items():
            tags = info.get("tags", "")
            clean_tags = []
            for t in tags.split(","):
                t = t.strip().strip("：:").strip()
                if len(t) <= 8 and "关键词" not in t and "标签" not in t:
                    clean_tags.append(t)
            first_tag = clean_tags[0] if clean_tags else "未分类"
            mapping[fname] = first_tag
        count = 0
        for fname, subdir in mapping.items():
            src = f"{dir_path}/{fname}"
            dst_dir = f"{dir_path}/{subdir}"
            os.makedirs(dst_dir, exist_ok=True)
            if os.path.exists(src):
                shutil.move(src, f"{dst_dir}/{fname}")
                count += 1

        return self._resp(f"✅ 整理完成，{count} 个文件已按标签分类移动到子目录")


if __name__ == "__main__":
    agent = VisionAgentV4("test")
    print(agent.process("生成 海边日落 动漫风格")["response"][:300])
