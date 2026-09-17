#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P0-1 定性工具：把日志里的「round 0」逐案定性（批153）。

背景：P0-1 的口径是「**定位历史未推进案例**」而不是「修一个必现 bug」——
批143/146 真跑里 round 0→6 正常推进，历史 21 例里才有未推进个案。

用法：
    python3 tools/p0_1_round0_diagnose.py [--log logs/gateway.log] [--json]

定性口径（四类，与执行卡一致）：
    已推进   —— 其后出现 [ROUND] round 1（或更高）
    环境     —— 窗口内出现 402/timeout/API错误/Connection/超时（外部服务问题，不算产品 bug）
    真挂     —— 无后续轮次、无错误标记、也无 return（LLM_START 后无 LLM_RETURN）
    误判     —— 有 LLM 返回/工具步/turn_end，但**没有 round 1 的日志**（推进了但日志没记）

新打点上线后（批153 起）：窗口内配对 [LLM_START]/[LLM_RETURN]（都带 run_id）即可机械判定，
本工具对**历史**日志用结构证据，对**新**日志直接读打点。
"""
import argparse
import json
import os
import re
import sys

ENV_KEYS = (
    "402",
    "balance insufficient",
    "timeout",
    "Timeout",
    "timed out",
    "API错误",
    "Connection",
    "超时",
    "SSLError",
    "Max retries",
)
ROUND0 = "[ROUND] round 0 开始"


def analyze(path):
    try:
        lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
    except Exception as e:
        print("读取失败: %s" % e)
        return []
    idx = [i for i, l in enumerate(lines) if ROUND0 in l]
    out = []
    for n, i in enumerate(idx):
        j = idx[n + 1] if n + 1 < len(idx) else len(lines)
        win = lines[i:j]
        txt = "\n".join(win)
        has_next_round = bool(re.search(r"\[ROUND\] round [1-9][0-9]* 开始", txt))
        env_hit = next((k for k in ENV_KEYS if k in txt), "")
        has_return = "[LLM_RETURN]" in txt or "LLM 返回 success=" in txt
        has_tool = "执行工具" in txt or "tool_calls=" in txt
        has_end = "turn_end" in txt or "正常完成" in txt or "[TURN_END]" in txt
        if has_next_round:
            verdict, why = "已推进", "其后出现 round≥1"
        elif env_hit:
            verdict, why = "环境", "窗口内命中 %r" % env_hit
        elif has_return and (has_tool or has_end):
            verdict, why = "误判", "有 LLM 返回/工具步但无 round≥1 日志"
        elif not has_return:
            verdict, why = "真挂", "LLM_START 后未见返回（历史日志无打点，按结构推定）"
        else:
            verdict, why = "误判", "有返回但无后续轮次日志"
        out.append(
            {
                "case": n + 1,
                "line_no": i + 1,
                "window_lines": len(win),
                "verdict": verdict,
                "why": why,
                "has_next_round": has_next_round,
                "has_llm_return": has_return,
                "env_hit": env_hit,
                "has_tool": has_tool,
                "has_end": has_end,
                "head": win[0][:120],
            }
        )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default="logs/gateway.log")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not os.path.exists(a.log):
        print("日志不存在: %s" % a.log)
        return 1
    cases = analyze(a.log)
    if a.json:
        print(json.dumps(cases, ensure_ascii=False, indent=1))
        return 0
    print("日志: %s ｜ round 0 案例数: %d" % (a.log, len(cases)))
    from collections import Counter

    c = Counter(x["verdict"] for x in cases)
    print("定性分布: " + " ".join("%s=%d" % (k, v) for k, v in c.items()))
    print("-" * 78)
    for x in cases:
        print("  #%-3d 行%-6d %-6s 窗口%-5d %s" % (x["case"], x["line_no"], x["verdict"], x["window_lines"], x["why"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
