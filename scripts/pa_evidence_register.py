# -*- coding: utf-8 -*-
u"""pa_evidence_register.py -- 件—账—印 登记器 CLI（task-82 · `core/pa/evidence_ledger.py` 之薄入口）。

  python -X utf8 -B scripts/pa_evidence_register.py register <path> --owner <席> --decision <D-id> --rerun <cmd>
        [--ledger <path>] [--captured-at <ISO>]
      ⇒ `{ok, registered, path, count, key}`；**幂等**（同 path+sha16+decision 已存 ⇒ registered=false，
        ⛔ 重记）；新登 ⇒ JSONL 追加 ＋ fsync

  python -X utf8 -B scripts/pa_evidence_register.py verify [--ledger <path>] [--base-dir <dir>]
        [--max-age-days <N>] [--require-owner|--no-require-owner]
      ⇒ `{ok, total, bad, superseded}`：逐行校形 ＋ **重算件 sha16/bytes**（篡改必抓）；
        `--max-age-days` 非空 ⇒ C15 保鲜（过期 ⇒ bad reason=stale；未来 ⇒ reason=future）；
        `--require-owner` 缺省开（owner 缺/空/非串 ⇒ bad reason=owner）；旧账用 `--no-require-owner`

  python -X utf8 -B scripts/pa_evidence_register.py supersede <path> --sha16 <旧印>
        --decision <D-id> --owner <席> --reason <文> [--ledger <path>]
      ⇒ 追加一条 `kind="supersede"`（⛔ 删/改旧行）；幂等键 path+sha16；
        verify 将「已 supersede 且当前件已不同」之旧记录归 `superseded`（⛔ 计 bad）

退出码：0 ＝ ok（含幂等命中）／ 2 ＝ 校验失败（记录形坏 ／ 账有坏行 ／ verify 有 bad）
        3 ＝ 用法 ／ 1 ＝ 运行错（件不可读等；⛔ traceback 外泄）
账件缺省：env `PA_EVIDENCE_LEDGER` ⇒ 否则 `data/v9/pa/evidence_ledger.jsonl`。
输出：stdout 单行 JSON（错误亦 JSON：`{ok:false, error, error_type}`）。
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
    u"""用法／参数形之错（退出码 3）。"""


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise _UsageError(message)


_EL = None


def _ledger_mod():
    u"""惰引 `core.pa.evidence_ledger`（`core.pa` 导入期之印导去 stderr ⇒ stdout 唯 JSON）。"""
    global _EL
    if _EL is None:
        sink = sys.stderr if sys.stderr is not None else io.StringIO()
        with contextlib.redirect_stdout(sink):
            from core.pa import evidence_ledger as _m
        _EL = _m
    return _EL


def _emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")
    sys.stdout.flush()


def _ledger_path(ns):
    if ns.ledger:
        return ns.ledger
    return str(_ledger_mod().default_ledger_path())


def _cmd_register(ns):
    mod = _ledger_mod()
    rec = mod.build_record(ns.path, ns.owner, ns.decision, ns.rerun,
                           captured_at=ns.captured_at)
    res = mod.register(_ledger_path(ns), rec)
    payload = {"ok": True}
    payload.update(res)
    _emit(payload)
    return 0


def _cmd_verify(ns):
    mod = _ledger_mod()
    if ns.max_age_days is not None and ns.max_age_days <= 0:
        raise _UsageError("--max-age-days 须为 >0 之数值（今 %r）" % (ns.max_age_days,))
    res = mod.verify(_ledger_path(ns), base_dir=ns.base_dir,
                     max_age_days=ns.max_age_days, require_owner=ns.require_owner)
    _emit(res)
    return 0 if res.get("ok") else 2


def _cmd_supersede(ns):
    mod = _ledger_mod()
    res = mod.supersede(_ledger_path(ns), ns.path, ns.sha16,
                        ns.decision, ns.owner, ns.reason)
    payload = {"ok": True}
    payload.update(res)
    _emit(payload)
    return 0


def _build_parser():
    ap = _Parser(prog="pa_evidence_register.py", description=u"件—账—印 登记器（register/verify/supersede）")
    sub = ap.add_subparsers(dest="cmd")

    p_reg = sub.add_parser("register", help=u"登记一条（幂等 · 追加 ＋ fsync）")
    p_reg.add_argument("path", help=u"件之径")
    p_reg.add_argument("--owner", required=True, help=u"域主席")
    p_reg.add_argument("--decision", required=True, help=u"裁决 id（如 D-20261030-01）")
    p_reg.add_argument("--rerun", required=True, help=u"复跑命令（两次同结果 ∨ 反例）")
    p_reg.add_argument("--ledger", default=None, help=u"账件径（缺省 env/PA 数据域）")
    p_reg.add_argument("--captured-at", dest="captured_at", default=None,
                       help=u"取刻（ISO 8601；缺省＝取件此刻）")

    p_ver = sub.add_parser("verify", help=u"逐行复核 ＋ 重算件 sha16（篡改必抓）")
    p_ver.add_argument("--ledger", default=None, help=u"账件径（缺省 env/PA 数据域）")
    p_ver.add_argument("--base-dir", dest="base_dir", default=None,
                       help=u"相对件径之基（缺省 cwd）")
    p_ver.add_argument("--max-age-days", dest="max_age_days", type=float, default=None,
                       help=u"C15 保鲜（>0 天）：过期/future 入 bad；不传 ⇒ 只校形/印（默认不变）")
    p_ver.add_argument("--require-owner", dest="require_owner",
                       action=argparse.BooleanOptionalAction, default=True,
                       help=u"owner 读侧强制（缺省开）：缺/空/非串 ⇒ bad reason=owner；"
                            u"--no-require-owner 兼容旧账")

    p_sup = sub.add_parser("supersede", help=u"显式退旧印（追加 supersede 行 · ⛔ 删史）")
    p_sup.add_argument("path", help=u"旧记录之件径")
    p_sup.add_argument("--sha16", required=True, help=u"旧记录之印（16 位小写 hex）")
    p_sup.add_argument("--decision", required=True, help=u"本次退印之裁决 id")
    p_sup.add_argument("--owner", required=True, help=u"域主席")
    p_sup.add_argument("--reason", required=True, help=u"退印之因（非空）")
    p_sup.add_argument("--ledger", default=None, help=u"账件径（缺省 env/PA 数据域）")
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
        _emit({"ok": False, "error": u"缺子命令（register|verify|supersede）", "error_type": "usage"})
        return 3
    try:
        if ns.cmd == "register":
            return _cmd_register(ns)
        if ns.cmd == "verify":
            return _cmd_verify(ns)
        if ns.cmd == "supersede":
            return _cmd_supersede(ns)
        _emit({"ok": False, "error": u"未知子命令：%s" % ns.cmd, "error_type": "usage"})
        return 3
    except _UsageError as exc:
        _emit({"ok": False, "error": str(exc), "error_type": "usage"})
        return 3
    except Exception as exc:
        mod = _EL
        invalid = mod is not None and isinstance(exc, (mod.RecordInvalid, mod.LedgerCorrupt))
        _emit({"ok": False, "error": str(exc)[:300], "error_type": type(exc).__name__})
        return 2 if invalid else 1


if __name__ == "__main__":
    raise SystemExit(main())
