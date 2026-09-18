# -*- coding: utf-8 -*-
"""防回潮 meta 测试(基线归零 2026-09-13)。

背景: 14 个基线失败里 9 个是"产品有意改了、测试没跟上", 根因是四种机制反复重演:
  ① 源码断言用"下一个 def"找函数边界 —— 函数搬走/成为文件最后一个顶层 def 就假失败
     (① test_bridge_loop_init: find(chr(10)+"def ") → -1 → 回退 2000 字符窗口 → 假失败)
  ② 注册表/工具表用**全等**集合断言 —— 每次有意新增工具/平台就红(假耦合)
     (⑫ tool_registry 多 4 个工具即红)
  ③ 全局 V9Context 服务被测试改脏(置 None) —— 顺序依赖: 单跑绿 / 全量红
     (⑭ provide_override("pending_writes_cleaner", None) 把 import 时注册的服务永久顶掉)
  ④ "逐条同基线"只看失败条数、不比内容 —— 14 稳定多轮没人盘
本文件把 ①②③ 扫成 case; ④ 交给门禁 tools/check_test_baseline.py + 两份台账。

注意: 本文件自身含反模式字面量, 扫描时排除自己。
"""
import ast
import json
import pathlib
import re

_TESTS_DIR = pathlib.Path(__file__).resolve().parent.parent
_REPO = _TESTS_DIR.parent
_SELF = pathlib.Path(__file__).resolve()
_LEDGER_DIR = _REPO / "tests" / "baseline"  # 台账入库(可 review); 运行产物在 data/test_baseline/


def _iter_test_files():
    for f in sorted(_TESTS_DIR.rglob("*.py")):
        if "__pycache__" in str(f) or f.resolve() == _SELF:
            continue
        yield f


def _tree(f):
    try:
        return ast.parse(f.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError:
        return None


def test_no_fragile_next_def_window():
    """① 禁"找下一个 def"的源码窗口 —— 必须用 AST 取函数体。

    只认**代码**里的调用(AST), 不误伤注释/文档字符串里对这种写法的说明。
    """
    bad = []
    for f in _iter_test_files():
        tree = _tree(f)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "find"
                and node.args
            ):
                continue
            try:
                _un = ast.unparse(node.args[0])
            except Exception:
                continue
            _is_next_def = ("def " in _un and "chr(10)" in _un) or ("\\ndef " in _un)
            if _is_next_def:
                bad.append(f"{f.relative_to(_REPO)}:{node.lineno}")
    assert not bad, "① 发现脆弱的'下一个 def'源码窗口(改用 ast.get_source_segment 取函数体): " + str(bad)


def test_no_exact_set_equality_on_registry():
    """② 注册表类集合断言禁全等(用 ⊇ 超集断言)"""
    pat = re.compile(r"\.keys\(\)\s*\)\s*==\s*\{")
    bad = []
    for f in _iter_test_files():
        for i, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if pat.search(line):
                bad.append(f"{f.relative_to(_REPO)}:{i}: {line.strip()[:90]}")
    assert not bad, "② 注册表集合断言应改超集(必需集 ⊆ 实际集), 否则新增条目即红: " + str(bad)


def test_tests_do_not_null_out_global_services():
    """③ 测试不得把全局 V9Context 服务置 None(会顶掉 import 时的一次性注册)"""
    bad = []
    for f in _iter_test_files():
        tree = _tree(f)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "provide_override"
                and len(node.args) >= 2
            ):
                continue
            if isinstance(node.args[1], ast.Constant) and node.args[1].value is None:
                bad.append(f"{f.relative_to(_REPO)}:{node.lineno}")
    assert not bad, "③ 测试把全局服务置 None(应恢复原值 / 原来没有就删键): " + str(bad)


def test_conftest_snapshots_global_services():
    """③ 兜底: conftest 必须每用例快照/还原全局服务表"""
    src = (_TESTS_DIR / "conftest.py").read_text(encoding="utf-8")
    assert "_v9ctx_service_isolation" in src, "conftest 缺全局服务快照/还原 fixture"
    assert "autouse=True" in src


def test_baseline_ledgers_present_and_wellformed():
    """④ 基线台账(失败/skip)必须存在且字段完整 —— 门禁脚本据此判红"""
    _f = _LEDGER_DIR / "failure_ledger.json"
    _s = _LEDGER_DIR / "skip_ledger.json"
    assert _f.exists(), f"缺失败台账: {_f}"
    assert _s.exists(), f"缺 skip 台账: {_s}"
    _fd = json.loads(_f.read_text(encoding="utf-8"))
    _sd = json.loads(_s.read_text(encoding="utf-8"))
    for entry in _fd.get("known_failures", []):
        for k in ("id", "nature", "owner", "plan"):
            assert entry.get(k), f"失败台账条目缺字段 {k}: {entry}"
    assert isinstance(_fd.get("resolved", []), list)
    _skips = _sd.get("skips", [])
    assert _skips, "skip 台账不应为空(当前有 7 条 skip)"
    for entry in _skips:
        for k in ("id", "reason", "nature", "restore"):
            assert entry.get(k), f"skip 台账条目缺字段 {k}: {entry}"
    # 门禁脚本必须在位(④ 的执行者)
    assert (_REPO / "tools" / "check_test_baseline.py").exists(), "缺门禁脚本 tools/check_test_baseline.py"


def test_env_dependent_cases_registered_not_as_flake():
    """⑤ 环境依赖用例必须登记为「环境依赖」而非 flake（DS 2026-09-18 拍）。

    区分: flake = 同一环境下不稳定(时绿时红); 环境依赖 = 依赖可达时稳定通过、
    缺失时**必红**(可复现的确定红)。把后者写成 flake 等于把环境问题**常态化**。
    本表是**留痕**、不是门禁输入(门禁只读 failure_ledger/skip_ledger),
    所以这里只钉「登记本身的形状」, 不参与失败/跳过判定。
    """
    _p = _LEDGER_DIR / "env_dependent_tests.json"
    assert _p.exists(), f"缺环境依赖用例登记表: {_p}"
    _d = json.loads(_p.read_text(encoding="utf-8"))
    _deps = _d.get("env_dependencies")
    assert _deps, "必须列明环境依赖项(否则「环境依赖」无从复跑)"
    for _dep in _deps:
        for _k in ("dep", "probe", "observed_state"):
            assert _dep.get(_k), f"环境依赖项缺字段 {_k}: {_dep}"
    _cases = _d.get("cases")
    assert _cases, "环境依赖用例表不得为空"
    for _c in _cases:
        for _k in ("id", "nature", "depends_on", "owner", "plan"):
            assert _c.get(_k), f"环境依赖用例缺字段 {_k}: {_c}"
        assert _c["id"].startswith("tests/"), f"用例 id 应为 pytest nodeid: {_c['id']}"
        assert _c["nature"] not in ("flake", "flaky"), (
            f"环境依赖用例不得登记为 flake(应写「环境依赖」): {_c['id']} -> {_c['nature']}"
        )
        assert _c["depends_on"], f"必须写明依赖项: {_c['id']}"
