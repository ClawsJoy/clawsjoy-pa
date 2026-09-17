# -*- coding: utf-8 -*-
"""模式关键词回归: 分析/盘点任务 → full; 读/列 → minimal(当前关键词配置)"""
import sys

sys.path.insert(0, ".")


def test_mode_keywords_include_read_list():
    from core.gateway.quota_manager import _ANALYSIS_KEYWORDS, get_mode, get_mode_tools

    # 当前 _ANALYSIS_KEYWORDS: 分析/盘点/排查/审查/检查/审计/调查/理解/总结/报告/评估/监控/梳理
    # 分析类任务 → full(含 list_dir)
    assert any(k in _ANALYSIS_KEYWORDS for k in ("分析", "盘点", "总结"))
    assert get_mode("s", "盘点项目状态") == "full", "盘点应 full"
    assert "list_dir" in get_mode_tools("s", "盘点项目状态"), "full 模式应含 list_dir"
    # 写任务 → minimal
    assert get_mode("s", "修改 core/x.py") == "minimal", "写任务仍 minimal"
