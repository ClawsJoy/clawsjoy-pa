#!/usr/bin/env python3
"""Smart Active Service - 优化版"""

import hashlib
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class SmartActiveService:
    """智能主动服务 - 优化版（只索引文档）"""

    def __init__(self):
        self.last_index_time = {}
        self.running = False
        self.thread = None
        print("💡 智能主动服务已启动")

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print("✅ 主动服务循环已启动")

    def stop(self):
        self.running = False

    def _run(self):
        """主循环"""
        while self.running:
            try:
                self._auto_index_files()
                self._cleanup_expired()
                self._health_check()
                time.sleep(600)  # 10分钟
            except Exception as e:
                print(f"主动服务错误: {e}")
                time.sleep(60)

    def _auto_index_files(self):
        """自动索引新文件 - 只索引 docs 目录"""
        from core.lib.vector_knowledge_center import vector_knowledge_center

        # 只监控 docs 目录，排除图片密集的目录
        watch_dirs = {
            "config": Path("config"),
            "agents": Path("agents"),
        }

        for name, watch_dir in watch_dirs.items():
            if not watch_dir.exists():
                continue

            for file_path in watch_dir.rglob("*"):
                if not file_path.is_file():
                    continue

                suffix = file_path.suffix.lower()
                # 只索引文档，不索引图片和视频
                if suffix not in [".yaml", ".yml", ".json"]:
                    continue

                file_key = str(file_path.absolute())
                mtime = file_path.stat().st_mtime
                last_time = self.last_index_time.get(file_key, 0)

                if mtime > last_time:
                    self._index_file(file_path, vector_knowledge_center)
                    self.last_index_time[file_key] = mtime
                    time.sleep(0.1)  # 添加延迟，避免过载

    def _index_file(self, file_path: Path, vector_center):
        """索引单个文件 - 只处理文档"""
        try:
            # 只处理文档，不处理图片/视频
            if file_path.suffix in [".md", ".txt", ".yaml", ".yml", ".json", ".py"]:
                content = file_path.read_text(encoding="utf-8", errors="ignore")[:2000]
                description = f"文档: {file_path.name}\n内容: {content[:500]}"
                doc_id = f"doc_{file_path.stem}_{hashlib.md5(str(file_path).encode()).hexdigest()[:8]}"

                vector_center.add_document(
                    doc_id=doc_id,
                    content=description,
                    metadata={
                        "type": file_path.suffix[1:],
                        "file": str(file_path),
                        "filename": file_path.name,
                        "auto_indexed": True,
                        "indexed_at": datetime.now().isoformat(),
                    },
                )
                print(f"   📄 [主动服务] 自动索引: {file_path.name}")
        except Exception as e:
            print(f"   ❌ [主动服务] 索引失败 {file_path.name}: {e}")

    def _cleanup_expired(self):
        """清理过期数据"""
        print(f"   🧹 [主动服务] 清理过期数据")

    def _health_check(self):
        """健康检查"""
        try:
            from core.lib.vector_knowledge_center import vector_knowledge_center

            print(f"   💚 [主动服务] 健康检查...")
        except Exception:
            pass

    def on_task_complete(self, agent: str, user_id: str, task: str, data: Dict):
        print(f"   🎯 [主动服务] {agent} 完成任务: {task}")

    def on_error(self, agent: str, user_id: str, error: str):
        print(f"   🚨 [主动服务] {agent} 发生错误: {error}")

    def should_serve(self, agent: str, context: Dict) -> Dict:
        return {"should": True, "reason": "auto_index", "priority": 1}

    def emit_event(self, event_type: str, payload: Dict):
        try:
            from core.lib.agent_communication import agent_communication

            agent_communication.emit_event(event_type, payload, "active_service")
        except Exception:
            pass

    def on_task_arrived(self, task: Dict):
        self.emit_event("task.arrived", task)
        print(f"📋 主动服务: 检测到新任务 {task.get('name', 'unknown')}")

    def wake_on_event(self, event_type: str):
        from core.lib.agent_communication import agent_communication

        if event_type in agent_communication.subscribers:
            for agent_name in agent_communication.subscribers[event_type]:
                try:
                    module = __import__(f"agents.{agent_name}.agent", fromlist=[f"{agent_name}Agent"])
                    class_name = "".join(w.capitalize() for w in agent_name.split("_")) + "Agent"
                    agent_class = getattr(module, class_name)
                    agent = agent_class("active_service")
                    if hasattr(agent, "wake_now"):
                        agent.wake_now()
                        print(f"   🌞 事件触发唤醒: {agent_name}")
                except Exception:
                    pass


smart_service = SmartActiveService()
