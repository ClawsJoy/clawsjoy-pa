# -*- coding: utf-8 -*-
u"""pa_msg.py -- the shell's HUMAN-FACING words (ONE PLACE, pm_1578 s2.2).

⛔ NOT via cmd's `echo`: a `.cmd` literal must be ASCII-ONLY.
  cmd.exe decodes the .cmd BYTES with the CONSOLE code page; a BOM-less UTF-8 file on a
  GBK(936) console mis-pairs CJK bytes with DBCS units, and Windows DBCS decoding SWALLOWS
  2 bytes on an invalid trail byte => it eats `\\r` (line splice) / `^` / `'` => CJK bytes get
  executed as commands (my first-hand control: on a 936 console `rem <star>` prints
  `'m' is not recognized as an internal or external command`).
=> Human words live here instead: the bundled Python writes the console via WriteConsoleW,
  which is CODE-PAGE INDEPENDENT, so CJK shows correctly on any console.

Usage (called by the four launchers):
  <root>\\runtime\\python.exe -X utf8 <root>\\scripts\\win_pa\\pa_msg.py start|stop|start-failed
"""
from __future__ import annotations

import sys

VERSION = u"1.0"

MSG = {
    u"start": u"[PA] 起服务（无窗）…… 首启约 30 秒（其间页面会显「未接」，属常）",
    u"stop": u"[PA] 停服……",
    u"start-failed": u"[PA] 起服 ⛔ 成 —— 因见上之数行（⛔ 静默）",
}


def render(key):
    u"""one message by key; None if unknown."""
    return MSG.get((key or u"").strip().lower())


def self_test():
    fails = []
    hits = []

    def say(ok, name):
        hits.append(bool(ok))
        print(u"  %s %s" % (u"+" if ok else u"X", name))
        if not ok:
            fails.append(name)

    say(sorted(MSG) == [u"start", u"start-failed", u"stop"], u"正控：三键齐（start ⁄ stop ⁄ start-failed）")
    say(all(v.strip() for v in MSG.values()), u"正控：无空辞")
    say(render(u"START") is MSG[u"start"] and render(u"") is None,
        u"正控：键不计大小写 ∧ 未知键 ⇒ None")
    print(u"=== pa_msg 自测 %d/%d ===" % (sum(hits), len(hits)))
    print(u"[self-test] %s" % (u"PASS" if not fails else u"FAIL"))
    for f in fails:
        print(u"  [FAIL] %s" % f)
    return 0 if not fails else 2


def main(argv):
    if sys.stdout is not None:
        try:
            sys.stdout.reconfigure(encoding=u"utf-8", errors=u"replace")
        except Exception:
            pass
    if argv and argv[0] == u"--self-test":
        return self_test()
    text = render(argv[0] if argv else u"")
    if text is None:
        print(u"pa_msg: unknown key %r -- known: %s" %
              (argv[0] if argv else u"", u" / ".join(sorted(MSG))))
        return 3
    print(text)
    return 0


if __name__ == u"__main__":
    sys.exit(main(sys.argv[1:]))
