"""H1 审核修复：边缘学习应调用 sag_feedback 正确实现（非本地僵尸函数）"""
import sys, inspect
sys.path.insert(0, ".")
import pytest


def test_uses_sag_feedback_implementation():
    """execute_agent_task 用 sag_feedback 的 _update_sag_edge_learning（正确 #81）"""
    from core.gateway import sag_feedback
    from core.gateway import execute_agent_task as EAT
    # EAT 模块里 _update_sag_edge_learning 应指向 sag_feedback 的（import 来的）
    assert EAT._update_sag_edge_learning is sag_feedback._update_sag_edge_learning, "未使用 sag_feedback 版本"


def test_no_local_zombie_definition():
    """本地不再定义 entity_names 版本的僵尸函数"""
    src = open("core/gateway/execute_agent_task.py", encoding="utf-8").read()
    # 不应有本地 def _update_sag_edge_learning(entity_names...)
    assert "def _update_sag_edge_learning(entity_names" not in src, "僵尸函数仍存在"
    # import 行含它
    assert "from core.gateway.sag_feedback import _build_code_edges, _update_sag_feedback, _update_sag_edge_learning" in src


def test_call_site_uses_task_name_params():
    """调用点传 task_name/session_id/user_id/messages（与 sag_feedback 签名匹配）"""
    src = open("core/gateway/execute_agent_task.py", encoding="utf-8").read()
    idx = src.find("_edge_updated = _update_sag_edge_learning")
    assert idx > 0
    region = src[idx:idx+250]
    assert "task_name=" in region and "session_id=" in region and "messages=" in region
    assert "entity_names=" not in region
