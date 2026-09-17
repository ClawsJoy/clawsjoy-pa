"""智能体市场引擎 - 第三方开发者发布、分享、安装"""

import hashlib
import json
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.lib.logger import engine_logger


class MarketplaceEngine:
    """智能体市场引擎"""

    def __init__(self):
        self.market_dir = Path("data/marketplace")
        self.packages_dir = self.market_dir / "packages"
        self.registry_file = self.market_dir / "registry.json"
        self.packages_dir.mkdir(parents=True, exist_ok=True)
        self._load_registry()
        engine_logger.get().info("🏪 智能体市场已初始化")

    def _load_registry(self):
        if self.registry_file.exists():
            with open(self.registry_file, "r") as f:
                self.registry = json.load(f)
        else:
            self.registry = {
                "packages": {},
                "categories": {},
                "statistics": {"total_downloads": 0, "total_packages": 0},
            }

    def _save_registry(self):
        with open(self.registry_file, "w") as f:
            json.dump(self.registry, f, indent=2)

    def publish_package(
        self,
        name: str,
        version: str,
        author: str,
        description: str,
        category: str,
        files: List[str],
    ) -> Dict:
        """发布技能包"""
        package_id = f"{name}-{version}"
        package_dir = self.packages_dir / package_id
        package_dir.mkdir(exist_ok=True)

        # 生成清单
        manifest = {
            "name": name,
            "version": version,
            "author": author,
            "description": description,
            "category": category,
            "published_at": datetime.now().isoformat(),
            "downloads": 0,
            "rating": 0,
            "reviews": [],
        }

        # 保存清单
        with open(package_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        # 注册
        self.registry["packages"][package_id] = manifest
        if category not in self.registry["categories"]:
            self.registry["categories"][category] = []
        self.registry["categories"][category].append(package_id)
        self.registry["statistics"]["total_packages"] += 1
        self._save_registry()

        engine_logger.get().info(f"   📦 发布包: {name} v{version}")
        return {"success": True, "package_id": package_id, "manifest": manifest}

    def search_packages(self, query: str, category: str = None) -> List[Dict]:
        """搜索技能包"""
        results = []
        query_lower = query.lower()

        for pkg_id, pkg in self.registry["packages"].items():
            if category and pkg.get("category") != category:
                continue
            if (
                query_lower in pkg.get("name", "").lower()
                or query_lower in pkg.get("description", "").lower()
                or query_lower in pkg.get("author", "").lower()
            ):
                results.append(pkg)

        return sorted(results, key=lambda x: -x.get("downloads", 0))[:20]

    def install_package(self, package_id: str) -> Dict:
        """安装技能包"""
        if package_id not in self.registry["packages"]:
            return {"success": False, "error": f"Package {package_id} not found"}

        pkg = self.registry["packages"][package_id]
        pkg["downloads"] = pkg.get("downloads", 0) + 1
        self.registry["statistics"]["total_downloads"] += 1
        self._save_registry()

        engine_logger.get().info(f"   📥 安装包: {package_id}")
        return {"success": True, "package": pkg}

    def get_categories(self) -> List[str]:
        """获取所有分类"""
        return list(self.registry["categories"].keys())

    def get_statistics(self) -> Dict:
        """获取市场统计"""
        return self.registry["statistics"]

    def get_stats(self) -> Dict:
        return {
            "total_packages": self.registry["statistics"]["total_packages"],
            "total_downloads": self.registry["statistics"]["total_downloads"],
            "categories": len(self.registry["categories"]),
            "status": "active",
        }

    def process(self, input_data: Any = None, **kwargs) -> Any:
        if input_data is None:
            return self.get_stats()
        if isinstance(input_data, str):
            return self.search_packages(input_data)
        if isinstance(input_data, dict):
            action = input_data.get("action", "search")
            if action == "publish":
                return self.publish_package(**input_data)
            elif action == "install":
                return self.install_package(input_data.get("package_id"))
            elif action == "search":
                return self.search_packages(
                    input_data.get("query", ""), input_data.get("category")
                )
        return self.get_stats()

    def reload(self) -> Dict:
        self._load_registry()
        return {"success": True, "message": "Marketplace reloaded"}

    def health_check(self) -> Dict:
        return {"name": "marketplace_engine", "status": "healthy"}


marketplace_engine = MarketplaceEngine()
