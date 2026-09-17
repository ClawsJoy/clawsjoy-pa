#!/usr/bin/env python3
"""Version Registry V1.0.02 20260517 - Version Registry V1.0.02 20260517 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""版本注册中心 v1.0.02 - JSON存储 + YAML导出"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# 尝试导入 yaml（可选）
try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class VersionRegistry:
    """版本注册中心 - 程序自动写入 JSON，可导出 YAML 供人工查看"""

    VERSION = "1.0.02"

    def __init__(self, root_path: Optional[Path] = None):
        self.root = Path(root_path) if root_path else Path(__file__).parent.parent

        # 主要存储：JSON（程序读写）
        self.json_file = self.root / "config" / "version_registry.json"

        # 可选导出：YAML（人工可读）
        self.yaml_file = self.root / "config" / "version_registry.yaml"

        # 系统版本文件
        self.system_version_file = self.root / "VERSION"

        # 加载注册表
        self.registry = self._load_registry()

    def _load_registry(self) -> Dict:
        """从 JSON 加载注册表"""
        if self.json_file.exists():
            with open(self.json_file, "r") as f:
                return json.load(f)
        return {
            "version": self.VERSION,
            "system_version": self._get_system_version(),
            "modules": {},
            "created_at": datetime.now().isoformat(),
            "last_updated": None,
            "format": "json",
        }

    def _save_registry(self):
        """保存注册表到 JSON（主存储）"""
        self.registry["last_updated"] = datetime.now().isoformat()

        with open(self.json_file, "w") as f:
            json.dump(self.registry, f, indent=2, ensure_ascii=False)

        # 同时导出 YAML（如果可用）
        self._export_yaml()

    def _export_yaml(self):
        """导出到 YAML（人工可读）"""
        if not YAML_AVAILABLE:
            return

        try:
            with open(self.yaml_file, "w") as f:
                yaml.dump(
                    self.registry, f, default_flow_style=False, allow_unicode=True
                )
        except Exception:
            pass

    def _get_system_version(self) -> str:
        """获取系统版本"""
        if self.system_version_file.exists():
            return self.system_version_file.read_text().strip()
        return "3.0.0"

    def _get_git_info(self, file_path: Path) -> Dict:
        """获取文件的 Git 信息"""
        try:
            cmd_time = f'git log -1 --format="%ai" -- "{file_path}"'
            time_result = subprocess.run(
                cmd_time, shell=True, capture_output=True, text=True, cwd=self.root
            )
            commit_time = time_result.stdout.strip()

            cmd_hash = f'git log -1 --format="%h" -- "{file_path}"'
            hash_result = subprocess.run(
                cmd_hash, shell=True, capture_output=True, text=True, cwd=self.root
            )
            commit_hash = hash_result.stdout.strip()

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

    def auto_version(self, module_path: str, module_type: str = "core") -> str:
        """自动生成模块版本号"""
        full_path = self.root / module_path

        if not full_path.exists():
            return f"v0.0.00_unknown"

        git_info = self._get_git_info(full_path)

        if git_info.get("has_git"):
            system_ver = self._get_system_version()
            revision = git_info["commit_count"]
            date_str = datetime.now().strftime("%Y%m%d")
            git_hash = git_info["commit_hash"]
            return f"v{system_ver}.{revision:02d}_{date_str}_{git_hash}"
        else:
            mtime = full_path.stat().st_mtime
            date_str = datetime.fromtimestamp(mtime).strftime("%Y%m%d")
            return f"v0.0.00_{date_str}_nogit"

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
            "status": "active",
        }

        self.registry["system_version"] = self._get_system_version()
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
        updated = []
        for name, info in self.registry.get("modules", {}).items():
            new_version = self.auto_version(info["path"], info["type"])
            if new_version != info["version"]:
                info["version"] = new_version
                info["updated_at"] = datetime.now().isoformat()
                updated.append(f"{name}: {info['version']} -> {new_version}")

        if updated:
            self.registry["system_version"] = self._get_system_version()
            self._save_registry()
            print("🔄 更新:")
            for u in updated:
                print(f"   {u}")

        return self.registry

    def get_status(self) -> Dict:
        """获取注册中心状态"""
        return {
            "registry_version": self.VERSION,
            "system_version": self._get_system_version(),
            "storage_file": str(self.json_file),
            "export_file": str(self.yaml_file) if YAML_AVAILABLE else None,
            "total_modules": len(self.registry["modules"]),
            "last_updated": self.registry.get("last_updated"),
        }


# 全局实例
version_registry = VersionRegistry()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "list":
            modules = version_registry.list_all()
            print(f"📦 已注册模块 ({len(modules)}):")
            for name, info in modules.items():
                print(f"   {info['version']}  {name}")

        elif cmd == "register":
            if len(sys.argv) >= 4:
                name, path, mtype = sys.argv[2], sys.argv[3], sys.argv[4]
                result = version_registry.register_module(name, path, mtype)
                print(f"✅ 已注册: {name} -> {result['version']}")

        elif cmd == "sync":
            version_registry.sync_all()
            print("✅ 同步完成")

        elif cmd == "status":
            status = version_registry.get_status()
            print(f"📌 版本注册中心 v{version_registry.VERSION}")
            print(f"   系统版本: {status['system_version']}")
            print(f"   存储文件: {status['storage_file']}")
            if status["export_file"]:
                print(f"   导出文件: {status['export_file']}")
            print(f"   模块数: {status['total_modules']}")
            print(f"   最后更新: {status['last_updated']}")
    else:
        print(version_registry.get_status())
