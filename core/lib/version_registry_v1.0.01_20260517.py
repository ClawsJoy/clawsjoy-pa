#!/usr/bin/env python3
"""Version Registry V1.0.01 20260517 - Version Registry V1.0.01 20260517 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""版本注册中心 v1.0.01 - 自动驱动版本号"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class VersionRegistry:
    """自动版本注册中心"""

    VERSION = "1.0.01"

    def __init__(self, root_path: Optional[Path] = None):
        self.root = Path(root_path) if root_path else Path(__file__).parent.parent
        self.registry_file = self.root / "config" / "version_registry.json"
        self.system_version_file = self.root / "VERSION"

        # 加载注册表
        self.registry = self._load_registry()

    def _load_registry(self) -> Dict:
        """加载版本注册表"""
        if self.registry_file.exists():
            with open(self.registry_file, "r") as f:
                return json.load(f)
        return {"modules": {}, "last_updated": None}

    def _save_registry(self):
        """保存版本注册表"""
        self.registry["last_updated"] = datetime.now().isoformat()
        with open(self.registry_file, "w") as f:
            json.dump(self.registry, f, indent=2, ensure_ascii=False)

    def _get_git_info(self, file_path: Path) -> Dict:
        """获取文件的 Git 信息"""
        try:
            # 获取最后一次 commit 时间
            cmd_time = f'git log -1 --format="%ai" -- "{file_path}"'
            time_result = subprocess.run(
                cmd_time, shell=True, capture_output=True, text=True, cwd=self.root
            )
            commit_time = time_result.stdout.strip()

            # 获取 commit 哈希（短）
            cmd_hash = f'git log -1 --format="%h" -- "{file_path}"'
            hash_result = subprocess.run(
                cmd_hash, shell=True, capture_output=True, text=True, cwd=self.root
            )
            commit_hash = hash_result.stdout.strip()

            # 获取 commit 次数
            cmd_count = f'git rev-list --count HEAD -- "{file_path}"'
            count_result = subprocess.run(
                cmd_count, shell=True, capture_output=True, text=True, cwd=self.root
            )
            commit_count = (
                int(count_result.stdout.strip()) if count_result.stdout.strip() else 0
            )

            return {
                "commit_count": commit_count,
                "commit_hash": commit_hash,
                "last_modified": commit_time,
                "has_git": True,
            }
        except Exception as e:
            return {"has_git": False, "error": str(e)}

    def _get_system_version(self) -> str:
        """获取系统版本"""
        if self.system_version_file.exists():
            return self.system_version_file.read_text().strip()
        return "3.0.0"

    def auto_version(self, module_path: str, module_type: str = "core") -> str:
        """自动生成模块版本号"""
        full_path = self.root / module_path

        if not full_path.exists():
            return f"v0.0.00_unknown"

        # 获取 Git 信息
        git_info = self._get_git_info(full_path)

        if git_info.get("has_git"):
            # 基于 Git 生成版本号
            system_ver = self._get_system_version()  # 3.0.0

            # 修订号 = Git commit 次数
            revision = git_info["commit_count"]
            date_str = datetime.now().strftime("%Y%m%d")
            git_hash = git_info["commit_hash"]

            version = f"v{system_ver}.{revision:02d}_{date_str}_{git_hash}"
        else:
            # 无 Git，基于文件修改时间
            mtime = full_path.stat().st_mtime
            date_str = datetime.fromtimestamp(mtime).strftime("%Y%m%d")
            version = f"v0.0.00_{date_str}_nogit"

        return version

    def register_module(
        self, module_name: str, module_path: str, module_type: str = "core"
    ) -> Dict:
        """注册模块并自动生成版本"""
        version = self.auto_version(module_path, module_type)

        self.registry["modules"][module_name] = {
            "path": module_path,
            "type": module_type,
            "version": version,
            "registered_at": datetime.now().isoformat(),
        }

        self._save_registry()
        return self.registry["modules"][module_name]

    def get_version(self, module_name: str) -> Optional[str]:
        """获取模块版本"""
        if module_name in self.registry["modules"]:
            return self.registry["modules"][module_name]["version"]
        return None

    def list_all(self) -> Dict:
        """列出所有已注册模块"""
        return self.registry.get("modules", {})

    def sync_all(self):
        """同步所有已注册模块的版本"""
        for name, info in self.registry.get("modules", {}).items():
            new_version = self.auto_version(info["path"], info["type"])
            if new_version != info["version"]:
                info["version"] = new_version
                info["updated_at"] = datetime.now().isoformat()
                print(f"🔄 {name}: {info['version']} -> {new_version}")

        self._save_registry()
        return self.registry


# 全局实例
version_registry = VersionRegistry()


# 命令行接口
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "list":
            modules = version_registry.list_all()
            print(f"已注册模块 ({len(modules)}):")
            for name, info in modules.items():
                print(f"  {info['version']}  {name}")

        elif cmd == "register":
            if len(sys.argv) >= 4:
                name, path, mtype = sys.argv[2], sys.argv[3], sys.argv[4]
                result = version_registry.register_module(name, path, mtype)
                print(f"✅ 已注册: {name} -> {result['version']}")

        elif cmd == "sync":
            version_registry.sync_all()
            print("✅ 已同步")

        elif cmd == "status":
            print(f"版本注册中心 v{version_registry.VERSION}")
            print(f"注册表文件: {version_registry.registry_file}")
            print(f"已注册模块: {len(version_registry.registry['modules'])}")
    else:
        print(version_registry.list_all())
