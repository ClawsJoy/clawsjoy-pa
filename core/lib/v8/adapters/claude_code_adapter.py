#!/usr/bin/env python3
"""Claude Code CLI 适配器"""

import json
import subprocess
from . import BaseAdapter


class ClaudeCodeAdapter(BaseAdapter):
    """Claude Code CLI 适配器"""

    def execute(self, prompt: str, system_prompt: str = "", history: list = None,
                workspace: str = "/sandbox/default") -> dict:
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{full_prompt}"

        cmd = [
            "claude", "-p", full_prompt,
            "--add-dir", workspace,
            "--output-format", "json",
            "--allowedTools", "Read,Edit",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                content = data.get("result", data.get("content", result.stdout))
                tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
                return {"success": True, "content": content, "tokens": tokens or self.count_tokens(prompt + content), "model": "claude-code"}
            else:
                return {"success": False, "content": result.stderr or "CLI执行失败", "tokens": 0, "model": "claude-code"}
        except FileNotFoundError:
            return {"success": False, "content": "Claude Code CLI 未安装", "tokens": 0, "model": "claude-code"}
        except Exception as e:
            return {"success": False, "content": f"CLI错误: {e}", "tokens": 0, "model": "claude-code"}
