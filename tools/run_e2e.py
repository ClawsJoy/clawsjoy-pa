# -*- coding: utf-8 -*-
r"""显式 e2e 入口 ＋ 隔离判据（DS 2026-09-21 裁②）。

为什么有本件
----------
`tests/unit/test_browser_hybrid_integration.py::test_baidu_hybrid_e2e` 是**三态**：
  不就绪 ⇒ skip（绿）｜就绪且无反爬 ⇒ pass ⇒ 撞门禁 `miss_skip`（红）｜反爬 ⇒ skip（绿）｜真缺陷 ⇒ fail（红）。
⇒ **件侧无解**（`flaky_watch` 只治 fail 侧）。DS 裁②：**移出默认可跑集**
（`pytest.ini` / `pyproject.toml` 的 `addopts = ... -m "not e2e"` ＋ 件内 `pytestmark = pytest.mark.e2e`），
另设**显式入口 ＋ 结果仍留痕**（反例：移出但不留痕 ⇒ 该件永久无人跑）。

本件补那两半：**显式入口**（命令行 `-m e2e` 覆盖 addopts 里的 `-m`）＋ **留痕**（JSON / JSONL）。
它**不改门**（`tools/check_test_baseline.py` 未动）—— 改门 ＝ 改判据面，须老板拍（见 `codex\方案_v9门条件态_v2`）。

用法
----
  python tools/run_e2e.py --verify          # 只跑隔离判据（5 格，不开浏览器）
  python tools/run_e2e.py --collect-only    # 只证选择面（不跑、不开浏览器）
  python tools/run_e2e.py                   # 先自证隔离判据，再真跑；结果落 data/test_baseline/
退出码：0 全过 ｜ 1 有 failed ｜ 2 判据不过或选择面为空（fail-loud，不冒充通过）｜ 其它 = pytest 中断码。
"""
import datetime
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "test_baseline")
LAST = os.path.join(OUT_DIR, "e2e_last_run.json")
HIST = os.path.join(OUT_DIR, "e2e_history.jsonl")
RAW = os.path.join(OUT_DIR, "e2e_raw_last.txt")
LEDGER = os.path.join(ROOT, "tests", "baseline", "skip_ledger.json")
MARK = "e2e"
EID = "tests/unit/test_browser_hybrid_integration.py::test_baidu_hybrid_e2e"
_SUM = re.compile(r"(\d+)/(\d+) tests collected \((\d+) deselected\)")
_NODE = re.compile(r"^[\w./\\-]+\.py::")


def _pytest(args, timeout=300):
    cmd = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider"] + args
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _sum(out):
    m = _SUM.search(out)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def _ids(out):
    return [l.strip() for l in out.splitlines() if _NODE.match(l.strip())]


def selected_ids(timeout=300):
    """显式入口的选择面（`-o addopts=` 只为拿到 -q 逐行 nodeid 格式；`-m e2e` 仍走命令行）。"""
    rc, out = _pytest(["-o", "addopts=", "-q", "-m", MARK, "--collect-only"], timeout=timeout)
    return rc, _ids(out), out


def _deselect(out):
    """从两种汇总式里取 (deselected, selected)：全库跑 「N/M tests collected (K deselected)」；
    点名件跑 「collected 1 item / 1 deselected / 0 selected」。取不到 ⇒ None（fail-loud，不猜）。"""
    m = re.search(r"(\d+) deselected / (\d+) selected", out)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = _SUM.search(out)
    if m:
        return int(m.group(3)), int(m.group(1))
    return None


def verify():
    """隔离判据 5 格。返回 (ok, cells)；cells = [(名, 过?, 读数)]。"""
    cells = []
    FILE = "tests/unit/test_browser_hybrid_integration.py"
    rc1, out1 = _pytest(["--collect-only", FILE])
    d1 = _deselect(out1)
    cells.append(("格1 默认集（真 config · 点名该件）不收它",
                  d1 == (1, 0), "rc=%s (deselected, selected)=%s" % (rc1, d1)))
    rc2, out2 = _pytest(["-m", MARK, "--collect-only"])
    s2 = _sum(out2)
    cells.append(("格2 显式 -m e2e 恰选中该件（命令行 -m 覆盖 addopts 的 -m）",
                  bool(s2) and s2[0] == 1 and "test_baidu_hybrid_e2e" in out2,
                  "rc=%s 汇总=%s" % (rc2, s2)))
    rc3, out3 = _pytest(["-o", "addopts=", "-q", "--collect-only"])
    cells.append(("格3 对照的对照：去掉 addopts 那半 ⇒ 该件回到默认集",
                  "::test_baidu_hybrid_e2e" in out3,
                  "rc=%s 含该件=%s" % (rc3, "::test_baidu_hybrid_e2e" in out3)))
    try:
        j = json.loads(io.open(LEDGER, encoding="utf-8").read())
        in_skips = any(e.get("id") == EID for e in j.get("skips", []))
        in_desel = any(e.get("id") == EID for e in j.get("deselected", []))
        cells.append(("格4 台账：不在 skips（否则 miss_skip 恒红）＋ 在 deselected（留痕不许消失）",
                      (not in_skips) and in_desel,
                      "in_skips=%s in_deselected=%s skips_n=%d" % (in_skips, in_desel, len(j.get("skips", [])))))
    except Exception as e:
        cells.append(("格4 台账校验", False, "读台账失败: %r" % (e,)))
    _rc5, out5 = _pytest(["-o", "addopts=", "-q", "-m", "no_such_marker_e2e_probe", "--collect-only"])
    n5 = len(_ids(out5))
    cells.append(("格5 空选择面 ⇒ 入口必须 fail-loud（不往下跑）", n5 == 0, "空标记选中 %d 条" % n5))
    ok = all(v for _n, v, _r in cells)
    print("[e2e-verify] 隔离判据：")
    for n, v, r in cells:
        print("  [%s] %s ｜ %s" % ("PASS" if v else "FAIL", n, r))
    print("[e2e-verify] 合计 %d 格 · FAIL=%d" % (len(cells), sum(0 if v else 1 for _n, v, _r in cells)))
    return ok, cells


def main():
    args = sys.argv[1:]
    ok, _cells = verify()
    if not ok:
        print("[e2e] **隔离判据不过 ⇒ 不跑**（fail-loud；不拿选择面当通过）")
        return 2
    rc_s, ids, out_s = selected_ids()
    print("[e2e] 选择面：%d 条" % len(ids))
    for i in ids:
        print("   -", i)
    if not ids:
        print("[e2e] **选择面为空 ⇒ 入口失效**（fail-loud，不冒充通过）")
        return 2
    if "--verify" in args or "--collect-only" in args:
        return 0
    rc, out = _pytest(["-m", MARK, "-v", "-rs", "--tb=short"], timeout=1800)
    try:
        os.makedirs(OUT_DIR, exist_ok=True)
        io.open(RAW, "w", encoding="utf-8", newline="\n").write(out)
    except Exception as e:
        print("[e2e] 原始输出留存失败: %r" % (e,))
    res = []
    for ln in out.splitlines():
        m = re.match(r"^(\S+\.py::\S+)\s+(PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS)", ln)
        if m:
            res.append({"id": m.group(1), "outcome": m.group(2)})
    skips = []
    for ln in out.splitlines():
        m2 = re.match(r"^SKIPPED \[\d+\] (\S+?):\d+: (.*)$", ln)
        if m2:
            skips.append({"where": m2.group(1), "reason": m2.group(2)})
    rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "pytest_rc": rc,
           "skip_reasons": skips,
           "marked": MARK, "selected": ids, "results": res,
           "counts": {k: sum(1 for r in res if r["outcome"] == k)
                      for k in ("PASSED", "FAILED", "SKIPPED", "ERROR", "XFAIL")}, "raw": RAW}
    try:
        os.makedirs(OUT_DIR, exist_ok=True)
        io.open(LAST, "w", encoding="utf-8", newline="\n").write(json.dumps(rec, ensure_ascii=False, indent=2) + "\n")
        with io.open(HIST, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print("[e2e] 留痕: %s（并追加 %s）" % (LAST, os.path.basename(HIST)))
    except Exception as e:
        print("[e2e] 留痕失败（**可见**，不静默）: %r" % (e,))
    print("[e2e] pytest rc=%d · counts=%s" % (rc, rec["counts"]))
    print("[e2e] 注: 本入口**不在**默认集内、门禁不收它；结果只进上述留痕，不进门禁台账。")
    return 0 if rc == 0 else (1 if rc == 1 else rc)


if __name__ == "__main__":
    sys.exit(main())