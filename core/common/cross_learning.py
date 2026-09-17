#!/usr/bin/env python3
"""Cross Learning - Cross Learning 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import json
from pathlib import Path
from core.lib import config_helper


class CrossLearning:
    """跨区学习管理器"""

    VERSION = "1.0.0"

    def __init__(self):
        self.shared_memory = Path(f"{config_helper.get_data_root()}/shared_memory")
        self.shared_memory.mkdir(parents=True, exist_ok=True)
        print(f"🔄 跨区学习模块 v{self.VERSION} 已启动")

    def share_knowledge(self, from_agent: str, to_agent: str, knowledge: Dict) -> bool:
        """分享知识到其他 Agent"""
        record = {
            "from": from_agent,
            "to": to_agent,
            "knowledge": knowledge,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "status": "pending",
        }

        # 写入共享队列
        queue_file = self.shared_memory / f"{from_agent}_to_{to_agent}.json"
        data = []
        if queue_file.exists():
            with open(queue_file, "r") as f:
                data = json.load(f)
        data.append(record)
        with open(queue_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"📤 {from_agent} 分享知识给 {to_agent}")
        return True

    def receive_knowledge(self, agent: str) -> list:
        """接收其他 Agent 分享的知识"""
        queue_file = self.shared_memory / f"*_to_{agent}.json"
        import glob

        results = []
        for f in glob.glob(str(queue_file)):
            with open(f, "r") as fp:
                data = json.load(fp)
                for item in data:
                    if item.get("status") == "pending":
                        item["status"] = "received"
                        results.append(item)
            # 更新状态
            with open(f, "w") as fp:
                json.dump(data, fp, indent=2)

        if results:
            print(f"📥 {agent} 收到 {len(results)} 条知识分享")
        return results

    def get_shared_stats(self) -> Dict:
        """获取共享统计"""
        import glob

        files = glob.glob(str(self.shared_memory / "*.json"))
        return {
            "shared_files": len(files),
            "shared_memory_path": str(self.shared_memory),
        }


cross_learning = CrossLearning()
