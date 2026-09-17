"""沙箱边界提示: bridge_loop 每轮注入系统消息(幂等去重)"""
import sys

sys.path.insert(0, ".")
import pytest


def test_bridge_loop_injects_sandbox_boundary_hint():
    """轮首注入「沙箱边界」系统提示(禁止 /tmp 等系统路径写)（S6-A 归位 round_start）"""
    src = open("core/gateway/v9_bridge/round_start.py", encoding="utf-8").read()
    assert "【沙箱边界】" in src, "应注入沙箱边界系统提示"
    assert "clawsjoy_dev/，所有文件必须写在此目录内" in src, "提示应指明沙箱目录"
    assert "禁止使用 /tmp" in src, "提示应禁止 /tmp 等系统路径"
    assert 'startswith("【沙箱边界】")' in src


def test_hint_uses_relative_path_guidance():
    """提示引导相对路径(data/x.txt)而非绝对路径"""
    src = open("core/gateway/v9_bridge/round_start.py", encoding="utf-8").read()
    assert "相对路径" in src and "data/x.txt" in src
