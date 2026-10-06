# -*- coding: utf-8 -*-
"""(乙′) Win-PA 卸载器 —— 唯动「注册之二物」（承 pm_1382 §二.2 ① · 三缺之首）。

注册之二物（本机一手核 · schtasks /query 皆 rc 0）：
  · 任务 ClawsJoy_PA_Boot        （ClawsJoy_PA_Boot.xml · 每 5 min 跑 boot_resume.py）
  · 任务 ClawsJoy_PA_Start_Once  （pa_nowindow.START_TASK · 起服之派）
  （名之首字符 ＝ chr(92) ＝ 任务树之根；⛔ 字面反斜杠 —— 同 pa_nowindow.py 之式）

三禁（逐字承 pm_1382 §二.2 ①）：
  ⓐ 缺省干跑：先印「将动何物」；唯 --go 方真删
  ⓑ 幂等：已在 ⇒ 删；不在 ⇒ 报「无物可卸」（rc 0 · ⛔ 崩）
  ⓒ ⛔ 动 data/**（唯 schtasks /delete 二任务；⛔ 触 data ／ logs ／ web ／ core ／ 任何产品档）
  ⓓ 反控：未注册 ⇒ 报「无物可卸」

用法：
  python -X utf8 scripts/win_pa/uninstall_win_pa.py            # 干跑（缺省）
  python -X utf8 scripts/win_pa/uninstall_win_pa.py --go       # 真删
  python -X utf8 scripts/win_pa/uninstall_win_pa.py --json
  python -X utf8 scripts/win_pa/uninstall_win_pa.py --self-test
退出码：0 ＝ 正常（含「无物可卸」）｜ 2 ＝ 有删失败 ｜ 3 ＝ 入口错
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

BS = chr(92)
TASK_BOOT = BS + "ClawsJoy_PA_Boot"
TASK_ONCE = BS + "ClawsJoy_PA_Start_Once"
REGISTERED = (TASK_BOOT, TASK_ONCE)
VERSION = 1


def _tasks():
    """待卸之任务名 —— env PA_UNINSTALL_TASKS（逗号分）覆盖 ⇒ 供自测（⛔ 常规用）。"""
    v = os.environ.get("PA_UNINSTALL_TASKS")
    if v:
        return tuple(x.strip() for x in v.split(",") if x.strip())
    return REGISTERED


def _is_registered(task):
    """schtasks /query（只读）—— ⛔ 例外外溢（schtasks 不在 ⇒ 视作「不在」）。"""
    try:
        r = subprocess.run(["schtasks", "/query", "/tn", task], capture_output=True)
    except Exception:
        return False
    return r.returncode == 0


def plan():
    return [{"item": "task", "name": t, "registered": _is_registered(t)} for t in _tasks()]


def render_and_maybe_delete(items, dry):
    """返回 (rc, lines)。⛔ 唯 schtasks /delete；⛔ 触任何档。"""
    lines = []
    to_del = [i for i in items if i["registered"]]
    lines.append("[uninstall] 将动：%d 件（注册之二物；余者无物可卸）" % len(to_del))
    for i in items:
        lines.append("  %-28s %s" % (i["name"], "在（将删）" if i["registered"] else "不在（无物可卸）"))
    lines.append("[uninstall] ⛔ 不动：data/ ／ logs/ ／ web/ ／ core/ ／ 任何产品档（唯 schtasks /delete 二任务）")
    if dry:
        lines.append("[uninstall] 干跑（⛔ 未删）—— --go 方真删")
        return 0, lines
    rc = 0
    for i in to_del:
        r = subprocess.run(["schtasks", "/delete", "/tn", i["name"], "/f"], capture_output=True)
        lines.append("  [del] %s -> rc=%s" % (i["name"], r.returncode))
        if r.returncode != 0:
            rc = 2
    left = [i["name"] for i in plan() if i["registered"]]
    lines.append("[uninstall] 留下：产品数据（data/ ／ logs/ 等 · ⛔ 本器 ⛔ 动）＋ 注册之二物之残余 %s"
                 % (left or "无（皆清）"))
    return rc, lines


def self_test():
    fails = []
    bogus = BS + "ClawsJoy_PA_SELFTEST_NOPE"
    if _is_registered(bogus):
        fails.append("反控 1：不存在之任务被判「在」")
    items = [{"item": "task", "name": bogus, "registered": _is_registered(bogus)}]
    rc, lines = render_and_maybe_delete(items, True)
    if rc != 0:
        fails.append("反控 2：干跑 rc=%s（应 0）" % rc)
    if not any("无物可卸" in x for x in lines):
        fails.append("反控 2：未报「无物可卸」")
    rc2, lines2 = render_and_maybe_delete(items, False)
    if rc2 != 0:
        fails.append("反控 3：对「不在」之任务 --go ⇒ rc=%s（应 0 · ⛔ 崩）" % rc2)
    if not any("留下" in x for x in lines2):
        fails.append("反控 3：未报「留下何物」")
    for n in REGISTERED:
        if "data" in n.lower():
            fails.append("反控 4：注册项含 data（⛔ 动 data/**）：%s" % n)
    src = open(__file__, "r", encoding="utf-8").read()
    if ("rm" + "tree") in src:
        fails.append("反控 5：源含删树调用（⛔）")
    print("[self-test] %s" % ("PASS（5 反控）" if not fails else "FAIL"))
    for f in fails:
        print("  [FAIL] %s" % f)
    return 0 if not fails else 2


def main(argv):
    args = list(argv)
    if "--help" in args or "-h" in args:
        print(__doc__)
        return 0
    if "--self-test" in args:
        return self_test()
    dry = "--go" not in args
    items = plan()
    rc, lines = render_and_maybe_delete(items, dry)
    if "--json" in args:
        print(json.dumps({"version": VERSION, "dry_run": dry, "rc": rc, "items": items,
                          "lines": lines}, ensure_ascii=False, indent=2))
    else:
        for x in lines:
            print(x)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
