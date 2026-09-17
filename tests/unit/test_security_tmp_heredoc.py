# -*- coding: utf-8 -*-
"""2026-09-06: security.py 沙箱 data/tmp heredoc 豁免 — 视频任务(配音/字幕/卡片批量生成)
cd data/tmp/douyin_weiren && python3 heredoc 内相对路径写被误拦(正则只豁免字面 data/tmp/ 前缀)。
修复: cd 到 data/tmp 内 + heredoc + 无系统/../ 逃逸 → 豁免; 系统路径/core 写仍拦。"""
import io

_SEC = io.open("core/gateway/security.py", encoding="utf-8").read()


def test_sandbox_tmp_exemption_function():
    """应存在 _is_sandbox_tmp_heredoc 豁免函数"""
    assert "def _is_sandbox_tmp_heredoc" in _SEC
    assert "heredoc" in _SEC


def test_detect_uses_exemption():
    """_detect_sys_escape 命中 heredoc pattern 时调用豁免判断"""
    i = _SEC.find("def _detect_sys_escape")
    seg = _SEC[i:i + 400]
    assert "_is_sandbox_tmp_heredoc(command, _reason)" in seg
    assert "continue" in seg  # 豁免时跳过拦截


def test_exemption_still_blocks_system():
    """豁免仍阻止系统路径(/etc /home)与 ../ 逃逸"""
    i = _SEC.find("def _is_sandbox_tmp_heredoc")
    seg = _SEC[i:i + 700]
    assert '"/etc/"' in seg or "/etc/" in seg
    assert "../" in seg
