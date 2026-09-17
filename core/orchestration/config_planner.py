"""配置驱动的任务规划器"""

import glob
from pathlib import Path
from typing import Dict, List, Optional

import yaml


class ConfigPlanner:
    def __init__(self, config_path: str = "config/orchestration/templates.yaml"):
        self.config_path = Path(config_path)
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict:
        if not self.config_path.exists():
            return {}
        with open(self.config_path, "r") as f:
            data = yaml.safe_load(f)
            return data.get("templates", {})

    def detect_intent(self, user_input: str) -> Optional[str]:
        for template_name, template in self.templates.items():
            triggers = template.get("triggers", [])
            for trigger in triggers:
                if trigger in user_input:
                    return template_name
        return None

    def create_tasks(self, user_input: str) -> List[Dict]:
        intent = self.detect_intent(user_input)
        if not intent:
            return self._create_default_tasks(user_input)

        template = self.templates.get(intent, {})
        tasks_config = template.get("tasks", [])

        video_files = glob.glob("downloads/*.mp4")
        video_file = video_files[0] if video_files else "downloads/sample.mp4"

        tasks = []
        for task_config in tasks_config:
            message = task_config.get("message", "")
            message = message.replace("{user_input}", user_input)
            message = message.replace("{video_file}", video_file)

            tasks.append(
                {
                    "name": task_config.get("name"),
                    "agent": task_config.get("agent"),
                    "params": {"message": message},
                    "depends_on": task_config.get("depends_on", []),
                    "optional": task_config.get("optional", False),
                }
            )

        return tasks

    def _create_default_tasks(self, user_input: str) -> List[Dict]:
        return [
            {
                "name": "analyze",
                "agent": "analysis_agent",
                "params": {"message": user_input},
                "depends_on": [],
                "optional": False,
            }
        ]

    def list_templates(self) -> List[str]:
        return list(self.templates.keys())


config_planner = ConfigPlanner()
