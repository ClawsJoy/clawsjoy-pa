#!/usr/bin/env python3
"""Config Auto Watcher - Config Auto Watcher 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from pathlib import Path

from core.lib.config_watcher import config_watcher


class ConfigAutoWatcher:
    """自动扫描并监听所有配置文件"""

    _scanned = False

    @classmethod
    def scan_and_register(cls, config_dirs: list = None):
        """扫描配置目录，自动注册监听"""
        if cls._scanned:
            return

        if config_dirs is None:
            config_dirs = [
                "config",  # 监听 config 根目录
                "config/system",
                "config/routes",
                "config/agents_soul",
                "config/butler",
                "config/agents/behaviors",
                "config/agents/registry",
                "config/skills",
                "skills/auto_generated",
            ]

        registered = 0
        for dir_path in config_dirs:
            dir_path = Path(dir_path)
            if not dir_path.exists():
                continue

            for file in list(dir_path.glob("*.yaml")) + list(dir_path.glob("*.py")):
                if cls._register_file(file):
                    registered += 1

        cls._scanned = True
        print(f"✅ 已自动注册 {registered} 个配置文件")

    @classmethod
    def _register_file(cls, file_path: Path) -> bool:
        """注册单个文件"""
        callback = cls._get_callback(file_path)
        if callback:
            config_watcher.register(str(file_path), callback)
            return True
        return False

    @classmethod
    def _get_callback(cls, file_path: Path):
        """根据文件路径返回对应的重载函数"""
        path_str = str(file_path)

        if "keywords.yaml" in path_str:
            from core.lib.unified_config import unified_config

            return unified_config._load

        if "system_unified.yaml" in path_str:
            from core.lib.unified_config import unified_config

            return unified_config._load

        if "routes.yaml" in path_str:
            from core.lib.route_registry import route_registry

            return route_registry.reload

        if "scriptbook.yaml" in path_str or "butler.yaml" in path_str:
            from agents.chat_agent.agent import ChatAgent

            return None

        if any(x in path_str for x in ["agents.yaml", "registry.yaml"]):
            from core.agents.builtin.agent_manager import agent_manager

            return agent_manager.reload

        if "skill" in path_str or "auto_generated" in path_str:
            from core.lib.skill_loader_v3 import skill_loader

            return skill_loader._load_all

        return None

    @classmethod
    def trigger_reload(cls):
        """手动触发重载"""
        print("🔄 手动触发配置重载...")
        from core.lib.unified_config import unified_config

        unified_config._load()
        from core.lib.route_registry import route_registry

        route_registry.reload()
        from core.agents.builtin.agent_manager import agent_manager

        agent_manager.reload()
        from core.lib.skill_loader_v3 import skill_loader

        skill_loader._load_all()
        print("✅ 配置重载完成")

    @classmethod
    def start(cls):
        """启动自动监听"""
        cls.scan_and_register()
        config_watcher.start()
        print("✅ 配置文件监听器已启动")


config_auto_watcher = ConfigAutoWatcher()


def start_file_watcher():
    """启动文件监听器"""
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        class ConfigFileHandler(FileSystemEventHandler):
            def on_modified(self, event):
                if event.src_path.endswith((".yaml", ".yml", ".json")):
                    print(f"📁 配置文件变更: {event.src_path}")
                    ConfigAutoWatcher.trigger_reload()

        observer = Observer()
        observer.schedule(ConfigFileHandler(), "config/", recursive=True)
        observer.start()
        print("✅ 配置文件监听器已启动")
        return observer
    except ImportError:
        print("⚠️ watchdog 未安装，文件自动重载不可用")
        return None
