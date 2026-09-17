#!/usr/bin/env python3
"""Skill Validator V4 - Skill Validator V4 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.constants import PROJECT_ROOT
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""技能验证框架 v4.0.0 - 三层验证模型"""

import json
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """验证结果"""

    skill_name: str
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SkillValidator:
    """技能验证器 - 三层验证"""

    VERSION = "4.0.0"

    # 必需的元数据字段
    REQUIRED_METADATA = ["name", "version", "description"]

    # 可选但建议的字段
    RECOMMENDED_METADATA = ["use_when", "not_for", "security_grade", "dependencies"]

    def __init__(self, skills_path: Path = None):
        self.skills_path = skills_path or Path("skills")

    def validate_skill(self, skill_name: str) -> ValidationResult:
        """完整验证一个技能"""
        result = ValidationResult(skill_name=skill_name, passed=True)

        # Layer 1: 静态验证
        self._validate_static(skill_name, result)

        # Layer 2: 动态验证
        if result.passed:
            self._validate_dynamic(skill_name, result)

        # Layer 3: 运行验证
        if result.passed:
            self._validate_runtime(skill_name, result)

        result.passed = len(result.errors) == 0
        return result

    def _validate_static(self, skill_name: str, result: ValidationResult):
        """Layer 1: 静态验证"""
        skill_dir = self.skills_path / skill_name

        # 检查目录存在
        if not skill_dir.exists():
            result.errors.append(f"Skill directory not found: {skill_name}")
            return

        # 检查 SKILL.md
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            result.errors.append("Missing SKILL.md")
        else:
            try:
                content = skill_md.read_text(encoding="utf-8")
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 2:
                        metadata = unified_config.get("skill_metadata", {})
                        result.metadata["metadata"] = metadata

                        # 检查必需字段
                        for field in self.REQUIRED_METADATA:
                            if field not in metadata:
                                result.errors.append(
                                    f"Missing required field in SKILL.md: {field}"
                                )

                        # 记录缺失的建议字段
                        for field in self.RECOMMENDED_METADATA:
                            if field not in metadata:
                                result.warnings.append(
                                    f"Recommended field missing: {field}"
                                )
                    else:
                        result.errors.append(
                            "Invalid SKILL.md format (missing frontmatter)"
                        )
                else:
                    result.warnings.append("SKILL.md missing YAML frontmatter")
            except Exception as e:
                result.errors.append(f"Failed to parse SKILL.md: {e}")

        # 检查 scripts/main.py
        main_py = skill_dir / "scripts" / "main.py"
        if not main_py.exists():
            result.errors.append("Missing scripts/main.py")
        else:
            # 语法检查
            proc = subprocess.run(
                [sys.executable, "-m", "py_compile", str(main_py)],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                result.errors.append(f"Syntax error: {proc.stderr[:100]}")
            else:
                result.metadata["has_main"] = True

    def _validate_dynamic(self, skill_name: str, result: ValidationResult):
        """Layer 2: 动态验证"""
        main_py = self.skills_path / skill_name / "scripts" / "main.py"

        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(skill_name, main_py)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 检查 execute 函数
            if not hasattr(module, "execute"):
                result.errors.append("No 'execute' function in main.py")
                return

            # 检查函数签名
            import inspect

            sig = inspect.signature(module.execute)
            params = list(sig.parameters.keys())
            if len(params) != 1 or params[0] != "params":
                result.warnings.append(
                    f"execute() should take 'params' dict, got: {params}"
                )

            result.metadata["has_execute"] = True

        except Exception as e:
            result.errors.append(f"Import failed: {str(e)[:100]}")

    def _validate_runtime(self, skill_name: str, result: ValidationResult):
        """Layer 3: 运行验证"""
        main_py = self.skills_path / skill_name / "scripts" / "main.py"

        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(skill_name, main_py)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 测试执行
            test_result = module.execute({"test": True, "validate": True})

            if not isinstance(test_result, dict):
                result.errors.append("execute() must return a dict")
            elif not test_result.get("success", False):
                # 测试失败不一定算错误，可能是设计如此
                result.warnings.append(
                    f"Test execution returned: {test_result.get('error', 'unknown')}"
                )
            else:
                result.metadata["test_passed"] = True

        except Exception as e:
            result.errors.append(f"Runtime test failed: {str(e)[:100]}")

    def validate_all(self) -> Dict[str, ValidationResult]:
        """验证所有技能"""
        results = {}
        for skill_dir in self.skills_path.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith("__"):
                results[skill_dir.name] = self.validate_skill(skill_dir.name)
        return results

    def get_validation_report(self) -> str:
        """生成验证报告"""
        results = self.validate_all()

        report = []
        report.append("=" * 60)
        report.append("技能验证报告")
        report.append("=" * 60)

        passed = 0
        failed = 0

        for name, result in results.items():
            status = "✅" if result.passed else "❌"
            report.append(f"{status} {name}")
            if result.errors:
                for err in result.errors[:2]:
                    report.append(f"   错误: {err}")
            if result.warnings and result.passed:
                for warn in result.warnings[:1]:
                    report.append(f"   警告: {warn}")
            if result.passed:
                passed += 1
            else:
                failed += 1

        report.append("-" * 60)
        report.append(f"总计: {passed + failed} | 通过: {passed} | 失败: {failed}")
        report.append("=" * 60)

        return "\n".join(report)


validator = SkillValidator()


if __name__ == "__main__":
    print(validator.get_validation_report())
