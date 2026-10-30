# -*- coding: utf-8 -*-
u"""pa_relations.py -- 外联脚手架 CLI（task-76/81 · T74/T78 校验器之**薄入口**）。

五子命令（逻辑唯在 `core/pa/relations.py` · 本件 ⛔ 另造语义）：

  python -X utf8 -B scripts/pa_relations.py evidence <path>
      ⇒ `make_evidence` 之 JSON（path ／ bytes ／ sha16 ／ captured_at）

  python -X utf8 -B scripts/pa_relations.py validate-evidence <json|文件|-> 
  python -X utf8 -B scripts/pa_relations.py validate-decision <json|文件|->
      ⇒ 校验器之 `{ok, missing, errors}`；`-` ＝ 自 stdin 读

  python -X utf8 -B scripts/pa_relations.py wip <json|文件|->
      ⇒ `{"ok": <check_wip>}`（同一 owner 多 `in_progress` ⇒ ok=false）

  python -X utf8 -B scripts/pa_relations.py freshness <json|文件|-> [--ttl-days 30] [--now <ISO>]
      ⇒ `{ok, age_days, expires_at, errors}`（C15：30 天 ／ owner 域主席）；
        `--now` 供复跑置刻（缺省＝此刻）；`--ttl-days` 覆 TTL（>0 数值）

退出码（一处定形）：
  0 ＝ ok ／ 2 ＝ 校验失败（validate_* 之 ok=false ／ wip 越界或形坏 ／ freshness 过期或非法）
  3 ＝ 用法（无子命令 ／ 未知子命令 ／ 缺参 ／ 输入非合法 JSON ／ 参数形坏）
  1 ＝ 运行错（件不可读等 —— 含异常类型，⛔ traceback 外泄）

输出：一律 **stdout 之单行 JSON**（错误亦 JSON：`{ok:false, error, error_type}`），
便于账／验器直取；⛔ 改路由 ／ UI ／ `relations.py` 语义。
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
from pathlib import Path

if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class _UsageError(Exception):
    u"""用法／输入形之错（映射退出码 3 · ⛔ 与运行错混）。"""


class _Parser(argparse.ArgumentParser):
    u"""argparse 之错 ⇒ `_UsageError`（默认 SystemExit(2) 会与「校验失败」混）。"""

    def error(self, message):
        raise _UsageError(message)


_RELATIONS = None


def _relations():
    u"""惰引 `core.pa.relations`（⛔ 顶层：`core.pa` 导入期有配置/向量初始化之印 ——
    须导离 stdout，否则污染「单行 JSON」之约；导去 stderr 照实可见）。"""
    global _RELATIONS
    if _RELATIONS is None:
        sink = sys.stderr if sys.stderr is not None else io.StringIO()
        with contextlib.redirect_stdout(sink):
            from core.pa import relations as _rel
        _RELATIONS = _rel
    return _RELATIONS


def _read_json_arg(arg):
    u"""`<json|文件|->` ⇒ 解出之对象；坏 JSON ⇒ _UsageError（退出码 3）。"""
    if arg == "-":
        text, where = sys.stdin.read(), u"stdin"
    else:
        try:
            is_file = Path(arg).is_file()
        except OSError:
            is_file = False
        if is_file:
            text, where = Path(arg).read_text(encoding="utf-8"), arg
        else:
            text, where = arg, u"参数"
    try:
        return json.loads(text)
    except Exception as exc:
        raise _UsageError(u"输入非合法 JSON（%s）：%s: %s"
                          % (where, type(exc).__name__, str(exc)[:160]))


def _emit(obj):
    u"""单行 JSON 落 stdout（⛔ 多行 ／ ⛔ 混人话）。"""
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")
    sys.stdout.flush()


def _cmd_evidence(path):
    rec = _relations().make_evidence(path)
    _emit(rec)
    return 0


def _cmd_validate_evidence(arg):
    got = _relations().validate_evidence(_read_json_arg(arg))
    _emit(got)
    return 0 if got.get("ok") else 2


def _cmd_validate_decision(arg):
    got = _relations().validate_decision(_read_json_arg(arg))
    _emit(got)
    return 0 if got.get("ok") else 2


def _cmd_wip(arg):
    tasks = _read_json_arg(arg)
    try:
        ok = _relations().check_wip(tasks)
    except ValueError as exc:
        _emit({"ok": False, "error": str(exc), "error_type": "ValueError"})
        return 2
    _emit({"ok": bool(ok)})
    return 0 if ok else 2


def _cmd_freshness(arg, ttl_days=30.0, now=None):
    got = _relations().check_freshness(_read_json_arg(arg), now=now, ttl_days=ttl_days)
    _emit(got)
    return 0 if got.get("ok") else 2


def _build_parser():
    ap = _Parser(prog="pa_relations.py", description=u"PA 外联脚手架：证据/裁决/WIP/保鲜 校验器 CLI")
    sub = ap.add_subparsers(dest="cmd")
    p_ev = sub.add_parser("evidence", help=u"取件之录（path/bytes/sha16/captured_at）")
    p_ev.add_argument("path", help=u"件之径")
    for name, helptext in (
        ("validate-evidence", u"校证据录之形"),
        ("validate-decision", u"校裁决录之形"),
        ("wip", u"校每席 WIP=1"),
    ):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("input", help=u"JSON 字串 ∨ 文件径 ∨ -（stdin）")
    p_fr = sub.add_parser("freshness", help=u"C15 证据保鲜（30 天 ／ owner 域主席）")
    p_fr.add_argument("input", help=u"JSON 字串 ∨ 文件径 ∨ -（stdin）")
    p_fr.add_argument("--ttl-days", dest="ttl_days", type=float, default=30.0,
                      help=u"保鲜期（天 · >0 数值 · 缺省 30）")
    p_fr.add_argument("--now", default=None,
                      help=u"置刻（ISO 8601 · 缺省＝此刻 · 供复跑）")
    return ap


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    try:
        ns = parser.parse_args(args)
    except _UsageError as exc:
        _emit({"ok": False, "error": str(exc), "error_type": "usage"})
        return 3
    if not ns.cmd:
        _emit({"ok": False,
               "error": u"缺子命令（evidence|validate-evidence|validate-decision|wip|freshness）",
               "error_type": "usage"})
        return 3
    try:
        if ns.cmd == "evidence":
            return _cmd_evidence(ns.path)
        if ns.cmd == "validate-evidence":
            return _cmd_validate_evidence(ns.input)
        if ns.cmd == "validate-decision":
            return _cmd_validate_decision(ns.input)
        if ns.cmd == "wip":
            return _cmd_wip(ns.input)
        if ns.cmd == "freshness":
            return _cmd_freshness(ns.input, ttl_days=ns.ttl_days, now=ns.now)
        _emit({"ok": False, "error": u"未知子命令：%s" % ns.cmd, "error_type": "usage"})
        return 3
    except _UsageError as exc:
        _emit({"ok": False, "error": str(exc), "error_type": "usage"})
        return 3
    except Exception as exc:  # 运行错：显类 ＋ 简讯，⛔ traceback
        _emit({"ok": False, "error": str(exc)[:300], "error_type": type(exc).__name__})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
