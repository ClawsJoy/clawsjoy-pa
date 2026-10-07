# -*- coding: utf-8 -*-
u"""import_closure.py -- 「载荷 = 入口之导入闭包」之器（承 pm_1598 令一）。

其病：make_client_bundle 之 PAYLOAD 为手写白名单，其「册」与「印」同出一单
  ⇒ 以清单自证清单 ⇒ 载荷缺 engine/ 与 gateway_endpoint.py 等而闸不响。

本器（判据换轴）：
- 闭包：自入口 agent_gateway_enhanced.py 静态可达之自有模块（逐件相对径）；
- 并取第三方之顶名（其可否解析归 site-packages 之验，非本器之责）；
- --check <载荷> ⇒ 报「闭包内之自有件 不在载荷」者 ⇒ 无缺则 rc 0，有缺则 rc 2。

用法：
  python -X utf8 scripts/win_pa/import_closure.py --repo <仓> --json
  python -X utf8 scripts/win_pa/import_closure.py --repo <仓> --check <载荷>
  python -X utf8 scripts/win_pa/import_closure.py --self-test
退出码：0 成 ｜ 2 载荷缺闭包之件（或自测败）｜ 3 入口钥。
"""
import argparse
import ast
import io
import json
import os
import sys

if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding=u"utf-8", errors="replace")
    except Exception:
        pass

ENTRY = u"agent_gateway_enhanced.py"
#: 非运行所需之顶名（开发物 ／ 构建物 ／ 运行产）遂除。
EXCLUDE_TOP = (u"tests", u"docs", u"_pm", u"_deploy", u"_backup", u"dist", u"data",
               u"logs", u"node_modules", u"wheel", u"runtime", u"__pycache__",
               u".venv", u"venv", u"_build_cache", u"_tmp")


def _has_py(d, limit=6000):
    n = 0
    for dp, dns, fns in os.walk(d):
        dns[:] = [x for x in dns if x != u"__pycache__"]
        for f in fns:
            if f.endswith(u".py"):
                return True
        n += 1
        if n > limit:
            return False
    return False


def local_tops(repo):
    u"""自有之顶名 ⇒ True（包之夹）／False（顶之 .py 件）。"""
    tops = {}
    for n in sorted(os.listdir(repo)):
        p = os.path.join(repo, n)
        if n.startswith(u".") or n in EXCLUDE_TOP or n.endswith(u".dist-info"):
            continue
        if os.path.isdir(p):
            if os.path.isfile(os.path.join(p, u"__init__.py")) or _has_py(p):
                tops[n] = True
        elif n.endswith(u".py"):
            tops.setdefault(n[:-3], False)
    return tops


def resolve(repo, dotted):
    u"""点径 ⇒ 相对径（无 ⇒ None）。含命名空间夹（无 __init__ 者）。"""
    if not dotted:
        return None
    parts = [x for x in dotted.split(u".") if x]
    p = os.path.join(repo, *parts)
    if os.path.isfile(p + u".py"):
        return os.path.relpath(p + u".py", repo)
    if os.path.isfile(os.path.join(p, u"__init__.py")):
        return os.path.relpath(os.path.join(p, u"__init__.py"), repo)
    if os.path.isdir(p) and _has_py(p):
        return os.path.relpath(p, repo)
    return None


def _imports(path):
    u"""件之导入（绝对名 ／ 层级 ／ from 之名表）-- 顶层与函数内皆取（皆可达）。"""
    if not os.path.isfile(path):   # 命名空间夹（无 __init__）⇒ 无件可析
        return []
    try:
        tree = ast.parse(io.open(path, encoding=u"utf-8", errors=u"replace").read())
    except (SyntaxError, ValueError, OSError):
        return []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                found.append((a.name, 0, []))
        elif isinstance(node, ast.ImportFrom):
            found.append((node.module or u"", node.level or 0,
                          [a.name for a in node.names]))
    return found


def _pkg_of(rel):
    d = os.path.dirname(rel)
    return d.replace(os.sep, u".").replace(u"/", u".")


def _cands(name, level, names, rel):
    u"""=> (sure, guess)：sure = 必为模块之点径；guess = 「from … import X」之 X 之猜
    （X 多为其内之符号而非子模块 ⇒ 不可解时 不计「未解」）。"""
    sure, guess = [], []
    if level == 0:
        if name:
            parts = [x for x in name.split(u".") if x]
            sure += [u".".join(parts[:i + 1]) for i in range(len(parts))]
            guess += [name + u"." + n for n in names]
        else:
            sure += [n for n in names if n]
    else:
        pkg = _pkg_of(rel).split(u".")
        base = pkg[:len(pkg) - (level - 1)] if level > 1 else pkg
        stem = u".".join([x for x in base if x])
        if name:
            mod = (stem + u"." + name) if stem else name
            sure.append(mod)
            guess += [(mod + u"." + n) for n in names]
        else:
            guess += [((stem + u"." + n) if stem else n) for n in names]
    return sure, guess


def closure(repo, entry=ENTRY):
    u"""=> (自有件之相对径之集, 第三方之顶名之集, 未解之点径之集)。"""
    tops = local_tops(repo)
    ent = entry.replace(u"/", os.sep)
    out, third, unresolved = set(), set(), set()
    seen = set()
    ent_abs = os.path.join(repo, ent)
    if not os.path.isfile(ent_abs):
        return out, third, {entry}
    out.add(ent)
    queue = [(ent, ent_abs)]
    seen.add(ent)
    while queue:
        rel, ap = queue.pop()
        for name, level, names in _imports(ap):
            sure, guess = _cands(name, level, names, rel)
            todo = [(x, False) for x in sure] + [(x, True) for x in guess]
            for c, spec in todo:
                if not c:
                    continue
                root = c.split(u".")[0]
                if root not in tops:
                    if not spec:
                        third.add(root)
                    continue
                rp = resolve(repo, c)
                if rp is None:
                    if not spec:
                        unresolved.add(c)
                    continue
                if rp not in seen:
                    seen.add(rp)
                    out.add(rp)
                    queue.append((rp, os.path.join(repo, rp)))
    return out, third, unresolved


def stdlib_names():
    n = set(getattr(sys, u"stdlib_module_names", ()) or ())
    n |= set(getattr(sys, u"builtin_module_names", ()) or ())
    return n


def check_payload(repo, payload, entry=ENTRY):
    u"""=> (ok, 报行 list)。"""
    out, third, unresolved = closure(repo, entry)
    rows = []
    miss = [rel for rel in sorted(out) if not os.path.exists(os.path.join(payload, rel))]
    rows.append(u"[%s] 闭包（自有）：%d 件 ｜ 载荷之内：%d ｜ 缺 %d"
                % (u"OK" if not miss else u"FAIL", len(out), len(out) - len(miss), len(miss)))
    for rel in miss[:40]:
        rows.append(u"   缺：%s" % rel)
    if len(miss) > 40:
        rows.append(u"   … 余 %d 件" % (len(miss) - 40))
    tp = sorted(x for x in third if x not in stdlib_names())
    rows.append(u"[--] 第三方之顶名（%d）：%s" % (len(tp), u" ".join(tp[:60])))
    if unresolved:
        rows.append(u"[--] 未解之点径（%d · 多为符号之名 人工核）：%s"
                    % (len(unresolved), u" ／ ".join(sorted(unresolved)[:20])))
    return (not miss), rows


def self_test():
    u"""反控（尽临时夹）：正控＝自有之闭包 ／ 缺件必报 ／ 第三方别于自有。"""
    import shutil
    import tempfile
    fails = []

    def say(ok, name):
        print(u"  %s %s" % (u"ok" if ok else u"XX", name))
        if not ok:
            fails.append(name)

    t = tempfile.mkdtemp(prefix=u"cjpa_clo_")
    try:
        def W(rel, text):
            p = os.path.join(t, *rel.split(u"/"))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            io.open(p, u"w", encoding=u"utf-8", newline=u"\n").write(text)

        W(u"agent_gateway_enhanced.py",
          u"import os\nimport requests\nfrom core.gateway.registry import Router\n"
          u"from engine.orchestration.task_manager import TaskManager\n"
          u"from gateway_endpoint import gateway_base_url\n"
          u"def f():\n    import later_only\n    return later_only\n")
        W(u"core/__init__.py", u"")
        W(u"core/gateway/__init__.py", u"")
        W(u"core/gateway/registry.py", u"from . import boot\nimport json\n")
        W(u"core/gateway/boot.py", u"")
        W(u"engine/__init__.py", u"from engine.youtube.auth import youtube_auth\n")
        W(u"engine/orchestration/__init__.py", u"")
        W(u"engine/orchestration/task_manager.py", u"")
        W(u"engine/youtube/__init__.py", u"")
        W(u"engine/youtube/auth.py", u"from gateway_endpoint import gateway_base_url\n")
        W(u"gateway_endpoint.py", u"def gateway_base_url():\n    return u''\n")
        W(u"later_only.py", u"")
        W(u"tests/test_x.py", u"import engine\n")

        out, third, unres = closure(t)
        want = {u"agent_gateway_enhanced.py", u"core/__init__.py", u"core/gateway/__init__.py",
                u"core/gateway/registry.py", u"core/gateway/boot.py", u"engine/__init__.py",
                u"engine/orchestration/__init__.py", u"engine/orchestration/task_manager.py",
                u"engine/youtube/__init__.py", u"engine/youtube/auth.py",
                u"gateway_endpoint.py", u"later_only.py"}
        got = {x.replace(os.sep, u"/") for x in out}
        say(got == want, u"正控：闭包 ＝ 逐件（%d 件 · 缺 %s ／ 多 %s）"
            % (len(want), sorted(want - got), sorted(got - want)))
        tp = {x for x in third if x not in stdlib_names()}
        say(u"requests" in tp and u"os" not in tp, u"正控：第三方取顶名 ／ 标准库别之")
        say(u"tests/test_x.py" not in got, u"反控：tests/ 不入闭包（不以它证它）")
        say(not unres, u"正控：无未解（%s）" % sorted(unres))
        ok, rows = check_payload(t, t)
        say(ok, u"正控：载荷 ＝ 仓 ⇒ 过（%s）" % rows[0])
        miss_dir = os.path.join(t, u"_p")
        shutil.copytree(t, miss_dir, ignore=shutil.ignore_patterns(u"engine"))
        ok2, rows2 = check_payload(t, miss_dir)
        say((not ok2) and any((u"engine" + os.sep) in r for r in rows2),
            u"反控：载荷缺 engine/ ⇒ 必红（报其件）")
    finally:
        shutil.rmtree(t, ignore_errors=True)
    print(u"=== import_closure 自测 %s ===" % (u"通过" if not fails else u"败"))
    return 0 if not fails else 2


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument(u"--repo", default=u"")
    ap.add_argument(u"--entry", default=ENTRY)
    ap.add_argument(u"--check", default=u"")
    ap.add_argument(u"--json", action=u"store_true")
    ap.add_argument(u"--self-test", action=u"store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    repo = os.path.abspath(a.repo) if a.repo else os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if not os.path.isdir(repo):
        print(u"[用法钥] 仓不在：%s" % repo)
        return 3
    if a.check:
        ok, rows = check_payload(repo, os.path.abspath(a.check), a.entry)
        print(u"# import_closure ｜ 仓：%s ｜ 载荷：%s" % (repo, a.check))
        print(u"\n".join(rows))
        return 0 if ok else 2
    out, third, unres = closure(repo, a.entry)
    tp = sorted(x for x in third if x not in stdlib_names())
    if a.json:
        print(json.dumps({u"repo": repo, u"entry": a.entry, u"files": sorted(out),
                          u"third_party": tp, u"unresolved": sorted(unres)},
                         ensure_ascii=False, indent=1))
    else:
        print(u"[闭包] 自有之件 %d ｜ 第三方之顶名 %d ｜ 未解 %d" % (len(out), len(tp), len(unres)))
        print(u"[第三方] %s" % u" ".join(tp))
        print(u"\n".join(u"   " + x for x in sorted(out)))
    return 0


if __name__ == u"__main__":
    sys.exit(main(sys.argv[1:]))