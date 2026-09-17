#!/usr/bin/env python3
"""技能推荐器 - 推荐系统没有的技能，支持自动下载 - 2.5 层 JSON 标准"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any

class SkillRecommender:
    """技能推荐器 - 2.5 层 JSON 标准"""

    VERSION = "2.5"

    # 在线技能仓库（OpenClaw 生态）
    REPOS = {
        "video_download": {
            "url": "https://github.com/openclaw/skill-video-download",
            "description": "下载视频技能 (YouTube, B站等)",
            "category": "media"
        },
        "image_editor": {
            "url": "https://github.com/openclaw/skill-image-editor",
            "description": "图片编辑技能 (裁剪、滤镜、文字)",
            "category": "media"
        },
        "pdf_generator": {
            "url": "https://github.com/openclaw/skill-pdf-generator",
            "description": "PDF 生成技能 (从文本/HTML生成PDF)",
            "category": "document"
        },
        "email_sender": {
            "url": "https://github.com/openclaw/skill-email-sender",
            "description": "邮件发送技能 (SMTP)",
            "category": "communication"
        },
        "api_client": {
            "url": "https://github.com/openclaw/skill-api-client",
            "description": "API 客户端技能 (REST API 调用)",
            "category": "integration"
        },
        "data_analyzer": {
            "url": "https://github.com/openclaw/skill-data-analyzer",
            "description": "数据分析技能 (CSV/Excel 分析)",
            "category": "data"
        },
        "chart_generator": {
            "url": "https://github.com/openclaw/skill-chart-generator",
            "description": "图表生成技能 (Matplotlib/Plotly)",
            "category": "visualization"
        },
        "web_scraper": {
            "url": "https://github.com/openclaw/skill-web-scraper",
            "description": "网页抓取技能 (爬虫)",
            "category": "data"
        }
    }

    def __init__(self):
        self.skills_dir = Path("skills")
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self._load_installed_skills()

    def _load_installed_skills(self):
        """加载已安装的技能列表"""
        self.installed_skills = {}
        for skill_path in self.skills_dir.iterdir():
            if skill_path.is_dir():
                self.installed_skills[skill_path.name] = {
                    "name": skill_path.name,
                    "path": str(skill_path),
                    "installed": True,
                    "has_init": (skill_path / "__init__.py").exists()
                }

    def recommend(self, user_request: str, user_id: str = "default") -> Dict:
        """
        根据用户请求推荐技能 - 2.5 层 JSON

        Args:
            user_request: 用户请求
            user_id: 用户ID

        Returns:
            2.5 层 JSON 推荐结果
        """
        recommendations = []
        request_lower = user_request.lower()

        # 关键词匹配推荐
        for skill_name, info in self.REPOS.items():
            matched = False
            if "下载" in request_lower and "video" in skill_name:
                matched = True
            elif "编辑" in request_lower and "image" in skill_name:
                matched = True
            elif "pdf" in request_lower and "pdf" in skill_name:
                matched = True
            elif "邮件" in request_lower and "email" in skill_name:
                matched = True
            elif "api" in request_lower and "api" in skill_name:
                matched = True
            elif "分析" in request_lower and "data" in skill_name:
                matched = True
            elif "图表" in request_lower and "chart" in skill_name:
                matched = True
            elif "抓取" in request_lower and "scraper" in skill_name:
                matched = True

            if matched:
                recommendations.append({
                    "name": skill_name,
                    "description": info["description"],
                    "category": info["category"],
                    "repo_url": info["url"],
                    "installed": skill_name in self.installed_skills,
                    "confidence": 0.85
                })

        return {
            "version": self.VERSION,
            "user_request": user_request,
            "user_id": user_id,
            "recommendations": recommendations,
            "total": len(recommendations),
            "status": "completed"
        }

    def install(self, skill_name: str, user_id: str = "default") -> Dict:
        """
        安装技能 - 2.5 层 JSON

        Args:
            skill_name: 技能名称
            user_id: 用户ID

        Returns:
            2.5 层 JSON 安装结果
        """
        # 检查是否已安装
        if skill_name in self.installed_skills:
            return {
                "version": self.VERSION,
                "success": True,
                "skill": skill_name,
                "message": f"技能 {skill_name} 已安装",
                "path": str(self.skills_dir / skill_name),
                "status": "already_installed"
            }

        # 检查仓库是否存在
        repo_info = self.REPOS.get(skill_name)
        if not repo_info:
            return {
                "version": self.VERSION,
                "success": False,
                "skill": skill_name,
                "error": f"未知技能: {skill_name}",
                "available": list(self.REPOS.keys()),
                "status": "not_found"
            }

        # 检查 Git 是否可用
        try:
            subprocess.run(["git", "--version"], capture_output=True, check=True)
        except Exception:
            return {
                "version": self.VERSION,
                "success": False,
                "skill": skill_name,
                "error": "Git 未安装，无法下载技能",
                "status": "git_not_available"
            }

        # 克隆仓库
        try:
            repo_url = repo_info["url"]
            target_path = self.skills_dir / skill_name

            result = subprocess.run(
                ["git", "clone", repo_url, str(target_path)],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                # 重新加载已安装技能列表
                self._load_installed_skills()

                return {
                    "version": self.VERSION,
                    "success": True,
                    "skill": skill_name,
                    "message": f"技能 {skill_name} 安装成功",
                    "path": str(target_path),
                    "status": "installed"
                }
            else:
                return {
                    "version": self.VERSION,
                    "success": False,
                    "skill": skill_name,
                    "error": result.stderr[:500],
                    "status": "clone_failed"
                }

        except subprocess.TimeoutExpired:
            return {
                "version": self.VERSION,
                "success": False,
                "skill": skill_name,
                "error": "下载超时 (120秒)",
                "status": "timeout"
            }
        except Exception as e:
            return {
                "version": self.VERSION,
                "success": False,
                "skill": skill_name,
                "error": str(e),
                "status": "error"
            }

    def get_available_skills(self) -> Dict:
        """获取所有可用技能 - 2.5 层 JSON"""
        skills = []
        for name, info in self.REPOS.items():
            skills.append({
                "name": name,
                "description": info["description"],
                "category": info["category"],
                "installed": name in self.installed_skills
            })

        return {
            "version": self.VERSION,
            "total": len(skills),
            "installed": len(self.installed_skills),
            "skills": skills,
            "status": "completed"
        }

    def uninstall(self, skill_name: str) -> Dict:
        """卸载技能 - 2.5 层 JSON"""
        import shutil

        if skill_name not in self.installed_skills:
            return {
                "version": self.VERSION,
                "success": False,
                "skill": skill_name,
                "error": f"技能 {skill_name} 未安装",
                "status": "not_installed"
            }

        skill_path = self.skills_dir / skill_name
        try:
            shutil.rmtree(skill_path)
            self._load_installed_skills()
            return {
                "version": self.VERSION,
                "success": True,
                "skill": skill_name,
                "message": f"技能 {skill_name} 已卸载",
                "status": "uninstalled"
            }
        except Exception as e:
            return {
                "version": self.VERSION,
                "success": False,
                "skill": skill_name,
                "error": str(e),
                "status": "error"
            }

# 全局实例
skill_recommender = SkillRecommender()
