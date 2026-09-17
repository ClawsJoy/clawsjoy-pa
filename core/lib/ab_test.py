#!/usr/bin/env python3
"""Ab Test - Ab Test 模块

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

"""A/B 测试框架 - 对比不同提示词效果"""

import json
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class ABTest:
    """A/B 测试框架"""

    def __init__(self):
        self.test_dir = Path(f"{get_data_root()}/ab_tests")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self._load_tests()

    def _load_tests(self):
        self.tests = {}
        for test_file in self.test_dir.glob("*.json"):
            with open(test_file, "r") as f:
                test = json.load(f)
                self.tests[test["id"]] = test

    def create_test(
        self,
        name: str,
        variants: Dict[str, str],
        traffic_split: Dict[str, float] = None,
    ) -> str:
        """创建 A/B 测试"""
        test_id = f"ab_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if traffic_split is None:
            # 平均分配流量
            per_variant = 1.0 / len(variants)
            traffic_split = {v: per_variant for v in variants.keys()}

        test = {
            "id": test_id,
            "name": name,
            "variants": variants,
            "traffic_split": traffic_split,
            "results": defaultdict(lambda: {"exposures": 0, "conversions": 0}),
            "started_at": datetime.now().isoformat(),
            "status": "running",
        }

        self.tests[test_id] = test
        self._save_test(test_id)

        return test_id

    def get_variant(self, test_id: str, user_id: str) -> str:
        """获取用户应看到的变体"""
        test = self.tests.get(test_id)
        if not test or test["status"] != "running":
            return list(test["variants"].keys())[0] if test else None

        # 基于用户 ID 哈希分配（保证同一用户始终看到同一变体）
        hash_val = hash(f"{test_id}_{user_id}") % 100
        cumulative = 0
        for variant, split in test["traffic_split"].items():
            cumulative += split * 100
            if hash_val < cumulative:
                return variant

        return list(test["variants"].keys())[0]

    def record_exposure(self, test_id: str, variant: str):
        """记录曝光"""
        if test_id in self.tests:
            self.tests[test_id]["results"][variant]["exposures"] += 1
            self._save_test(test_id)

    def record_conversion(self, test_id: str, variant: str):
        """记录转化"""
        if test_id in self.tests:
            self.tests[test_id]["results"][variant]["conversions"] += 1
            self._save_test(test_id)

    def get_results(self, test_id: str) -> Dict:
        """获取测试结果"""
        test = self.tests.get(test_id)
        if not test:
            return {"error": "测试不存在"}

        results = {}
        for variant, stats in test["results"].items():
            exposures = stats["exposures"]
            conversions = stats["conversions"]
            results[variant] = {
                "exposures": exposures,
                "conversions": conversions,
                "conversion_rate": conversions / exposures if exposures > 0 else 0,
            }

        # 计算置信度（简化版）
        if len(results) >= 2:
            rates = [r["conversion_rate"] for r in results.values()]
            results["winner"] = max(
                results.items(), key=lambda x: x[1]["conversion_rate"]
            )[0]

        return {
            "test_id": test_id,
            "name": test["name"],
            "status": test["status"],
            "results": results,
        }

    def stop_test(self, test_id: str):
        """停止测试"""
        if test_id in self.tests:
            self.tests[test_id]["status"] = "stopped"
            self.tests[test_id]["ended_at"] = datetime.now().isoformat()
            self._save_test(test_id)

    def _save_test(self, test_id: str):
        test_file = self.test_dir / f"{test_id}.json"
        # 转换 defaultdict 为普通 dict
        test_copy = dict(self.tests[test_id])
        test_copy["results"] = dict(test_copy["results"])
        with open(test_file, "w") as f:
            json.dump(test_copy, f, indent=2)


ab_test = ABTest()
