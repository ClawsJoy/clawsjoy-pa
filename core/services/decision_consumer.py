#!/usr/bin/env python3
"""Decision Consumer - Decision Consumer 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

import requests

from core.lib.unified_config import unified_config


class DecisionConsumer:
    def __init__(self):
        self.running = False
        self.thread = None
        self.task_dir = Path("data/exchange/to_decision/decision_agent")
        self.processing_dir = Path("data/exchange/processing")
        self.response_dir = Path("data/exchange/to_chat/butler")
        self.completed_dir = Path("data/exchange")

        self.task_dir.mkdir(parents=True, exist_ok=True)
        self.processing_dir.mkdir(parents=True, exist_ok=True)
        self.response_dir.mkdir(parents=True, exist_ok=True)

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._consume_loop, daemon=True)
        self.thread.start()
        print("🧠 决策师消费者已启动")

    def _push_notification(self, user_id: str, response: str, task_id: str):
        """主动推送结果"""
        try:
            from core.services.sse_service import sse_service

            sse_service.push(
                user_id,
                {
                    "type": "task_completed",
                    "task_id": task_id,
                    "response": response,
                    "timestamp": datetime.now().isoformat(),
                },
            )
            print(f"📡 主动推送: user={user_id}, response={response[:50]}")
        except Exception as e:
            print(f"推送失败: {e}")

    def _consume_loop(self):
        while self.running:
            self._process_one_task()
            time.sleep(1)

    def _process_one_task(self):
        task_files = list(self.task_dir.glob("*.json"))
        if not task_files:
            return

        task_file = task_files[0]
        try:
            with open(task_file, "r") as f:
                task = json.load(f)
        except Exception as e:
            print(f"读取失败: {e}")
            return

        processing_path = self.processing_dir / task_file.name
        if not task_file.exists():
            print(f"⚠️ 文件不存在，跳过: {task_file}")
            return
        shutil.move(str(task_file), str(processing_path))

        message = task.get("message", {}).get("message", "")
        user_id = task.get("message", {}).get("user_id", "")

        print(f"[消费者] 处理: {message}")

        try:
            gateway_host = unified_config.get("services.gateway.host", "localhost")
            gateway_port = unified_config.get("services.gateway.port", 5002)
            url = (
                f"http://{gateway_host}:{gateway_port}/api/agent/decision_agent/message"
            )
            resp = requests.post(
                url, json={"message": message, "user_id": user_id}, timeout=30
            )
            result = (
                resp.json()
                if resp.status_code == 200
                else {"error": f"HTTP {resp.status_code}"}
            )
        except Exception as e:
            result = {"error": str(e)}

        response_text = result.get("response", result.get("error", "处理失败"))

        # 保存响应
        response_task = {
            "id": f"response_{task_file.stem}.json",
            "from": "decision_agent",
            "to": "butler",
            "response": response_text,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
        }

        response_path = self.response_dir / f"resp_{task_file.stem}.json"
        with open(response_path, "w") as f:
            json.dump(response_task, f, indent=2)

        # 主动推送
        self._push_notification(user_id, response_text, task_file.stem)

        # 清理
        if processing_path.exists():
            processing_path.unlink()


# 全局实例
decision_consumer = DecisionConsumer()
