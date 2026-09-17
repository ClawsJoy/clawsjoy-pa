"""测试 Agent - LLM 驱动的配置决策 + 记录"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from lib.smart_adapter import smart_adapter
from lib.workspace_manager import workspace_manager

from core.agents.base.smart_agent import SmartAgent


class TestAgent001(SmartAgent):
    name = "test_agent_001"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self.behavior = workspace_manager.get_behavior_config("test_agent_001")
        # 记录目录
        self.log_dir = Path("data/exchange")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        print(f"🧪 测试Agent 初始化完成")

    def _save_record(self, record: dict):
        """保存记录"""
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
        filepath = self.log_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
        print(f"[记录] 已保存: {filepath}")

    def process(self, user_input: str, context=None) -> Dict:
        print(f"[Test] 收到: {user_input}")

        routing = self.behavior.get("routing", {}) if self.behavior else {}
        rules = routing.get("rules", [])

        if not rules:
            return {"response": "无配置规则", "success": False}

        prompt = f"""
根据以下规则，判断用户输入应该触发哪个动作。

规则列表:
{json.dumps(rules, ensure_ascii=False, indent=2)}

用户输入: {user_input}

请返回 JSON 格式，只输出 JSON:
{{"action": "delegate或respond", "target": "目标Agent", "response": "直接响应内容", "reason": "判断理由"}}
"""

        try:
            llm_response = smart_adapter.generate(prompt, auto_select=True)
            json_match = re.search(r"\{.*\}", llm_response, re.DOTALL)
            result = json.loads(json_match.group()) if json_match else json.loads(llm_response)

            print(f"[Test] LLM 决策: {result}")

            # 记录决策
            decision_record = {
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "user_id": self.user_id,
                "input": user_input,
                "decision": result,
                "llm_raw_response": llm_response,
            }
            self._save_record(decision_record)

            if result.get("action") == "delegate":
                target = result.get("target")
                if target:
                    import requests

                    start_time = datetime.now()

                    resp = requests.post(
                        f"http://localhost:5002/api/agent/{target}/message",
                        json={"message": user_input, "user_id": self.user_id},
                        timeout=5,
                    )

                    # 记录调用
                    call_record = {
                        "timestamp": start_time.isoformat(),
                        "duration_ms": (datetime.now() - start_time).total_seconds() * 1000,
                        "from": self.name,
                        "to": target,
                        "request": user_input,
                        "response": resp.json() if resp.status_code == 200 else None,
                        "status_code": resp.status_code,
                    }
                    self._save_record(call_record)

                    if resp.status_code == 200:
                        data = resp.json()
                        return {
                            "response": data.get("response", "处理完成"),
                            "success": True,
                            "user_id": self.user_id,
                            "agent": self.name,
                        }
            elif result.get("action") == "respond":
                return {
                    "response": result.get("response", "已处理"),
                    "success": True,
                    "user_id": self.user_id,
                    "agent": self.name,
                }
        except Exception as e:
            print(f"[Test] 错误: {e}")

        return {"response": "无法处理", "success": False, "user_id": self.user_id}


test_agent_001 = TestAgent001()
