#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""死模块双扫描（2026-09-13）—— 删任何模块**之前**跑它。

为什么需要两个扫描：
  1. **静态/动态代码引用**：import 语句、importlib.import_module(...) 的**字面量**参数；
  2. **字符串注册（弱引用）**：模块名以**字符串**形式出现在注册表/列表里
     （如 register_module(name, path) / 列表项 "lib.x"）——
     **import 扫描发现不了这一类**，文件删了不报错但注册表与事实脱节。
     本条是 2026-09-13 减法第一批踩出来的：删完 route_handlers 后仍剩 3 处字符串注册。

用法：
    python3 tools/dead_module_scan.py <module_name> [search_root]
    # 例：python3 tools/dead_module_scan.py route_handlers
退出码：0 = 无任何引用（可安全删）；1 = 仍有引用（不可删）。
"""
import os
import re
import sys

SKIP_DIRS = (".git", ".venv", "node_modules", "__pycache__", "archive", "data", "logs", ".pytest_cache")


def _iter_py(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(".py"):
                yield os.path.join(dirpath, fn)


def scan(name, root="."):
    """返回 {static:[], dynamic:[], string_reg:[]}，每项为 'path:line: 内容'。"""
    out = {"static": [], "dynamic": [], "string_reg": []}
    # 2026-09-13 修盲区：原正则只认裸模块名，漏掉「点号路径 import」——
    # from core.lib.X import ... / import core.lib.X as X 都匹配不到，
    # 导致 route_vectorizer 被误判为 0 引用并归档（被回归测试当场抓回）。
    mod_re = re.compile(
        r"^\s*(?:from\s+[\w.]*\b%s\s+import|import\s+[\w.]*\b%s\b)" % (re.escape(name), re.escape(name))
    )
    # 属性/变量访问：X.get_stats(...) 这类即使没有 import 行也要算引用
    attr_re = re.compile(r"\b%s\s*\." % re.escape(name))
    dotted = re.compile(r"[\w.]*%s[\w.]*" % re.escape(name))
    dyn_lit = re.compile(r"import_module\s*\(\s*['\"]([^'\"]+)['\"]")
    dyn_var = re.compile(r"import_module\s*\(\s*[^'\")\s]")
    glob_var = re.compile(r"globals\s*\(\s*\)\s*\[\s*[^'\"]")
    reg = re.compile(r"register_module\s*\(\s*['\"][^'\"]*%s" % re.escape(name))
    for p in _iter_py(root):
        try:
            lines = open(p, encoding="utf-8", errors="ignore").read().split(chr(10))
        except Exception:
            continue
        for i, ln in enumerate(lines, 1):
            tag = "%s:%d: %s" % (p, i, ln.strip()[:110])
            if mod_re.match(ln):
                out["static"].append(tag)
            elif attr_re.search(ln) and not ln.strip().startswith("#"):
                out["static"].append(tag + "   [属性访问]")
            if dyn_lit.search(ln) and name in ln:
                out["dynamic"].append(tag)
            if (dyn_var.search(ln) or glob_var.search(ln)) and name in ln:
                out["dynamic"].append(tag)
            if reg.search(ln):
                out["string_reg"].append(tag)
            elif name in ln and ("'" in ln or '"' in ln) and not mod_re.match(ln) and not ln.strip().startswith("#"):
                if dotted.search(ln) and name in ln:
                    out["string_reg"].append(tag)
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    name = sys.argv[1]
    root = sys.argv[2] if len(sys.argv) > 2 else "."
    r = scan(name, root)
    total = sum(len(v) for v in r.values())
    print("=== 死模块双扫描：%s（root=%s）===" % (name, root))
    for k, label in (("static", "① 静态 import 引用"), ("dynamic", "② 动态 import 引用"), ("string_reg", "③ 字符串注册（弱引用）")):
        print(chr(10) + label + "：%d" % len(r[k]))
        for x in r[k][:12]:
            print("   " + x)
    print(chr(10) + "合计引用：%d → %s" % (total, "可安全删" if total == 0 else "**不可删**"))
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

# (2026-09-13) 用于验证 diff_count 真值
