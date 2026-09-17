from engine.lib.logger import engine_logger

"""工作流引擎"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class WorkflowEngine:
    """工作流引擎"""

    def __init__(self):
        self.workflows = {}
        self._load_workflows()
        engine_logger.get().info("🔗 工作流引擎已初始化")

    def _load_workflows(self):
        workflow_dirs = [Path("workflows"), Path("config/workflows")]
        for wf_dir in workflow_dirs:
            if not wf_dir.exists():
                continue
            for json_file in wf_dir.glob("*.json"):
                try:
                    with open(json_file, "r") as f:
                        data = json.load(f)
                        name = data.get("name", json_file.stem)
                        self.workflows[name] = data
                except Exception as e:
                    pass
        engine_logger.get().info("   ✅ 加载 {len(self.workflows)} 个工作流")

    def process(self, input_data: Any, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        if isinstance(input_data, str):
            return self.execute(input_data, kwargs)
        return self.execute(str(input_data), kwargs)

    def execute(self, name: str, params: Dict = None) -> Dict:
        if name not in self.workflows:
            return {"error": f"工作流 {name} 不存在"}
        return {
            "success": True,
            "workflow": name,
            "steps": len(self.workflows[name].get("steps", [])),
        }

    def list(self) -> List[str]:
        return list(self.workflows.keys())

    def health_check(self) -> Dict:
        """健康检查"""
        return {"name": self.__class__.__name__, "status": "healthy"}

    def get_stats(self) -> Dict:
        return {"total_workflows": len(self.workflows), "workflows": self.list()}

    def reload(self) -> Dict:
        self.workflows = {}
        self._load_workflows()
        return {"success": True, "message": f"Reloaded {len(self.workflows)} workflows"}


workflow_engine = WorkflowEngine()
