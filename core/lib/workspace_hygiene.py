# -*- coding: utf-8 -*-
u"""workspace_hygiene.py —— **仓洁之阈**（承 pm_1811 §一.2⒝ · TD f202f89）。

由（一手 · 承 pm_1767 ／ pm_1779 ／ pm_1810）：
  Paseo 之 `workspace-git-service` **每轮**数「未入仓 ＋ 被忽略」之件
  （`git ls-files -o -i --directory --exclude-standard`）⇒ 其**单次耗时随件数而增**：
    ① `186,980` 件 ⇒ **超 `30 s`**（`git` 服务超时 ⇒ `eventLoopDelay p50 19,562 ms` ⇒ daemon 瘫）；
    ② `1,617` 件 ⇒ `941 ms`；
    ③ `1,240` 件 ⇒ `450 ms`（我 `1810` 一手之七取：p50 `450 ms` ／ p95 `464 ms`）。
  ⚠ **⛔ 频** —— 那 `30 s` 是 **`DEFAULT_TIMEOUT_MS`（逐命令超时）**，⛔ 周期（承 pm_1811 §二 之认误）。
⇒ 故设**一条可查之阈**：逾 ⇒ **告警入日志**（`<根>/logs/workspace_hygiene.log`）并**报 PM**。

三条口径（承 pm_1811 §一.2⒝）：
  ⒈ **唯读**：⛔ 删 ／ ⛔ 移（清弃树归人 · ⛔ 本器）；
  ⒉ **⛔ 以「0」充「干净」**：探败 ／ 超时 ⇒ 记「未知」（`count=None` ∧ `why` 显因）——
     承「**空 ⛔ 混 缺**」：量得 `0` ⇔ 未量得，⛔ 同；
  ⒊ **一处定形**：阈唯在 `THRESHOLD_UNTRACKED_IGNORED` 一处（⛔ 逐处硬编）。

用法：
  python -X utf8 -B -m core.lib.workspace_hygiene [--root <仓根>] [--threshold N] [--json]
  退码：0 ＝ 未逾 ｜ **2 ＝ 逾**（须清弃树）｜ 4 ＝ **未量得**（器病 ⇒ ⛔ 当「干净」）｜ 3 ＝ 用法错。
"""
import io
import os
import sys
import time

from core.lib import _proc as _proc_xh   # ⭐ pm_1791 §三.2：窗隐唯「_proc」出口（core/lib/** 之令）

#: ⭐⭐ **阈（一条可查 · 一处定形）** —— pm_1811 §一.2⒝ 之「建议阈 `5,000` 件」。
#:   由：`192,000` 件级 ⇒ 逾 `30 s`（瘫）⇒ 阈须**远早于**其处 ⇒ 取 `5,000`
#:   （此刻之常值约 `1,240` ⇒ 阈给 `4×` 之余量 · ⛔ 噪）。
THRESHOLD_UNTRACKED_IGNORED = 5000

#: 数件之令（**逐字** ＝ daemon 超时那句所报者 ⇒ 同源可比）。
GIT_COUNT_ARGV = ["git", "ls-files", "-o", "-i", "--directory", "--exclude-standard"]

#: 告警之件（相于根）。
LOG_REL = ("logs", "workspace_hygiene.log")


def repo_root():
    u"""仓根（本件之径反推 · ⛔ 依赖 `cwd` —— 那会随调用者漂）。"""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def count(root=None, timeout=20.0):
    u"""数「未入仓 ＋ 被忽略」之件（**唯读** · ⛔ 出网 ／ ⛔ 改盘）。

    ⚠ 超时 `20 s` **恰为对治**：彼超时 `30 s` ⇒ 本器须**先于**其报（⛔ 与 daemon 一起挂）。
    返 `{"count": int|None, "seconds": float, "rc": int|None, "why": str, "root": str}`——
    `count=None` ⇒ **未量得**（⛔ 报 `0`）。

    ⚠ **径之传法**：`cwd=<根>`（⛔ `ls-files … -C` —— 被判「unknown switch `C`」⇒
     `rc 129` ⇒ 空果一条 · 器病）。一件两处之病，我一手撞见并改（承「器病 ≠ 面病」）。
    """
    root = root or repo_root()
    t0 = time.time()
    out = {"root": str(root), "count": None, "seconds": 0.0, "rc": None, "why": u""}
    try:
        r = _proc_xh.run_hidden(list(GIT_COUNT_ARGV), cwd=str(root),
                                capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=timeout)
    except Exception as e:                                    # noqa: BLE001 — 照实报因（含 TimeoutExpired）
        out["seconds"] = round(time.time() - t0, 3)
        out["why"] = u"%s: %s" % (type(e).__name__, str(e)[:200])
        return out
    out["seconds"] = round(time.time() - t0, 3)
    out["rc"] = int(r.returncode)
    if r.returncode != 0:
        out["why"] = u"git rc=%s：%s" % (r.returncode, (r.stderr or u"")[:200])
        return out
    out["count"] = len([_l for _l in (r.stdout or u"").splitlines() if _l.strip()])
    return out


def check(root=None, threshold=None, timeout=20.0):
    u"""量 ＋ 判（⛔ 落盘 · ⛔ 打印）。返 `count(...)` 之诸键 ＋
    `{"threshold", "exceeded", "verdict", "why_verdict"}`——
    `verdict ∈ {"ok", "over", "unknown"}`（⭐ 三态：⛔ 以 `ok` 充 `unknown`）。"""
    th = int(threshold if threshold is not None else THRESHOLD_UNTRACKED_IGNORED)
    d = count(root, timeout=timeout)
    d["threshold"] = th
    if d["count"] is None:
        d["exceeded"] = False                                  # ⚠ ⛔ 「未逾」之证 ⇒ verdict 另书
        d["verdict"] = "unknown"
        d["why_verdict"] = u"未量得（%s）⇒ ⛔ 判「干净」（承「空 ⛔ 混 缺」）" % (d["why"] or u"无因")
    elif d["count"] > th:
        d["exceeded"] = True
        d["verdict"] = "over"
        d["why_verdict"] = u"逾阈：%d > %d" % (d["count"], th)
    else:
        d["exceeded"] = False
        d["verdict"] = "ok"
        d["why_verdict"] = u"未逾：%d ≤ %d" % (d["count"], th)
    return d


def log_path(root=None):
    return os.path.join(root or repo_root(), *LOG_REL)


def warn_if_exceeded(root=None, threshold=None, timeout=20.0, log=None):
    u"""逾 ⇒ **告警入日志**（一处 · 追加）＋ 返 `check()` 之果。

    ⚠ `unknown`（未量得）⇒ **⛔ 静默**（⛔ 以「告警」充「探败」—— 承「凡败须显」：
    其因在 `why` ／ CLI 之退码 `4`）。
    """
    root = root or repo_root()
    d = check(root, threshold, timeout=timeout)
    if d.get("verdict") != "over":
        return d
    d["log"] = None
    lp = log or log_path(root)
    try:
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        line = (u"%s 逾阈 件=%d 阈=%d 耗=%.3fs 根=%s 令=%s\n"
                % (time.strftime("%Y-%m-%dT%H:%M:%S"), d["count"], d["threshold"],
                   d["seconds"], root, u" ".join(GIT_COUNT_ARGV)))
        with io.open(lp, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(line)
        d["log"] = lp
    except OSError as e:                                      # ⚠ 落不成 ⇒ 显报（⛔ 静默）
        d["why_log"] = u"%s: %s" % (type(e).__name__, e)
    return d


def _main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    root = None
    th = None
    want_json = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--root" and i + 1 < len(argv):
            root = argv[i + 1]; i += 2; continue
        if a == "--threshold" and i + 1 < len(argv):
            try:
                th = int(argv[i + 1])
            except ValueError:
                sys.stderr.write(u"[用法错] --threshold 须为整数\n"); return 3
            i += 2; continue
        if a == "--json":
            want_json = True; i += 1; continue
        sys.stderr.write(u"[用法错] 未知之参：%s\n" % a); return 3
    d = warn_if_exceeded(root, th)
    if want_json:
        import json as _json
        sys.stdout.write(_json.dumps(d, ensure_ascii=False) + u"\n")
    else:
        sys.stdout.write(u"[仓洁] 件=%s 阈=%s 耗=%.3fs 判=%s ／ %s\n"
                         % (d["count"], d["threshold"], d["seconds"], d["verdict"], d["why_verdict"]))
        if d.get("log"):
            sys.stdout.write(u"[仓洁] 告警已入日志：%s\n" % d["log"])
        elif d.get("why_log"):
            sys.stdout.write(u"[仓洁] ⚠ 日志 ⛔ 成：%s\n" % d["why_log"])
    if d["verdict"] == "over":
        return 2
    if d["verdict"] == "unknown":
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(_main())
