#!/usr/bin/env python
# -*- coding: utf-8 -*-
u"""⭐ 客户端依赖清单之**器**（承 pm_1386 §二.1）—— 以 **import 扫描** 出「装此客户端要什么」。

以何形调用（判通／断须附）：
  python -X utf8 -B scripts/dev/scan_client_deps.py             # 人读表
  python -X utf8 -B scripts/dev/scan_client_deps.py --json      # 机读
  python -X utf8 -B scripts/dev/scan_client_deps.py --sites     # 并出诸处（径:行）
  python -X utf8 -B scripts/dev/scan_client_deps.py --root <仓> [--all]

法（⛔ 手拟）：
  1. 根 ＝ `scripts/win_pa/pa_nowindow.py`（起器）⇒ **逐跳**载其图：**仓内**模块以 `ast` 递归，
     第三方止。⚠ pa_nowindow.py 以**子进程**起网关 ⇒ 其**字符串里 `.py` 之路**（`APP` ／
     `PREFLIGHT`）亦作根 —— ⛔ 则「起器」之依漏（那是**净机之死**）。
  2. 逐 import 记：顶级模块名 ＋ **诸处**（径:行）＋ **层**。层之三则（⛔ 一名蔽之）：
       **必需** ＝ 本件经**全必需之链**达 ∧ 该 import 在**模块级** ∧ ⛔ 不在 `try/except` 内；
       **兜底** ＝ 同上而在 `try/except` 内（缺 ⇒ **静默降级** ⇒ ⛔ 断网关，然**须点名**）；
       **惰性** ＝ 在**函数体**内 ∨ 经惰性之链达（缺 ⇒ 唯触该路时方断）。
     ⚠ 「仓内」之判：**逐级上溯**（`a.b.c` ⇒ 试 `a/b/c.py` ／ `a/b/c/__init__.py` ⇒ 上溯 `a/b` …）
       ＋ 顶层在 `LOCAL_PREFIXES` 且为目录（**命名空间包**）—— ⛔ 则 `from core.tools import x`
       之 `x`（**本地符号 · ⛔ 模块**）被误记成第三方「`core`」。
  3. 顶级模块名 ⇒ **发行名**（`importlib.metadata.packages_distributions`）。
  4. 「已声明否」＝ 扫 `requirements.txt` ／ `requirements-runtime.txt` ／ `pyproject.toml`
     （并记其**段**：「运行依赖」⟷「可选依赖」）；「**带来者**」＝ 该发行名见于**已声明之某发行**的
     `Requires-Dist`（⇒ **间接依** · ⛔ 断网关）。

判：⛔ 以「装完就应能跑」为据 —— 凡「**必需而直接未声明**」者点名（净机 `pip install -r` 之后
    `ImportError` ⇒ 首屏 ⛔ 开）。⚠ 本器**唯字面扫**：⛔ 及 `exec` ／ 配置驱动之动态名 ⇒
    另列「⛔ 静态不可扫」之栏（⛔ 静默吞）。
"""
import argparse
import ast
import io
import json
import os
import re
import sys
from importlib.metadata import packages_distributions, requires as _dist_requires, version as _pkg_version
from pathlib import Path

DEFAULT_ROOT = "scripts/win_pa/pa_nowindow.py"
#: 声明之档（相对仓根）—— `requirements-dev.txt` ⛔ 入（那是**开发**之依 · ⛔ 客户端）
DECL_FILES = ("requirements.txt", "requirements-runtime.txt")
#: 入图之本地顶层（仓内之包 ／ 命名空间目录）
LOCAL_PREFIXES = ("core", "routes", "services", "web", "agents", "engine", "scripts", "tools", "pa_api", "api", "tests")


def _norm(name):
    u"""PEP 503 名之归一（⛔ 则 `PyYAML` ⟷ `pyyaml` 判二物）。"""
    return re.sub(r"[-_.]+", "-", str(name)).strip().lower()


def _is_stdlib(mod):
    if mod in sys.builtin_module_names:
        return True
    if mod in getattr(sys, "stdlib_module_names", ()):
        return True
    return mod in ("__future__",)


def _resolve(mod, root):
    u"""模块名 ⇒ 仓内之路（⛔ 仓内 ⇒ None）。逐级上溯 ＋ 命名空间包（无 `__init__.py` 之目录）。"""
    parts = mod.split(".")
    top = parts[0]
    if _is_stdlib(top):
        return None
    for i in range(len(parts), 0, -1):
        p = root.joinpath(*parts[:i])
        if p.with_suffix(".py").is_file():
            return p.with_suffix(".py")
        if (p / "__init__.py").is_file():
            return p / "__init__.py"
        if i == 1 and top in LOCAL_PREFIXES and p.is_dir():
            return p
    return None


#: 建**茎名索引**时之跳目录（⛔ 则 `data/**` ／ 虚拟环境把仓走穿 ⇒ 数十秒）
_SKIP_DIRS = {"data", "logs", "node_modules", ".git", ".venv", "venv", "__pycache__",
              ".pytest_cache", "dist", "build", ".tox", ".mypy_cache", ".ruff_cache"}
_STEM_INDEX = {}          # ⚠ 逐**根**为键（⛔ 一取蔽诸根 —— 我一手逮之：tmp 之索引污染本仓之判）


def _stems(R):
    u"""仓内 `.py` 之**茎名 ⇒ 相对径**（逐根一取 · 剔 `data/**` 等）—— 供「仓内同名」之判。"""
    k = str(R)
    if k in _STEM_INDEX:
        return _STEM_INDEX[k]
    m = {}
    for dirpath, dirnames, filenames in os.walk(str(R)):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            if fn.endswith(".py") and ".before_" not in fn:
                m.setdefault(fn[:-3], os.path.relpath(os.path.join(dirpath, fn), str(R)).replace(os.sep, "/"))
    _STEM_INDEX[k] = m
    return m


def _shadow(mod, R):
    u"""裸名 ⇒ 仓内同名之 `.py`（＝ **仓内同名之件 · ⛔ 全限定名**）—— ⛔ 则 `from code_entity_extractor
    import X`（`core/lib` 之兄弟件 · 倚 `sys.path`）被误记成第三方发行（**假红** 之族）。"""
    if "." in mod:
        return None
    return _stems(R).get(mod)


def _pkg_inits(path, root):
    u"""`path` 之**诸父包**之 `__init__.py`（Python 语义：`import a.b.c` 先执行 `a/__init__.py` ／
    `a/b/__init__.py`）—— ⛔ 则 `core/__init__.py` 之依（`tenant_vector_index` ⇒ `chromadb`）漏。
    亦有 `import a.b` ⇒ 须执行 `a/__init__.py`，故取 leaf 之父链。"""
    out = []
    d = path.parent if path.is_file() else path
    while d != root and root in d.parents:
        ip = d / "__init__.py"
        if ip.is_file():
            out.append(ip)
        d = d.parent
    return out


def _top_level_ids(tree):
    u"""模块级之节点 id 集（⛔ 入 FunctionDef ／ ClassDef 之体 ⇒ 惰性）。"""
    tops, stack = set(), list(tree.body)
    while stack:
        n = stack.pop()
        tops.add(id(n))
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for c in ast.iter_child_nodes(n):
            stack.append(c)
    return tops


def _guarded_ids(tree):
    u"""`try` 之体 ／ `except` ／ `else` ／ `finally` 内之节点（＝ **兜底**之 import）。"""
    g = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            for sub in list(node.body) + list(node.orelse) + list(node.finalbody) + list(node.handlers):
                for n in ast.walk(sub):
                    g.add(id(n))
    return g


def _imports_of(tree):
    u"""⇒ [(模块名, 行, **模块级否**, **兜底否**, 子模块候选否)] ／ [(模块名|None, 行)] 动态。

    ⚠ 二实**分立**（⛔ 一名蔽二态）：「在 `try` 内」⟷「经惰性之链达」＝ **二事**：
      `try` 内 ⇒ **兜底**（缺 ⇒ 该处静默降级）；经惰性之链 ⇒ **惰性**（触该路方断）。
    """
    tops, guard = _top_level_ids(tree), _guarded_ids(tree)
    out, dyn = [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.append((a.name, node.lineno, id(node) in tops, id(node) in guard, False))
        elif isinstance(node, ast.ImportFrom):
            if node.level or not node.module:
                continue
            mt, gd = id(node) in tops, id(node) in guard
            out.append((node.module, node.lineno, mt, gd, False))
            for a in node.names:      # `from 包 import 子模块` ⇒ 及子模块（⛔ 则子树漏）
                if a.name != "*":
                    out.append((node.module + "." + a.name, node.lineno, mt, gd, True))
        elif isinstance(node, ast.Call):
            f = node.func
            nm = getattr(f, "attr", None) or getattr(f, "id", None)
            if nm in ("import_module", "__import__"):
                a0 = node.args[0] if node.args else None
                lit = a0.value if (isinstance(a0, ast.Constant) and isinstance(a0.value, str)) else None
                dyn.append((lit, node.lineno))
    return out, dyn


def _subprocess_py_targets(path, root):
    u"""`pa_nowindow.py` 字符串里之 `.py` 名 ⇒ 另作根（**子进程**之入口）。"""
    hits = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return hits
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            v = node.value
            if v.endswith(".py"):
                p = root / v
                if p.is_file():
                    hits.append(p)
    return hits


def scan(root, entry_rel=DEFAULT_ROOT):
    root = os.path.abspath(root)
    R = Path(root)
    entry = R / entry_rel.replace("/", os.sep)
    third, dyn_all, roots, shadows = {}, [], [], {}
    state, stack = {}, []                    # 件之路 ⇒ 是否**必需之链**达
    if entry.is_file():
        roots.append(entry_rel)
        stack.append((entry, True))
        for p in _subprocess_py_targets(entry, R):
            roots.append(p.relative_to(R).as_posix())
            stack.append((p, True))
    while stack:
        path, req = stack.pop()
        rp = str(path)
        prev = state.get(rp)
        if prev is True or (prev is False and not req):
            continue
        state[rp] = req
        if path.is_dir():                    # 命名空间包：无件可析
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, OSError):
            continue
        rel = path.relative_to(R).as_posix() if rp.startswith(root) else rp
        imps, dyn = _imports_of(tree)
        for mod, ln, modlvl, guarded, is_sub in imps:
            strong = modlvl and not guarded          # 强 ＝ 模块级 ∧ ⛔ 兜底 ⇒ 可传「必需」
            loc = _resolve(mod, R)
            if loc is not None:
                stack.append((loc, req and strong))
                for pp in _pkg_inits(loc, R):
                    stack.append((pp, req and strong))
                continue
            if is_sub:                       # 本地之**符号**（⛔ 模块）⇒ 其父之条已记
                continue
            top = mod.split(".")[0]
            if _is_stdlib(top):
                continue
            sh = _shadow(top, R)             # 仓内同名之件 ⇒ ⛔ 第三方（另列 · ⛔ 静默吞）
            if sh:
                site = "%s:%d" % (rel, ln)
                row = shadows.setdefault(top, {"模块": top, "仓内同名": sh, "诸处": []})
                if site not in row["诸处"]:
                    row["诸处"].append(site)
                continue
            cur = third.setdefault(top, {"必需": False, "兜底": False, "惰性": False, "诸处": []})
            if req and strong:
                cur["必需"] = True
            elif modlvl and guarded:         # 模块级 ∧ 在 try 内 ⇒ 缺则**该处静默降级**
                cur["兜底"] = True
            else:
                cur["惰性"] = True
            site = "%s:%d" % (rel, ln)
            if site not in cur["诸处"]:
                cur["诸处"].append(site)
        for m, ln in dyn:
            dyn_all.append({"模块": m, "径:行": "%s:%d" % (rel, ln), "静态可扫": m is not None})
            if m:
                top = m.split(".")[0]
                if not _is_stdlib(top) and _resolve(m, R) is None:
                    cur = third.setdefault(top, {"必需": False, "兜底": False, "惰性": False, "诸处": []})
                    cur["惰性"] = cur["动态"] = True
                    site = "%s:%d" % (rel, ln)
                    if site not in cur["诸处"]:
                        cur["诸处"].append(site)
    return third, dyn_all, roots, shadows


def declared(root):
    u"""声明之发行名 ⇒ (档, 约束, 段)（PEP 503 归一）—— 段自 `# ==== 名 ====` 之注取。"""
    names = {}
    for f in DECL_FILES:
        p = os.path.join(root, f)
        if not os.path.isfile(p):
            continue
        sec = ""
        for ln in io.open(p, encoding="utf-8", errors="replace").read().splitlines():
            s = ln.strip()
            if s.startswith("#"):
                mm = re.search(r"=\s*([^=]+?)\s*=", s)
                if mm:
                    sec = mm.group(1).strip()
                continue
            s = s.split("#")[0].strip()
            if not s:
                continue
            m = re.match(r"^([A-Za-z0-9][A-Za-z0-9_.\-]*)\s*(.*)$", s)
            if m:
                names.setdefault(_norm(m.group(1)), (f, m.group(2).strip() or "*", sec))
    py = os.path.join(root, "pyproject.toml")
    if os.path.isfile(py):
        txt = io.open(py, encoding="utf-8", errors="replace").read()
        m = re.search(r"(?m)^dependencies\s*=\s*\[(.*?)\]", txt, re.S)
        if m:
            for s in re.findall(r"[\"\']([^\"\']+)[\"\']", m.group(1)):
                nm = re.match(r"^([A-Za-z0-9][A-Za-z0-9_.\-]*)", s)
                if nm:
                    names.setdefault(_norm(nm.group(1)), ("pyproject.toml[dependencies]", s, "project.dependencies"))
    return names


def _bringers(dist, declared_dists):
    u"""该发行名由**已声明之谁**带来（`Requires-Dist` 反查）—— 非空 ⇒ **间接依**。"""
    out = []
    for d in declared_dists:
        try:
            rs = _dist_requires(d) or []
        except Exception:
            continue
        for r in rs:
            m = re.match(r"^([A-Za-z0-9][A-Za-z0-9_.\-]*)", r.split(";")[0].strip())
            if m and _norm(m.group(1)) == _norm(dist):
                out.append(d)
                break
    return out


def report(root):
    third, dyn_all, roots, shadows = scan(root)
    decl = declared(root)
    pd = _pd()
    _inst = {_norm(x) for v in _pd().values() for x in v}
    decl_dists = sorted({k for k in decl if k in _inst})
    rows = []
    for top in sorted(third):
        info = third[top]
        dist = (pd.get(top) or [top])[0]
        try:
            ver = _pkg_version(dist)
        except Exception:
            ver = None
        ddecl = decl.get(_norm(dist)) or decl.get(_norm(top))
        layer = "必需" if info["必需"] else ("兜底" if info["兜底"] else "惰性")
        br = [] if ddecl else _bringers(dist, decl_dists)
        rows.append({
            "模块": top, "发行": dist, "钉版（本机）": ver, "层": layer,
            "用途": info["诸处"][0] if info["诸处"] else "", "诸处": info["诸处"],
            "本机在否": bool(ver), "已声明否": bool(ddecl),
            "声明于": (ddecl or [None])[0], "声明段": (ddecl or [None, None, ""])[2] or "",
            "带来者": br, "动态": bool(info.get("动态")),
        })
    hard = [r for r in rows if r["层"] == "必需" and not r["已声明否"] and not r["带来者"]]
    soft = [r for r in rows if r["层"] == "兜底" and not r["已声明否"] and not r["带来者"]]
    ind = [r for r in rows if not r["已声明否"] and r["带来者"]]
    return {"根": roots, "行": rows, "动态import": dyn_all, "仓内同名（⛔ 全限定名）": shadows,
            "必需而未声明": [r["发行"] for r in hard],
            "兜底而未声明": [r["发行"] for r in soft],
            "间接（未声明 · 由 X 带来）": [{"发行": r["发行"], "由": r["带来者"]} for r in ind],
            "口径": u"唯字面扫；⛔ 及 exec ／ 配置驱动之动态名"}


_PD_CACHE = None


def _pd():
    u"""`packages_distributions()` 之**一取**（其极贵 · ⛔ 逐名复取）。"""
    global _PD_CACHE
    if _PD_CACHE is None:
        _PD_CACHE = packages_distributions()
    return _PD_CACHE


def _installed(norm_name):
    u"""该**发行**名在本机装有否（归一比对）。"""
    for d in _pd().values():
        for x in d:
            if _norm(x) == norm_name:
                return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--all", action="store_true", help=u"并列**惰性**之依（缺省藏：惰性 ∧ 已声明）")
    ap.add_argument("--sites", action="store_true", help=u"并出诸处（径:行）")
    a = ap.parse_args()
    r = report(a.root)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    print(u"根：%s" % u" 、 ".join(r["根"]))
    print(u"%-16s %-16s %-10s %-6s %-6s %-6s %-14s %s" % (
        u"模块", u"发行", u"钉版", u"层", u"在", u"声明", u"段", u"用途"))
    for x in r["行"]:
        if not a.all and x["层"] == "惰性" and x["已声明否"]:
            continue
        print(u"%-16s %-16s %-10s %-6s %-6s %-6s %-14s %s" % (
            x["模块"], x["发行"], str(x["钉版（本机）"]), x["层"],
            u"是" if x["本机在否"] else u"⛔否", u"是" if x["已声明否"] else u"⛔否",
            (x["声明段"][:14] if x["已声明否"] else (u"间接" if x["带来者"] else u"—")), x["用途"]))
        if a.sites and len(x["诸处"]) > 1:
            for s in x["诸处"][1:]:
                print(u"%-16s   ↳ %s" % (u"", s))
    uns = [d for d in r["动态import"] if not d["静态可扫"]]
    if uns:
        print(u"\n⛔ 静态不可扫（动态 import · 名非字面）:")
        for d in uns:
            print(u"  %s" % d["径:行"])
    if r["仓内同名（⛔ 全限定名）"]:
        print(u"\n仓内同名之件（⛔ 全限定名 · 倚 sys.path · ⛔ 第三方发行）:")
        for k in sorted(r["仓内同名（⛔ 全限定名）"]):
            v = r["仓内同名（⛔ 全限定名）"][k]
            print(u"  %-24s ⇒ %s  ｜ %s" % (k, v["仓内同名"], u" 、 ".join(v["诸处"][:2])))
    print(u"\n**必需而未声明（硬缺）**：%s" % (u"、".join(r["必需而未声明"]) or u"（无）"))
    print(u"**兜底而未声明（缺 ⇒ 静默降级）**：%s" % (u"、".join(r["兜底而未声明"]) or u"（无）"))
    for s in r["间接（未声明 · 由 X 带来）"]:
        print(u"  间接：%s（由 %s）" % (s["发行"], u"、".join(s["由"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
