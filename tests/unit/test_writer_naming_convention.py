"""写者标识（``writer``）命名规范判据 —— X-16 批 D · D3（DS 2026-09-18 拍做）。

口径：所有**进入写台账 ``writer`` 字段**的字面量必须是**点分模块名**
``^[a-z_]+(\\.[a-z_]+)+$``。理由：``writer`` 是**同列字段**，必须能按同一规则聚合；
PA 侧原用**文件路径**（``core/pa/threads.py``）、PES 侧用点分模块名（``pes.boss_grant``）
⇒ 同列不可聚合（X-16 现状重核记；经验库 L-09「多真源 ⇒ 陈旧字面量必漂」）。

**为什么本判据必须做「实参 → 模块常量」解析**（这是它存在的理由，不是装饰）：
真实缺陷（6 处 ``core/pa/*.py``，12 个调用点）**不是** ``writer=`` 关键字实参，而是模块常量
``_WRITER = "core/pa/threads.py"`` 以**位置实参**传进 ``read_state`` / ``write_state``。
只扫 ``writer=`` 的判据对它们**零命中**（实测 16 条字面量里 0 条是它们）⇒ 那是**假绿**判据
（经验库 L-04）。故本判据：① 从**函数定义**推 ``writer`` 的**位置下标**（不硬编码，防签名
漂移；**同文件定义优先**，防跨文件同名函数下标误配）；② 取 ``writer=`` 关键字实参 **或** 该
下标的位置实参；③ ``Name`` ⇒ 解析**同文件模块级赋值**或**所在函数的局部赋值**取值。

四类，全部留痕，**不静默放过**：
  · ``literal``    ⇒ 静态取到字符串 ⇒ **判规**；
  · ``exempt``     ⇒ 命中 ``EXEMPT``（出口自身缺省值）⇒ 放行，**必须命中**（陈旧豁免 = 红）；
  · ``indirect``   ⇒ 值是形参/局部变量（``state_out.read_state(writer=writer)``、
                     ``self._atomic_write(doc, w, reason)``）⇒ 静态取不到 ⇒ 放行，
                     **逐条钉住**（``INDIRECT``，多一条/少一条 = 红）；
  · ``unresolved`` ⇒ 既非字面量、又非形参/局部、也解析不出（含「同名函数下标矛盾」）⇒ **红**。
"""
from __future__ import annotations

import ast
import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
#: 扫描根。**钉在断言里**（改动 = 红），防「悄悄缩小范围」把判据做成空转。
SCAN_SCOPE = ("core", "tools", "web")
_SKIP_DIRS = {"__pycache__", ".venv", "node_modules", ".git", "build", "dist"}

#: 点分模块名（小写 + 下划线，至少一个点）。
PAT = re.compile(r"^[a-z_]+(\.[a-z_]+)+$")

#: 出口自身的**缺省值**（只在调用方**省略** ``writer`` 时生效；生产代码里没有任何
#: 省略 ``writer`` 的写调用 —— 实测）。登记为豁免；**条目必须命中，陈旧豁免 = 红**。
EXEMPT = (
    ("core/pes/state_integrity.py", "unknown",
     "StateFile.__init__ 的 writer 缺省值；生产调用一律显式传 writer"),
    ("core/pes/state_integrity.py", "boss",
     "set_seed 的 writer 缺省值；生产代码零调用（实测）"),
)

#: 形参/局部变量透传（静态取不到值），按 **(文件, 宿主函数)** 逐条钉住：
#: 新增/消失 = 红 —— 防「静默长出新的不可判定实参」（经验库 L-04 的反面）。
INDIRECT = (
    ("core/pa/state_out.py", "read_state"),
    ("core/pa/state_out.py", "write_state"),
    ("core/pes/authorization.py", "_store"),
    ("core/pes/state_integrity.py", "_atomic_write"),
    ("core/pes/state_integrity.py", "update_runtime"),
    ("core/pes/state_integrity.py", "set_seed"),
)

#: 反空转下限（实测：文件 715 / 字面量 23 / core/pa 侧 12）。
MIN_FILES = 600
MIN_LITERALS = 20
MIN_PA_LITERALS = 6


def _rel(p):
    return Path(p).resolve().relative_to(REPO).as_posix()


def _iter_py():
    for root in SCAN_SCOPE:
        base = REPO / root
        if not base.exists():
            continue
        for dp, dn, fn in os.walk(base):
            dn[:] = [d for d in dn if d not in _SKIP_DIRS]
            for f in fn:
                if f.endswith(".py"):
                    yield Path(dp) / f


def _callee(node):
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return None


def _pos_names(fn):
    a = fn.args
    names = [x.arg for x in (list(a.posonlyargs) + list(a.args))]
    if names and names[0] == "self":
        names = names[1:]
    return names


def _writer_pos(fn):
    names = _pos_names(fn)
    return names.index("writer") if "writer" in names else None


def _writer_default(fn):
    a = fn.args
    pos = list(a.posonlyargs) + list(a.args)
    deco = [None] * (len(pos) - len(a.defaults)) + list(a.defaults)
    pairs = list(zip(pos, deco))
    if a.kwonlyargs:
        pairs += list(zip(a.kwonlyargs, a.kw_defaults))
    for arg, d in pairs:
        if arg.arg == "writer" and isinstance(d, ast.Constant) and isinstance(d.value, str):
            return d.value
    return None


def _writer_sites(tree):
    """从**函数定义**推：被调用者名 → ``writer`` 的位置下标 + 缺省字面量行。"""
    idx: dict = {}
    defaults = []
    defined = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef) and sub.name == "__init__":
                    defined.add(node.name)
                    i = _writer_pos(sub)
                    if i is None:
                        continue
                    out = {node.name: i}
                    for k, v in out.items():
                        idx.setdefault(k, set()).add(v)
                    d = _writer_default(sub)
                    if d is not None:
                        defaults.append((node.name, sub.lineno, d))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined.add(node.name)
            i = _writer_pos(node)
            if i is None:
                continue
            idx.setdefault(node.name, set()).add(i)
            d = _writer_default(node)
            if d is not None:
                defaults.append((node.name, node.lineno, d))
    return idx, defaults, defined


def _module_consts(tree):
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and isinstance(node.value, ast.Constant) \
                        and isinstance(node.value.value, str):
                    out[t.id] = node.value.value
    return out


def _fn_scopes(tree):
    """→ [(lo, hi, name, params, locals{name: value_node})]；locals 按**行范围**归属。"""
    raw = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names = _pos_names(node) + [x.arg for x in node.args.kwonlyargs]
            raw.append([node.lineno, node.end_lineno or node.lineno, node.name, set(names), {}])
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for s in raw:
                if s[0] <= node.lineno <= s[1]:
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            s[4].setdefault(t.id, node.value)
    return [(s[0], s[1], s[2], s[3], s[4]) for s in raw]


def _owner_of(scopes, lineno):
    best = None
    for (s, e, name, params, loc) in scopes:
        if s <= lineno <= e and (best is None or s > best[0]):
            best = (s, e, name, params, loc)
    return (best[2], best[3], best[4]) if best else ("<module>", set(), {})


def _value_of(arg, consts, locals_, params):
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return ("literal", arg.value)
    if isinstance(arg, ast.Name):
        n = arg.id
        if n in consts:
            return ("literal", consts[n])
        if n in locals_:
            v = locals_[n]
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                return ("literal", v.value)
            return ("indirect", n)
        if n in params:
            return ("indirect", n)
        return ("unresolved", n)
    return ("unresolved", ast.dump(arg)[:80])


_CACHE: dict = {}


def collect():
    """→ (files, rows, stale)。``stale`` = 同名函数 `writer` 下标矛盾且**跨文件**解析的名字。"""
    if _CACHE:
        return _CACHE["files"], _CACHE["rows"], _CACHE["stale"]
    files = sorted(_iter_py())
    parsed, glob, stale = [], {}, set()
    for fp in files:
        try:
            tree = ast.parse(fp.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        parsed.append((fp, tree))
        idx, _d, _def = _writer_sites(tree)
        for k, vs in idx.items():
            glob.setdefault(k, set()).update(vs)
    rows = []
    for fp, tree in parsed:
        consts = _module_consts(tree)
        scopes = _fn_scopes(tree)
        file_idx, defaults, file_defined = _writer_sites(tree)
        # 定义处缺省值同样会进入 writer 字段 ⇒ 一并判规（也是 EXEMPT 的命中来源）。
        for owner, lineno, val in defaults:
            rows.append({"file": _rel(fp), "line": lineno, "callee": owner, "owner": owner,
                         "kind": "literal", "value": val, "via": "default"})
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _callee(node.func)
            owner, params, loc = _owner_of(scopes, node.lineno)
            # ① 同文件定义优先（防跨文件同名函数下标误配）；
            # ② 否则用全局唯一定义；③ 全局仍矛盾 ⇒ 显式 unresolved（不静默跳过）。
            i = None
            vs = file_idx.get(name)
            if vs and len(vs) == 1:
                i = next(iter(vs))
            elif vs:
                stale.add(name)
                rows.append({"file": _rel(fp), "line": node.lineno, "callee": name,
                             "owner": owner, "kind": "unresolved", "value": name,
                             "via": "ambiguous-index"})
                continue
            elif name in file_defined:
                # 同文件另有同名定义（**无** writer 形参）⇒ 不是同一个被调用者。
                continue
            elif name in glob:
                gv = glob[name]
                if len(gv) == 1:
                    i = next(iter(gv))
                else:
                    stale.add(name)
                    rows.append({"file": _rel(fp), "line": node.lineno, "callee": name,
                                 "owner": owner, "kind": "unresolved", "value": name,
                                 "via": "ambiguous-index"})
                    continue
            if i is None:
                continue
            arg = None
            for kw in node.keywords:
                if kw.arg == "writer":
                    arg = kw.value
            if arg is None:
                if len(node.args) > i:
                    arg = node.args[i]
            if arg is None:
                continue
            kind, val = _value_of(arg, consts, loc, params)
            rows.append({"file": _rel(fp), "line": node.lineno, "callee": name,
                         "owner": owner, "kind": kind, "value": val, "via": "call"})
    _CACHE.update(files=files, rows=rows, stale=stale)
    return files, rows, stale


def _is_exempt(r):
    return (r["file"], r["value"]) in {(f, v) for f, v, _ in EXEMPT}


def test_写者字面量必须是点分模块名():
    _files, rows, _stale = collect()
    bad = [r for r in rows
           if r["kind"] == "literal" and not PAT.match(r["value"]) and not _is_exempt(r)]
    assert not bad, "下列 writer 字面量不是点分模块名：\n" + "\n".join(
        "  %s:%s [%s/%s] %r" % (r["file"], r["line"], r["callee"], r["via"], r["value"])
        for r in bad)


def test_未知的写者实参不得静默放过():
    _files, rows, _stale = collect()
    bad = [r for r in rows if r["kind"] == "unresolved"]
    assert not bad, "下列 writer 实参无法静态判定（须显式字面量或登记为 indirect）：\n" + "\n".join(
        "  %s:%s [%s/%s] %s" % (r["file"], r["line"], r["owner"], r["via"], r["value"]) for r in bad)


def test_透传实参必须与钉子逐条一致():
    _files, rows, _stale = collect()
    got = sorted({(r["file"], r["owner"]) for r in rows if r["kind"] == "indirect"})
    assert got == sorted(INDIRECT), (
        "透传实参集合与钉子不一致（多了/少了都要显式登记）：\n  实测 %s\n  钉子 %s"
        % (got, sorted(INDIRECT)))


def test_豁免条目必须命中():
    _files, rows, _stale = collect()
    hit = {(r["file"], r["value"]) for r in rows}
    miss = [(f, v) for f, v, _why in EXEMPT if (f, v) not in hit]
    assert not miss, "陈旧豁免（已不存在，必须删条目）：%s" % (miss,)


def test_同名函数跨文件解析必须唯一():
    _files, _rows, stale = collect()
    assert not stale, "同名被调用者的 writer 下标跨文件矛盾（判据会错读实参）：%s" % (sorted(stale),)


def test_扫描口径与反空转下限():
    files, rows, _stale = collect()
    assert SCAN_SCOPE == ("core", "tools", "web"), "扫描根被改过：%s" % (SCAN_SCOPE,)
    lits = [r for r in rows if r["kind"] == "literal"]
    assert len(files) >= MIN_FILES, "扫描文件数 %d < 下限 %d（判据可能在空转）" % (len(files), MIN_FILES)
    assert len(lits) >= MIN_LITERALS, "writer 字面量 %d < 下限 %d（判据可能在空转）" % (len(lits), MIN_LITERALS)
    pa = [r for r in lits if r["file"].startswith("core/pa/")]
    assert len(pa) >= MIN_PA_LITERALS, "core/pa 侧 writer 字面量 %d < 下限 %d" % (len(pa), MIN_PA_LITERALS)