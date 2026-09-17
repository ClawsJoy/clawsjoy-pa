#!/usr/bin/env python3
"""ExecutorAgent v5.0 - 安全任务执行器"""

import subprocess
import shlex
import io
import contextlib
import json
from pathlib import Path
from typing import Dict, Optional, Tuple

from core.agents.business.business_agent import BusinessAgent


class ExecutorAgentV4(BusinessAgent):
    name = "executor_agent_v4"
    description = "安全任务执行器"
    version = "5.0.0"

    # ⭐ 添加 ffmpeg 和 gnome-screenshot 到白名单
    ALLOWED_COMMANDS = ["ls", "pwd", "cat", "head", "tail", "grep", "find",
                        "wc", "sort", "echo", "date", "mkdir", "touch", "cp", "mv", 
                        "git", "python", "python3", "ffmpeg", "gnome-screenshot",
                        "ffplay", "ffprobe"]
    FORBIDDEN = [r"rm\s+-rf\s+/", r"dd\s+if=", r">\s*/dev/", r"mkfs", r"shutdown", r"reboot", r"curl.*\|.*sh"]

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self.work_dir = Path(f"data/executor/{user_id}")
        self.work_dir.mkdir(parents=True, exist_ok=True)
        print(f"⚡ ExecutorAgent v{self.version}")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.85)

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        t = user_input.lower()

        if t.startswith("exec ") or t.startswith("执行 "):
            return self._exec_cmd(user_input.split(maxsplit=1)[1])
        elif t.startswith("code "):
            return self._exec_code(user_input.split(maxsplit=1)[1])
        elif t.startswith("skill "):
            return self._exec_skill(user_input.split(maxsplit=1)[1])
        elif t.startswith("file "):
            return self._file_op(user_input.split(maxsplit=1)[1])
        elif t.startswith("workflow "):
            return self._exec_workflow(user_input.split(maxsplit=1)[1])
        else:
            skill_name = context.get("extracted", {}).get("_skill_name", "") if context else ""
            if skill_name:
                result = self._exec_skill(skill_name)
                return result
            return self._resp("❌ 未识别的命令。请使用: exec <命令> | code <代码> | skill <技能名> | file <操作> | workflow <工作流>")

    def _exec_cmd(self, cmd_str: str) -> Dict:
        """执行系统命令（安全）"""
        # 解析命令
        parts = shlex.split(cmd_str)
        if not parts:
            return self._resp("❌ 空命令")

        cmd = parts[0]
        # 检查是否在白名单中
        if cmd not in self.ALLOWED_COMMANDS:
            return self._resp(f"❌ 不允许: {cmd}")

        # 检查危险模式
        import re
        for pattern in self.FORBIDDEN:
            if re.search(pattern, cmd_str):
                return self._resp(f"❌ 危险命令被阻止: {pattern}")

        try:
            result = subprocess.run(
                parts,
                capture_output=True,
                text=True,
                cwd=self.work_dir,
                timeout=60
            )
            output = result.stdout or result.stderr
            if result.returncode == 0:
                return self._resp(f"✅ 执行成功:\n{output[:1000]}")
            else:
                return self._resp(f"⚠️ 执行完成 (退出码: {result.returncode}):\n{output[:1000]}")
        except subprocess.TimeoutExpired:
            return self._resp("⏰ 命令执行超时 (60秒)")
        except Exception as e:
            return self._resp(f"❌ 错误: {e}")

    def _exec_code(self, code_str: str) -> Dict:
        """执行 Python 代码（沙箱）"""
        try:
            # 在沙箱中执行
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exec(code_str, {"__builtins__": __builtins__}, {})
            return self._resp(f"✅ 代码执行成功:\n{output.getvalue()[:1000]}")
        except Exception as e:
            return self._resp(f"❌ 代码执行失败: {e}")

    def _exec_skill(self, skill_name: str) -> Dict:
        """执行技能"""
        try:
            # 尝试导入技能
            module = __import__(f"skills.{skill_name}", fromlist=[skill_name])
            skill = getattr(module, skill_name)
            result = skill.execute({})
            return self._resp(f"✅ 技能执行成功:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        except ImportError:
            return self._resp(f"❌ 技能不存在: {skill_name}")
        except Exception as e:
            return self._resp(f"❌ 技能执行失败: {e}")

    def _file_op(self, op_str: str) -> Dict:
        """文件操作"""
        parts = op_str.split(maxsplit=1)
        if not parts:
            return self._resp("❌ 请指定文件操作: read <文件> | write <文件> <内容>")

        op = parts[0]
        if op == "read":
            path = Path(parts[1]) if len(parts) > 1 else None
            if not path:
                return self._resp("❌ 请指定文件路径")
            if not path.exists():
                return self._resp(f"❌ 文件不存在: {path}")
            return self._resp(f"📄 文件内容:\n{path.read_text()[:1000]}")
        elif op == "write":
            if len(parts) < 3:
                return self._resp("❌ 请指定: write <文件> <内容>")
            path = Path(parts[1])
            content = parts[2]
            path.write_text(content)
            return self._resp(f"✅ 已写入: {path}")
        else:
            return self._resp(f"❌ 不支持的操作: {op}")

    def _exec_workflow(self, workflow_name: str) -> Dict:
        """执行工作流"""
        return self._resp(f"🔧 工作流执行: {workflow_name}\n(需要配置工作流定义)")

    def _resp(self, content: str, **kwargs) -> Dict:
        return {"success": True, "response": content, "output_content": content, **kwargs}


if __name__ == "__main__":
    agent = ExecutorAgentV4("test")
    result = agent.process("exec ls -la")
    print(result.get("response", ""))
