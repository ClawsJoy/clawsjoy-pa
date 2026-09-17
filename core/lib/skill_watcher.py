#!/usr/bin/env python3
"""Skill Watcher - Skill Watcher 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import importlib
import os
import threading
import time
from pathlib import Path
from typing import Callable, Dict


class SkillWatcher:
    """skills 目录热重载监听器"""

    _instance = None
    _running = False
    _thread = None
    _file_mtimes: Dict[str, float] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def start(self):
        """启动监听"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        print("🔥 skills 目录热重载监听已启动")

    def _watch_loop(self):
        """监听循环"""
        skills_dir = Path("skills")

        while self._running:
            try:
                # 扫描所有技能文件
                for py_file in skills_dir.rglob("*.py"):
                    if py_file.stem == "__init__":
                        continue

                    current_mtime = py_file.stat().st_mtime
                    key = str(py_file)

                    if key not in self._file_mtimes:
                        self._file_mtimes[key] = current_mtime
                        print(f"📁 新技能发现: {py_file}")
                        self._reload_skill(py_file)
                    elif self._file_mtimes[key] != current_mtime:
                        self._file_mtimes[key] = current_mtime
                        print(f"🔄 技能更新: {py_file}")
                        self._reload_skill(py_file)

                time.sleep(3)
            except Exception as e:
                print(f"⚠️ 监听错误: {e}")
                time.sleep(5)

    def _reload_skill(self, skill_file: Path):
        """重新加载技能"""
        try:
            # 重新加载技能模块
            module_name = f"skills.{skill_file.parent.name}.{skill_file.stem}"
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])

            # 重新加载技能加载器
            importlib.reload(importlib.import_module("lib.skill_loader_v3"))
            print(f"   ✅ 技能已重载: {skill_file.stem}")
        except Exception as e:
            print(f"   ⚠️ 重载失败: {e}")


skill_watcher = SkillWatcher()
