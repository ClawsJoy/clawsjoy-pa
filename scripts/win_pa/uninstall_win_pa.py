# -*- coding: utf-8 -*-
"""(乙′) Win-PA 卸载器 —— 唯动「注册之二物」＋「装程所设之用户级键」
（承 pm_1382 §二.2 ① · pm_1500 §一.1 要4）。

注册之二物（本机一手核 · schtasks /query 皆 rc 0）：
  · 任务 ClawsJoy_PA_Boot        （ClawsJoy_PA_Boot.xml · 每 5 min 跑 boot_resume.py）
  · 任务 ClawsJoy_PA_Start_Once  （pa_nowindow.START_TASK · 起服之派）
  （名之首字符 ＝ chr(92) ＝ 任务树之根；⛔ 字面反斜杠 —— 同 pa_nowindow.py 之式）
  · 用户级键 PA_VAULT_DIR（装程 --vault-dir 所设 · 落 HKCU\\Environment）

三禁（逐字承 pm_1382 §二.2 ①）：
  ⓐ 缺省干跑：先印「将动何物」；唯 --go 方真删
  ⓑ 幂等：已在 ⇒ 删；不在 ⇒ 报「无物可卸」（rc 0 · ⛔ 崩）
  ⓒ ⛔ 动 data/**（唯 schtasks /delete 二任务 ＋ reg delete 用户键；⛔ 触 data ／ logs ／ web ／ core ／ 任何产品档）
  ⓓ 反控：未注册 ／ 未设 ⇒ 报「无物可卸」

⚠ 界（该键之撤 · 承 pm_1500 §一.1 要4）：
  · 唯用户级（HKCU\\Environment）· ⛔ 触系统级（HKLM）· ⛔ 触 Process
  · 该键若「他因所设」⇒ 本器亦删（reg delete 无名下之别）
    ⇒ 故唯 --unset-vault 显式开（⛔ 缺省带上 —— 免误删主人自设之库根）

用法：
  python -X utf8 scripts/win_pa/uninstall_win_pa.py            # 干跑（缺省 · 唯任务）
  python -X utf8 scripts/win_pa/uninstall_win_pa.py --unset-vault   # 干跑（并含该键）
  python -X utf8 scripts/win_pa/uninstall_win_pa.py --go       # 真删（任务）
  python -X utf8 scripts/win_pa/uninstall_win_pa.py --unset-vault --go  # 真删（任务 ＋ 该键）
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
VAULT_ENV = "PA_VAULT_DIR"          # 装程乙所设之用户级键（本器之回退面 · pm_1500 §一.1 要4）
ENV_KEYS = (VAULT_ENV,)
ENV_SCOPE = "HKCU" + BS + "Environment"
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


def _env_keys():
    """待卸之用户级键 —— env PA_UNINSTALL_ENV_KEYS（逗号分）覆盖 ⇒ 供自测（⛔ 常规用）。"""
    v = os.environ.get("PA_UNINSTALL_ENV_KEYS")
    if v:
        return tuple(x.strip() for x in v.split(",") if x.strip())
    return ENV_KEYS


def _env_present(name):
    """`HKCU\\Environment\\<name>` 是否在（`reg query` · 只读）。⛔ 例外外溢。"""
    try:
        r = subprocess.run(["reg", "query", ENV_SCOPE, "/v", name], capture_output=True)
    except Exception:
        return False
    return r.returncode == 0


def _env_delete(name):
    """删用户级 `<name>`（`reg delete ... /f`）⇒ rc。⛔ 触系统级（HKLM）。"""
    r = subprocess.run(["reg", "delete", ENV_SCOPE, "/v", name, "/f"], capture_output=True)
    return r.returncode


def _live(i):
    """该项「在否」—— task 看 registered ／ env 看 present（一处定形）。"""
    return i["registered"] if i["item"] == "task" else i["present"]


def plan(include_env=False):
    items = [{"item": "task", "name": t, "registered": _is_registered(t)} for t in _tasks()]
    if include_env:
        for k in _env_keys():
            items.append({"item": "env", "name": k, "present": _env_present(k)})
    return items


def render_and_maybe_delete(items, dry):
    """返回 (rc, lines)。⛔ 唯 schtasks /delete ＋ reg delete（用户键）；⛔ 触任何档。"""
    lines = []
    to_del = [i for i in items if _live(i)]
    lines.append("[uninstall] 将动：%d 件（任务 ／ 用户键；余者无物可卸）" % len(to_del))
    for i in items:
        lines.append("  %-28s %s" % (i["name"], "在（将删）" if _live(i) else "不在（无物可卸）"))
    lines.append("[uninstall] ⛔ 不动：data/ ／ logs/ ／ web/ ／ core/ ／ 任何产品档"
                 "（唯 schtasks /delete 任务 ＋ reg delete 用户键）")
    if dry:
        lines.append("[uninstall] 干跑（⛔ 未删）—— --go 方真删")
        return 0, lines
    rc = 0
    for i in to_del:
        if i["item"] == "task":
            r = subprocess.run(["schtasks", "/delete", "/tn", i["name"], "/f"], capture_output=True)
            _rc = r.returncode
        else:
            _rc = _env_delete(i["name"])
        lines.append("  [del] %s -> rc=%s" % (i["name"], _rc))
        if _rc != 0:
            rc = 2
    _has_env = any(i["item"] == "env" for i in items)
    left = [i["name"] for i in plan(_has_env) if _live(i)]
    lines.append("[uninstall] 留下：产品数据（data/ ／ logs/ 等 · ⛔ 本器 ⛔ 动）＋ 注册项之残余 %s"
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
    # 反控 6（pm_1500 §一.1 要4）：用户级键之回退面（唯读之查 · ⛔ 触真键）
    _bogus = "PA_UNINSTALL_SELFTEST_NOPE"
    if _env_present(_bogus):
        fails.append("反控 6：不存在之键被判「在」")
    _ie = [{"item": "env", "name": _bogus, "present": _env_present(_bogus)}]
    _rce, _le = render_and_maybe_delete(_ie, True)
    if _rce != 0 or not any("无物可卸" in x for x in _le):
        fails.append("反控 6：未设之键干跑 rc=%s ／ 未报「无物可卸」" % _rce)
    _rce2, _ = render_and_maybe_delete(_ie, False)
    if _rce2 != 0:
        fails.append("反控 6：未设之键 --go ⇒ rc=%s（应 0 · ⛔ 崩）" % _rce2)
    # 反控 7：唯用户级（域须绑定 ENV_SCOPE=HKCU\Environment）＋ ⛔ 缺省带上该键
    import re as _re
    if 'ENV_SCOPE = "HKCU" + BS + "Environment"' not in src:
        fails.append("反控 7：用户级之域非 HKCU" + BS + "Environment")
    _regcalls = _re.findall(r'subprocess\.run\(\["reg",\s*"(?:query|delete)",\s*ENV_SCOPE', src)
    if len(_regcalls) != 2:
        fails.append("反控 7：reg 之调未皆以 ENV_SCOPE 为域（得 %d 处 · 应 2）" % len(_regcalls))
    _hklm_a = "HKEY_" + "LOCAL_" + "MACHINE"     # 拆写：免「自查之字面自指」之假红
    _hklm_b = chr(34) + "HK" + "LM"
    if (_hklm_a in src) or (_hklm_b in src):
        fails.append("反控 7：源含系统级（HKLM）之域（⛔）")
    _ln = render_and_maybe_delete([{"item": "env", "name": _bogus, "present": True}], True)[1]
    if not any(_bogus in x and "在（将删）" in x for x in _ln):
        fails.append("反控 7：键项未入「将动」之列")
    if not any("将动：1 件" in x for x in _ln):
        fails.append("反控 7：键项未计入「将动」之数")
    if [i for i in plan() if i["item"] == "env"]:
        fails.append("反控 7：缺省即带该键（应唯 --unset-vault 方带）")
    print("[self-test] %s" % ("PASS（7 反控）" if not fails else "FAIL"))
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
    include_env = "--unset-vault" in args
    items = plan(include_env)
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
