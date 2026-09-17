#!/usr/bin/env python3
"""Version Registry V1.0.03 20260517 - Version Registry V1.0.03 20260517 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""版本注册中心 v1.0.03 - 修复版本格式和导入问题"""

import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class VersionRegistry:
    """版本注册中心 - 程序自动写入 JSON，可导出 YAML 供人工查看"""

    VERSION = "1.0.03"

    def __init__(self, root_path: Optional[Path] = None):
        self.root = Path(root_path) if root_path else Path(__file__).parent.parent

        self.json_file = self.root / "config" / "version_registry.json"
        self.yaml_file = self.root / "config" / "version_registry.yaml"
        self.system_version_file = self.root / "VERSION"

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
        """保存注册表到 JSON"""
        self.registry["last_updated"] = datetime.now().isoformat()
        self.registry["system_version"] = self._get_system_version()

        with open(self.json_file, "w") as f:
            json.dump(self.registry, f, indent=2, ensure_ascii=False)

        self._export_yaml()

    def _export_yaml(self):
        """导出到 YAML"""
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

    def _extract_version_from_filename(self, file_path: Path) -> Optional[str]:
        """从文件名提取版本号"""
        name = file_path.name
        # 匹配 v1.0.01_20260517 格式
        match = re.search(r"v(\d+\.\d+\.\d+)_(\d{8})", name)
        if match:
            return f"v{match.group(1)}_{match.group(2)}"

        # 匹配 v3.0.00_20260517 格式（系统版本）
        match = re.search(r"v(\d+\.\d+\.\d+)_(\d{8})", name)
        if match:
            return f"v{match.group(1)}_{match.group(2)}"

        return None

    def _get_git_info(self, file_path: Path) -> Dict:
        """获取文件的 Git 信息"""
        try:
            cmd_count = f'git rev-list --count HEAD -- "{file_path}" 2>/dev/null'
            count_result = subprocess.run(
                cmd_count, shell=True, capture_output=True, text=True, cwd=self.root
            )
            commit_count = (
                int(count_result.stdout.strip()) if count_result.stdout.strip() else 0
            )

            cmd_hash = f'git log -1 --format="%h" -- "{file_path}" 2>/dev/null'
            hash_result = subprocess.run(
                cmd_hash, shell=True, capture_output=True, text=True, cwd=self.root
            )
            commit_hash = hash_result.stdout.strip()

            cmd_time = f'git log -1 --format="%ai" -- "{file_path}" 2>/dev/null'
            time_result = subprocess.run(
                cmd_time, shell=True, capture_output=True, text=True, cwd=self.root
            )
            commit_time = time_result.stdout.strip()

            return {
                "commit_count": commit_count,
                "commit_hash": commit_hash,
                "last_modified": commit_time,
                "has_git": commit_count > 0,
            }
        except Exception:
            return {"has_git": False}

    def auto_version(self, module_path: str) -> str:
        """自动生成模块版本号 - 从文件名提取或 Git 生成"""
        full_path = self.root / module_path

        if not full_path.exists():
            return "v0.0.00_unknown"

        # 优先从文件名提取版本
        filename_version = self._extract_version_from_filename(full_path)
        if filename_version:
            return filename_version

        # 其次从 Git 生成
        git_info = self._get_git_info(full_path)
        if git_info.get("has_git"):
            system_ver = self._get_system_version()
            revision = git_info["commit_count"]
            date_str = datetime.now().strftime("%Y%m%d")
            git_hash = git_info["commit_hash"]
            return f"v{system_ver}.{revision:02d}_{date_str}_{git_hash}"

        # 最后基于文件修改时间
        mtime = full_path.stat().st_mtime
        date_str = datetime.fromtimestamp(mtime).strftime("%Y%m%d")
        return f"v0.0.00_{date_str}_nogit"

    def register_module(
        self, module_name: str, module_path: str, module_type: str = "core"
    ) -> Dict:
        """注册模块"""
        version = self.auto_version(module_path)

        self.registry["modules"][module_name] = {
            "path": module_path,
            "type": module_type,
            "version": version,
            "registered_at": datetime.now().isoformat(),
            "status": "active",
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
        updated = []
        for name, info in self.registry.get("modules", {}).items():
            new_version = self.auto_version(info["path"])
            if new_version != info["version"]:
                info["version"] = new_version
                info["updated_at"] = datetime.now().isoformat()
                updated.append(f"{name}: {info['version']} -> {new_version}")

        if updated:
            self._save_registry()
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


# 全局实例（使用统一的导入名）
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
