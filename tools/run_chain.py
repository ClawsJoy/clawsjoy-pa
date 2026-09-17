#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_chain —— 用 run_id / run 窗口机械取全链（批152 · P0-0 交付物）。

用法：
    python3 tools/run_chain.py <session_id>:<turn_id>          # 严格按 run_id 字段取（turn_id 未 canonical 前可能不全）
    python3 tools/run_chain.py --latest <session_id>           # 取**最后一个 run 窗口**（today 的实用入口，取到完整链）
    python3 tools/run_chain.py --runs <session_id>             # 列出该 session 的所有 run（并显示其 turn_ids —— 暴露 turn_id 不纯）
    python3 tools/run_chain.py --window <session_id> <seq_from> <seq_to>
    python3 tools/run_chain.py --dir <session_logs 目录> …     # 指定日志目录（默认 cwd/data/session_logs，回落代码根）

**不需要在任务正文里放任何标记**（批105 的手工标记法作废，见 P0-0 验收）。
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.gateway.run_id import (  # noqa: E402
    chain_summary,
    default_log_dir,
    iter_run_events,
    iter_run_window,
    list_runs,
    make_run_id,
    parse_run_id,
)


def _warn_if_session_file_missing(session_id, base_dir):
    """批173 F 段：**会话文件不存在时必须显式告警**。

    此前只告警"目录不存在"；当目录在、文件不在时会静默打印「无事件」——
    批171 实测：在 dev 树跑 live 的 run_id 得到 0 条，看起来像"链取不到"，其实只是**取错了树**。
    """
    from pathlib import Path as _P

    d = _P(base_dir) if base_dir else default_log_dir()
    f = d / (session_id.replace("/", "_").replace(":", "_") + ".jsonl")
    if not f.exists():
        print("❌ 会话文件不存在：%s" % f)
        print("   （当前工作目录 %s；该 run 可能是在**另一棵树/另一个进程**里产生的）" % _P.cwd())
        print("   ⇒ 用 --dir <session_logs 目录> 指定正确位置；**不要把 0 条当成链取不到**（体检项 63）")
        return False
    return True


def _print_events(evs, title):
    s = chain_summary(evs)
    print(title)
    print("  事件总数 : %d" % s["count"])
    if not evs:
        print("  （无事件）")
        return
    print("  段落分布 : " + " ".join("%s=%d" % (k, v) for k, v in s["segments"].items()))
    print("  类型分布 : " + ", ".join("%s×%d" % (k, v) for k, v in sorted(s["types"].items(), key=lambda x: -x[1])))
    print("-" * 74)
    for ev in evs:
        _p = ev.get("payload") or {}
        _hint = ""
        for _k in ("tool", "name", "stage", "reason", "status", "ok", "success", "path", "error", "content"):
            if _k in _p:
                _hint += " %s=%s" % (_k, str(_p[_k]).replace(chr(10), " ")[:56])
        print(
            "  #%-4s turn=%-11s step=%-3s %-18s%s"
            % (ev.get("seq"), ev.get("turn_id"), ev.get("step_id"), ev.get("type"), _hint[:150])
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="用 run_id / run 窗口机械取全链事件")
    ap.add_argument("run_id", nargs="?", help="格式 session_id:turn_id")
    ap.add_argument("--latest", metavar="SESSION_ID", help="取该 session 的最后一个 run 窗口")
    ap.add_argument("--runs", metavar="SESSION_ID", help="列出该 session 的所有 run")
    ap.add_argument("--window", nargs=3, metavar=("SESSION_ID", "SEQ_FROM", "SEQ_TO"), help="按 seq 窗口取")
    ap.add_argument("--dir", metavar="DIR", help="session_logs 目录")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    a = ap.parse_args()
    bd = Path(a.dir) if a.dir else None
    print("日志目录 : %s" % (bd or default_log_dir()))
    if not (bd or default_log_dir()).exists():
        print("❌ 日志目录不存在 —— 取链会得到空；请用 --dir 指定（体检项 63：空结果要先自证在场）")
        return 1

    # 批173 F 段：先自证"要读的文件在场"，再谈"有没有事件"
    _sess = None
    if a.run_id:
        _sess = parse_run_id(a.run_id)[0]
    elif a.latest:
        _sess = a.latest
    elif a.window:
        _sess = a.window[0]
    if _sess and not _warn_if_session_file_missing(_sess, bd):
        return 1

    if a.runs:
        rs = list_runs(a.runs, base_dir=bd)
        if a.json:
            print(json.dumps(rs, ensure_ascii=False, indent=1))
            return 0 if rs else 1
        print("session %s 共 %d 个 run：" % (a.runs, len(rs)))
        for r in rs:
            print(
                "  run%-2d seq %-4s-%-4s 事件%-3d turn_ids=%s"
                % (r["index"], r["seq_from"], r["seq_to"], r["count"], r["turn_ids"])
            )
            if r.get("user_head"):
                print("        用户: %s" % r["user_head"].replace(chr(10), " ")[:70])
        return 0 if rs else 1

    if a.window:
        _sid, _f, _t = a.window
        evs = iter_run_window(_sid, int(_f), int(_t), base_dir=bd)
        if a.json:
            print(
                json.dumps(
                    {"session_id": _sid, "seq_from": _f, "seq_to": _t, "summary": chain_summary(evs), "events": evs},
                    ensure_ascii=False,
                    indent=1,
                )
            )
            return 0 if evs else 1
        _print_events(evs, "run 窗口 %s seq %s-%s" % (_sid, _f, _t))
        return 0 if evs else 1

    if a.latest:
        rs = list_runs(a.latest, base_dir=bd)
        if not rs:
            print("❌ 该 session 没有任何事件（检查 session_id / --dir）")
            return 1
        r = rs[-1]
        evs = iter_run_window(a.latest, r["seq_from"], r["seq_to"], base_dir=bd)
        if a.json:
            print(
                json.dumps(
                    {"session_id": a.latest, "run": r, "summary": chain_summary(evs), "events": evs},
                    ensure_ascii=False,
                    indent=1,
                )
            )
            return 0
        print("run 窗口 : seq %s-%s（该 run 内的 turn_ids=%s）" % (r["seq_from"], r["seq_to"], r["turn_ids"]))
        _print_events(evs, "最后一个 run 的完整链")
        return 0

    if a.run_id:
        _sid, _turn = parse_run_id(a.run_id)
        if not _sid:
            print("非法 run_id：%s（应为 session_id:turn_id）" % a.run_id)
            return 2
        evs = iter_run_events(a.run_id, base_dir=bd)
        if a.json:
            print(
                json.dumps(
                    {"run_id": a.run_id, "summary": chain_summary(evs), "events": evs}, ensure_ascii=False, indent=1
                )
            )
            return 0 if evs else 1
        print(
            "run_id   : %s（严格按字段取；批155 起 turn_id 已 canonical 化 ⇒ 一次运行的全链都在此 run_id 下，"
            "无需 --latest；--latest/--window 仅对批155 之前的老日志有用）" % a.run_id
        )
        _print_events(evs, "run_id=%s 的事件" % a.run_id)
        return 0 if evs else 1

    print(
        "用法：python3 tools/run_chain.py <session>:<turn> ｜ --latest <session> ｜ --runs <session> ｜ --window <session> <f> <t>"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
