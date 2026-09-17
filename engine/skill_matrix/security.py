"""技能安全引擎 - 风险扫描与安全评估"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class SkillSecurityEngine:
    """技能安全扫描引擎 - 兼容现有 security_grade 机制"""

    # 危险模式检测
    DANGEROUS_PATTERNS = {
        "critical": [
            (r"os\.system\(", "执行系统命令"),
            (r"subprocess\.", "子进程调用"),
            (r"eval\(", "动态代码执行"),
            (r"exec\(", "代码执行"),
            (r"__import__\(", "动态导入"),
            (r"shutil\.rmtree", "删除目录"),
            (r"os\.remove\(", "删除文件"),
        ],
        "high": [
            (r"requests\.(get|post|put|delete)", "网络请求"),
            (r"socket\.", "网络通信"),
            (r"base64\.", "编码解码"),
            (r"pickle\.", "序列化"),
        ],
        "medium": [
            (r"glob\(", "文件遍历"),
            (r"Path\(.*\)\.(read|write)", "文件操作"),
            (r"tempfile\.", "临时文件"),
        ],
    }

    # 安全等级映射
    SECURITY_GRADES = {
        "A": {"badge": "🟢", "level": "安全", "description": "可直接使用"},
        "B": {"badge": "🟡", "level": "中等", "description": "需要审计"},
        "C": {"badge": "🟠", "level": "高风险", "description": "建议沙箱"},
        "D": {"badge": "🔴", "level": "危险", "description": "禁止使用"},
    }

    def __init__(self):
        print("🔒 技能安全引擎已初始化")

    def scan_skill(self, skill_path: Path) -> Dict:
        """扫描技能文件"""
        risks = []

        if not skill_path.exists():
            return {"risk_level": "unknown", "risks": [], "error": "Skill not found"}

        # 扫描 Python 文件
        for py_file in skill_path.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
                risks.extend(self._scan_content(content, py_file.name))
            except Exception as e:
                pass

        # 扫描 SKILL.md
        skill_md = skill_path / "SKILL.md"
        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8")
            risks.extend(self._scan_content(content, skill_md.name))

        # 计算风险等级
        risk_level = self._calculate_risk_level(risks)

        return {
            "skill_path": str(skill_path),
            "risk_level": risk_level,
            "risks": risks,
            "is_safe": risk_level in ["low", "medium"],
        }

    def _scan_content(self, content: str, filename: str) -> List[Dict]:
        """扫描内容"""
        risks = []
        for level, patterns in self.DANGEROUS_PATTERNS.items():
            for pattern, description in patterns:
                if re.search(pattern, content):
                    risks.append(
                        {
                            "level": level,
                            "description": description,
                            "file": filename,
                            "line": self._find_line(content, pattern),
                        }
                    )
        return risks

    def _find_line(self, content: str, pattern: str) -> int:
        """查找匹配行号"""
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line):
                return i
        return 0

    def _calculate_risk_level(self, risks: List[Dict]) -> str:
        """计算风险等级"""
        if any(r["level"] == "critical" for r in risks):
            return "critical"
        if any(r["level"] == "high" for r in risks):
            return "high"
        if any(r["level"] == "medium" for r in risks):
            return "medium"
        return "low"

    def get_security_grade(self, skill_name: str) -> str:
        """获取安全等级 (A/B/C/D)"""
        skill_path = Path(f"skills/{skill_name}")
        if not skill_path.exists():
            skill_path = Path(f"marketplace/skills/{skill_name}")

        if not skill_path.exists():
            return "A"

        # 读取 SKILL.md 中的 security_grade
        skill_md = skill_path / "SKILL.md"
        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8")
            for line in content.split("\n"):
                if "security_grade:" in line:
                    grade = line.split(":")[-1].strip()
                    # 去除 emoji
                    grade = (
                        grade.replace("🟢", "")
                        .replace("🟡", "")
                        .replace("🟠", "")
                        .replace("🔴", "")
                        .strip()
                    )
                    if grade in ["A", "B", "C", "D"]:
                        return grade

        # 默认 A 级
        return "A"

    def get_security_badge(self, grade: str) -> str:
        """获取安全徽章"""
        return self.SECURITY_GRADES.get(grade, {"badge": "⚪"})["badge"]

    def assess_skill(self, skill_path: Path) -> Dict:
        """综合评估技能安全"""
        # 1. 代码扫描
        scan_result = self.scan_skill(skill_path)

        # 2. 读取现有安全等级
        skill_name = skill_path.name
        existing_grade = self.get_security_grade(skill_name)

        # 3. 综合评分
        risk_level = scan_result.get("risk_level", "low")
        if risk_level == "critical":
            recommended_grade = "D"
        elif risk_level == "high":
            recommended_grade = "C"
        elif risk_level == "medium":
            recommended_grade = "B"
        else:
            recommended_grade = "A"

        return {
            "skill_path": str(skill_path),
            "skill_name": skill_name,
            "existing_grade": existing_grade,
            "recommended_grade": recommended_grade,
            "risk_level": risk_level,
            "risks": scan_result.get("risks", []),
            "badge": self.get_security_badge(recommended_grade),
            "is_safe": recommended_grade in ["A", "B"],
        }


# 全局实例
skill_security = SkillSecurityEngine()
