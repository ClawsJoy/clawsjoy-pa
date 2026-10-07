# -*- coding: utf-8 -*-
u"""port_lite.py -- 极轻之端口读器（**唯读真源之一小口** · ⛔ import core · ⛔ 副作用）。

为何另立此器（承 pm_1595 §二 · 令二）：取一个端口号本应是一次**纯配置读** ——
  然 `import core.lib.port_config` **必连带** `core/__init__` 之 `tenant_index_manager`
  ⇒ `core.tenant.*` ⇒ `chromadb`（**拉起半个应用 ∧ 触向量库 ∧ 与之争库 ∧ 迟**）。
  ⭐ 一手之实（副本之树 · 器取）：`IMPORT_S=1.46 ∧ chromadb_loaded=True ∧ tenant_loaded=True`。

一处定形（⛔ 二源 · 承 pm_1595 §二 · 令三）：
  ⭐ **值之家** ＝ `config/system/system_unified.yaml` 之 `services.gateway.port`
    （**与 `core.lib.port_config.SOURCE_KEY` 同键**）—— 本器 ⛔ 自持值 ∧ ⛔ 字面。
  ⭐ **应用之出口** ＝ `core.lib.port_config.gateway_port()`（**⛔ 本器**）。
  ⭐ **本器** ＝ **薄径**（启动器 ／ 状态 ／ 开页面）之**同键之读** ⇒ 其等价由齿锁
    （`tests/unit/test_win_pa_port_lite.py` · **器取**：本器之值 ⟷ `gateway_port()` 须同）。

用法：
  python -X utf8 scripts\\win_pa\\port_lite.py [--root <装根>] [--url] [--self-test]
退出码：0 ＝ 得值（印**唯数**）｜2 ＝ 未配 ／ 不可读（**fail-loud** · 承 port_config 口径 3）｜3 ＝ 入口错。
"""
from __future__ import annotations

import argparse
import io
import os
import sys

#: 真源之键链（＝ `port_config.SOURCE_KEY` 之拆写 · ⛔ 值之字面）
SOURCE_KEY = (u"services", u"gateway", u"port")
#: 真源之件（相对装根）
CONFIG_REL = os.path.join(u"config", u"system", u"system_unified.yaml")
#: 与 `port_config.CLIENT_HOST` 同值（⛔ 端口之值 · 承其口径 1：绑定址 ⛔ 作连接址）
CLIENT_HOST = u"127.0.0.1"
#: PA 页面之径（**一处定形**）
PAGE_PATH = u"/web/pa.html"


class PortUnconfigured(Exception):
    u"""端口未配 ／ 不可读 ⇒ **fail-loud**（⛔ 回落字面量 · 承 port_config 口径 3 ／ pm_1595 §二.1 ⒜）。"""


def default_root():
    u"""本器所在之装根（`<root>\\scripts\\win_pa\\port_lite.py` ⇒ `<root>`）。"""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _uncomment(raw):
    u"""去注释（唯 `#` 起首 ∨ 其前为空白 ⇒ 断）—— ⛔ 伤值内之 `#`。"""
    line = raw.rstrip(u"\r\n")
    if line.lstrip().startswith(u"#"):
        return u""
    for i, ch in enumerate(line):
        if ch == u"#" and (i == 0 or line[i - 1] in u" \t"):
            return line[:i]
    return line


def read_port(root=None):
    u"""真源之端口（**唯读** · ⛔ import core）。⛔ 得 ⇒ raise PortUnconfigured。"""
    root = root or default_root()
    path = os.path.join(root, CONFIG_REL)
    try:
        text = io.open(path, encoding=u"utf-8").read()
    except Exception as e:
        raise PortUnconfigured(u"真源不可读：%s（%s）" % (path, e))
    stack = []          # [(缩进, 键)] —— 唯走「键链」；⛔ 自持值
    for raw in text.split(u"\n"):
        line = _uncomment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(u" "))
        key, sep, val = line.strip().partition(u":")
        if not sep:
            continue
        key = key.strip()
        val = val.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        chain = [k for _i, k in stack] + [key]
        if chain == list(SOURCE_KEY):
            v = val.strip().strip(u'"').strip(u"'").strip()
            if not v.isdigit():
                raise PortUnconfigured(u"真源之值 ⛔ 为端口数：%r（%s）" % (val, path))
            return int(v)
        if not val:
            stack.append((indent, key))
    raise PortUnconfigured(u"⛔ 见真源之键 %s（%s）" % (u".".join(SOURCE_KEY), path))


def page_url(root=None):
    u"""PA 页面之址（**一处定形**：主机 ＋ 端口 ＋ 径皆出于此）。
    ⭐ 与 `port_config.gateway_base_url()` ＋ `PAGE_PATH` **须同**（由齿锁）。"""
    return u"http://%s:%d%s" % (CLIENT_HOST, read_port(root), PAGE_PATH)


def self_test():
    u"""自证：真源之读 ＋ 键链 ＋ 反控（缺键 ／ 非数 ／ 无件）＋ **⛔ 拉栈**（决定之齿）。"""
    import shutil
    import tempfile
    fails = []
    hits = []

    def say(ok, name):
        hits.append(bool(ok))
        print(u"  %s %s" % (u"+" if ok else u"X", name))
        if not ok:
            fails.append(name)

    say(u"core" not in sys.modules, u"正控：本器 ⛔ 拉 `core`（⛔ 连带 chromadb ／ 向量库）")
    p = read_port(default_root())
    say(isinstance(p, int) and 1024 < p < 65536, u"正控：真源之端口 ＝ %d" % p)
    say(page_url(default_root()).endswith(u":%d%s" % (p, PAGE_PATH)), u"正控：页面之址含同值")
    tmp = tempfile.mkdtemp(prefix=u"cjpa_pl_")
    try:
        d = os.path.join(tmp, u"config", u"system")
        os.makedirs(d, exist_ok=True)
        f = os.path.join(d, u"system_unified.yaml")

        def W(t):
            with io.open(f, u"w", encoding=u"utf-8", newline=u"") as fh:
                fh.write(t)

        W(u"services:\n  gateway:\n    port: 6011\n")
        say(read_port(tmp) == 6011, u"正控：同键之链 ⇒ 6011")
        W(u"services:\n  gateway:\n    port: 6011\n    debug: false\n")
        say(read_port(tmp) == 6011, u"正控：其下有他键 ⇒ 仍 6011")
        W(u"services:\n  gateway:\n    host: 0.0.0.0\n")
        try:
            read_port(tmp)
            say(False, u"反控：缺 `port` ⇒ 须 PortUnconfigured")
        except PortUnconfigured:
            say(True, u"反控：缺 `port` ⇒ PortUnconfigured")
        W(u"services:\n  gateway:\n    port: abc\n")
        try:
            read_port(tmp)
            say(False, u"反控：非数 ⇒ 须 PortUnconfigured")
        except PortUnconfigured:
            say(True, u"反控：非数 ⇒ PortUnconfigured")
        W(u"gateway:\n  port: 6011\n")
        try:
            read_port(tmp)
            say(False, u"反控：键链 ⛔ 合（缺 `services`）⇒ 须 PortUnconfigured")
        except PortUnconfigured:
            say(True, u"反控：键链 ⛔ 合 ⇒ PortUnconfigured")
        os.remove(f)
        try:
            read_port(tmp)
            say(False, u"反控：无件 ⇒ 须 PortUnconfigured")
        except PortUnconfigured:
            say(True, u"反控：无件 ⇒ PortUnconfigured")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(u"=== port_lite 自测 %d/%d ===" % (sum(hits), len(hits)))
    print(u"[self-test] %s" % (u"PASS" if not fails else u"FAIL"))
    for x in fails:
        print(u"  [FAIL] %s" % x)
    return 0 if not fails else 2


def main(argv):
    if sys.stdout is not None:
        try:
            sys.stdout.reconfigure(encoding=u"utf-8", errors=u"replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument(u"--root", default=u"")
    ap.add_argument(u"--url", action=u"store_true")
    ap.add_argument(u"--self-test", action=u"store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    root = os.path.abspath(a.root) if a.root else default_root()
    try:
        if a.url:
            print(page_url(root))
        else:
            print(read_port(root))
    except PortUnconfigured as e:
        print(u"[port_lite] %s" % e)
        return 2
    return 0


if __name__ == u"__main__":
    sys.exit(main(sys.argv[1:]))
