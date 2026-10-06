# -*- coding: utf-8 -*-
u"""(甲′) Win-PA 一键安装器 —— 净机「装得上」（承 pm_1384 §三.4 · M1 余件之四）。

五约（逐字承 pm_1384 §三.4 之判成）：
  ⓐ 干跑（缺省）：先印「将动何物」逐条 ＋ 前置闸逐条；唯 --go 方真立目录
  ⓑ 幂等：已在 ⇒ no-op；跑二遍 ⇒ 第二遍全 no-op（⛔ 重复动作）
  ⓒ ⛔ 动 data/** 之**文件**（唯立目录 ＋ 前置闸之「自建自删」探针 · 同 preflight_start 之式）
  ⓓ 反控：前置 ⛔ 足 ⇒ **⛔ 装** ∧ 逐条报因（⛔ 装成可用 —— 承产品三禁）
  ⓔ 系统动作（计划任务之注册）⛔ 缺省做 —— 须显式 --register-tasks（⛔ 提权／⛔ 默默改机）
  ⓕ 离线（承 pm_1386 §二.2）：--offline ⇒ 闸「离线包 wheel」＋ `pip install --no-index
     --find-links=<wheel>`（⛔ 现场拉网）；真装依赖须显式 --go --pip-install（⛔ 缺省动机）

前置闸（**显形** · 人话之因 ＋ 修之门；⛔ 静默过）：
  1. Python 版（>= 3.10 · 承 pyproject requires-python）
  2. 依赖（flask ／ yaml）—— 逐条 import（⛔ 只查清单）
  3. 端口（**真源** config/system/system_unified.yaml · 可绑）
  4. data\\ 可写（**真源** core.lib.config_helper.get_data_root()）
  5. 显存（nvidia-smi memory.total · 硬闸 >= 4096 MiB · 荐 >= 8192 MiB）
  6. ollama 三态（承 30b523c：未接 ／ 在·无权重 ／ 可用）
⚠ 前置闸③–⑥ 由 scripts/win_pa/preflight_start.py **一处出**（⛔ 本器另写一遍 —— 二源必漂）。

用法：
  python -X utf8 scripts\\win_pa\\install_win_pa.py                          # 干跑（缺省）
  python -X utf8 scripts\\win_pa\\install_win_pa.py --go                       # 真立目录
  python -X utf8 scripts\\win_pa\\install_win_pa.py --register-tasks --go       # 并注册二任务（须提权）
  python -X utf8 scripts\\win_pa\\install_win_pa.py --json
  python -X utf8 scripts\\win_pa\\install_win_pa.py --self-test
退出码：0 ＝ 正常（含干跑 ／ 幂等 all no-op）｜ 2 ＝ 前置不足 ∨ 立目录失败 ｜ 3 ＝ 入口错
"""
from __future__ import annotations

import importlib
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BS = chr(92)
VERSION = 1

#: ⭐ 唯**立目录**（⛔ 写文件）—— 皆相对 ROOT；幂等之的
DIRS = ("data", "data/tmp", "data/v9/pa", "logs")
#: ⭐ 内置知识库之根（pm_1442 §二.2「库根新立」）—— 即 `core.lib.paths._builtin_kb()`
#: 之 `get_data_root()/kb`（同本器 DIRS 之默认形 · `get_data_root()` 默认 ＝ `data`）。
KB_REL = "data/kb"
#: 计划任务（与卸载器同一物 · 二器共一真源字面）
TASK_BOOT = BS + "ClawsJoy_PA_Boot"
TASK_ONCE = BS + "ClawsJoy_PA_Start_Once"
TASKS = (TASK_BOOT, TASK_ONCE)
#: 依赖（逐条 import ⇒ 「可导入」≠「在清单里」）
#: 自测钩：env PA_INSTALL_FORCE_FAIL=<闸名子串> ⇒ 置该闸败（⛔ 常规用 · 唯为反控验齿）
DEPS = ("flask", "yaml")
PY_MIN = (3, 10)
VRAM_MIN_MIB = 4096          # 硬闸（低于 ⇒ ⛔ 本机模型路不可用）
VRAM_RECOMMEND_MIB = 8192    # 荐（承 pm_1382 §二.5：荐 >= 8 GB；唯 6 GB ⇒ 用小模型）


def kb_subdirs():
    u"""六约定子目录之**名** —— **一处定形**：`core.lib.note_kernel.SUBDIRS`
    （⛔ 本器另写一份字面 · 供暗漂）⇒ `(names, None)` ∨ `((), 因)`（**显因** · 承「缺则显因」）。
    """
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    try:
        from core.lib.note_kernel import SUBDIRS as _S
        return tuple(_S), None
    except Exception as e:
        return (), u"%s: %s" % (type(e).__name__, str(e)[:120])


_PF_ERR = None       # ⛔ ⛔ 静默：导入败之因须留（承「缺则显因」）


def _pf():
    u"""前置器（**一处出**）：preflight_start.py —— ⛔ 本器另写一遍其闸。"""
    global _PF_ERR
    try:
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        return importlib.import_module("preflight_start")
    except Exception as e:
        _PF_ERR = u"%s: %s" % (type(e).__name__, str(e)[:160])
        return None


_MC_ERR = None


def _mc():
    u"""离线包器（**一处出**）：make_client_bundle.py —— ⛔ 本器另写一遍「依之表」（二源必漂）。"""
    global _MC_ERR
    try:
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        return importlib.import_module("make_client_bundle")
    except Exception as e:
        _MC_ERR = u"%s: %s" % (type(e).__name__, str(e)[:160])
        return None


def install_deps(wheel_dir, offline):
    u"""⭐ 装依赖（**唯 `--go --pip-install` 方行** —— ⛔ 缺省动机 · 承五约 ⓔ 之式）。

    ⓕ 离线（承 pm_1386 §二.2）：`offline` ⇒ `--no-index --find-links=<wheel>` ⇒ **⛔ 现场拉网**。
    """
    cmd = [sys.executable, "-m", "pip", "install"]
    if offline:
        cmd += ["--no-index", "--find-links", wheel_dir]
    cmd += ["-r", os.path.join(ROOT, "requirements-runtime.txt")]
    print(u"[install] pip（%s）: %s" % (u"离线" if offline else u"**须网**", u" ".join(cmd)))
    return subprocess.run(cmd).returncode


def _vram():
    u"""显存（MiB）—— `nvidia-smi` 只读；⛔ 有 ⇒ (None, 人话之因)。"""
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=memory.total",
                            "--format=csv,noheader,nounits"],
                           capture_output=True, timeout=25)
    except Exception as e:
        return None, u"nvidia-smi 不可调（%s）｜修之门：装显卡驱动（或换算力机 · 裸机无 GPU 时本机模型不可用）" % type(e).__name__
    out = (r.stdout or b"").decode("utf-8", "replace")
    if r.returncode != 0:
        return None, u"nvidia-smi rc=%s（%s）｜修之门：装显卡驱动" % (r.returncode, out.strip()[:80])
    vals = [int(x) for x in out.replace("\r", "").split() if x.strip().isdigit()]
    if not vals:
        return None, u"nvidia-smi 无读数（%s）｜修之门：查驱动" % out.strip()[:80]
    return max(vals), u"nvidia-smi 报 %d MiB" % max(vals)


def _self_answering(port):
    u"""该端口是否**本器**在答（⛔ 判据 ＝ 服务之名 · ⛔ 只判「端口开」）。"""
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/" % port, timeout=3) as r:
            j = json.loads(r.read().decode("utf-8", "replace"))
        return j.get("service") == "ClawsJoy Gateway"
    except Exception:
        return False


def preflight_gates(offline=False, wheel_dir=None):
    u"""前置闸（逐条:**人话之因 ＋ 修之门** · ⛔ 只退 rc）—— 返回 [{name, ok, reason, note}]。"""
    g = []
    ok = sys.version_info >= PY_MIN
    g.append({"name": u"Python 版", "ok": ok,
              "reason": u"%d.%d.%d" % sys.version_info[:3],
              "note": u"" if ok else u"修之门：装 Python %d.%d+（python.org）" % PY_MIN})
    for m in DEPS:
        try:
            importlib.import_module(m)
            g.append({"name": u"依赖 %s" % m, "ok": True, "reason": u"可导入", "note": u""})
        except Exception as e:
            g.append({"name": u"依赖 %s" % m, "ok": False, "reason": u"%s: %s" % (type(e).__name__, str(e)[:80]),
                      "note": u"修之门：python -m pip install -r requirements.txt（或 pip install %s）" % m})
    _m = _pf()
    if _m is None:
        g.append({"name": u"前置器", "ok": False,
                  "reason": u"preflight_start.py 不可导入（%s）" % _PF_ERR,
                  "note": u"修之门：查 scripts/win_pa/preflight_start.py 是否在"})
    else:
        root = _m.resolve_root()
        try:
            port, psrc = _m.resolve_port(root)
            ok2, why, _x = _m.probe_port(port)
            if ok2:
                g.append({"name": u"端口 %d" % port, "ok": True, "reason": u"可绑", "note": u""})
            elif _self_answering(port):
                # ⭐ 幂等之要（承 pm_1384 §三.4 ⒝）：**本器已在跑** ⇒ 视为「已装」⇒ no-op（⛔ 判红）
                g.append({"name": u"端口 %d" % port, "ok": True, "reason": u"已有实例在答（ClawsJoy Gateway）",
                          "note": u"⇒ 视为**已装 · no-op**（⛔ 判红 —— 判红则二跑 ⛔ 幂等）"})
            else:
                g.append({"name": u"端口 %d" % port, "ok": False, "reason": why,
                          "note": u"⛔ 非本器（他一进程占）｜修之门：netstat -ano | findstr :%d" % port})
        except Exception as e:
            g.append({"name": u"端口", "ok": False, "reason": u"%s: %s" % (type(e).__name__, str(e)[:80]), "note": u""})
        try:
            ok3, why3, _x3 = _m.probe_writable(os.path.join(root, "data"))
            g.append({"name": u"data\\ 可写", "ok": bool(ok3), "reason": why3, "note": u"" if ok3 else u"修之门：给该目录写权（或改真源 get_data_root()）"})
        except Exception as e:
            g.append({"name": u"data\\ 可写", "ok": False, "reason": u"%s: %s" % (type(e).__name__, str(e)[:80]), "note": u""})
        try:
            ok4, why4, note4 = _m.probe_ollama()
            g.append({"name": u"ollama", "ok": bool(ok4), "reason": why4, "note": note4 or u""})
        except Exception as e:
            g.append({"name": u"ollama", "ok": False, "reason": u"%s: %s" % (type(e).__name__, str(e)[:80]), "note": u""})
    _v, _vr = _vram()
    _vok = (_v is not None) and (_v >= VRAM_MIN_MIB)
    _vnote = u""
    if _vok and _v < VRAM_RECOMMEND_MIB:
        _vnote = u"⚠ 荐 >= %d MiB（本机 %d MiB ⇒ 用 qwen2.5:7b-instruct-q4_0-gpu · num_ctx 8192）" % (VRAM_RECOMMEND_MIB, _v)
    if not _vok:
        _vnote = u"修之门：换机 ∨ 用远端算力（P2 · 未接）—— 硬闸 >= %d MiB" % VRAM_MIN_MIB
    g.append({"name": u"显存 >= %d MiB" % VRAM_MIN_MIB, "ok": bool(_vok), "reason": _vr, "note": _vnote})
    if offline:
        _b = _mc()
        if _b is None:
            g.append({"name": u"离线包 wheel", "ok": False,
                      "reason": u"离线包器不可用（%s）" % _MC_ERR,
                      "note": u"修之门：查 scripts/win_pa/make_client_bundle.py 是否在"})
        else:
            _ds = _b.required_dists(ROOT)
            _miss = _b.missing_wheels(wheel_dir or os.path.join(ROOT, "wheel"), _ds)
            g.append({"name": u"离线包 wheel", "ok": not _miss,
                      "reason": (u"缺 %d 个：%s" % (len(_miss), u"、".join(_miss[:6])) if _miss
                                 else u"全（%d 依）" % len(_ds)),
                      "note": (u"修之门：在有网之机跑 python -X utf8 scripts" + BS
                               + u"win_pa" + BS + u"make_client_bundle.py --go") if _miss else u""})
    # ⭐ pm_1442 §二.2（库根新立）：骨架之名 ← note 内核（**一处定形**）；⛔ 得 ⇒ 闸败（显因 ⇒ rc 2）
    _subs, _serr = kb_subdirs()
    if _serr is None:
        g.append({"name": u"知识库骨架", "ok": True,
                  "reason": u"六约定之名得自 note_kernel.SUBDIRS（%s）" % u"、".join(_subs), "note": u""})
    else:
        g.append({"name": u"知识库骨架", "ok": False,
                  "reason": u"note_kernel.SUBDIRS ⛔ 得（%s）" % _serr,
                  "note": u"修之门：查 core/lib/note_kernel.py 是否在"})
    # ⚠ 自测专用之钩（⛔ 常规用）：env PA_INSTALL_FORCE_FAIL=<闸名之子串> ⇒ 置该闸败 ⇒ 验「⛔ 足 ⇒ ⛔ 装」
    _f = os.environ.get("PA_INSTALL_FORCE_FAIL")
    if _f:
        for _g in g:
            if _f in _g["name"]:
                _g["ok"] = False
                _g["reason"] = u"⛔ 人为置败（PA_INSTALL_FORCE_FAIL · 自测用）"
                _g["note"] = u"修之门：演示"
                break
    return g


def _is_registered(task):
    u"""schtasks /query（只读）—— ⛔ 例外外溢（schtasks 不在 ⇒ 视作「不在」）。"""
    try:
        r = subprocess.run(["schtasks", "/query", "/tn", task], capture_output=True)
    except Exception:
        return False
    return r.returncode == 0


def dir_items():
    u"""立目录之逐项（含内置知识库之骨架 · 名自 note 内核 · pm_1442 §二.2）。"""
    subs, _err = kb_subdirs()
    rels = list(DIRS) + ([] if _err else ([KB_REL] + [KB_REL + "/" + n for n in subs]))
    out = []
    for rel in rels:
        _abs = os.path.join(ROOT, rel.replace("/", os.sep))
        it = {"item": "dir", "path": rel, "abs": _abs, "exists": os.path.isdir(_abs)}
        if rel == KB_REL:
            it["note"] = (u"内置知识库之骨架（note 内核之六约定 · pm_1442 §二.2）"
                          if not _err else (u"⛔ 子目录之名 ⛔ 得：%s" % _err))
        out.append(it)
    return out


def task_items():
    u"""二任务之式（与 `ClawsJoy_PA_Boot.xml` ／ `pa_nowindow.START_TASK` 同物 · ⛔ 另造）。"""
    _boot_cmd = u"%s -X utf8 %s" % (sys.executable, os.path.join(HERE, "boot_resume.py"))
    _once_cmd = u"%s -X utf8 %s start" % (sys.executable, os.path.join(HERE, "pa_nowindow.py"))
    return [
        {"item": "task", "name": TASK_BOOT, "registered": _is_registered(TASK_BOOT),
         "cmd": _boot_cmd, "sched": ["/sc", "minute", "/mo", "5"]},
        {"item": "task", "name": TASK_ONCE, "registered": _is_registered(TASK_ONCE),
         "cmd": _once_cmd, "sched": ["/sc", "once", "/st", "00:00"]},
    ]


def plan(offline=False, wheel_dir=None):
    return {"preflight": preflight_gates(offline, wheel_dir), "dirs": dir_items(), "tasks": task_items()}


def render_and_maybe_apply(p, dry, register_tasks=False):
    u"""返回 (rc, lines)。⛔ 唯 os.makedirs（⛔ 写任何文件 ／ ⛔ 删任何物）。"""
    lines = []
    bad = [i for i in p.get("preflight", []) if not i.get("ok")]
    for i in p.get("preflight", []):
        lines.append(u"  [%s] %-18s %s%s" % ("PASS" if i.get("ok") else "FAIL", i.get("name"),
                                              i.get("reason"),
                                              (u"  ｜ " + i["note"]) if i.get("note") else u""))
    if bad:
        lines.append(u"[install] ⛔ 前置不足 %d 项 ⇒ **⛔ 装**（⛔ 装成可用 —— 承产品三禁）· 修之门见上" % len(bad))
        return 2, lines
    todo = [d for d in p.get("dirs", []) if not d["exists"]]
    lines.append(u"[install] 将动：立目录 %d 件（已在 %d ⇒ no-op）" % (len(todo), len(p.get("dirs", [])) - len(todo)))
    for d in p.get("dirs", []):
        lines.append(u"  %-22s %s%s" % (
            d["path"], u"在（no-op）" if d["exists"] else u"缺（将立）",
            (u"  ｜ " + d["note"]) if d.get("note") else u""))
    lines.append(u"[install] ⛔ 不动：data/** 之**文件**（唯立目录）· ⛔ 改 ／ ⛔ 删任何产品档 · ⛔ 起停")
    if register_tasks and p.get("tasks"):
        for t in p["tasks"]:
            lines.append(u"  %-26s %s" % (t["name"], u"在（no-op）" if t["registered"] else u"不在（将注册）"))
    else:
        lines.append(u"[install] 计划任务：⛔ 本器 ⛔ 注册（**系统动作** ⇒ 须显式 --register-tasks；缺省 ⛔ 改机）")
    lines.append(u"[install] 组织版（可选）三键 —— 面之数由三键定（缺则面减 · ⛔ 静默）：① PA_ORG_FACES=1（功能级开关 · 默认关）② PA_WS_ROOT=〈工作区根〉 ③ PA_VAULT_DIR=〈知识库根〉 ⇒ 首启引导（GET /v9/pa/first_run · 键「面之源」）逐条显其「今」")
    if dry:
        lines.append(u"[install] 干跑（⛔ 未动）—— --go 方真立目录")
        return 0, lines
    rc = 0
    for d in todo:
        try:
            os.makedirs(d["abs"], exist_ok=True)
            lines.append(u"  [mkdir] %s -> ok" % d["path"])
        except Exception as e:
            lines.append(u"  [mkdir] %s -> 败（%s: %s）" % (d["path"], type(e).__name__, str(e)[:80]))
            rc = 2
    if register_tasks:
        for t in p.get("tasks", []):
            if t["registered"]:
                lines.append(u"  [task] %s -> 在（no-op）" % t["name"])
                continue
            _cmd = ["schtasks", "/create", "/tn", t["name"], "/tr", t["cmd"],
                    "/f"] + list(t["sched"])
            r = subprocess.run(_cmd, capture_output=True)
            lines.append(u"  [task] %s -> rc=%s" % (t["name"], r.returncode))
            if r.returncode != 0:
                rc = 2
    left = [d["path"] for d in dir_items() if not d["exists"]]
    lines.append(u"[install] 立毕：仍缺 %s ／ 后三步：① 起服 python -X utf8 scripts\\win_pa\\pa_nowindow.py start"
                 u" ② 首启引导（GET /v9/pa/first_run）③ 卸载 python -X utf8 scripts\\win_pa\\uninstall_win_pa.py --go"
                 % (left or u"无（皆立）"))
    return rc, lines


def self_test():
    u"""反控 5（⛔ 皆**离机**：以合成之 plan 喂之 · ⛔ 触真盘 ／ ⛔ 起停）。"""
    fails = []
    good = [{"name": u"闸", "ok": True, "reason": u"正", "note": u""}]
    badp = [{"name": u"闸", "ok": False, "reason": u"⛔ 未接：演示", "note": u"修之门：演示"}]
    dirs = [{"item": "dir", "path": u"___nope___", "abs": os.path.join(ROOT, "___nope___"), "exists": False}]
    # 反控 1：前置 ⛔ 足 ⇒ rc 2 ∧ 报因 ∧ ⛔ 装
    rc1, l1 = render_and_maybe_apply({"preflight": badp, "dirs": dirs, "tasks": []}, True)
    if rc1 != 2:
        fails.append(u"反控 1：前置不足 rc=%s（应 2）" % rc1)
    if not any(u"⛔ 装" in x for x in l1):
        fails.append(u"反控 1：未报「⛔ 装」")
    if any(u"mkdir" in x for x in l1):
        fails.append(u"反控 1：前置不足仍动盘")
    # 反控 2：干跑 ⇒ rc 0 ∧ 印「将动」∧ ⛔ 动盘
    rc2, l2 = render_and_maybe_apply({"preflight": good, "dirs": dirs, "tasks": []}, True)
    if rc2 != 0 or not any(u"将动" in x for x in l2):
        fails.append(u"反控 2：干跑 rc=%s" % rc2)
    if os.path.isdir(os.path.join(ROOT, "___nope___")):
        fails.append(u"反控 2：干跑竟立了目录")
    if not any(u"未动" in x for x in l2):
        fails.append(u"反控 2：未印「⛔ 未动」")
    # 反控 3：幂等 ⇒ 「已在」之目录 ⇒ no-op（⛔ 重复动作）
    dirs_in = [{"item": "dir", "path": u"data", "abs": os.path.join(ROOT, "data"), "exists": True}]
    _rc3, l3 = render_and_maybe_apply({"preflight": good, "dirs": dirs_in, "tasks": []}, True)
    if not any(u"no-op" in x and u"data" in x for x in l3):
        fails.append(u"反控 3：已在之目录未报 no-op")
    # 反控 4：唯目录（⛔ 文件写点）—— 源扫（唯读之 open 方可）
    import re as _re
    src = io.open(__file__, "r", encoding="utf-8").read()
    _opens = _re.findall(r"(?<![A-Za-z_])open\(([^)]*)\)", src)   # ⛔ 取 urlopen（其非文件写点）
    _bad = [o for o in _opens if (chr(39) + "r" + chr(39)) not in o and (chr(34) + "r" + chr(34)) not in o]
    if _bad:
        fails.append(u"反控 4：源含非读之 open（⛔ 动 data/** 之文件）：%s" % _bad)
    # 反控 4／5 之式：判**调用形**（⛔ 判「文中提到同名」—— ⛔ 则文档串自指 ⇒ 假红）
    _pick = len(_re.findall(r"(shutil\.rmtree|os\.remove|os\.unlink)\(", src)) + len(_re.findall(r"\.unlink\(", src))
    if _pick:
        fails.append(u"反控 4：源含删调用（⛔）：%d 处" % _pick)
    _kill = _re.findall(r"subprocess\.run\([^)]*pa_nowindow", src)
    if _kill:
        fails.append(u"反控 5：源含起服调用（⛔ 起停）")
    if _re.search(r"(subprocess\.run|Popen)\([^)]*(git\"|\"push)", src):
        fails.append(u"反控 5：源含平台动作（⛔ push）")
    print(u"[self-test] %s" % (u"PASS（5 反控）" if not fails else u"FAIL"))
    for f in fails:
        print(u"  [FAIL] %s" % f)
    return 0 if not fails else 2


def main(argv):
    args = list(argv)
    if "--help" in args or "-h" in args:
        print(__doc__)
        return 0
    if "--self-test" in args:
        return self_test()
    dry = "--go" not in args
    register_tasks = "--register-tasks" in args
    offline = "--offline" in args
    pip_install = "--pip-install" in args
    wheel_dir = os.path.join(ROOT, "wheel")
    for _i, _a in enumerate(args):
        if _a == "--wheel-dir" and _i + 1 < len(args):
            wheel_dir = args[_i + 1]
    if pip_install and "--json" in args:
        print(u"[install] \u26d4 --pip-install \u26d4 \u914d --json\uff08\u7eaf JSON \u987b\u4fdd\uff09")
        return 3
    # ⚠ `--json` 须**纯 JSON**：前置闸会 import core 之配置（其向 stdout 打 [CONFIG] 数行）
    #   ⇒ 缺省径照印；`--json` 径**收其杂记**（归 `杂记` 键 · ⛔ 弃 —— 承「照实」）
    _chatter = u""
    if "--json" in args:
        import contextlib as _cl
        import io as _io

        class _Sink(_io.StringIO):
            u"""收杂记之池 —— ⚠ 前置器于**导入期**行 `sys.stdout.reconfigure(...)` ⇒ 须**容忍**之
            （纯 StringIO 无此属性 ⇒ 导入即崩 ＝ 我一手逮之实）。"""

            def reconfigure(self, *a, **k):
                return None

        _buf = _Sink()
        with _cl.redirect_stdout(_buf):
            p = plan(offline, wheel_dir)
            rc, lines = render_and_maybe_apply(p, dry, register_tasks)
        _chatter = _buf.getvalue()
        print(json.dumps({"version": VERSION, "dry_run": dry, "register_tasks": register_tasks,
                          "rc": rc, "plan": p, "lines": lines, "杂记": _chatter},
                         ensure_ascii=False, indent=2))
    else:
        p = plan(offline, wheel_dir)
        rc, lines = render_and_maybe_apply(p, dry, register_tasks)
        for x in lines:
            print(x)
        if not offline:
            print(u"[install] \u26a0 \u672a --offline \u21d2 \u88c5\u4f9d\u8d56\u987b**\u7f51**"
                  u"\uff08\u26d4 \u6f14\u793a\u73b0\u573a\u62c9\u7f51 \u00b7 \u627f pm_1386 \u00a7\u4e8c.2 \u24d5\uff09")
    if rc == 0 and pip_install and "--go" in args:
        rc = install_deps(wheel_dir, offline)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
