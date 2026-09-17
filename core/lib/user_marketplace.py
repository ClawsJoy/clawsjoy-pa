#!/usr/bin/env python3
"""User Marketplace - User Marketplace 模块

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

"""用户商店系统 - 一键安装技能/Agent，支持基础共享+自定义"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class UserMarketplace:
    """用户商店 - 管理用户安装的技能和 Agent"""

    def __init__(self):
        self.marketplace_dir = Path(f"{get_data_root()}/marketplace")
        self.marketplace_dir.mkdir(parents=True, exist_ok=True)
        self._init_default_packages()

    def _init_default_packages(self):
        """初始化默认可安装包"""
        packages = [
            {
                "id": "language_master",
                "name": "语言大师",
                "type": "agent",
                "version": "1.0.0",
                "description": "智能翻译助手，支持中英文翻译和关键词提取",
                "base_skill": "translate_master",
                "base_agent": "translate_agent",
                "configurable": ["custom_vocab", "translation_style"],
                "price": "free",
                "popularity": 95,
            },
            {
                "id": "video_maker",
                "name": "视频制作大师",
                "type": "skill",
                "version": "1.0.0",
                "description": "一键制作漫剧视频、添加字幕、视频合成",
                "base_skill": "manju_maker",
                "configurable": ["output_format", "resolution", "fps"],
                "price": "free",
                "popularity": 88,
            },
            {
                "id": "image_processor",
                "name": "图像处理大师",
                "type": "skill",
                "version": "1.0.0",
                "description": "AI 图像生成、去背景、图片轮播",
                "base_skill": "ai_image",
                "configurable": ["width", "height", "style"],
                "price": "free",
                "popularity": 82,
            },
            {
                "id": "code_assistant",
                "name": "代码助手",
                "type": "agent",
                "version": "1.0.0",
                "description": "智能编程助手，代码生成、审查、调试",
                "base_agent": "code_agent",
                "configurable": ["language_preference", "code_style"],
                "price": "free",
                "popularity": 90,
            },
        ]

        for pkg in packages:
            pkg_file = self.marketplace_dir / f"{pkg['id']}.json"
            if not pkg_file.exists():
                with open(pkg_file, "w") as f:
                    json.dump(pkg, f, indent=2)

    def list_available(self, type_filter: str = None) -> List[Dict]:
        """列出可安装的包"""
        packages = []
        for pkg_file in self.marketplace_dir.glob("*.json"):
            with open(pkg_file, "r") as f:
                pkg = json.load(f)
                if not type_filter or pkg.get("type") == type_filter:
                    packages.append(pkg)
        return packages

    def install(
        self, user_id: str, package_id: str, custom_config: Dict = None
    ) -> Dict:
        """用户一键安装"""
        # 获取包信息
        pkg_file = self.marketplace_dir / f"{package_id}.json"
        if not pkg_file.exists():
            return {"success": False, "error": "包不存在"}

        with open(pkg_file, "r") as f:
            pkg = json.load(f)

        # 用户安装目录
        user_install_dir = Path(
            funified_config.get("paths.users_dir", f"{get_data_root()}/users/")
            + "/{user_id}/installed/{package_id}"
        )
        user_install_dir.mkdir(parents=True, exist_ok=True)

        # 保存安装记录
        install_info = {
            "package_id": package_id,
            "name": pkg["name"],
            "type": pkg["type"],
            "version": pkg["version"],
            "installed_at": datetime.now().isoformat(),
            "base_config": pkg,
            "user_config": custom_config or {},
            "status": "active",
        }

        with open(user_install_dir / "install.json", "w") as f:
            json.dump(install_info, f, indent=2)

        # 如果是 Agent，创建用户实例
        if pkg["type"] == "agent":
            self._create_user_agent_instance(user_id, pkg, custom_config)

        # 如果是技能，创建用户技能包装器
        if pkg["type"] == "skill":
            self._create_user_skill_wrapper(user_id, pkg, custom_config)

        return {
            "success": True,
            "package": pkg["name"],
            "type": pkg["type"],
            "user_id": user_id,
            "message": f"✅ 已安装 {pkg['name']}",
        }

    def _create_user_agent_instance(self, user_id: str, pkg: Dict, config: Dict):
        """创建用户 Agent 实例"""
        from core.agents.user_translate_agent import get_user_translator

        if pkg["id"] == "language_master":
            translator = get_user_translator(user_id)
            if config:
                for key, value in config.items():
                    if key == "translation_style":
                        translator.preferences["style"] = value
                translator._save_memory()
            print(f"✅ 用户 {user_id} 的语言大师实例已创建")

    def _create_user_skill_wrapper(self, user_id: str, pkg: Dict, config: Dict):
        """创建用户技能包装器"""
        user_skill_dir = Path(
            funified_config.get("paths.users_dir", f"{get_data_root()}/users/")
            + "/{user_id}/skills/{pkg['id']}"
        )
        user_skill_dir.mkdir(parents=True, exist_ok=True)

        # 创建用户技能配置
        skill_config = {
            "base_skill": pkg["base_skill"],
            "user_config": config or {},
            "created_at": datetime.now().isoformat(),
        }

        with open(user_skill_dir / "config.json", "w") as f:
            json.dump(skill_config, f, indent=2)

        print(f"✅ 用户 {user_id} 的技能 {pkg['name']} 已安装")

    def get_user_installed(self, user_id: str) -> List[Dict]:
        """获取用户已安装的包"""
        installed = []
        user_install_base = Path(
            funified_config.get("paths.users_dir", f"{get_data_root()}/users/")
            + "/{user_id}/installed"
        )
        if user_install_base.exists():
            for install_dir in user_install_base.iterdir():
                install_file = install_dir / "install.json"
                if install_file.exists():
                    with open(install_file, "r") as f:
                        installed.append(json.load(f))
        return installed

    def uninstall(self, user_id: str, package_id: str) -> Dict:
        """卸载"""
        user_install_dir = Path(
            funified_config.get("paths.users_dir", f"{get_data_root()}/users/")
            + "/{user_id}/installed/{package_id}"
        )
        if user_install_dir.exists():
            shutil.rmtree(user_install_dir)
            return {"success": True, "message": f"已卸载 {package_id}"}
        return {"success": False, "error": "未安装"}


user_marketplace = UserMarketplace()
