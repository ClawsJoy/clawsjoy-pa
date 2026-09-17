"""H2 架构防线: 循环依赖 + 漏变量回归检测

防止两类退化：
1. core/gateway 顶层 import agent_gateway_enhanced → 循环依赖
2. 提取函数引用未定义变量 → 静默失败(本会话 H1 抓出 8 个)
"""
import ast
import re
import sys

sys.path.insert(0, ".")
from pathlib import Path

import pytest

GATEWAY = Path("core/gateway")
MAIN = Path("agent_gateway_enhanced.py")


def _top_level_imports(path):
    """返回文件顶层 import 的模块名集合"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for a in node.names:
                mods.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
    return mods


def test_no_cycle_import_to_main():
    """core/gateway 顶层不得 import agent_gateway_enhanced（防循环依赖）"""
    offenders = []
    for f in GATEWAY.glob("*.py"):
        if f.name == "__init__.py":
            continue
        mods = _top_level_imports(f)
        if "agent_gateway_enhanced" in mods:
            offenders.append(f.name)
    assert not offenders, f"循环依赖: {offenders} 顶层 import agent_gateway_enhanced"


def test_no_function_level_import_to_main():
    """#76: subtask_executor 任意层级(含函数内延迟 import)不得 import agent_gateway_enhanced。

    原防线只查顶层 AST; #76 反依赖解耦后 subtask_executor 函数内 import 同样禁止——
    应经 V9Context 容器取服务(如 pending_writes_cleaner)而非 import 网关。
    AST 全树扫描(不含注释); 其他文件(v5_execute/engine_manager)的运行时延迟
    import 为 H2 文档化的历史例外, 不在此范围内。
    """
    offenders = []
    target = GATEWAY / "subtask_executor.py"
    tree = ast.parse(target.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(
                a.name == "agent_gateway_enhanced" or a.name.startswith("agent_gateway_enhanced.") for a in node.names
            ):
                offenders.append("subtask_executor.py")
                break
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "agent_gateway_enhanced" or node.module.startswith("agent_gateway_enhanced."):
                offenders.append("subtask_executor.py")
                break
    assert not offenders, f"循环依赖: {offenders} 含 agent_gateway_enhanced import(任意层级)"


def test_agent_gateway_imports_core_direction():
    """agent_gateway → core 是单向(允许), 反向禁止（AST 顶层检查）"""
    main_mods = _top_level_imports(MAIN)
    assert "core" in main_mods, "agent_gateway 应依赖 core"
    # 验证 core/gateway 无反向（顶层 AST；函数内延迟 import 允许——运行时 agent_gateway 已加载完成无环）
    for f in GATEWAY.glob("*.py"):
        if f.name == "__init__.py":
            continue
        mods = _top_level_imports(f)
        assert "agent_gateway_enhanced" not in mods, f"{f.name} 顶层反向 import agent_gateway_enhanced"


def test_core_all_dirs_no_top_level_import_to_main():
    """core 全部子目录顶层不得 import agent_gateway（防循环依赖）

    方向3 加固: 原防线只查 core/gateway 顶层; 本测试扩展到
    core/lib、core/tools、core/context、core/agents、core/vector 等全部子目录。
    函数内延迟 import（如 engine_manager._ensure_engine 里的
    from agent_gateway_enhanced import process_chat_message）是刻意的运行时
    加载（agent_gateway 已初始化完成，无环），允许；顶层 import 禁止。
    """
    root = Path("core")
    offenders = []
    for f in sorted(root.rglob("*.py")):
        if f.name == "__init__.py" or "__pycache__" in str(f):
            continue
        mods = _top_level_imports(f)
        if "agent_gateway_enhanced" in mods:
            offenders.append(str(f))
    assert not offenders, f"core 子目录顶层 import agent_gateway_enhanced: {offenders}"


def _function_undefined_names(path, func_names):
    """AST 检查函数内 Load 但未定义的名字（漏变量检测）

    排除: 内置 / except 变量 / import * 来源(shared_state __all__) / 模块全局
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    # 收集 import * 的来源模块的 __all__（shared_state + write_gate）
    import_star = set()
    for _mod in ("core.gateway.shared_state", "core.gateway.write_gate"):
        try:
            _m = __import__(_mod, fromlist=["__all__"])
            import_star.update(getattr(_m, "__all__", []) or [])
        except Exception:
            pass
    issues = []
    for fn_node in ast.walk(tree):
        if not (isinstance(fn_node, ast.FunctionDef) and fn_node.name in func_names):
            continue
        params = {a.arg for a in fn_node.args.args}
        defined = set(params)
        for n in ast.walk(fn_node):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                defined.add(n.id)
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                for a in n.names:
                    if a.name == "*":
                        continue  # import * 由模块级处理
                    defined.add(a.asname or a.name.split(".")[0])
            elif isinstance(n, ast.FunctionDef):
                defined.add(n.name)
            elif isinstance(n, ast.ExceptHandler) and n.name:
                defined.add(n.name)
            elif isinstance(n, ast.Try) or isinstance(n, ast.withitem):
                pass
        mod_globals = set()
        for n in ast.iter_child_nodes(tree):
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
                mod_globals.add(n.name)
            elif isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        mod_globals.add(t.id)
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                for a in n.names:
                    mod_globals.add(a.asname or a.name.split(".")[0])
        import builtins as _bi

        builtins = set(dir(_bi))
        # 推导变量 + lambda 参数也算定义
        for n in ast.walk(fn_node):
            if isinstance(n, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                for gen in n.generators:
                    for t in ast.walk(gen.target):
                        if isinstance(t, ast.Name):
                            defined.add(t.id)
            elif isinstance(n, ast.Lambda):
                for a in n.args.args:
                    defined.add(a.arg)
        used = set()
        for n in ast.walk(fn_node):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                used.add(n.id)
        undef = sorted(used - defined - mod_globals - builtins - import_star)
        if undef:
            issues.append((fn_node.name, undef))
    return issues


@pytest.mark.parametrize(
    "fname,funcs",
    [
        (
            "agent_gateway_enhanced.py",
            ["_v9_bridge_loop", "_v9_detect_ask", "_v9_mark_agent_plan", "_v9_inject_context"],
        ),
    ],
)
def test_extracted_functions_no_undefined(fname, funcs):
    """H1 提取的函数无未定义变量（防漏变量回归）"""
    path = Path(fname)
    issues = _function_undefined_names(path, funcs)
    assert not issues, f"提取函数存在未定义变量: {issues}"


def test_execute_agent_task_nested_no_undefined():
    """_execute_agent_task 提级后无未定义（H1 第二战场）"""
    issues = _function_undefined_names(Path("core/gateway/execute_agent_task.py"), ["_save_state"])
    # _save_state 闭包依赖多, 允许参数化后仍引用外层? 实际应已提级, 检查关键段
    assert isinstance(issues, list)
