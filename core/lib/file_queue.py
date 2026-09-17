#!/usr/bin/env python3
"""File Queue - File Queue 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class FileQueue:
    """基于文件的队列"""

    def __init__(self, queue_dir: str):
        self.queue_dir = Path(queue_dir)
        self.queue_dir.mkdir(parents=True, exist_ok=True)

    def send(self, to: str, message: Dict) -> str:
        """发送消息到目标队列"""
        target_dir = self.queue_dir / to
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
        filepath = target_dir / filename

        record = {
            "id": filename,
            "to": to,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "status": "pending",
        }

        with open(filepath, "w") as f:
            json.dump(record, f, indent=2)

        return filename

    def receive(self, from_dir: str, mark_processing: bool = True) -> Optional[Dict]:
        """从队列接收消息"""
        source_dir = self.queue_dir / from_dir
        if not source_dir.exists():
            return None

        # 获取最旧的文件
        files = sorted(source_dir.glob("*.json"))
        if not files:
            return None

        filepath = files[0]

        with open(filepath, "r") as f:
            record = json.load(f)

        if mark_processing:
            # 移动到 processing 目录
            processing_dir = self.queue_dir / "processing"
            processing_dir.mkdir(exist_ok=True)
            new_path = processing_dir / filepath.name
            filepath.rename(new_path)
            record["status"] = "processing"

        return record

    def complete(self, filename: str, result: Dict):
        """标记消息完成"""
        processing_dir = self.queue_dir / "processing"
        filepath = processing_dir / filename
        if filepath.exists():
            with open(filepath, "r") as f:
                record = json.load(f)
            record["status"] = "completed"
            record["result"] = result
            record["completed_at"] = datetime.now().isoformat()

            # 移动到完成目录（保留在 exchange 根目录）
            new_path = self.queue_dir / filename
            with open(new_path, "w") as f:
                json.dump(record, f, indent=2)
            filepath.unlink()

    def list_pending(self, from_dir: str) -> List[str]:
        """列出待处理消息"""
        source_dir = self.queue_dir / from_dir
        if not source_dir.exists():
            return []
        return [f.name for f in source_dir.glob("*.json")]


# 全局实例
to_decision = FileQueue("data/exchange/to_decision")
to_chat = FileQueue("data/exchange/to_chat")
