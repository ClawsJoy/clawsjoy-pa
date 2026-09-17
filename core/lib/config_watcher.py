#!/usr/bin/env python3
"""Config Watcher - Config Watcher 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import threading
import time
from pathlib import Path
from typing import Callable, Dict


class ConfigWatcher:
    _instance = None
    _callbacks: Dict[str, Callable] = {}
    _file_mtimes: Dict[str, float] = {}
    _running = False
    _thread = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, config_path: str, callback: Callable):
        full_path = str(Path(config_path).absolute())
        self._callbacks[full_path] = callback
        if Path(full_path).exists():
            self._file_mtimes[full_path] = Path(full_path).stat().st_mtime
        print(f"📁 监听配置: {Path(config_path).name}")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        print("🔥 配置热重载监听已启动")

    def _watch_loop(self):
        while self._running:
            try:
                for config_path, callback in self._callbacks.items():
                    path = Path(config_path)
                    if path.exists():
                        current_mtime = path.stat().st_mtime
                        if config_path in self._file_mtimes:
                            if current_mtime != self._file_mtimes[config_path]:
                                self._file_mtimes[config_path] = current_mtime
                                print(f"🔄 配置变更: {path.name}")
                                try:
                                    callback()
                                except Exception as e:
                                    print(f"⚠️ 回调执行失败: {e}")
                        else:
                            self._file_mtimes[config_path] = current_mtime
                time.sleep(2)
            except Exception as e:
                print(f"⚠️ 监听错误: {e}")
                time.sleep(5)

    def stop(self):
        self._running = False

    def register(self, config_path: str, callback: Callable):
        full_path = str(Path(config_path).absolute())
        self._callbacks[full_path] = callback
        if Path(full_path).exists():
            self._file_mtimes[full_path] = Path(full_path).stat().st_mtime
        print(f"📁 监听配置: {Path(config_path).name}")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        print("🔥 配置热重载监听已启动")

    def _watch_loop(self):
        while self._running:
            try:
                for config_path, callback in self._callbacks.items():
                    path = Path(config_path)
                    if path.exists():
                        current_mtime = path.stat().st_mtime
                        if config_path in self._file_mtimes:
                            if current_mtime != self._file_mtimes[config_path]:
                                self._file_mtimes[config_path] = current_mtime
                                print(f"🔄 配置变更: {path.name}")
                                try:
                                    callback()
                                except Exception as e:
                                    print(f"⚠️ 回调执行失败: {e}")
                        else:
                            self._file_mtimes[config_path] = current_mtime
                time.sleep(2)
            except Exception as e:
                print(f"⚠️ 监听错误: {e}")
                time.sleep(5)

    def stop(self):
        self._running = False


config_watcher = ConfigWatcher()
