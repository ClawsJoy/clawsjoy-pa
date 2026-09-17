#!/usr/bin/env python3
"""Proactive Service - Proactive Service 模块

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

"""主动服务 - 定期清理、优化、报告、通知"""

import json
import smtplib
import subprocess
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List

import requests


class ProactiveService:
    """主动服务 - 自主执行维护任务"""

    def __init__(self):
        self.notification_config = self._load_config()
        self.task_log = []

    def _load_config(self) -> Dict:
        config_file = Path("config/notification.yaml")
        if config_file.exists():
            import yaml

            with open(config_file, "r") as f:
                return yaml.safe_load(f)
        return {
            "email": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "sender": "",
                "password": "",
                "receivers": [],
            },
            "webhook": {"enabled": False, "url": ""},
        }

    def clear_cache(self) -> Dict:
        """清理缓存"""
        result = {"actions": [], "freed_bytes": 0}

        # 清理临时会话
        temp_sessions = Path(f"{get_data_root()}/temp_sessions")
        if temp_sessions.exists():
            before = sum(f.stat().st_size for f in temp_sessions.glob("*.json"))
            import shutil

            shutil.rmtree(temp_sessions)
            temp_sessions.mkdir()
            after = 0
            freed = before - after
            result["actions"].append(f"清理临时会话: {freed} bytes")
            result["freed_bytes"] += freed

        # 清理旧日志（7天前）
        log_dir = Path("logs")
        if log_dir.exists():
            import time

            now = time.time()
            for log_file in log_dir.glob("*.log"):
                if now - log_file.stat().st_mtime > 7 * 24 * 3600:
                    size = log_file.stat().st_size
                    log_file.unlink()
                    result["actions"].append(
                        f"删除旧日志: {log_file.name} ({size} bytes)"
                    )
                    result["freed_bytes"] += size

        # 清理 Python 缓存
        for cache_dir in Path(".").rglob("__pycache__"):
            if cache_dir.is_dir():
                size = sum(f.stat().st_size for f in cache_dir.glob("*"))
                import shutil

                shutil.rmtree(cache_dir)
                result["actions"].append(f"清理缓存: {cache_dir} ({size} bytes)")
                result["freed_bytes"] += size

        self._log_task("clear_cache", result)
        return result

    def optimize_skills(self) -> Dict:
        """优化技能库"""
        result = {"actions": [], "skills_checked": 0, "skills_fixed": 0}

        # 同步技能
        try:
            resp = requests.post(
                'http://{unified_config.get("services.gateway.host", "localhost")}:{unified_config.get("services.gateway.port", 5002)}/api/knowledge/sync',
                timeout=get_timeout("default"),
            )
            if resp.status_code == 200:
                result["actions"].append("技能同步完成")
        except Exception as e:
            result["actions"].append(f"技能同步失败: {e}")

        # 检查技能注册中心
        registry_file = Path(f"{get_data_root()}/skill_registry_v2.json")
        if registry_file.exists():
            import json

            with open(registry_file, "r") as f:
                registry = json.load(f)
            result["skills_checked"] = len(registry)

            # 检查禁用技能
            disabled = [k for k, v in registry.items() if not v.get("enabled", True)]
            if disabled:
                result["actions"].append(f"发现 {len(disabled)} 个禁用技能")

        self._log_task("optimize_skills", result)
        return result

    def generate_report(self) -> Dict:
        """生成系统报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "system": {},
            "skills": {},
            "memory": {},
            "issues": [],
        }

        # 获取系统状态
        try:
            resp = requests.get(
                'http://{unified_config.get("services.gateway.host", "localhost")}:{unified_config.get("services.gateway.port", 5002)}/api/health',
                timeout=5,
            )
            report["system"]["health"] = (
                resp.json() if resp.status_code == 200 else {"error": "无法获取"}
            )
        except Exception as e:
            report["system"]["health"] = {"status": "unreachable"}

        # 获取技能统计
        try:
            resp = requests.get(
                'http://{unified_config.get("services.gateway.host", "localhost")}:{unified_config.get("services.gateway.port", 5002)}/api/skills',
                timeout=5,
            )
            skills = resp.json() if resp.status_code == 200 else {}
            report["skills"]["total"] = skills.get("total", 0)
            report["skills"]["categories"] = list(skills.get("categories", {}).keys())[
                :10
            ]
        except Exception as e:
            report["skills"]["error"] = "无法获取"

        # 获取记忆统计
        try:
            from core.lib.memory_vector import vector_memory

            report["memory"]["vector_count"] = vector_memory.collection.count()
        except Exception as e:
            report["memory"]["vector_count"] = 0

        # 获取磁盘使用
        import shutil

        usage = shutil.disk_usage("/")
        report["system"]["disk_free_gb"] = usage.free / (1024**3)
        report["system"]["disk_used_gb"] = usage.used / (1024**3)

        # 保存报告
        report_file = Path(
            f"{get_data_root()}/reports/system_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        report_file.parent.mkdir(exist_ok=True)
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        report["file"] = str(report_file)
        self._log_task("generate_report", {"file": str(report_file)})

        return report

    def send_notification(
        self, subject: str, content: str, level: str = "info"
    ) -> Dict:
        """发送通知（邮件/webhook）"""
        results = []

        # 邮件通知
        if self.notification_config.get("email", {}).get("enabled"):
            try:
                self._send_email(subject, content)
                results.append({"method": "email", "success": True})
            except Exception as e:
                results.append({"method": "email", "success": False, "error": str(e)})

        # Webhook 通知
        if self.notification_config.get("webhook", {}).get("enabled"):
            try:
                webhook_url = self.notification_config["webhook"]["url"]
                resp = requests.post(
                    webhook_url,
                    json={"subject": subject, "content": content, "level": level},
                    timeout=10,
                )
                results.append(
                    {"method": "webhook", "success": resp.status_code == 200}
                )
            except Exception as e:
                results.append({"method": "webhook", "success": False, "error": str(e)})

        # 控制台输出（备选）
        print(f"\n📧 [{level.upper()}] {subject}")
        print(f"   {content[:200]}")

        self._log_task("send_notification", {"subject": subject, "level": level})
        return {"results": results}

    def _send_email(self, subject: str, content: str):
        """发送邮件"""
        config = self.notification_config.get("email", {})
        msg = MIMEText(content, "plain", "utf-8")
        msg["Subject"] = f"[ClawsJoy] {subject}"
        msg["From"] = config.get("sender")
        msg["To"] = ", ".join(config.get("receivers", []))

        with smtplib.SMTP(config.get("smtp_server"), config.get("smtp_port")) as server:
            server.starttls()
            server.login(config.get("sender"), config.get("password"))
            server.send_message(msg)

    def _log_task(self, task: str, result: Dict):
        """记录任务执行"""
        self.task_log.append(
            {"task": task, "result": result, "timestamp": datetime.now().isoformat()}
        )
        # 保留最近100条
        self.task_log = self.task_log[-100:]

    def run_maintenance(self) -> Dict:
        """运行完整维护流程"""
        print("\n🔧 开始系统维护...")

        # 1. 清理缓存
        cache_result = self.clear_cache()
        print(f"  🗑️ 清理缓存: 释放 {cache_result['freed_bytes']} bytes")

        # 2. 优化技能
        skill_result = self.optimize_skills()
        print(f"  🔧 优化技能: 检查 {skill_result['skills_checked']} 个")

        # 3. 生成报告
        report = self.generate_report()
        print(f"  📊 生成报告: {report.get('file', '')}")

        # 4. 如果有问题，发送通知
        if report.get("issues"):
            self.send_notification(
                "系统发现问题",
                f"发现 {len(report['issues'])} 个问题: {report['issues'][:3]}",
                "warning",
            )

        return {
            "cache": cache_result,
            "skills": skill_result,
            "report": report,
            "timestamp": datetime.now().isoformat(),
        }


proactive = ProactiveService()

# 全局实例
proactive_service = ProactiveService()
