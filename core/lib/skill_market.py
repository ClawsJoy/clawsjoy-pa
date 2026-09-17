#!/usr/bin/env python3
"""Skill Market - Skill Market 模块

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

"""技能市场 - 社区技能共享"""
import json
from datetime import datetime
from pathlib import Path

import requests


class SkillMarket:
    def __init__(self, market_file=f"{get_data_root()}/skill_market.json"):
        self.market_file = Path(market_file)
        self.skills = self._load()

    def _load(self):
        if self.market_file.exists():
            with open(self.market_file, "r") as f:
                return json.load(f)
        return {"local": [], "remote": []}

    def _save(self):
        with open(self.market_file, "w") as f:
            json.dump(self.skills, f, indent=2)

    def publish(self, skill_name, author, description, version="1.0.0"):
        """发布技能到市场"""
        skill_info = {
            "name": skill_name,
            "author": author,
            "description": description,
            "version": version,
            "published_at": datetime.now().isoformat(),
            "downloads": 0,
        }

        if skill_info not in self.skills["local"]:
            self.skills["local"].append(skill_info)
            self._save()
            return {"success": True, "message": f"技能 {skill_name} 已发布"}
        return {"success": False, "error": "技能已存在"}

    def list_local(self):
        return self.skills["local"]

    def list_remote(self, market_url=None):
        """从远程市场获取技能"""
        if market_url:
            try:
                resp = requests.get(f"{market_url}/api/market/skills", timeout=10)
                if resp.status_code == 200:
                    return resp.json().get("skills", [])
            except Exception as e:
                pass
        return []

    def install(self, skill_name, source_url=None):
        """安装技能"""
        # 从远程下载技能
        if source_url:
            try:
                resp = requests.get(
                    f"{source_url}/api/market/skills/{skill_name}/download",
                    timeout=unified_config.get("timeouts.default", 30),
                )
                if resp.status_code == 200:
                    skill_code = resp.text
                    skill_path = Path(f"skills/market_{skill_name}.py")
                    skill_path.write_text(skill_code)
                    return {"success": True, "message": f"技能 {skill_name} 已安装"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "需要提供源地址"}


skill_market = SkillMarket()
