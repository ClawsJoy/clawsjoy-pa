from pathlib import Path

"""任务规划器 - 将自然语言转换为任务计划"""

import re
from typing import Dict, List


class TaskPlanner:
    """任务规划器"""

    # 任务模板库
    DAG_KEYWORDS = {"dag", "并行", "依赖", "并行组", "拆解", "多任务", "pipeline"}
    PARALLEL_MAX = 5
    TEMPLATES = {
        "video_production": {
            "name": "视频制作",
            "description": "制作一个{title}视频",
            "tasks": [
                {
                    "name": "understand",
                    "agent": "chat_agent",
                    "action": "understand",
                    "message": "理解需求",
                    "estimated": 5,
                },
                {
                    "name": "collect",
                    "agent": "video_agent",
                    "action": "search",
                    "message": "收集素材",
                    "estimated": 30,
                },
                {
                    "name": "script",
                    "agent": "writer_agent",
                    "action": "write",
                    "message": "生成脚本",
                    "estimated": 20,
                },
                {
                    "name": "voice",
                    "agent": "audio_agent",
                    "action": "tts",
                    "message": "制作配音",
                    "estimated": 15,
                    "optional": True,
                },
                {
                    "name": "edit",
                    "agent": "video_agent",
                    "action": "edit",
                    "message": "剪辑视频",
                    "estimated": 60,
                },
                {
                    "name": "subtitle",
                    "agent": "video_agent",
                    "action": "subtitle",
                    "message": "添加字幕",
                    "estimated": 10,
                    "optional": True,
                },
            ],
        },
        "image_generation": {
            "name": "图像生成",
            "description": "生成{title}图像",
            "tasks": [
                {
                    "name": "generate",
                    "agent": "vision_agent",
                    "action": "generate",
                    "message": "生成图像",
                    "estimated": 15,
                },
                {
                    "name": "analyze",
                    "agent": "vision_agent",
                    "action": "analyze",
                    "message": "分析图像",
                    "estimated": 10,
                    "optional": True,
                },
                {
                    "name": "optimize",
                    "agent": "vision_agent",
                    "action": "optimize",
                    "message": "优化图像",
                    "estimated": 10,
                    "optional": True,
                },
            ],
        },
        "data_analysis": {
            "name": "数据分析",
            "description": "分析{title}数据",
            "tasks": [
                {
                    "name": "collect",
                    "agent": "collector_agent",
                    "action": "collect",
                    "message": "收集数据",
                    "estimated": 20,
                },
                {
                    "name": "analyze",
                    "agent": "analysis_agent",
                    "action": "analyze",
                    "message": "分析数据",
                    "estimated": 30,
                },
                {
                    "name": "report",
                    "agent": "writer_agent",
                    "action": "write",
                    "message": "生成报告",
                    "estimated": 20,
                },
            ],
        },
        "code_generation": {
            "name": "代码生成",
            "description": "创建{title}代码文件",
            "tasks": [
                {
                    "name": "create_first_file",
                    "agent": "chat_agent",
                    "action": "write",
                    "message": "创建{file1}文件",
                    "estimated": 10,
                    "depends_on": [],
                    "parallel_group": "g1",
                },
                {
                    "name": "create_second_file",
                    "agent": "chat_agent",
                    "action": "write",
                    "message": "创建{file2}文件",
                    "estimated": 10,
                    "depends_on": [],
                    "parallel_group": "g1",
                },
            ],
        },
        "audit": {
            "name": "审计分析",
            "description": "对{title}进行审计分析（只读 read_file + query_index，不要求 write_file）",
            "tasks": [
                {
                    "name": "audit",
                    "agent": "analysis_agent",
                    "action": "audit",
                    "message": "审计检查：{title}",
                    "estimated": 10,
                    "depends_on": [],
                    "tools": ["read_file", "query_index"],
                    "requires_write_file": False,
                    "done_when": "报告该项检查结果",
                },
            ],
        },
    }

    def plan(self, user_input: str) -> Dict:
        """生成任务计划"""

        # 1. 识别意图
        intent = self._detect_intent(user_input)
        if self._is_dag_request(user_input):
            result = self.plan_dag(user_input)
            # 注入 Brief：从 user_input 提取 user_id / session_id，生成任务简报并回填 task_id
            user_id, session_id = "", ""
            if isinstance(user_input, dict):
                user_id = str(user_input.get("user_id", ""))
                session_id = str(user_input.get("session_id", ""))
            else:
                m = re.search(r"(?:data/projects/)?([\w.\-]+)/(session_\w+)", str(user_input))
                if m:
                    user_id, session_id = m.group(1), m.group(2)
                else:
                    mu = re.search(r"user_id[:=]([\w.\-]+)", str(user_input))
                    ms = re.search(r"session_id[:=]([\w.\-]+)", str(user_input))
                    user_id = mu.group(1) if mu else ""
                    session_id = ms.group(1) if ms else ""
            if user_id and session_id:
                try:
                    from core.lib.brief_manager import get_brief_manager

                    result["task_id"] = get_brief_manager(user_id, session_id).generate(user_input)
                except Exception:
                    pass
            return result

        # 2. 提取参数
        params = self._extract_params(user_input, intent)

        # 3. 选择模板
        template = self.TEMPLATES.get(intent, self.TEMPLATES["video_production"])

        # 4. 填充模板
        return {
            "success": True,
            "intent": intent,
            "name": template["name"],
            "description": template["description"].format(**params),
            "tasks": template["tasks"],
            "params": params,
            "total_estimated": sum(t.get("estimated", 0) for t in template["tasks"]),
        }

    def plan_dag(self, user_input: str) -> Dict:
        """DAG 模式任务规划：拆解为最小任务单元并构建依赖拓扑"""
        try:
            # 1. 意图兜底 + 提取参数
            intent = self._detect_intent(user_input)
            params = self._extract_params(user_input, intent)
            title = params.get("title", "任务")

            # 2. 拆解为最小任务单元（t1, t2...）：由模板库 _template_to_dag 动态生成（替换硬编码）
            # 1.5 从 user_input 中动态提取 .py 文件名（如 hello.py、world.py）
            py_files = re.findall(r"[\w./\-\\]+\.py\b", user_input)
            py_files = list(dict.fromkeys(py_files))  # 去重保序

            # 2. 拆解为最小任务单元（t1, t2...）：由模板库 _template_to_dag 动态生成（替换硬编码）
            if py_files:
                # 动态生成：每个 .py 文件一个 create 任务，互不依赖（并行）
                raw_tasks = [
                    {
                        "name": "t{}".format(i),
                        "agent": "code_agent",
                        "action": "create",
                        "message": "创建文件 {}".format(f),
                        "estimated": 10,
                        "depends_on": [],  # 自动设置：无前置依赖
                        "files": [f],
                    }
                    for i, f in enumerate(py_files, 1)
                ]
                params["py_files"] = py_files
            else:
                raw_tasks = self._template_to_dag(intent, params)

            # 2.5 审计意图：展开为只读审计任务（read_file + query_index，不要求 write_file）
            if intent == "audit":
                raw_tasks = self._expand_audit_task(user_input, params)
            # 3. 拓扑分层 parallel_group（g1, g2...）：基于模板 tasks 的 depends_on 依赖链
            depth_map = {t["name"]: 0 for t in raw_tasks}
            for _ in range(len(raw_tasks)):
                for task in raw_tasks:
                    for dep in task.get("depends_on", []):
                        depth_map[task["name"]] = max(depth_map[task["name"]], depth_map.get(dep, 0) + 1)
            layers = {}
            for task in raw_tasks:
                layers.setdefault(depth_map[task["name"]], []).append(task)

            # 5. 收集每个任务的 files 并输出
            tasks = []
            for depth in sorted(layers):
                group_name = "g{}".format(depth + 1)
                for task in layers[depth]:
                    task["parallel_group"] = group_name
                    task.setdefault("files", ["outputs/{}.txt".format(task["name"])])
                    task["done_when"] = "check:file_exists:{file}".format(file=task["files"][0])
                    tasks.append(task)

            return {
                "dag": True,
                "success": True,
                "intent": intent,
                "params": params,
                "tasks": tasks,
                "mode": "dag",
                "total_estimated": sum(t.get("estimated", 0) for t in tasks),
            }
        except Exception:
            # 异常时回退到原 plan() 逻辑（临时绕过 dag 分支，避免递归）
            orig_check = self._is_dag_request
            self._is_dag_request = lambda _u: False
            try:
                return self.plan(user_input)
            finally:
                self._is_dag_request = orig_check

    def _template_to_dag(self, intent: str, params: Dict) -> List[Dict]:
        """根据模板库生成 DAG 任务单元：t1/t2... 编号 + depends_on 依赖映射"""
        template = self.TEMPLATES.get(intent, self.TEMPLATES["video_production"])
        raw_tasks = []
        name_map = {}
        for idx, t in enumerate(template.get("tasks", []), 1):
            name = "t{}".format(idx)
            name_map[t.get("name", name)] = name
            msg = t.get("message", "")
            if "{" in msg:
                try:
                    msg = msg.format(**params)
                except Exception:
                    pass
            raw_tasks.append(
                {
                    "name": name,
                    "agent": t.get("agent", "chat_agent"),
                    "action": t.get("action", t.get("name", "")),
                    "message": msg,
                    "estimated": t.get("estimated", 10),
                    "optional": t.get("optional", False),
                    "rollback": t.get("rollback", ""),
                }
            )
        # depends_on：模板内任务名 → tN 编号
        for idx, t in enumerate(template.get("tasks", [])):
            raw_tasks[idx]["depends_on"] = [name_map.get(d, d) for d in t.get("depends_on", [])]
        return raw_tasks

    def _expand_audit_task(self, user_input: str, params: Dict) -> List[Dict]:
        """审计意图：展开为只读审计任务（read_file + query_index，不要求 write_file）"""
        template = self.TEMPLATES.get("audit", self.TEMPLATES["video_production"])
        raw_tasks = []
        for idx, t in enumerate(template.get("tasks", []), 1):
            msg = t.get("message", "")
            if "{" in msg:
                try:
                    msg = msg.format(**params)
                except Exception:
                    pass
            raw_tasks.append(
                {
                    "name": "t{}".format(idx),
                    "agent": t.get("agent", "analysis_agent"),
                    "action": t.get("action", "audit"),
                    "message": msg,
                    "estimated": t.get("estimated", 10),
                    "depends_on": t.get("depends_on", []),
                    "tools": t.get("tools", ["read_file", "query_index"]),
                    "requires_write_file": t.get("requires_write_file", False),
                    "done_when": t.get("done_when", "报告该项检查结果"),
                }
            )
        return raw_tasks

    def _is_dag_request(self, user_input: str) -> bool:
        """检查用户输入是否包含 DAG 关键词"""
        return any(kw in user_input for kw in self.DAG_KEYWORDS)

    def _detect_intent(self, user_input: str) -> str:
        """检测意图"""
        if "审计" in user_input or "audit" in user_input.lower():
            return "audit"
        if "视频" in user_input and ("制作" in user_input or "剪辑" in user_input):
            return "video_production"
        elif "图片" in user_input and ("生成" in user_input or "画" in user_input):
            return "image_generation"
        elif "分析" in user_input and ("数据" in user_input or "趋势" in user_input):
            return "data_analysis"
        elif any(kw in user_input for kw in ("代码", "编程", "写", "创建", "实现", "开发")):
            if "数据" in user_input or "分析" in user_input:
                return "data_analysis"
            return "code_generation"
        else:
            return "video_production"  # 默认

    def _extract_params(self, user_input: str, intent: str) -> Dict:
        """提取参数"""
        # 提取主题
        title = user_input
        keywords = ["制作", "生成", "分析", "关于", "一个"]
        for kw in keywords:
            title = title.replace(kw, "")
        title = title.strip()[:50]

        return {"title": title or "默认主题"}


class TaskExecutor:
    """任务执行器 - 不修改原有 Agent，通过标准接口调用"""

    def __init__(self):
        self.results = []
        self.checkpoints = []

    def execute(self, task: Dict, user_id: str) -> Dict:
        """执行单个任务"""
        agent_name = task.get("agent")
        action = task.get("action")
        message = task.get("message", "")

        # 通过标准接口调用 Agent
        result = self._call_agent(agent_name, action, message, user_id)

        return {
            "task": task.get("name"),
            "success": result.get("success", False),
            "result": result,
            "message": message,
        }

    def _call_agent(self, agent_name: str, action: str, message: str, user_id: str) -> Dict:
        """调用 Agent（不修改原有代码）"""
        try:
            # 动态导入 Agent
            if agent_name == "video_agent":
                from agents.video_agent.agent_v4 import VideoAgentV4 as VideoAgent

                agent = VideoAgent(user_id)
                return agent.process(message)
            elif agent_name == "vision_agent":
                from agents.vision_agent.agent import VisionAgent

                agent = VisionAgent(user_id)
                return agent.process(message)
            elif agent_name == "writer_agent":
                from agents.writer_agent.agent import WriterAgent

                agent = WriterAgent(user_id)
                return agent.process(message)
            elif agent_name == "chat_agent":
                from agents.chat_agent.agent import ChatAgent

                agent = ChatAgent(user_id)
                return agent.process(message)
            else:
                from agents.executor_agent.agent import ExecutorAgent

                agent = ExecutorAgent(user_id)
                return agent.process(message)
        except Exception as e:
            return {"success": False, "error": str(e)}


class ProgressTracker:
    """进度追踪器"""

    def __init__(self, storage_dir: str = "data/orchestration"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, plan_id: str, data: Dict):
        """保存进度"""
        import json

        with open(self.storage_dir / f"{plan_id}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self, plan_id: str) -> Dict:
        """加载进度"""
        import json

        file = self.storage_dir / f"{plan_id}.json"
        if file.exists():
            with open(file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def format_progress(self, completed: int, total: int) -> str:
        """格式化进度显示"""
        percent = int(completed / total * 100)
        bar_length = 20
        filled = int(bar_length * completed / total)
        bar = "█" * filled + "░" * (bar_length - filled)
        return f"[{bar}] {percent}% ({completed}/{total})"
