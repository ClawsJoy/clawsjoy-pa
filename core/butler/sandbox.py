#!/usr/bin/env python3
"""用户沙箱 - 安全执行环境"""

import subprocess
import tempfile
import os
import re
from pathlib import Path
from typing import Dict

class UserSandbox:
    """用户沙箱 - 安全执行代码"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.work_dir = Path(f"/tmp/sandbox/{user_id}")
        self.work_dir.mkdir(parents=True, exist_ok=True)
    
    def execute_code(self, code: str, timeout: int = 10) -> Dict:
        """安全执行 Python 代码"""
        # 安全检查
        if not self._is_safe(code):
            return {"success": False, "error": "代码包含危险操作"}
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            result = subprocess.run(
                ['python3', temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.work_dir)
            )
            
            os.unlink(temp_file)
            
            output = result.stdout if result.stdout else result.stderr
            return {
                "success": result.returncode == 0,
                "output": output,
                "error": result.stderr if result.stderr else None
            }
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "执行超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _is_safe(self, code: str) -> bool:
        """安全检查"""
        dangerous = [
            r'os\.system', r'subprocess', r'eval', r'exec',
            r'__import__', r'open\(.*["\']w', r'rm\s+-rf',
            r'import\s+os', r'import\s+sys', r'builtins'
        ]
        for pattern in dangerous:
            if re.search(pattern, code):
                return False
        return True
    
    def execute_command(self, cmd: str, timeout: int = 30) -> Dict:
        """执行命令（受限）"""
        allowed_commands = ['ls', 'pwd', 'echo', 'cat']
        cmd_name = cmd.split()[0] if cmd else ""
        
        if cmd_name not in allowed_commands:
            return {"success": False, "error": f"命令 {cmd_name} 不允许执行"}
        
        try:
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.work_dir)
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

def set_user_local_root(path: str):
    """设置用户本地根目录"""
    os.environ["CLAWSJOY_USER_ROOT"] = path
