#!/usr/bin/env python3
"""Monitor Alert - Monitor Alert 模块

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

#!/usr/bin/env python3
"""监控告警系统"""

import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import requests


class MonitorAlert:
    VERSION = "1.0.0"

    def __init__(self):
        self.alerts = []
        self.alert_file = Path(f"{get_data_root()}/alerts.json")
        self._load_alerts()

    def _load_alerts(self):
        if self.alert_file.exists():
            import json

            with open(self.alert_file, "r") as f:
                self.alerts = json.load(f)

    def _save_alerts(self):
        import json

        with open(self.alert_file, "w") as f:
            json.dump(self.alerts[-1000:], f, indent=2)

    def check_service(self, url: str, timeout: int = 5) -> Dict:
        try:
            start = time.time()
            resp = requests.get(url, timeout=timeout, verify=False)
            elapsed = time.time() - start
            return {
                "url": url,
                "status": "up" if resp.status_code == 200 else "down",
                "status_code": resp.status_code,
                "response_time": elapsed,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "url": url,
                "status": "down",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def check_services(self) -> List[Dict]:
        services = [
            (
                f"http://{unified_config.get("services.driver.host", "localhost")}:{unified_config.get("services.driver.port", 5443)}/health",
                "驱动服务",
            ),
            (
                f"http://{unified_config.get("services.auth.host", "localhost")}:{unified_config.get("services.auth.port", 5444)}/auth/verify",
                "认证服务",
            ),
            (
                f"http://{unified_config.get("services.preference.host", "localhost")}:{unified_config.get("services.preference.port", 5445)}/",
                "偏好服务",
            ),
            (
                f"http://{unified_config.get("services.web.host", "localhost")}:{unified_config.get("services.web.port", 5446)}/",
                "Web服务",
            ),
            ("config_loader.get_ollama_url()/api/tags", "Ollama"),
        ]
        results = []
        for url, name in services:
            result = self.check_service(url)
            result["name"] = name
            results.append(result)
        return results

    def check_and_alert(self) -> List[Dict]:
        alerts = []
        services = self.check_services()
        for svc in services:
            if svc["status"] == "down":
                alert = {
                    "level": "critical",
                    "type": "service",
                    "name": svc.get("name", svc["url"]),
                    "error": svc.get("error", "连接失败"),
                    "timestamp": datetime.now().isoformat(),
                }
                alerts.append(alert)
                print(f"⚠️ 告警: {alert}")

        for alert in alerts:
            self.alerts.append(alert)
        self._save_alerts()
        return alerts

    def start_monitor(self, interval: int = 60):
        def _monitor():
            while True:
                time.sleep(interval)
                self.check_and_alert()

        thread = threading.Thread(target=_monitor, daemon=True)
        thread.start()
        print(f"📊 监控已启动 (间隔 {interval}s)")


monitor = MonitorAlert()


if __name__ == "__main__":
    print(f"监控告警 v{monitor.VERSION}")
    alerts = monitor.check_and_alert()
    print(f"发现告警: {len(alerts)}")
    monitor.start_monitor(30)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n监控停止")
