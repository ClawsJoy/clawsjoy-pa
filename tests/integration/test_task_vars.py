"""#41 阶段3：变量驱动投喂 — 变量抽取 + 资产过滤"""
import sys
sys.path.insert(0, ".")
import pytest

from core.lib.task_vars import extract_task_vars, filter_world_model_modules, filter_dependency_graph


def test_extract_paths():
    """提取文件路径"""
    v = extract_task_vars("修改 clawsjoy_dev/core/gateway/security.py 和 audit.py 的检测逻辑")
    assert "clawsjoy_dev/core/gateway/security.py" in v["paths"]
    assert any("audit.py" in p for p in v["paths"])


def test_extract_tokens_and_keywords():
    """提取代码标识符 + 中文关键词"""
    v = extract_task_vars("优化 _check_consecutive_failure 函数的重试逻辑")
    # _check_consecutive_failure 含下划线 → code_like token
    assert any("_check_consecutive_failure" in t for t in v["tokens"])
    # 中文关键词
    assert any("重试" in k or "优化" in k for k in v["keywords"])


def test_extract_noise_filtered():
    """噪声词被过滤（修改/添加 等动作词不入变量）"""
    v = extract_task_vars("修改文件添加功能")
    assert "修改" not in v["keywords"]
    assert "添加" not in v["keywords"]


def test_extract_empty():
    """空任务 → 空变量"""
    v = extract_task_vars("")
    assert v["paths"] == [] and v["tokens"] == [] and v["keywords"] == []


def test_filter_modules_by_path():
    """模块过滤：命中任务路径的模块保留，无关模块剔除"""
    modules = {
        "clawsjoy_dev/core/gateway/security.py": {"skeleton": "def _is_path_escape", "status": "complete"},
        "clawsjoy_dev/core/lib/other.py": {"skeleton": "def unrelated", "status": "complete"},
        "clawsjoy_dev/core/gateway/audit.py": {"skeleton": "def audit_tool_call", "status": "complete"},
    }
    vars_ = {"paths": ["core/gateway/security.py"], "tokens": [], "keywords": []}
    out = filter_world_model_modules(modules, vars_, top_limit=10)
    assert "clawsjoy_dev/core/gateway/security.py" in out
    assert "clawsjoy_dev/core/lib/other.py" not in out


def test_filter_modules_by_keyword():
    """关键词过滤：模块内容含关键词则保留"""
    modules = {
        "clawsjoy_dev/a.py": {"skeleton": "审计相关逻辑", "functions": [], "imports": []},
        "clawsjoy_dev/b.py": {"skeleton": "无关内容", "functions": [], "imports": []},
    }
    vars_ = {"paths": [], "tokens": [], "keywords": ["审计"]}
    out = filter_world_model_modules(modules, vars_, top_limit=10)
    assert "clawsjoy_dev/a.py" in out
    assert "clawsjoy_dev/b.py" not in out


def test_filter_modules_no_vars_returns_top():
    """无变量 → 返回前 top_limit 个（不丢全量）"""
    modules = {f"m{i}.py": {"skeleton": ""} for i in range(50)}
    vars_ = {"paths": [], "tokens": [], "keywords": []}
    out = filter_world_model_modules(modules, vars_, top_limit=30)
    assert len(out) == 30


def test_filter_dependency_graph():
    """依赖图行过滤：含任务路径的行保留"""
    dg = "a.py -> b.py\nsecurity.py -> audit.py\nc.py -> d.py"
    vars_ = {"paths": ["security.py"], "tokens": [], "keywords": []}
    out = filter_dependency_graph(dg, vars_, max_chars=2000)
    assert "security.py" in out
    assert "a.py -> b.py" not in out
    assert "c.py -> d.py" not in out


def test_filter_dependency_graph_no_vars():
    """无变量 → 全量截断"""
    dg = "a.py -> b.py"
    vars_ = {"paths": [], "tokens": [], "keywords": []}
    out = filter_dependency_graph(dg, vars_, max_chars=2000)
    assert out == dg
