#!/usr/bin/env python3
"""增量修复器 - 只修改问题行/块"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Union

sys.path.insert(0, '/home/flybo/clawsjoy_v5')


class IncrementalFixer:
    """增量修复器 - 逐行/逐块修改，保留其他代码"""

    def __init__(self):
        self.lines: List[str] = []
        self.file_path: Optional[str] = None

    def load_file(self, file_path: str) -> bool:
        """加载文件"""
        self.file_path = file_path
        path = Path(file_path)
        if not path.exists():
            return False
        self.lines = path.read_text(encoding='utf-8').split('\n')
        return True

    def fix_line(self, line_num: int, new_line: str) -> Dict:
        """修复指定行"""
        if line_num < 1 or line_num > len(self.lines):
            return {'success': False, 'error': f'行号 {line_num} 超出范围'}

        old_line = self.lines[line_num - 1]
        self.lines[line_num - 1] = new_line

        return {
            'success': True,
            'line': line_num,
            'old': old_line,
            'new': new_line,
            'changed': old_line != new_line
        }

    def fix_line_with_context(self, line_num: int, new_line: str, context_lines: int = 3) -> Dict:
        """修复指定行，并提供上下文供验证"""
        if line_num < 1 or line_num > len(self.lines):
            return {'success': False, 'error': f'行号 {line_num} 超出范围'}

        start = max(0, line_num - context_lines - 1)
        end = min(len(self.lines), line_num + context_lines)

        context_before = self.lines[start:line_num - 1]
        context_after = self.lines[line_num:end]
        old_line = self.lines[line_num - 1]

        return {
            'success': True,
            'line': line_num,
            'old': old_line,
            'new': new_line,
            'context_before': context_before,
            'context_after': context_after,
            'changed': old_line != new_line
        }

    def fix_block(self, start_line: int, end_line: int, new_lines: List[str]) -> Dict:
        """修复一个代码块（多行）"""
        if start_line < 1 or end_line > len(self.lines) or start_line > end_line:
            return {'success': False, 'error': '行号范围无效'}

        old_block = self.lines[start_line - 1:end_line]
        self.lines[start_line - 1:end_line] = new_lines

        return {
            'success': True,
            'start_line': start_line,
            'end_line': end_line,
            'old': old_block,
            'new': new_lines,
            'changed': old_block != new_lines
        }

    def save(self) -> bool:
        """保存修改后的文件"""
        if not self.file_path:
            return False
        Path(self.file_path).write_text('\n'.join(self.lines), encoding='utf-8')
        return True

    def get_lines(self) -> List[str]:
        """获取当前所有行"""
        return self.lines

    def get_diff(self) -> str:
        """获取修改差异（类似 git diff）"""
        # 简单实现：显示修改前后的对比
        return '待实现'


def create_fixer(file_path: str) -> Optional[IncrementalFixer]:
    """创建增量修复器实例"""
    fixer = IncrementalFixer()
    if fixer.load_file(file_path):
        return fixer
    return None
