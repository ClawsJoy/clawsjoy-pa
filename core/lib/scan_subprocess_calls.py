# -*- coding: utf-8 -*-
r"""scan_subprocess_calls.py —— **别名感知之扫器**：找出一棵树里**所有**「直接调 subprocess」之处。

⭐ 为何须此器（PM b136893 令 2026-10-05 19:26 · 裁「立为定式器」）：
  前扫以「**名形** `subprocess.run`」判 ⇒ **漏**「`import subprocess as _sp`」之别名调用
  （`core/gateway/**` 一处漏了 `13` 处：`_sp` / `_sub` / `_sp2` / `_sp_heredoc` / `_sp_inline` / `_sp_deg`）。
  ⇒ 承「**以形判 ⇒ 必漏**」（PM-92）与「**断无先扫其体**」（PM-87）⇒ 两条合为一律：
  **扫「××之调用」⇒ 须「别名感知 ＋ 扫其全体」**。

--- 域定义（逐字 · ⭐ 「何谓一处调用」）---
  一处调用 ＝ 下列**任一** AST `Call` 节点：
    ⒜ 属性形 `<M>.<fn>(...)`，其中 `M` 在**该调用可见之作用域链**上绑定于 `subprocess`
       （来源：`import subprocess` ∨ `import subprocess as <M>`，**模块级或任意函数级皆算**）；
    ⒝ 直接形 `<F>(...)`，其中 `F` 绑定于 `subprocess` 之某函数
       （来源：`from subprocess import <fn>` ∨ `from subprocess import <fn> as <F>`）。
  `fn` ∈ {run, Popen, call, check_output, check_call, getoutput, getstatusoutput}。
  ⭐ 分类：`flags`（带 `creationflags=`）／ ⭐ `bare`（**裸调** · ⛔ 旗）／ `shell=True` 另标。
  ⚠ 保守之处（照实）：作用域链取「该节点之**词法**祖先」之导入并集（⛔ 数据流）⇒ 宁多报。
  ⛔ 默认跳过 `.before_*` 与 `__pycache__`（存底／缓存 ⇒ ⛔ 活件）。

--- 用法 ---
  python scan_subprocess_calls.py [--root <目录>] [--json] [--all]
    --root <目录>  要扫之根（默认：core/gateway）
    --json         机读（末行打 JSON）
    --all          含存底（.before_*）与 __pycache__（默认排除）
    --exclude <子串>  排除路径含此子串之件（可重）⇒ ⭐ 如 `--exclude _proc.py`：
                    ⛔ 排「唯一出口」之本体（`_proc.py` 内之 3 处裸调**即那个出口** ⇒ ⛔ 算裸调）

--- ⭐ 归档桶（2026-10-05 · PM b136893 令「器须自识归档并分桶显之」§三.⒝ · 治根）---
  判据（逐字 · PM 2026-10-05 20:34 令 §二 之裁）：正则 `_v[\d._]+_\d{8}\.py$`
     ⇒ **点号形（`_v1.0.01_20260517.py`）与下划线形（`_v1_0_00_20260517.py`）皆收**。
  由（PM）：⭐ **「归档」之判据须以「义」定**（名含**版本号 ＋ 8 位日期戳**），⛔ 以「点号 ∨ 下划线」
     之**书写形**定 —— 二者**同一个意思的两种写法**；**只收一种 ⇒ 必漏**（承「以形判必漏」）。
  ⚠ **防过宽之界**：「义」之核 ＝ 名须含「**版本号 ＋ 8 位日期戳**」两件（⛔ 只「含 `_v`」）。
  由：**「归档即封」**是我们已立之律（`version_registry_v1.0.01/02/03_20260517.py` · `9` 处 `shell=True`）
      ⇒ **器应认得它** ⇒ ⛔ 靠每处手写 `--exclude`（**必漂** ⇒ PM 令之由）。
  ⚠ **假红可致真错**（CW 之预警 · PM 采）：归档入判 ⇒ 面报 `rc 2` ⇒ 人或**误修归档三件**。
  ⇒ 面须显 **「归档 `N` 件 · 豁免 `M` 处」**（⛔ 静默豁免 · 承「⛔ 藏」）｜**归档 ⛔ 计入 `rc`**。
  ⭐ `件数` ＝ **总（活 ＋ 归档）**（与老语义同）｜`活件数` ／ `归档件数` 分列 ⇒ `rc 5`（无件可扫）
     **唯**「总 `0`」时成立（⛔ 因「凡件皆归档」而误报空扫）。
  ⭐ 2026-10-05 20:34：**下划线形已并入**（PM 裁 §二）⇒ 原「候裁」之格**已销**。

--- 退出码（本器私有 · ⛔ 与 codex_guard 互换）· ⭐ 五分义（2026-10-05 修 · 承 CW `1167` 之二洞）---
  0 = 无裸调（凡调用皆带 `creationflags=` 或 ⛔ 直接调 subprocess）
  2 = **有裸调**（判红 · 须改）
  3 = 用法／路径错（**闸没跑** · 与「判红」⛔ 同）
  4 = ⭐ **闸未跑完**（**坏件 > 0** ⇒ ⛔ 得报 `0` · 承「不可达 ≠ 0」）
  5 = ⭐ **无件可扫**（**件数 == 0** ⇒ ⛔ 得报 `0` · 承「空 ≠ 缺」）
  优先级：3 > 5 > 4 > 2 > 0（“未跑完 / 无件” ‹‘净’ ⇒ → ⛔ 得报 `0`）
  ⚠ 读件一律 `utf-8-sig`（BOM 亦纳 —— 否则 BOM 之件入「坏件」而静默漏扫）。

唯读（⛔ 写任何件）· 附印（器印 ＋ 面之印 ＋ 取数刻）· 可唯读调。
"""
import argparse
import ast
import datetime
import hashlib
import io
import json
import os
import re
import sys

FN_NAMES = ("run", "Popen", "call", "check_output", "check_call", "getoutput", "getstatusoutput")

RC_MEAN = {
    0: u"已扫且净",
    2: u"有裸调（判红）",
    3: u"用法／路径错（闸没跑）",
    4: u"闸未跑完（坏件>0）",
    5: u"无件可扫（件数==0）",
}
HERE = os.path.abspath(__file__)

# ⭐ 归档之判据（逐字 · PM 2026-10-05 20:34 令 §二 之裁）：`_v[\d._]+_\d{8}\.py$`。
#   ⭐ **点号形 ＋ 下划线形皆收**（同一个意思的两种写法 · ⛔ 以形判必漏）；
#   ⚠ **防过宽**：`[\d._]+` 须**至少一字** ∧ **8 位日期戳收尾** ⇒ 名必含「版本号 ＋ 日期戳」两件。
ARCHIVE_RE = re.compile(r"_v[\d._]+_\d{8}\.py$")


def is_archive(path):
    u"""归档件之判（⛔ 唯看文件名 ⇒ ⛔ 读内容 · ⛔ 起子进程）。"""
    return bool(ARCHIVE_RE.search(os.path.basename(path)))


def sha16(path):
    try:
        with io.open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        return None


def _collect_scope_aliases(tree):
    u"""建：作用域节点 → (模块别名集, 函数别名集)；并记 parent。"""
    parent = {}
    scope_alias = {}
    scope_fnalias = {}
    scope_types = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)

    def walk(node, cur):
        if isinstance(node, scope_types):
            cur = node
        for child in ast.iter_child_nodes(node):
            parent[child] = node
            walk(child, cur)
    walk(tree, tree)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "subprocess":
                    sc = None
                    p = node
                    while p is not None:
                        if isinstance(p, scope_types):
                            sc = p
                            break
                        p = parent.get(p)
                    if sc is None:
                        sc = tree
                    scope_alias.setdefault(id(sc), set()).add(a.asname or "subprocess")
        elif isinstance(node, ast.ImportFrom):
            if node.module == "subprocess" and node.level == 0:
                sc = None
                p = node
                while p is not None:
                    if isinstance(p, scope_types):
                        sc = p
                        break
                    p = parent.get(p)
                if sc is None:
                    sc = tree
                for a in node.names:
                    if a.name in FN_NAMES:
                        scope_fnalias.setdefault(id(sc), set()).add(a.asname or a.name)
    return parent, scope_alias, scope_fnalias


def _aliases_visible(node, parent, scope_alias, scope_fnalias):
    mods, fns = set(), set()
    p = node
    while p is not None:
        mods |= scope_alias.get(id(p), set())
        fns |= scope_fnalias.get(id(p), set())
        p = parent.get(p)
    return mods, fns


def scan_file(path):
    u"""扫一件 ⇒ 调用点清单（每点：行 ／ 形 ／ 分类 ／ shell）。"""
    src = io.open(path, encoding="utf-8-sig").read()
    tree = ast.parse(src)
    parent, sa, sf = _collect_scope_aliases(tree)
    sites = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        mods, fns = _aliases_visible(node, parent, sa, sf)
        callee = None
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id in mods and node.func.attr in FN_NAMES:
                callee = node.func.value.id + "." + node.func.attr
        elif isinstance(node.func, ast.Name):
            if node.func.id in fns:
                callee = node.func.id + "()"
        if callee is None:
            continue
        kw = {k.arg for k in node.keywords if k.arg}
        has_flags = "creationflags" in kw
        sites.append({
            "line": node.lineno,
            "callee": callee,
            "kind": "flags" if has_flags else "bare",
            "shell": "shell" in kw,
        })
    return sites


def walk_tree(root, include_all=False):
    out = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if include_all or d != "__pycache__"]
        for name in sorted(fn):
            if not name.endswith(".py"):
                continue
            if not include_all and name.startswith(".before_"):
                continue
            out.append(os.path.join(dp, name))
    return sorted(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="alias-aware scanner for direct subprocess calls")
    ap.add_argument("--root", default=os.path.join("core", "gateway"))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--exclude", action="append", default=[], metavar="SUBSTR",
                    help=u"排除路径含此子串之件（可重 · 如 -_-exclude _proc.py ⇒ 排「唯一出口」之本体）")
    a = ap.parse_args(argv)

    root = os.path.abspath(a.root)
    if not os.path.isdir(root):
        sys.stderr.write(u"⛔ 路径不存在（闸没跑）：%s\n" % root)
        return 3

    files = walk_tree(root, a.all)
    if a.exclude:
        files = [f for f in files if not any(x in f.replace(os.sep, "/") for x in a.exclude)]
    live = [f for f in files if not is_archive(f)]   # ⭐ 活件（判 rc 之唯一据）
    arch = [f for f in files if is_archive(f)]       # ⭐ 归档桶（自识 · ⛔ 计入 rc）
    rep = {
        u"器": HERE,
        u"器印": sha16(HERE),
        u"面之径逐字": root,
        u"取数刻": datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z"),
        u"域定义": u"subprocess 之直接调用（含别名导入；run/Popen/call/check_output/check_call/getoutput/getstatusoutput）",
        u"排除": list(a.exclude),
        u"件数": len(files),          # ⭐ 总（活 ＋ 归档 ⇒ 与老语义同 · ⛔ 只活件）
        u"活件数": len(live),
        u"调用点": [],
        u"裸调数": 0,
        u"带旗数": 0,
        u"shell数": 0,
        u"坏件": [],
        u"归档件数": len(arch),
        u"归档调用点": [],
        u"归档豁免调用点": 0,
        u"归档豁免裸调": 0,
        u"归档坏件": [],
    }
    for f in live:
        try:
            sites = scan_file(f)
        except Exception as e:
            rep[u"坏件"].append({"file": f, "err": "%s" % e})
            continue
        for s in sites:
            s["file"] = os.path.relpath(f, root).replace(os.sep, "/")
            rep[u"调用点"].append(s)
            if s["kind"] == "bare":
                rep[u"裸调数"] += 1
            else:
                rep[u"带旗数"] += 1
            if s["shell"]:
                rep[u"shell数"] += 1

    # ⭐ 归档桶：扫之（报数 · 可回指）然 **⛔ 计入 rc**（PM §三.⒝：归档 ⛔ 计 rc）
    for f in arch:
        try:
            sites = scan_file(f)
        except Exception as e:
            rep[u"归档坏件"].append({"file": os.path.relpath(f, root).replace(os.sep, "/"), "err": "%s" % e})
            continue
        for s in sites:
            s["file"] = os.path.relpath(f, root).replace(os.sep, "/")
            s["archive"] = True
            rep[u"归档调用点"].append(s)
            rep[u"归档豁免调用点"] += 1
            if s["kind"] == "bare":
                rep[u"归档豁免裸调"] += 1

    if rep[u"件数"] == 0:
        rc = 5   # 无件可扫 ⇒ ⛔ 得报 0（空 ≠ 缺）
    elif rep[u"坏件"]:
        rc = 4   # 闸未跑完 ⇒ ⛔ 得报 0（不可达 ≠ 0）
    elif rep[u"裸调数"]:
        rc = 2   # 有裸调（判红）
    else:
        rc = 0   # 已扫且净
    rep[u"rc"] = rc

    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    else:
        print(u"器: %s" % rep[u"器"])
        print(u"器印: %s" % rep[u"器印"])
        print(u"面之径逐字: %s" % rep[u"面之径逐字"])
        print(u"取数刻: %s" % rep[u"取数刻"])
        print(u"域定义: %s" % rep[u"域定义"])
        if rep[u"排除"]:
            print(u"排除: %s" % rep[u"排除"])
        print(u"—— 件 %d（活 %d ＋ ⭐ 归档 %d）｜ 调用点 %d ｜ 裸调 %d ｜ 带旗 %d ｜ shell=True %d ｜ 坏件 %d"
              " ｜ ⭐ 归档豁免 %d 处（内裸调 %d）"
              % (rep[u"件数"], rep[u"活件数"], rep[u"归档件数"], len(rep[u"调用点"]), rep[u"裸调数"],
                 rep[u"带旗数"], rep[u"shell数"], len(rep[u"坏件"]),
                 rep[u"归档豁免调用点"], rep[u"归档豁免裸调"]))
        if rep[u"归档坏件"]:
            print(u"   ⚠ 归档坏件 %d（⛔ 计入 rc）：%s" % (len(rep[u"归档坏件"]), rep[u"归档坏件"][0]["file"]))
        print(u"rc: %d \uff1d %s" % (rep[u"rc"], RC_MEAN.get(rep[u"rc"], u"?")))
        for s in rep[u"调用点"]:
            tag = "BARE" if s["kind"] == "bare" else "flags"
            print(u"  %-46s :%-5d %-22s [%s]%s" % (s["file"], s["line"], s["callee"], tag, " shell=True" if s["shell"] else ""))
        for b in rep[u"坏件"]:
            print(u"  ⚠ 坏件 %s: %s" % (b["file"], b["err"]))

    return rc


if __name__ == "__main__":
    sys.exit(main())
