# -*- coding: utf-8 -*-
u"""本机体检（只读 · 一阶段七面）—— 承 pm_1750 §二 ／ pm_1751 §一–§四 ／ pm_1753 §一–§二。

铁律（不可越 · 令 pm_1750 §四 ／ pm_1753 §二）：
  * 唯读 —— ⛔ 写盘 ／ ⛔ 改注册表（`winreg` 唯 `KEY_READ`）／ ⛔ 起停服务 ／ ⛔ 提权静默
    （须管理员之读 ⇒ 该条 `结论 = unknown` ＋ `needs_admin = True` ＋ `去处 = guide`）。
  * ⛔ 出机 —— 全程本机（⛔ 端内出站请求）。
  * 内生之器 —— 本仓 runtime ＋ 标准库 ＋ 既有 `psutil` ＋ **定字面**之系统读
    （⛔ 引第三方 agent ／ ⛔ 下二进制 ／ ⛔ 拼用户输入入命令）。
  * 有界 —— `SCAN_BUDGET_S` ／ `PANEL_BUDGET_S` ／ `WALK_MAX_DEPTH` ／ `WALK_MAX_FILES` ／ `SYS_TTL_S`。
  * 五件套 —— 每项 `人话 ＋ 读数 ＋ 源 ＋ 结论 ＋ 去处`（＋ `needs_admin`）；每面一句 `verdict_text`
    （⛔ 空 —— 「看不到」亦须一句人话）。
  * 清之险唯三等 —— `未验` ／ `须授权` ／ `建议清`（唯二阶段演练后方书）⇒ ⛔ 出「安全」之辞（pm_1753 §二.1）。
  * 每面附 `text`（纯文本之渲染 · 唯前端一选一拷之便 · ⛔ 写盘 —— pm_1753 §二.3）。

一阶段之四证（⛔ 写盘 ／ ⛔ 改注册表 ／ ⛔ 起停服务 ／ ⛔ 提权静默）见 `tests/unit/test_pa_sys_1751.py`。
本器唯**读**；一切「动作」（清 ／ 打开某页）＝ 二阶段之授权之约（⛔ 本件）。
"""
from __future__ import annotations

import os
import platform
import string
import sys
import time

from core.pa import _proc

try:                                    # psutil 已随仓（承 core/lib/hardware_probe.py 之既有用法）
    import psutil
except Exception:                       # pragma: no cover —— 缺 ⇒ 各面照实降级为 unknown
    psutil = None

# ---- 有界（一处定形 · pm_1751 §四.4） ------------------------------------
SCAN_BUDGET_S = 6.0        # 一次 snapshot 之总窗
PANEL_BUDGET_S = 2.5       # 单面之窗
PS_TIMEOUT_S = 1.8         # 单条 powershell 之窗
WALK_MAX_DEPTH = 4         # 递归之深
WALK_MAX_FILES = 20000     # 递归之件
SYS_TTL_S = 300            # 缓存之 TTL

PANELS = ("disk", "disk_c", "windows", "startup", "perf", "net", "guard")
TITLES = {"disk": u"磁盘", "disk_c": u"C 盘之占用大项", "windows": u"Windows 与更新",
          "startup": u"启动项", "perf": u"内存与 CPU", "net": u"网络",
          "guard": u"防护（只报不杀）"}
SOURCE_NOTE = u"psutil ＋ winreg（唯读）＋ 定字面之系统读（唯读）"
_FW_SRC = u"winreg:HKLM/.../FirewallPolicy（域／专用／公用 · 唯读）"

OUR_DIR = u"ClawsJoyPA"                  # 我司之装位（点名识别）
OUR_PREFIX = u"clawsjoy"                 # 我司物之小写前缀
TEMP_PREFIXES = (u"clawsjoy", u"pa_")

#: 「清之险」唯三等 ⇒ ⛔ 「安全」之辞（pm_1753 §二.1）
RISK_UNVERIFIED = u"未验 —— 我们尚未真跑过清它"
RISK_ADMIN = u"须授权 —— 须管理员方可动"
RISK_SUGGEST = u"已试清（唯二阶段演练后方书）"
CAN_CLEAN_P1 = u"待二阶段"

_SETTINGS_STORAGE = "ms-settings:storagesense"
_SETTINGS_WU = "ms-settings:windowsupdate"
_SETTINGS_SECURITY = "windowsdefender://"
_SETTINGS_STARTUP = "ms-settings:startupapps"


# ============================== 小件 ==============================
def _stamp():
    return time.strftime(u"%Y-%m-%dT%H:%M:%S%z")


def _human(n):
    u"""字节 ⇒ 人话（⛔ 修饰 ⇒ 唯量纲之一处定形）。"""
    try:
        v = float(n)
    except Exception:
        return u"—"
    for unit, k in ((u"TB", 2.0 ** 40), (u"GB", 2.0 ** 30), (u"MB", 2.0 ** 20), (u"KB", 2.0 ** 10)):
        if v >= k:
            return u"%.1f %s" % (v / k, unit)
    return u"%d B" % int(v)


def _guide(label, target):
    return {"kind": "guide", "label": label, "target": target}


def _none():
    return {"kind": "none", "label": u"", "target": u""}


def _item(iid, name, value, src, verdict, action=None, needs_admin=False, risk=None):
    u"""五件套之一项 —— **一处定形**（⛔ 各面自造形）。"""
    it = {"id": iid, "人话": name, "读数": value, "源": src,
          "结论": verdict, "去处": action if action is not None else _none(),
          "needs_admin": bool(needs_admin)}
    if risk is not None:
        it["清之险"] = risk
    return it


def _unknown(iid, name, src, why, action=None, admin=True):
    u"""取不得之正解 —— `unknown` ＋ 照实之因 ＋ 人话之去处（pm_1753 §二.2）。"""
    return _item(iid, name, u"取不得（%s）" % why, src, "unknown",
                 action if action is not None else _none(), needs_admin=admin)


def _run(cmd, timeout):
    u"""唯读调起（窗隐 · 经 `core/pa/_proc` 之唯一出口）⇒ `(rc, text)`。⛔ 例外外溢。"""
    try:
        r = _proc.run_hidden(cmd, capture_output=True, timeout=max(0.2, float(timeout)))
    except Exception:
        return None, u""
    try:
        return r.returncode, (r.stdout or b"").decode("utf-8", "replace")
    except Exception:
        return None, u""


def _ps_json(script, timeout=PS_TIMEOUT_S):
    u"""跑一条**定字面**之 powershell ⇒ 解其 JSON。失败 ⇒ `(None, 因)`（⛔ 抛）。"""
    if os.name != "nt":
        return None, u"非 Windows（%s）" % os.name
    rc, txt = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], timeout)
    if rc is None:
        return None, u"超窗 %.1f s" % timeout
    if rc != 0:
        return None, u"rc=%s" % rc
    t = (txt or u"").strip()
    if not t:
        return None, u"空答"
    try:
        import json as _json
        return _json.loads(t), u""
    except Exception as e:
        return None, u"答非 JSON（%s）" % type(e).__name__


def _ps_rows(obj):
    u"""`ConvertTo-Json` 之单件 ∨ 数组 ⇒ 皆归为 `list[dict]`。"""
    if obj is None:
        return []
    if isinstance(obj, dict):
        return [obj]
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    return []

def _ps_budget(deadline, want):
    u"""本面之窗（⛔ 越窗 · 承有界之约）⇒ 与 `PS_TIMEOUT_S` 取小。"""
    left = float(deadline) - time.monotonic() - 0.15
    if left < 0.3:
        left = 0.3
    return min(float(want), float(PS_TIMEOUT_S), left)


def _firewall_state():
    u"""防火墙三面之态 —— **唯读注册表**（⛔ 写 · `KEY_READ` · 快且不随语言变）。"""
    try:
        import winreg
    except Exception as e:
        return [], u"无 winreg（%s）" % type(e).__name__
    base = r"SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy"
    out = []
    for sub, label in ((u"DomainProfile", u"域"), (u"StandardProfile", u"专用"),
                       (u"PublicProfile", u"公用")):
        v, why = _reg_value(winreg.HKEY_LOCAL_MACHINE, base + u"\\" + sub, u"EnableFirewall")
        if v is None and why not in (u"未设",):
            return [], why
        out.append((label, bool(v)))
    return out, u""


def _reg_enum(hive, path):
    u"""唯读枚举 `(名, 值)`（`KEY_READ` · ⛔ 写）⇒ `(rows, 因)`。"""
    try:
        import winreg
    except Exception as e:
        return [], u"无 winreg（%s）" % type(e).__name__
    rows = []
    try:
        with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as k:
            i = 0
            while True:
                try:
                    n, v, _t = winreg.EnumValue(k, i)
                except OSError:
                    break
                rows.append((str(n), str(v)))
                i += 1
                if i > 200:                      # 有界（⛔ 无限）
                    break
    except FileNotFoundError:
        return [], u"（本机无此键）"
    except Exception as e:
        return [], u"取不得（%s）" % type(e).__name__
    return rows, u""


def _reg_value(hive, path, name):
    u"""唯读取一名之值（`KEY_READ`）⇒ `(值 ∨ None, 因)`。"""
    try:
        import winreg
    except Exception as e:
        return None, u"无 winreg（%s）" % type(e).__name__
    try:
        with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as k:
            v, _t = winreg.QueryValueEx(k, name)
            return v, u""
    except FileNotFoundError:
        return None, u"未设"
    except Exception as e:
        return None, u"取不得（%s）" % type(e).__name__


def _dir_size(path, deadline):
    u"""**唯量尺**（⛔ 写 ／ ⛔ 删）⇒ `(bytes, files, truncated)`。深与件皆有界。"""
    total = 0
    files = 0
    trunc = False
    stack = [(path, 0)]
    while stack:
        if time.monotonic() > deadline:
            trunc = True
            break
        p, d = stack.pop()
        try:
            it = os.scandir(p)
        except Exception:
            continue
        with it:
            for e in it:
                if files >= WALK_MAX_FILES:
                    trunc = True
                    break
                try:
                    if e.is_dir(follow_symlinks=False):
                        if d + 1 <= WALK_MAX_DEPTH:
                            stack.append((e.path, d + 1))
                        else:
                            trunc = True
                    elif e.is_file(follow_symlinks=False):
                        total += e.stat(follow_symlinks=False).st_size
                        files += 1
                except Exception:
                    pass
    return total, files, trunc


def _drives():
    if os.name != "nt":
        return [u"/"]
    out = []
    for ch in string.ascii_uppercase:
        d = u"%s:\\" % ch
        try:
            if os.path.exists(d):
                out.append(d)
        except Exception:
            pass
    return out


def _verdict_free(ratio):
    if ratio <= 0.05:
        return "crit"
    if ratio <= 0.10:
        return "warn"
    return "ok"


_RANK = {"ok": 0, "info": 1, "unknown": 2, "warn": 3, "crit": 4}


def _worst(vs):
    best = "ok"
    for v in vs:
        if v is None:
            continue
        if _RANK.get(v, 1) > _RANK.get(best, 0):
            best = v
    return best


def _state_of(items):
    u"""`ok` ／ `partial` ／ `unavailable` —— **部分取不得 ⇒ partial**（⛔ 整面报 ok ＝ 假绿）。"""
    if not items:
        return "unavailable"
    unk = sum(1 for i in items if i.get("结论") == "unknown")
    if unk == 0:
        return "ok"
    if unk == len(items):
        return "unavailable"
    return "partial"


def _suspect(target):
    u"""可疑之**标**（一阶段唯「标」· ⛔ 判「木马」）⇒ 一句因 ∨ 空。"""
    t = (target or u"").lower()
    if u"\\temp\\" in t or t.startswith(u"%temp%"):
        return u"径在暂存处（用户可写）"
    if u"\\downloads\\" in t or u"\\public\\" in t:
        return u"径在用户可写之处"
    if t.endswith((u".bat", u".cmd", u".vbs", u".js", u".jse", u".wsf", u".ps1", u".scr", u".hta")):
        return u"脚本类可执行"
    return u""

# ============================== ① 磁盘 ==============================
def panel_disk(deadline):
    items = []
    if psutil is None:
        return ([_unknown("disk:ERR", u"磁盘", "psutil.disk_usage", u"psutil 缺",
                          _guide(u"打开「设置 → 系统 → 存储」", _SETTINGS_STORAGE))],
                u"磁盘：取不得（psutil 缺）⇒ 请你在「设置 → 系统 → 存储」自看", u"")
    worst_v, worst_txt = "ok", u""
    for d in _drives():
        if time.monotonic() > deadline:
            items.append(_unknown("disk:%s" % d[0], u"%s 卷" % d, "psutil.disk_usage(%r)" % d,
                                  u"逾窗", _guide(u"打开「设置 → 系统 → 存储」", _SETTINGS_STORAGE)))
            continue
        try:
            u_ = psutil.disk_usage(d)
        except Exception as e:
            items.append(_unknown("disk:%s" % d[0], u"%s 卷" % d, "psutil.disk_usage(%r)" % d,
                                  type(e).__name__,
                                  _guide(u"打开「设置 → 系统 → 存储」", _SETTINGS_STORAGE)))
            continue
        ratio = (float(u_.free) / float(u_.total)) if u_.total else 0.0
        v = _verdict_free(ratio)
        if _RANK.get(v, 0) > _RANK.get(worst_v, 0):
            worst_v, worst_txt = v, u"%s 余 %.0f%% ⇒ %s" % (
                d, ratio * 100.0, u"很紧张（须尽早清）" if v == "crit" else u"偏紧")
        items.append(_item("disk:%s" % d[0], u"%s 卷" % d,
                           u"总 %s ／ 已用 %s ／ 余 %s（余 %.0f%%）"
                           % (_human(u_.total), _human(u_.used), _human(u_.free), ratio * 100.0),
                           "psutil.disk_usage(%r)" % d, v,
                           _guide(u"打开「设置 → 系统 → 存储」", _SETTINGS_STORAGE)))
    txt = worst_txt or u"各卷余量皆 > 10% ⇒ 尚可"
    return items, txt, u""


# ============================== ② C 盘之占用大项 ==============================
def _our_root():
    la = (os.environ.get(u"LOCALAPPDATA") or u"").strip()
    if la:
        return os.path.join(la, OUR_DIR)
    return os.path.join((os.environ.get(u"ProgramData") or u"").strip(), OUR_DIR)


def panel_disk_c(deadline):
    u"""C 盘之占用大项 —— **唯量尺**（⛔ 删）＋ `可否清 ＝ 待二阶段` ＋ 清之险之三等。"""
    items = []
    root = _our_root()
    if os.path.isdir(root):
        tot, nf, trunc = _dir_size(root, deadline)
        items.append(_item("c:ours", u"我司自身之残留（装位）",
                           u"%s ／ %d 件%s" % (_human(tot), nf, u"（有界之数 · 下界）" if trunc else u""),
                           "os.scandir(%s)" % root, "warn" if tot > (200 * 2 ** 20) else "info",
                           _guide(u"将来可在「本机管理」里清（须你逐次确认）", u""),
                           risk=RISK_UNVERIFIED))
        for sub, label in ((os.path.join(u"update", u"backup"), u"旧备份（回滚之靠山）"),
                           (os.path.join(u"update", u"stage"), u"暂存（旧包）"),
                           (u"diag", u"诊断包"), (u"shell", u"壳之日志")):
            sp = os.path.join(root, sub)
            if not os.path.isdir(sp):
                continue
            sz, n2, tr2 = _dir_size(sp, deadline)
            it = _item("c:ours:%s" % sub.replace(u"\\", u"/"), label,
                       u"%s ／ %d 件%s" % (_human(sz), n2, u"（有界之数 · 下界）" if tr2 else u""),
                       "os.scandir(%s)" % sp, "info",
                       _guide(u"将来可在「本机管理」里清（须留最近一份）", u""),
                       risk=RISK_UNVERIFIED)
            it["可否清"] = CAN_CLEAN_P1 + (u"（须留最近一份）" if u"backup" in sub else u"")
            items.append(it)
    else:
        items.append(_item("c:ours", u"我司自身之残留（装位）", u"本机无（%s）" % root,
                           "os.path.isdir", "ok", _none()))
    tmp = (os.environ.get(u"TEMP") or os.environ.get(u"TMP") or u"").strip()
    if tmp and os.path.isdir(tmp):
        ours, tot2, cnt, trunc2 = [], 0, 0, False
        try:
            for nm in os.listdir(tmp):
                if time.monotonic() > deadline:
                    trunc2 = True
                    break
                if nm.lower().startswith(TEMP_PREFIXES):
                    fp = os.path.join(tmp, nm)
                    if os.path.isdir(fp):
                        sz2, _n, _t = _dir_size(fp, deadline)
                    else:
                        try:
                            sz2 = os.path.getsize(fp)
                        except Exception:
                            sz2 = 0
                    ours.append(u"%s（%s）" % (nm, _human(sz2)))
                    tot2 += sz2
                    cnt += 1
        except Exception:
            pass
        it2 = _item("c:temp_ours", u"暂存处（TEMP）之我司物",
                    u"%d 件 ／ 共 %s ／ %s%s" % (cnt, _human(tot2), u"；".join(ours[:6]) or u"无",
                                                u"（有界之数 · 下界）" if trunc2 else u""),
                    "os.listdir(%s)" % tmp, "warn" if tot2 > (200 * 2 ** 20) else "info",
                    _guide(u"将来可在「本机管理」里逐项确认后清", u""),
                    risk=RISK_UNVERIFIED)
        it2["可否清"] = CAN_CLEAN_P1
        items.append(it2)
    sysd = (os.environ.get(u"SystemDrive") or u"C:").rstrip(u"\\")
    for sub, label in ((os.path.join(u"Windows", u"Temp"), u"系统暂存（Windows\\Temp）"),
                       (os.path.join(u"Windows", u"SoftwareDistribution", u"Download"), u"更新之下载缓存"),
                       (u"$Recycle.Bin", u"回收站")):
        pp = os.path.join(sysd + u"\\", sub)
        if not os.path.isdir(pp):
            continue
        sz3, n3, tr3 = _dir_size(pp, deadline)
        it3 = _item("c:sys:%s" % sub.replace(u"\\", u"/"), label,
                    u"%s ／ %d 件%s" % (_human(sz3), n3, u"（有界之数 · 下界）" if tr3 else u""),
                    "os.scandir(%s)" % pp, "info",
                    _guide(u"此面属系统 ⇒ 一阶段唯报（⛔ 代你动）", _SETTINGS_STORAGE),
                    risk=RISK_UNVERIFIED)
        it3["可否清"] = u"⛔ 非本器之事（系统之物）"
        items.append(it3)
    for fn, label in ((u"hiberfil.sys", u"休眠档（hiberfil.sys）"),
                      (u"pagefile.sys", u"分页档（pagefile.sys）")):
        fp = os.path.join(sysd + u"\\", fn)
        try:
            sz4 = os.path.getsize(fp)
        except Exception:
            continue
        it4 = _item("c:sysfile:%s" % fn, label, _human(sz4), "os.path.getsize", "info",
                    _guide(u"此面属系统 ⇒ 一阶段唯报", _SETTINGS_STORAGE),
                    risk=RISK_UNVERIFIED)
        it4["可否清"] = u"⛔ 非本器之事（系统之物）"
        items.append(it4)
    big = [i for i in items if i.get("结论") in ("warn", "crit")]
    txt = (u"%d 处偏大之项 ⇒ 见下（可否清我们尚未验 = 唯「待二阶段」）" % len(big)) if big \
        else u"C 盘未见我司之残留偏大 ⇒ 见下逐项"
    return items, txt, u""

# ============================== ③ Windows 与更新 ==============================
def panel_windows(deadline):
    items = []
    build = u""
    try:
        wv = sys.getwindowsversion()
        build = u"%d.%d.%d" % (wv.major, wv.minor, wv.build)
    except Exception:
        build = u""
    try:
        rel, ver, _csd, _ptype = platform.win32_ver()
    except Exception:
        rel = ver = u""
    if build or ver:
        items.append(_item("win:ver", u"Windows 版本",
                           u"build %s（%s %s）" % (build or u"—", rel or u"—", ver or u"—"),
                           "sys.getwindowsversion() + platform.win32_ver()", "info", _none()))
    else:
        items.append(_unknown("win:ver", u"Windows 版本", "sys.getwindowsversion()", u"读数 ⛔ 得",
                              _guide(u"自己看：开始 → 运行 → 输入 winver", u"")))
    try:
        import winreg
        pause, why = _reg_value(winreg.HKEY_LOCAL_MACHINE,
                                r"SOFTWARE\Microsoft\WindowsUpdate\UX\Settings",
                                u"PauseUpdatesExpiryTime")
    except Exception:
        pause, why = None, u"无 winreg"
    _src_pause = "winreg:HKLM/.../WindowsUpdate/UX/Settings/PauseUpdatesExpiryTime"
    if pause:
        items.append(_item("win:pause", u"更新之暂停", u"已暂停至 %s" % pause, _src_pause, "warn",
                           _guide(u"打开「Windows 更新」看详情", _SETTINGS_WU)))
    else:
        items.append(_item("win:pause", u"更新之暂停", u"未见暂停（%s）" % (why or u"未设"), _src_pause,
                           "info", _guide(u"打开「Windows 更新」看详情", _SETTINGS_WU)))
    obj, why2 = _ps_json(u"Get-Service -Name wuauserv,BITS -ErrorAction SilentlyContinue | "
                         u"Select-Object -Property Name,@{n='Status';e={[string]$_.Status}} | "
                         u"ConvertTo-Json -Compress", timeout=_ps_budget(deadline, 1.2))
    rows = _ps_rows(obj)
    if rows:
        st = {}
        for r in rows:
            st[str(r.get("Name"))] = str(r.get("Status") or u"").strip()
        seg = u" ／ ".join(u"%s=%s" % (k, v or u"—") for k, v in st.items())
        _wu = st.get(u"wuauserv", u"")
        _bad = bool(_wu) and _wu.lower() != u"running"
        _bits = st.get(u"BITS", u"")
        _tail = u"（BITS 乃按需启动 ⇒ 常 Stopped · 乃常）" if _bits.lower() == u"stopped" else u""
        items.append(_item("win:svc", u"更新之服务", u"%s%s" % (seg, _tail),
                           "powershell:Get-Service wuauserv,BITS", "warn" if _bad else "ok",
                           _guide(u"打开「Windows 更新」看详情", _SETTINGS_WU)))
    else:
        items.append(_unknown("win:svc", u"更新之服务", "powershell:Get-Service wuauserv,BITS",
                              why2 or u"取不得",
                              _guide(u"打开「Windows 更新」看详情", _SETTINGS_WU)))
    obj3, why3 = _ps_json(u"Get-HotFix -ErrorAction SilentlyContinue | "
                          u"Sort-Object -Property InstalledOn -Descending | "
                          u"Select-Object -First 3 -Property HotFixID,"
                          u"@{n='On';e={if($_.InstalledOn){$_.InstalledOn.ToString('yyyy-MM-dd')}else{''}}} | "
                          u"ConvertTo-Json -Compress", timeout=_ps_budget(deadline, 2.0))
    rows3 = _ps_rows(obj3)
    if rows3:
        seg = u" ／ ".join(u"%s（%s）" % (r.get("HotFixID"), str(r.get("On") or u"—")[:10])
                           for r in rows3)
        items.append(_item("win:hotfix", u"最近装之更新", seg, "powershell:Get-HotFix", "info",
                           _guide(u"打开「Windows 更新」看全部", _SETTINGS_WU)))
    else:
        items.append(_unknown("win:hotfix", u"最近装之更新", "powershell:Get-HotFix", why3 or u"取不得",
                              _guide(u"打开「Windows 更新」看全部", _SETTINGS_WU)))
    items.append(_unknown("win:pending", u"有无待装",
                          u"Windows 更新之接口（本器 ⛔ 代问）", u"一阶段 ⛔ 取",
                          _guide(u"打开「Windows 更新」⇒ 它自会告你有无待装", _SETTINGS_WU)))
    warn = [i for i in items if i.get("结论") in ("warn", "crit")]
    txt = (u"%d 处须看（见下）" % len(warn)) if warn \
        else u"版本与更新之服务未见异常（待装之数请到「Windows 更新」自看）"
    return items, txt, u""


# ============================== ④ 启动项 ==============================
def _startup_folders():
    out = []
    for key in (u"APPDATA", u"ProgramData"):
        base = (os.environ.get(key) or u"").strip()
        if base:
            out.append(os.path.join(base, u"Microsoft", u"Windows", u"Start Menu",
                                    u"Programs", u"Startup"))
    return out


def panel_startup(deadline):
    items = []
    try:
        import winreg
        hives = ((winreg.HKEY_CURRENT_USER, u"HKCU"), (winreg.HKEY_LOCAL_MACHINE, u"HKLM"))
        rpaths = (r"Software\Microsoft\Windows\CurrentVersion\Run",
                  r"Software\Microsoft\Windows\CurrentVersion\RunOnce")
    except Exception:
        hives, rpaths = (), ()
    for hv, hn in hives:
        for rp in rpaths:
            rows, _why = _reg_enum(hv, rp)
            src = u"winreg:%s\\%s" % (hn, rp)
            for nm, val in rows:
                low = (nm + u" " + val).lower()
                if OUR_PREFIX in low:
                    items.append(_item("run:%s:%s" % (hn, nm), u"%s（我司之务）" % nm, val, src,
                                       "info", _none()))
                    continue
                sus = _suspect(val)
                if sus:
                    items.append(_item("run:%s:%s" % (hn, nm), u"%s（可疑）" % nm,
                                       u"%s ｜ 因：%s" % (val, sus), src, "warn",
                                       _guide(u"到「Windows 安全中心」看，或自行核对",
                                              _SETTINGS_SECURITY)))
                else:
                    items.append(_item("run:%s:%s" % (hn, nm), nm, val, src, "info", _none()))
    for d in _startup_folders():
        if not os.path.isdir(d):
            continue
        try:
            for nm in sorted(os.listdir(d))[:60]:
                if nm.lower() == u"desktop.ini":
                    continue
                items.append(_item("startupf:%s" % nm, u"%s（启动夹）" % nm, d,
                                   "os.listdir(%s)" % d,
                                   "warn" if _suspect(nm) else "info",
                                   _guide(u"打开「启动应用」看 ／ 管", _SETTINGS_STARTUP)))
        except Exception:
            pass
    obj, why = _ps_json(u"Get-ScheduledTask -ErrorAction SilentlyContinue | "
                        u"Where-Object {$_.State -ne 'Disabled'} | "
                        u"Select-Object -Property TaskName,State -First 80 | ConvertTo-Json -Compress")
    rows2 = _ps_rows(obj)
    if rows2:
        names = [str(r.get("TaskName")) for r in rows2]
        mine = [n for n in names if OUR_PREFIX in n.lower()]
        items.append(_item("sched", u"计划任务（唯名与态）",
                           u"未禁用者 %d 条%s" % (len(names),
                                                  (u"；我司之务：%s" % u" ／ ".join(mine[:6])) if mine else u""),
                           "powershell:Get-ScheduledTask（名 + 态 · ⛔ 全参）", "info",
                           _guide(u"打开「任务计划程序」看详情", u"")))
    else:
        items.append(_unknown("sched", u"计划任务（唯名与态）", "powershell:Get-ScheduledTask",
                              why or u"取不得", _guide(u"打开「任务计划程序」看详情", u"")))
    warn = [i for i in items if i.get("结论") in ("warn", "crit")]
    txt = (u"%d 处须看（可疑者已标 · ⛔ 我们 ⛔ 判「木马」）" % len(warn)) if warn \
        else u"启动项未见可疑者（我司之务已点名）"
    return items, txt, u""

# ============================== ⑤ 内存与 CPU ==============================
def panel_perf(deadline):
    items = []
    if psutil is None:
        return ([_unknown("perf:ERR", u"内存与 CPU", "psutil", u"psutil 缺",
                          _guide(u"打开「任务管理器」看", u""))],
                u"内存与 CPU：取不得（psutil 缺）⇒ 请你在「任务管理器」自看", u"")
    try:
        vm = psutil.virtual_memory()
        items.append(_item("perf:mem", u"内存",
                           u"共 %s ／ 在用 %s（%.0f%%）／ 可用 %s"
                           % (_human(vm.total), _human(vm.used), vm.percent, _human(vm.available)),
                           "psutil.virtual_memory()", "warn" if vm.percent >= 90 else "ok",
                           _guide(u"打开「任务管理器 → 性能」看", u"")))
    except Exception as e:
        items.append(_unknown("perf:mem", u"内存", "psutil.virtual_memory()", type(e).__name__,
                              _guide(u"打开「任务管理器 → 性能」看", u"")))
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        items.append(_item("perf:cpu", u"CPU",
                           u"%d 核 ／ 当刻 %.0f%%" % (psutil.cpu_count(logical=True) or 0, cpu),
                           "psutil.cpu_percent(interval=0.1)", "warn" if cpu >= 90 else "ok",
                           _guide(u"打开「任务管理器 → 性能」看", u"")))
    except Exception as e:
        items.append(_unknown("perf:cpu", u"CPU", "psutil.cpu_percent()", type(e).__name__,
                              _guide(u"打开「任务管理器 → 性能」看", u"")))
    try:
        me = psutil.Process(os.getpid())
        rss = me.memory_info().rss
        kids = 0
        krss = 0
        try:
            for ch in me.children(recursive=True):
                kids += 1
                krss += ch.memory_info().rss
        except Exception:
            pass
        items.append(_item("perf:ours", u"我司所占",
                           u"本进程 %s ／ 子进程 %d 个 %s（共 %s）"
                           % (_human(rss), kids, _human(krss), _human(rss + krss)),
                           "psutil.Process(os.getpid()).memory_info()", "info",
                           _guide(u"打开「任务管理器」按内存排序看", u"")))
    except Exception as e:
        items.append(_unknown("perf:ours", u"我司所占", "psutil.Process()", type(e).__name__,
                              _guide(u"打开「任务管理器」看", u"")))
    return items, u"见下（内存 ／ CPU ／ 我司所占）", u""


# ------------------------------ 监听之判 ／ 辞（pm_1765 §二.4 · 一处定形） ------------------------------
def _listen_shape(ip):
    u"""监听之**绑形**：`127.x` ／ `::1` ⇒ `local`（真本机）；`0.0.0.0` ／ `::` ⇒ `any`（全域 · 局网可达）；
    余（具体网卡 IP）⇒ `iface`（他面）。⭐ 一处定形 ⇒ ⛔ 各面自判。"""
    s = str(ip or u"").strip().lower()
    if s.startswith(u"127.") or s in (u"::1", u"0:0:0:0:0:0:0:1"):
        return "local"
    if s in (u"0.0.0.0", u"::", u"0:0:0:0:0:0:0:0", u"*"):
        return "any"
    return "iface"


def _listen_verdict(rows):
    u"""`5102` 之监听 ⇒ `(辞, 结论, 去处)`。**辞须如实**（pm_1765 §二.4⒝）：
    ⛔ 以「唯本机」之恒辞盖「全域」之实（承「⛔ 不实之辞入屏」）；⛔ 由本器去改绑（那是二阶段之动作）。"""
    by = {}
    for _ip, _port in (rows or []):
        sh = _listen_shape(_ip)
        if sh not in by:
            by[sh] = str(_ip)
    if not by:
        return (u"未见任何 5102 之监听（服务或未起）", "info",
                u"服务或未起 ⇒ 见「更新」面 ／ 壳之日志")
    if "any" in by:
        return (u"已见 %s:5102（全域 · 局网可达 ⇒ 建议只绑本机，或确认已有凭据）" % by["any"],
                "warn", u"本器唯报（改绑属二阶段 · ⛔ 代你动）")
    if "iface" in by:
        return (u"已见 %s:5102（他面 · 非本机回环）" % by["iface"], "warn",
                u"本器唯报（改绑属二阶段 · ⛔ 代你动）")
    return (u"已见 %s:5102（唯本机）" % by["local"], "ok", u"本器之端唯本机可达")


# ============================== ⑥ 网络 ==============================
def panel_net(deadline):
    items = []
    if psutil is None:
        return ([_unknown("net:ERR", u"网络", "psutil.net_connections", u"psutil 缺",
                          _guide(u"打开「设置 → 网络和 Internet」看", u""))],
                u"网络：取不得（psutil 缺）", u"")
    try:
        conns = psutil.net_connections(kind="inet")
        hist = {}
        listen_rows = []
        for c in conns:
            try:
                hist[c.status] = hist.get(c.status, 0) + 1
            except Exception:
                pass
            try:
                la = c.laddr
                ip = getattr(la, "ip", None) if la is not None else None
                port = getattr(la, "port", None) if la is not None else None
                if c.status == psutil.CONN_LISTEN and port == 5102:
                    listen_rows.append((ip, port))
            except Exception:
                pass
        seg = u" ／ ".join(u"%s=%d" % (k, v) for k, v in sorted(hist.items()) if k)
        items.append(_item("net:conn", u"网络连接（唯计数 ／ 态 · ⛔ 远址之原文 ⛔ 上屏）",
                           u"共 %d 条（%s）" % (len(conns), seg or u"—"),
                           "psutil.net_connections(kind='inet')", "info",
                           _guide(u"打开「设置 → 网络和 Internet」看", u"")))
        _lt, _lv, _lguide = _listen_verdict(listen_rows)
        items.append(_item("net:ours", u"我司之监听（端口 5102）", _lt,
                           u"psutil.net_connections（唯 LISTEN ∧ 端口 5102 之 laddr）",
                           _lv, _guide(_lguide, u"")))
    except Exception as e:
        items.append(_unknown("net:conn", u"网络连接", "psutil.net_connections()", type(e).__name__,
                              _guide(u"打开「设置 → 网络和 Internet」看", u"")))
    try:
        import winreg
        en, _w1 = _reg_value(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                             u"ProxyEnable")
        sv, _w2 = _reg_value(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                             u"ProxyServer")
        on = bool(en)
        items.append(_item("net:proxy", u"代理",
                           (u"开（%s）" % (sv or u"—")) if on else u"关（未见代理）",
                           "winreg:HKCU/.../Internet Settings/ProxyEnable", "warn" if on else "info",
                           _guide(u"打开「设置 → 网络和 Internet → 代理」看", u"")))
    except Exception as e:
        items.append(_unknown("net:proxy", u"代理", "winreg:HKCU/.../Internet Settings",
                              type(e).__name__,
                              _guide(u"打开「设置 → 网络和 Internet → 代理」看", u"")))
    items.append(_item("net:local", u"本器之界", u"本器 ⛔ 出机（全程本机 · ⛔ 端内出站）",
                       u"本器之约", "ok", _none()))
    return items, u"见下（连接 ／ 我司监听 ／ 代理）；本器全程 ⛔ 出机", u""

# ============================== ⑦ 防护（只报不杀） ==============================
def panel_guard(deadline, startup_items=None):
    items = []
    obj, why = _ps_json(u"Get-MpComputerStatus -ErrorAction SilentlyContinue | "
                        u"Select-Object -Property AMServiceEnabled,RealTimeProtectionEnabled,"
                        u"AntispywareEnabled,"
                        u"@{n='SigUpdated';e={if($_.AntivirusSignatureLastUpdated)"
                        u"{$_.AntivirusSignatureLastUpdated.ToString('yyyy-MM-dd HH:mm')}else{''}}} | "
                        u"ConvertTo-Json -Compress", timeout=_ps_budget(deadline, 1.6))
    rows = _ps_rows(obj)
    _src_mp = "powershell:Get-MpComputerStatus（唯读）"
    if rows:
        r = rows[0]
        on = bool(r.get("AMServiceEnabled"))
        sig = str(r.get("SigUpdated") or u"")
        items.append(_item("guard:defender", u"Windows Defender 在不在跑",
                           u"%s（实时防护=%s ／ 反间谍=%s ／ 签名库刻=%s）"
                           % (u"在跑" if on else u"未见在跑（或 ⛔ 读得）",
                              r.get("RealTimeProtectionEnabled"), r.get("AntispywareEnabled"),
                              sig[:19] or u"—"),
                           _src_mp, "ok" if on else "warn",
                           _guide(u"到「Windows 安全中心」看", _SETTINGS_SECURITY)))
        n = None
        try:
            import datetime as _dt
            t = sig[:10]
            if len(t) == 10:
                d0 = _dt.date(*[int(x) for x in t.split("-")])
                n = (_dt.date.today() - d0).days
        except Exception:
            n = None
        if n is not None:
            items.append(_item("guard:sig_age", u"签名库之新旧", u"%d 天前更新" % n, _src_mp,
                               "warn" if n > 7 else "ok",
                               _guide(u"到「Windows 安全中心 → 病毒和威胁防护 → 检查更新」",
                                      _SETTINGS_SECURITY)))
    else:
        items.append(_unknown("guard:defender", u"Windows Defender 在不在跑", _src_mp,
                              why or u"取不得",
                              _guide(u"此项多半须授权 ⇒ 请你自己到「Windows 安全中心」看",
                                     _SETTINGS_SECURITY)))
    fw, fwhy = _firewall_state()
    if fw:
        seg = u" ／ ".join(u"%s=%s" % (k, u"开" if v else u"关") for k, v in fw)
        items.append(_item("guard:fw", u"防火墙", seg, _FW_SRC,
                           "warn" if any(not v for _k, v in fw) else "ok",
                           _guide(u"到「Windows 安全中心」⇒ 打开 → 防火墙和网络保护 → 逐个网络打开",
                                  _SETTINGS_SECURITY)))
    else:
        items.append(_unknown("guard:fw", u"防火墙", _FW_SRC, fwhy or u"取不得",
                              _guide(u"到「Windows 安全中心」看", _SETTINGS_SECURITY)))
    sus = [i for i in (startup_items or []) if i.get("结论") in ("warn", "crit")]
    items.append(_item("guard:sus", u"可疑之启动项（我们唯「标」）",
                       (u"%d 处（见「启动项」面之标）" % len(sus)) if sus else u"未见",
                       "取「启动项」面之标", "warn" if sus else "ok",
                       _guide(u"到「Windows 安全中心」看，或自行核对", _SETTINGS_SECURITY)))
    items.append(_item("guard:scope", u"本器之能",
                       u"唯有「体检 + 提示 + 去处」⇒ ⛔ 杀毒 ／ ⛔ 清 ／ ⛔ 隔离（我们 ⛔ 是杀毒软件）",
                       u"本器之约", "info", _none()))
    warn = [i for i in items if i.get("结论") in ("warn", "crit")]
    txt = (u"%d 处须看 ⇒ 请到「Windows 安全中心」" % len(warn)) if warn \
        else u"防护未见异常（⛔ 我们 ⛔ 保证「无木马」—— 唯报所见）"
    return items, txt, u""


_PANEL_FN = {"disk": panel_disk, "disk_c": panel_disk_c, "windows": panel_windows,
             "startup": panel_startup, "perf": panel_perf, "net": panel_net}


# ============================== 渲染（纯文本 · 唯前端复制之便） ==============================
def _render_panel(doc):
    out = [u"── %s ──（%s）" % (doc.get("title") or doc.get("panel"), doc.get("generated_at") or u"")]
    if doc.get("verdict_text"):
        out.append(u"结论：%s" % doc["verdict_text"])
    for it in doc.get("items") or []:
        out.append(u"· %s：%s" % (it.get("人话"), it.get("读数")))
        out.append(u"    源：%s%s" % (it.get("源"), u"（须授权）" if it.get("needs_admin") else u""))
        if it.get("清之险"):
            out.append(u"    清之险：%s" % it["清之险"])
        act = it.get("去处") or {}
        if act.get("kind") == "guide" and act.get("label"):
            out.append(u"    去处：%s" % act["label"])
    if doc.get("note"):
        out.append(u"（%s）" % doc["note"])
    return u"\n".join(out)


def _render_snapshot(doc):
    out = [u"【本机体检（只读 · 一阶段）】 %s" % (doc.get("generated_at") or u""),
           u"结论：%s" % (doc.get("verdict_text") or u""),
           u"本器全程 ⛔ 出机 ／ ⛔ 写 ／ ⛔ 提权（须授权者已明标）", u""]
    for p in doc.get("panels") or []:
        out.append(_render_panel(p))
        out.append(u"")
    return u"\n".join(out)


# ============================== 主（面） ==============================
_CACHE = {}          # pid -> {"t": float, "doc": dict}


def _with_unknown(text, items):
    u"""⛔ 一片未知之反面 —— 有取不得者 ⇒ 句末照实报其数（⛔ 以「未见异常」盖之）。"""
    unk = sum(1 for i in items if i.get("结论") == "unknown")
    if not unk:
        return text
    return u"%s；另 %d 项取不得（见下逐项之因与去处）" % (text, unk)


def _fallback_text(items):
    if not items:
        return u"本面 ⛔ 得任何读数"
    unk = sum(1 for i in items if i.get("结论") == "unknown")
    if unk == len(items):
        return u"本面之读数皆取不得 ⇒ 见下逐项之因与去处"
    return u"见下逐项"


def _scan(pid):
    t0 = time.monotonic()
    deadline = t0 + PANEL_BUDGET_S
    items, vtext, note = [], u"", u""
    try:
        if pid == "guard":
            _hit = _CACHE.get("startup")
            s_items = []
            if _hit:
                s_items = list((_hit.get("doc") or {}).get("items") or [])
            elif time.monotonic() < deadline - 0.4:
                try:
                    s_items, _st, _sn = panel_startup(deadline)
                except Exception:
                    s_items = []
            items, vtext, note = panel_guard(deadline, startup_items=s_items)
        else:
            items, vtext, note = _PANEL_FN[pid](deadline)
    except Exception as e:
        note = u"%s: %s" % (type(e).__name__, str(e)[:160])
        items = [_unknown(pid + ":ERR", TITLES.get(pid) or pid, u"器之内部", type(e).__name__)]
    doc = {"ok": True, "panel": pid, "title": TITLES.get(pid) or pid,
           "verdict": _worst([i.get("结论") for i in items]),
           "verdict_text": _with_unknown(vtext or _fallback_text(items), items),
           "state": _state_of(items), "note": note, "source_note": SOURCE_NOTE,
           "items": items, "elapsed_s": round(time.monotonic() - t0, 2)}
    doc["text"] = _render_panel(doc)
    return doc


def _skipped(pid, why=u"逾总窗"):
    doc = {"ok": True, "panel": pid, "title": TITLES.get(pid) or pid, "verdict": "unknown",
           "verdict_text": u"%s：本次 %s ⇒ ⛔ 未扫（请点「重扫」再取一次）" % (TITLES.get(pid) or pid, why),
           "state": "partial", "note": why, "source_note": SOURCE_NOTE,
           "items": [_unknown(pid + ":SKIP", TITLES.get(pid) or pid, u"本次 ⛔ 扫", why)],
           "cached": False, "age_s": 0.0, "elapsed_s": 0.0}
    doc["text"] = _render_panel(doc)
    return doc


def build(panel, fresh=False):
    u"""单面之盘（唯读 · 有缓存 ＋ `fresh=True` 强制重扫）。"""
    pid = str(panel or "").strip()
    if pid not in PANELS:
        return {"ok": False, "error": u"⛔ 未识之面：%s（白名单：%s）" % (pid, u" ／ ".join(PANELS))}
    now = time.time()
    hit = _CACHE.get(pid)
    if (not fresh) and hit and (now - hit["t"]) < SYS_TTL_S:
        doc = dict(hit["doc"])
        doc["cached"] = True
        doc["age_s"] = round(now - hit["t"], 1)
        return doc
    doc = _scan(pid)
    doc["generated_at"] = _stamp()
    doc["cached"] = False
    doc["age_s"] = 0.0
    _CACHE[pid] = {"t": now, "doc": dict(doc)}
    return doc


def snapshot(fresh=False):
    u"""七面之合体（一屏 ＝ 一次取 · 与单面**同源** ⇒ ⛔ 二套读者）。"""
    t0 = time.monotonic()
    panels = []
    for pid in PANELS:
        left = SCAN_BUDGET_S - (time.monotonic() - t0)
        if left <= 0.2:
            panels.append(_skipped(pid))
            continue
        panels.append(build(pid, fresh=fresh))
    doc = {"ok": True, "panel": "snapshot", "title": u"本机体检（只读 · 一阶段）",
           "verdict": _worst([p.get("verdict") for p in panels]),
           "generated_at": _stamp(),
           "cached": all(bool(p.get("cached")) for p in panels),
           "state": ("unavailable" if all(p.get("state") == "unavailable" for p in panels)
                     else ("partial" if any(p.get("state") in ("partial", "unavailable")
                                            for p in panels) else "ok")),
           "source_note": SOURCE_NOTE, "panels": panels,
           "elapsed_s": round(time.monotonic() - t0, 2)}
    bad = [p for p in panels if p.get("verdict") in ("warn", "crit")]
    _part = [p for p in panels if p.get("state") in ("partial", "unavailable")]
    _base = (u"%d 面须看 ⇒ 见下（先看「C 盘之占用大项」）" % len(bad)) if bad \
        else u"七面未见须急看之项"
    doc["verdict_text"] = (_base + (u"；其中 %d 面有取不得之项（须授权者已明标）" % len(_part))
                           if _part else _base)
    doc["text"] = _render_snapshot(doc)
    return doc


def reset_cache():
    u"""清缓存（唯测试之用 · ⛔ 面）。"""
    _CACHE.clear()
