# -*- coding: utf-8 -*-
r"""pa_lifecycle.py —— 「停用 ／ 卸载」之二径 ＋ 复扫（反入侵之根 · 承 CEO 2268 §二 · 技术总监席 f202f89）。

⭐ 面（face）＝ 本机**已注册**之计划任务中，名以 \ClawsJoy 起者（前缀可 --prefix 覆）。
⭐ 口径（caliber）＝ schtasks /query /fo CSV /nh ⇒ 取首列「任务名」⇒ 以「前缀」筛（⛔ 猜）。
⭐ 二径：
   · 停用（disable）—— 逐条 schtasks /change /tn <名> /disable ⇒ **可回**（启用 复原）。
   · 卸载（uninstall）—— 逐条 schtasks /delete /tn <名> /f（可选 --env 并撤用户级键）。
⭐ 反控（必咬 · ⛔ 以「命令返 0」为足）：
   · 装后卸 ⇒ 复扫 必净（rc 0）∧ 有残余 ⇒ rc 2。
   · --self-test ⇒ 以**合成之名**（\ClawsJoy_SELFTEST_<pid>）真跑全链：造 ⇒ 扫见 ⇒ 干跑⛔动 ⇒ 停用 ⇒ Disabled ⇒ 启用 ⇒ Enabled ⇒ 卸载 ⇒ 复扫净。
⭐ 三禁：
   ⓐ 缺省干跑（唯印「将动何物」）· 唯 --go 方真动。
   ⓑ ⛔ 动 data/** ／ logs/** ／ 任何产品档（唯 schtasks 之 change ／ delete ＋ 可选 reg delete）。
   ⓒ 面空 ⇒ 报「无物」∧ rc 0（⛔ 崩）；⛔ 前缀之外之任务（一字 ⛔ 触）。

用法：
  python -X utf8 scripts/win_pa/pa_lifecycle.py                # 扫（只读）
  python -X utf8 scripts/win_pa/pa_lifecycle.py 停用            # 干跑
  python -X utf8 scripts/win_pa/pa_lifecycle.py 停用 --go        # 真停用（可 启用 复原）
  python -X utf8 scripts/win_pa/pa_lifecycle.py 启用 --go
  python -X utf8 scripts/win_pa/pa_lifecycle.py 卸载 --go        # 真卸载（删任务）
  python -X utf8 scripts/win_pa/pa_lifecycle.py 卸载 --go --env  # 并撤用户级键 PA_VAULT_DIR
  python -X utf8 scripts/win_pa/pa_lifecycle.py 复扫             # 只读 · 有残余 ⇒ rc 2
  python -X utf8 scripts/win_pa/pa_lifecycle.py --json
  python -X utf8 scripts/win_pa/pa_lifecycle.py --self-test
退出码：0 ＝ 成（含「无物」）｜ 2 ＝ 有败（改 ／ 删失败 ∨ 复扫有残余 ∨ 反控未过）｜ 3 ＝ 入口错
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BS = chr(92)
DEFAULT_PREFIX = BS + "ClawsJoy"
ENV_SCOPE = "HKCU" + BS + "Environment"
ENV_KEYS = ("PA_VAULT_DIR",)
VERSION = 1
CMDS = {"停用": "disable", "启用": "enable", "卸载": "delete"}
SUBCOMMANDS = ("扫", "停用", "启用", "卸载", "复扫")


def _run(args):
    u"""跑一条命令（只读 ∨ 动）⇒ (rc, 出)。⛔ 例外外溢（视作失败）。"""
    try:
        r = subprocess.run(args, capture_output=True)
    except Exception as e:
        return 1, u"⛔ %s" % type(e).__name__
    return r.returncode, (r.stdout or b"").decode("utf-8", "replace") + (r.stderr or b"").decode("utf-8", "replace")


def face(prefix=None):
    u"""面 ⇒ (rc, [任务名], 原出)。口径：schtasks /query /fo CSV /nh 之首列 ⇒ 以「前缀」筛。"""
    pfx = prefix or DEFAULT_PREFIX
    rc, out = _run(["schtasks", "/query", "/fo", "CSV", "/nh"])
    names = []
    if rc != 0:
        return rc, names, out
    q = chr(34)
    for ln in out.splitlines():
        s = ln.strip()
        if not s.startswith(q):
            continue
        parts = s.split(q)
        if len(parts) >= 2 and parts[1].startswith(pfx):
            names.append(parts[1])
    return 0, sorted(set(names)), out


def state(task):
    u"""任务之态 ⇒ 'Enabled' ／ 'Disabled' ／ None（只读 · 口径 = schtasks /query /tn <名> /fo LIST /v 之 Scheduled Task State）。"""
    rc, out = _run(["schtasks", "/query", "/tn", task, "/fo", "LIST", "/v"])
    if rc != 0:
        return None
    for ln in out.splitlines():
        if ln.strip().startswith("Scheduled Task State:"):
            return ln.split(":", 1)[1].strip()
    return None


def stamp2(path):
    u"""印之书法二形（一处出 · 承 PM 2205 §二）。"""
    b = open(path, "rb").read()
    return u"md5[:16] %s ／ sha16 %s" % (hashlib.md5(b).hexdigest()[:16], hashlib.sha256(b).hexdigest()[:16])


def head(names, pfx):
    u"""报头：面 ＋ 刻 ＋ 口径 ＋ 印（二形）。"""
    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")
    joined = ("\n").join(names).encode("utf-8")
    return [
        u"[pa_lifecycle] 刻 %s" % now,
        u"[pa_lifecycle] 面 %d 条（口径：schtasks /query /fo CSV /nh · 首列任务名 ⇒ 名以 %s 起）" % (len(names), pfx),
        u"[pa_lifecycle] 面之印 md5[:16] %s ／ sha16 %s"
        % (hashlib.md5(joined).hexdigest()[:16], hashlib.sha256(joined).hexdigest()[:16]),
        u"[pa_lifecycle] 本器之印（二形）%s" % stamp2(os.path.abspath(__file__)),
    ]


def act(tasks, cmd, go):
    u"""停用 ／ 启用 ／ 卸载 —— 逐条动（⛔ 及前缀之外）⇒ (rc, lines)。缺省干跑。"""
    if cmd not in CMDS:
        return 3, [u"[pa_lifecycle] ⛔ 未知之令：%s" % cmd]
    lines = []
    todo = []
    for t in tasks:
        st = state(t)
        done = (cmd == "停用" and st == "Disabled") or (cmd == "启用" and st == "Enabled")
        if done:
            lines.append(u"  %-44s 已如令（幂等 · ⛔ 动）" % t)
        else:
            todo.append(t)
    if not todo:
        lines.append(u"[pa_lifecycle] 无物可动（皆已如令）⇒ rc 0")
        return 0, lines
    lines.append(u"[pa_lifecycle] 将动 %d 件（令 ＝ %s ／ 干跑 ＝ %s）" % (len(todo), cmd, not go))
    if not go:
        for t in todo:
            lines.append(u"  [干跑] %s %s" % (cmd, t))
        lines.append(u"[pa_lifecycle] 干跑（⛔ 未动）—— --go 方真动")
        return 0, lines
    bad = 0
    for t in todo:
        if cmd == "卸载":
            rc, out = _run(["schtasks", "/delete", "/tn", t, "/f"])
        elif cmd == "停用":
            rc, out = _run(["schtasks", "/change", "/tn", t, "/disable"])
        else:
            rc, out = _run(["schtasks", "/change", "/tn", t, "/enable"])
        lines.append(u"  [%s] %-44s rc=%s" % (cmd, t, rc))
        if rc != 0:
            bad += 1
            lines.append(u"     %s" % out.strip().replace(u"\n", u" ")[:200])
    if bad:
        lines.append(u"[pa_lifecycle] ⛔ %d 件未成 ⇒ rc 2" % bad)
        return 2, lines
    lines.append(u"[pa_lifecycle] 皆成 ⇒ rc 0")
    return 0, lines


def verify(prefix=None):
    u"""复扫（只读）⇒ (rc, lines)：面空 ⇒ rc 0；有残余 ⇒ rc 2。"""
    rc, names, _ = face(prefix)
    if rc != 0:
        return 1, [u"[复扫] ⛔ schtasks 不可查（rc=%s）" % rc]
    lines = [u"[复扫] 面 %d 条（口径：名以 %s 起）" % (len(names), prefix or DEFAULT_PREFIX)]
    for n in names:
        lines.append(u"  残余 %s（态 %s）" % (n, state(n)))
    if names:
        lines.append(u"[复扫] ⛔ 有残余 ⇒ rc 2")
        return 2, lines
    lines.append(u"[复扫] 净 ⇒ rc 0")
    return 0, lines


def _report(fails):
    print(u"[self-test] %s" % (u"PASS（装后卸 ⇒ 复扫必净 ＋ 干跑⛔动 ＋ 停用≠删）" if not fails else u"FAIL"))
    for f in fails:
        print(u"  [FAIL] %s" % f)
    return 0 if not fails else 2


def self_test():
    r"""以合成之名真跑全链（⛔ 触真任务：前缀 ＝ \ClawsJoy_SELFTEST_<pid>）。"""
    fails = []
    t = DEFAULT_PREFIX + "_SELFTEST_" + str(os.getpid())
    rc, _, _ = face(t)
    if rc != 0:
        fails.append(u"面法不可查（schtasks rc=%s）" % rc)
        return _report(fails)
    rc, out = _run(["schtasks", "/create", "/tn", t, "/tr", "cmd /c exit 0",
                    "/sc", "once", "/st", "23:59", "/f"])
    if rc != 0:
        fails.append(u"反控未跑：⛔ 无权造合成任务（%s）" % out.strip().replace(u"\n", u" ")[:160])
        return _report(fails)
    try:
        if t not in face(t)[1]:
            fails.append(u"① 装后 ⇒ 扫 ⛔ 见（应见 %s）" % t)
        act([t], "卸载", False)
        if t not in face(t)[1]:
            fails.append(u"② 干跑竟删了（⛔ 干跑须 ⛔ 动）")
        act([t], "停用", True)
        if state(t) != "Disabled":
            fails.append(u"③ 停用后 state=%s（应 Disabled）" % state(t))
        if t not in face(t)[1]:
            fails.append(u"③b 停用竟删了（⛔ 停用 == 改 · ⛔ 删）")
        act([t], "启用", True)
        if state(t) != "Enabled":
            fails.append(u"④ 启用后 state=%s（应 Enabled）" % state(t))
        act([t], "卸载", True)
        if t in face(t)[1]:
            fails.append(u"⑤ 卸载后仍在册（⛔）")
        rc6, _ = verify(t)
        if rc6 != 0:
            fails.append(u"⑥ 复扫未净 rc=%s（装后卸 ⇒ 复扫必净）" % rc6)
    finally:
        _run(["schtasks", "/delete", "/tn", t, "/f"])
    return _report(fails)


def main(argv):
    a = list(argv)
    if "--help" in a or "-h" in a:
        print(__doc__)
        return 0
    if "--self-test" in a:
        return self_test()
    go = "--go" in a
    as_json = "--json" in a
    with_env = "--env" in a
    prefix = None
    if "--prefix" in a:
        i = a.index("--prefix")
        if i + 1 >= len(a):
            print(u"[pa_lifecycle] ⛔ --prefix 后须给值")
            return 3
        prefix = a[i + 1]
    cmd = "扫"
    for tok in a:
        if tok in SUBCOMMANDS:
            cmd = tok
            break
    pfx = prefix or DEFAULT_PREFIX
    rc, names, _raw = face(prefix)
    if rc != 0:
        print(u"[pa_lifecycle] ⛔ schtasks 不可查（rc=%s）" % rc)
        return 1
    lines = head(names, pfx)
    if cmd == "复扫":
        rc, l2 = verify(prefix)
        lines += l2
    elif cmd == "扫":
        for n in names:
            lines.append(u"  %-46s %s" % (n, state(n)))
        lines.append(u"[pa_lifecycle] 面 %d 条（只读 · ⛔ 动）" % len(names))
        rc = 0
    else:
        rc, l2 = act(names, cmd, go)
        lines += l2
        if go and cmd == "卸载" and with_env:
            for k in ENV_KEYS:
                rec, out = _run(["reg", "delete", ENV_SCOPE, "/v", k, "/f"])
                lines.append(u"  [卸载·键] %s rc=%s" % (k, rec))
    if as_json:
        print(json.dumps({"version": VERSION, "cmd": cmd, "go": go, "dry_run": not go,
                          "prefix": pfx, "n": len(names), "names": names,
                          "rc": rc, "lines": lines}, ensure_ascii=False, indent=2))
    else:
        for x in lines:
            print(x)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
