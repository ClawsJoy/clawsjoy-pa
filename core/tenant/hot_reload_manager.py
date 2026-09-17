#!/usr/bin/env python3
"""Hot Reload Manager - Hot Reload Manager 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""API热加载管理器 - 零代码技能注册"""
import importlib
import inspect
import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from core.tenant.tenant_vector_index import tenant_index_manager


class HotReloadManager:
    """热加载管理器 - 自动发现和注册技能"""

    VERSION = "1.0.0"

    def __init__(self):
        self.skills_registry: Dict[str, Dict] = {}
        self.tenant_skills: Dict[str, Dict] = {}
        self.watcher_thread = None
        self.running = False
        self.base_path = Path(
            f"{unified_config.get("paths.data_root", "data")}/tenants"
        )
        self.base_path.mkdir(parents=True, exist_ok=True)

    def register_skill(self, tenant_id: str, skill_id: str, skill_config: Dict) -> bool:
        """注册技能到热加载系统"""
        try:
            if tenant_id not in self.tenant_skills:
                self.tenant_skills[tenant_id] = {}

            # 技能配置
            skill = {
                "id": skill_id,
                "name": skill_config.get("name", skill_id),
                "version": skill_config.get("version", "1.0.0"),
                "description": skill_config.get("description", ""),
                "entry": skill_config.get("entry", f"{skill_id}.py"),
                "author": skill_config.get("author", "anonymous"),
                "permissions": skill_config.get("permissions", []),
                "registered_at": datetime.now().isoformat(),
                "status": "active",
            }

            self.tenant_skills[tenant_id][skill_id] = skill
            self._save_skill_manifest(tenant_id, skill_id, skill)

            print(f"✅ [热加载] 技能注册成功: {tenant_id}/{skill_id}")

            # 向量索引
            try:
                from core.tenant.tenant_vector_index import tenant_index_manager

                tenant_index_manager.index_skill(
                    tenant_id,
                    skill_id,
                    skill.get("name", skill_id),
                    skill.get("description", ""),
                    skill.get("category", "general"),
                )
            except Exception as e:
                pass
            return True

        except Exception as e:
            print(f"❌ [热加载] 注册失败: {e}")
            return False

    def unregister_skill(self, tenant_id: str, skill_id: str) -> bool:
        """卸载技能"""
        if (
            tenant_id in self.tenant_skills
            and skill_id in self.tenant_skills[tenant_id]
        ):
            del self.tenant_skills[tenant_id][skill_id]
            self._remove_skill_manifest(tenant_id, skill_id)
            print(f"🗑️ [热加载] 技能卸载: {tenant_id}/{skill_id}")
            return True
        return False

    def get_tenant_skills(self, tenant_id: str) -> Dict:
        """获取租户所有技能"""
        return self.tenant_skills.get(tenant_id, {})

    def execute_skill(self, tenant_id: str, skill_id: str, params: Dict) -> Dict:
        """执行技能 - 支持热加载"""
        if tenant_id not in self.tenant_skills:
            return {"success": False, "error": f"租户 {tenant_id} 不存在"}

        if skill_id not in self.tenant_skills[tenant_id]:
            return {"success": False, "error": f"技能 {skill_id} 不存在"}

        skill = self.tenant_skills[tenant_id][skill_id]
        skill_path = self.base_path / tenant_id / "skills" / skill["entry"]

        if not skill_path.exists():
            return {"success": False, "error": f"技能文件不存在: {skill['entry']}"}

        try:
            # 动态加载技能模块
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                f"{tenant_id}_{skill_id}", skill_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 查找 execute 函数
            if hasattr(module, "execute"):
                result = module.execute(params)
                return {"success": True, "result": result}
            else:
                return {"success": False, "error": "技能缺少 execute 函数"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def scan_and_register(self, tenant_id: str):
        """扫描目录并自动注册技能"""
        skills_dir = self.base_path / tenant_id / "skills"
        if not skills_dir.exists():
            skills_dir.mkdir(parents=True)
            return

        for skill_file in skills_dir.glob("*.py"):
            skill_id = skill_file.stem
            manifest_file = skills_dir / f"{skill_id}.manifest.json"

            if manifest_file.exists():
                with open(manifest_file, "r") as f:
                    skill_config = json.load(f)
            else:
                skill_config = {
                    "name": skill_id,
                    "version": "1.0.0",
                    "description": f"自动发现技能: {skill_id}",
                    "entry": skill_file.name,
                }

            self.register_skill(tenant_id, skill_id, skill_config)

    def start_watcher(self):
        """启动热加载监控线程"""
        if self.watcher_thread and self.watcher_thread.is_alive():
            return

        self.running = True
        self.watcher_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.watcher_thread.start()
        print("🔥 [热加载] 监控已启动，每5秒扫描一次")

    def _watch_loop(self):
        """监控循环"""
        last_state = {}

        while self.running:
            try:
                # 扫描所有租户
                for tenant_dir in self.base_path.iterdir():
                    if tenant_dir.is_dir():
                        tenant_id = tenant_dir.name
                        skills_dir = tenant_dir / "skills"
                        if skills_dir.exists():
                            current_state = {}
                            for f in skills_dir.glob("*.py"):
                                current_state[f.name] = f.stat().st_mtime

                            # 检查变化
                            old_state = last_state.get(tenant_id, {})
                            for filename, mtime in current_state.items():
                                if (
                                    filename not in old_state
                                    or old_state[filename] != mtime
                                ):
                                    skill_id = Path(filename).stem
                                    self._reload_skill(tenant_id, skill_id)

                            last_state[tenant_id] = current_state

                time.sleep(5)  # 每5秒扫描一次

            except Exception as e:
                print(f"⚠️ [热加载] 监控错误: {e}")
                time.sleep(5)

    def _reload_skill(self, tenant_id: str, skill_id: str):
        """重新加载单个技能"""
        skills_dir = self.base_path / tenant_id / "skills"
        manifest_file = skills_dir / f"{skill_id}.manifest.json"

        if manifest_file.exists():
            with open(manifest_file, "r") as f:
                skill_config = json.load(f)
        else:
            skill_config = {"name": skill_id, "entry": f"{skill_id}.py"}

        self.register_skill(tenant_id, skill_id, skill_config)
        print(f"🔄 [热加载] 重新加载: {tenant_id}/{skill_id}")

    def _save_skill_manifest(self, tenant_id: str, skill_id: str, skill: Dict):
        """保存技能清单"""
        manifest_dir = self.base_path / tenant_id / "skills"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_file = manifest_dir / f"{skill_id}.manifest.json"

        with open(manifest_file, "w") as f:
            json.dump(skill, f, indent=2, ensure_ascii=False)

    def _remove_skill_manifest(self, tenant_id: str, skill_id: str):
        """删除技能清单"""
        manifest_file = (
            self.base_path / tenant_id / "skills" / f"{skill_id}.manifest.json"
        )
        if manifest_file.exists():
            manifest_file.unlink()


# 全局实例
hot_reload = HotReloadManager()
hot_reload.start_watcher()
