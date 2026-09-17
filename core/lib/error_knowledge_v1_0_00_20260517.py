#!/usr/bin/env python3
"""Error Knowledge V1 0 00 20260517 - Error Knowledge V1 0 00 20260517 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""错误知识库 v1.0.00 - 主动查询和写入"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.lib.memory_simple import memory
from core.lib.unified_config import unified_config


class ErrorKnowledge:
    """错误知识库 - 主动查询和写入"""

    VERSION = "1.0.00"

    def __init__(self):
        self.root = unified_config.ROOT
        self.error_file = self.root / "data" / "error_learning.json"
        self.similarity_threshold = 0.7  # 相似度阈值
        self.max_retry_same_error = 3  # 同一错误最大重试次数

    def _load_errors(self) -> List[Dict]:
        """加载错误知识库"""
        if self.error_file.exists():
            try:
                with open(self.error_file, "r") as f:
                    data = json.load(f)
                    return data.get("learned_errors", [])
            except Exception as e:
                return []
        return []

    def _save_errors(self, errors: List[Dict]):
        """保存错误知识库"""
        with open(self.error_file, "w") as f:
            json.dump({"learned_errors": errors}, f, indent=2, ensure_ascii=False)

    def _calculate_similarity(self, error1: str, error2: str) -> float:
        """计算两个错误信息的相似度"""
        # 简单关键词匹配
        words1 = set(re.findall(r"\w+", error1.lower()))
        words2 = set(re.findall(r"\w+", error2.lower()))

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)

    def _extract_error_type(self, error_msg: str) -> str:
        """提取错误类型"""
        patterns = {
            "connection_refused": r"Connection refused|port \d+",
            "timeout": r"timeout|timed out|Max retries",
            "not_found": r"No such file|not found|No video found|does not exist",
            "permission": r"Permission denied",
            "import_error": r"ModuleNotFoundError|ImportError|No module named",
            "json_error": r"JSONDecodeError|Invalid JSON",
            "ffmpeg_error": r"ffmpeg|ffprobe",
            "port_in_use": r"Address already in use|port.*in use",
        }

        for error_type, pattern in patterns.items():
            if re.search(pattern, error_msg, re.IGNORECASE):
                return error_type

        return "unknown"

    def query(self, task_name: str, error_msg: str = None) -> Optional[Dict]:
        """
        查询错误知识库
        返回: 匹配的错误信息或 None
        """
        errors = self._load_errors()

        if not errors:
            return None

        # 先按任务名匹配
        for err in errors:
            context = err.get("context", "")
            if task_name in context or context in task_name:
                return err

        # 再按错误内容匹配
        if error_msg:
            error_type = self._extract_error_type(error_msg)

            for err in errors:
                err_type = self._extract_error_type(err.get("error", ""))
                if error_type == err_type and error_type != "unknown":
                    similarity = self._calculate_similarity(
                        error_msg, err.get("error", "")
                    )
                    if similarity >= self.similarity_threshold:
                        return err

        return None

    def add(self, task_name: str, error_msg: str, skill: str = "") -> Dict:
        """添加错误到知识库"""
        errors = self._load_errors()

        # 检查是否已存在
        existing = self.query(task_name, error_msg)
        if existing:
            # 更新重试计数
            existing["retry_count"] = existing.get("retry_count", 0) + 1
            existing["last_seen"] = datetime.now().isoformat()
            self._save_errors(errors)
            return existing

        # 新增错误
        new_error = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "task": task_name,
            "error": error_msg[:200],
            "error_type": self._extract_error_type(error_msg),
            "skill": skill,
            "context": f"技能失败: {skill}" if skill else task_name,
            "retry_count": 1,
            "created_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "solution": self._suggest_solution(error_msg),
        }

        errors.append(new_error)
        self._save_errors(errors)

        # 同时写入记忆系统
        memory.remember(
            f"错误|{task_name}|{error_msg[:100]}", category="error_knowledge"
        )

        return new_error

    def _suggest_solution(self, error_msg: str) -> str:
        """根据错误类型建议解决方案"""
        error_type = self._extract_error_type(error_msg)

        solutions = {
            "connection_refused": "检查服务是否启动: docker ps 或 systemctl status",
            "timeout": "增加超时时间或检查网络连接",
            "not_found": "检查文件路径是否正确，确认文件存在",
            "permission": "检查文件权限: chmod +x <file>",
            "import_error": "安装缺失模块: pip install <module>",
            "json_error": "检查 JSON 格式是否正确",
            "ffmpeg_error": "安装 ffmpeg: sudo apt install ffmpeg -y",
            "port_in_use": "释放端口: fuser -k <port>/tcp",
        }

        return solutions.get(error_type, "查看日志获取详细信息")

    def should_skip(self, task_name: str, retry_count: int = 0) -> Tuple[bool, str]:
        """判断是否应该跳过任务"""
        error = self.query(task_name)

        if error:
            retry_count = error.get("retry_count", retry_count)
            if retry_count >= self.max_retry_same_error:
                return (
                    True,
                    f"重复失败 {retry_count} 次，建议: {error.get('solution', '人工介入')}",
                )

        return False, ""

    def get_stats(self) -> Dict:
        """获取错误知识库统计"""
        errors = self._load_errors()

        type_counts = {}
        for err in errors:
            err_type = err.get("error_type", "unknown")
            type_counts[err_type] = type_counts.get(err_type, 0) + 1

        return {
            "total_errors": len(errors),
            "by_type": type_counts,
            "most_frequent": (
                max(errors, key=lambda x: x.get("retry_count", 0)) if errors else None
            ),
        }


# 全局实例
error_knowledge = ErrorKnowledge()


if __name__ == "__main__":
    # 测试
    print("错误知识库 v1.0.00")
    print(f"统计: {error_knowledge.get_stats()}")

    # 示例查询
    result = error_knowledge.query("youtube_uploader")
    print(f"查询结果: {result}")
