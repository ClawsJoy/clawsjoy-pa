# -*- coding: utf-8 -*-
"""守卫：函数内 import 不得遮蔽模块级同名符号（2026-09-13 立）。

真实事故：agent_gateway_enhanced.py 的 _v9_bridge_loop 里有一行
    from core.gateway.message_assembler import _compress_messages, _tg_estimate, _calc_token_budget
函数内 import 会把 _tg_estimate/_calc_token_budget 变成该函数的**局部名**，于是同一函数中
更早的 TOKEN_GUARD 分支（line 572）抛 UnboundLocalError。该分支只在
finish_reason == "length"（长输出被截断）时进入 —— 短任务永不触发，**长交付必崩**，
而长交付正是工作层要干的事。前端还把 type=error 事件吞掉，表现是「进度刷一屏然后静默」。

扫描口径（防误报）：
- 每个函数独立分析，不下钻 nested def / lambda / 推导式（它们有各自作用域）；
- 只查 **import 绑定**（赋值/for/with/except 目标先绑后用的语义不同，另论）；
- 推导式循环变量是 Store 但不是函数级绑定 → 剔除。
"""
import ast
import os
import sys
import tempfile

sys.path.insert(0, ".")

SCAN_DIRS = ["core", "routes", "web"]
SCAN_FILES = ["agent_gateway_enhanced.py"]
SKIP_PARTS = (".git", "data", "logs", "__pycache__", "node_modules", "archive", ".venv", "tests", ".pytest_cache")


class _FnScope(ast.NodeVisitor):
    """只走本函数作用域: 碰到 nested def/lambda 不再下钻(`visit_*` 覆写为空)。"""

    def __init__(self):
        self.loads = {}
        self.imports = {}

    def visit_FunctionDef(self, node):
        pass

    def visit_AsyncFunctionDef(self, node):
        pass

    def visit_Lambda(self, node):
        pass

    def _record_import(self, node):
        for a in node.names:
            self.imports.setdefault(a.asname or a.name.split(".")[0], []).append(node.lineno)
        self.generic_visit(node)

    def visit_Import(self, node):
        self._record_import(node)

    def visit_ImportFrom(self, node):
        self._record_import(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.loads.setdefault(node.id, []).append(node.lineno)


def _comprehension_targets(node):
    names = set()
    for sub in ast.walk(node):
        if isinstance(sub, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for gen in sub.generators:
                for t in ast.walk(gen.target):
                    if isinstance(t, ast.Name):
                        names.add(t.id)
    return names


def scan_file(path):
    """返回 [(path, 函数名, 名字, 使用行, 绑定行)] —— 先用后绑定(import)的函数级遮蔽。"""
    tree = ast.parse(open(path, encoding="utf-8").read())
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        sc = _FnScope()
        for stmt in node.body:
            sc.visit(stmt)
        comp = _comprehension_targets(node)
        for name, bind_lines in sc.imports.items():
            if name in comp:
                continue
            earlier = [l for l in sc.loads.get(name, []) if l < min(bind_lines)]
            if earlier:
                out.append((path, node.name, name, min(earlier), min(bind_lines)))
    return out


def _iter_py_files():
    for f in SCAN_FILES:
        if os.path.exists(f):
            yield f
    for d in SCAN_DIRS:
        for root, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if x not in SKIP_PARTS]
            for fn in files:
                if fn.endswith(".py"):
                    yield os.path.join(root, fn)


def test_no_use_before_local_import_shadowing():
    offenders = []
    for p in _iter_py_files():
        try:
            offenders.extend(scan_file(p))
        except SyntaxError:
            continue
    assert not offenders, "存在「先用后绑定」的函数内 import 遮蔽(会 UnboundLocalError): %s" % offenders


def test_scanner_detects_the_original_regression():
    """自检: 把原始事故片段喂给扫描器必须能检出 —— 防测试本身失效。"""
    code = (
        "def _v9_bridge_loop(messages, tools):\n"
        "    _tg_before = _tg_estimate(messages, tools)\n"
        "    try:\n"
        "        from core.gateway.message_assembler import _compress_messages, _tg_estimate\n"
        "        return _tg_estimate(messages, tools)\n"
        "    except Exception:\n"
        "        return _tg_before\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as fh:
        fh.write(code)
        p = fh.name
    try:
        bad = scan_file(p)
    finally:
        os.unlink(p)
    assert any(b[2] == "_tg_estimate" for b in bad), bad


def test_scanner_ignores_comprehension_variables():
    """自检: 推导式循环变量不是函数级绑定, 不得误报。"""
    code = "def f(items):\n" "    xs = [s for s in items]\n" "    from m import s\n" "    return s(xs)\n"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as fh:
        fh.write(code)
        p = fh.name
    try:
        bad = scan_file(p)
    finally:
        os.unlink(p)
    assert not bad, bad


_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_scanner_flags_parameter_rebound_by_local_import():
    """口径齿（有意保守 · pm_1848 §四.4）：**参数名**被函数内 import 覆绑 ⇒ 亦红。

    由（一手所逮）：core/pa/agent_scan.py:366,397 走此形 —— 参数 roster_mod 调时已绑
    ⇒ 运行 **无** UnboundLocalError ⇒ 就「先用后绑定」之原旨论，系**器之过宽**。
    然「一名二义」（参数 ＝ 注入位 ／ import ＝ 真源）确为面之瑕 ⇒ 本判据**有意**保其严格，
    治在**改码**（另立 _roster 再赋），⛔ 治在松闸 —— 否则本形之新例将静默溜过。
    """
    code = ("def f(x=None):\n"
            "    if x is None:\n"
            "        from m import y as x\n"
            "    return x\n")
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as fh:
        fh.write(code)
        fp = fh.name
    try:
        bad = scan_file(fp)
    finally:
        os.unlink(fp)
    assert any(b[2] == "x" for b in bad), bad


def test_agent_scan_face_has_no_offenders():
    """面之齿（pm_1848 §四.4）：core/pa/agent_scan.py 须**零**违（改码后之留痕）。"""
    fp = os.path.join(_REPO, "core", "pa", "agent_scan.py")
    bad = scan_file(fp)
    assert not bad, bad


def test_scanner_accepts_distinct_local_alias():
    """正控（治之形）：另立 _roster 再赋 ⇒ **不**红（即本批之改法）。"""
    code = ("def f(x=None):\n"
            "    if x is None:\n"
            "        from m import y as _y\n"
            "        x = _y\n"
            "    return x\n")
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as fh:
        fh.write(code)
        fp = fh.name
    try:
        bad = scan_file(fp)
    finally:
        os.unlink(fp)
    assert not bad, bad
