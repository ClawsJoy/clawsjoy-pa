# -*- coding: utf-8 -*-
u"""pa_update.py -- 应用**增量包**（甲-P0 之器二 · 承 pm_1620 §二.1 ＋ §三 ／ pm_1645 §二 令一 · TD f202f89）。

其的：把「本批之小修」从建机送到用户机并生效 ⇒ **⛔ 重下整包**（`534.3 MB` ⟷ `≈ 0.6 MB`）。

十步（**全程可见** —— 承 pm_1620 §三.7：凡等待必有**提示 ＋ 进度 ＋ 时长** ⇒ ⛔ 静默）：
  ① 取清单（源之声明一处出）② 校形 ／ 通道 ／ 基础版 ③ 逐件下 ④ 逐件校（sha256 ＋ size）
  ⑤ 备份（**唯装根之外** —— 见下）⑥ 先停后换（服务在跑 ⇒ 文件占用）⑦ **原子替换**（同卷 `os.replace`）
  ⑧ 逐件落成 ⑨ 重启 ⑩ 探 `/health`。
**任一步败 ⇒ 反替换 ＋ fail-loud「已回滚至 <版本>」**（承 pm_1620 §三.5）。

陈三铁律：
  ⒜ **⛔ 动用户环境之数据**（承 pm_1620 §三.8）：`data/` ／ 会话 ／ 库 ／ 台账 ／ 记忆 ／
     `config/.env`（密钥）**一律 ⛔ 碰**（清单若含之 ⇒ **拒** —— `NEVER` 之点名 ＋ `data/` 前缀）。
     ⇒ 本器之备份 ／ 态 **⛔ 入装根之 `data/`**（落 `%LOCALAPPDATA%\\ClawsJoyPA\\update`）。
  ⒝ **⛔ 明文信任**（承 pm_1620 §三.9）：唯 `sha256` ＋ `size` 为凭（**逐件校** · 一件 ⛔ 合 ⇒ 整体 ⛔ 落）。
  ⒞ **⛔ 半途**：**先全下全验，后方动盘**（⇒ 网断之败 ⛔ 留半成品之树）。

用法：
  python -X utf8 scripts\\win_pa\\pa_update.py                       # 干跑（印将动何物）
  python -X utf8 scripts\\win_pa\\pa_update.py --go                  # 真办
  ... [--src <url>] [--manifest <本机清单.json>] [--root <装根>] [--staged <已下之树>]
      [--force] [--no-restart] [--json] [--self-test]
退出码：0 成（含「已是最新」∧「同版号之重发」）｜ 2 前置 ⛔ 足 ∨ 败（已回滚）｜ 3 入口错
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import time

# ⭐ 窗隐（pm_1865 §二.1 · **一处定形**）：本层之 spawn ⇒ 一律经 `_proc`（⛔ 手写 creationflags）。
#   由：本层器常由**无控制台之父**起（任务宿主 `svchost` ／ `DETACHED_PROCESS` 之器）⇒ 裸 spawn
#   ⇒ Windows **新开**一个控制台窗（屏上一闪 · pm_1862 §一② ／ §一① 之一手）。
#   真源 ＝ `core/pa/_proc.py`；本层器 `scripts/win_pa/_proc.py` ① 同目录 `import _proc`
#   （常路）—— ⛔ 成 ⇒ ② 按**文件路径**载（⛔ 倚 sys.path · 同 `boot_resume.py:94-122` 之形）；
#   皆败 ⇒ `None`（caller 退**本地等价** · 并落警 · ⛔ 静默）。
def _load_proc():
    try:
        import _proc
        return _proc
    except Exception:                                     # noqa: BLE001 — 照实退下一步
        pass
    try:
        import importlib.util as _ilu
        _s = _ilu.spec_from_file_location("_win_pa_proc", os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "_proc.py"))
        _m = _ilu.module_from_spec(_s)
        _s.loader.exec_module(_m)
        return _m
    except Exception as _e:                               # noqa: BLE001 — 照实报因
        sys.stderr.write(u"⚠ 窗隐器皆载不到（%s: %s）\n" % (type(_e).__name__, str(_e)[:120]))
    return None


_PROC = _load_proc()


def run_hidden(cmd, **kw):
    u"""本器之 spawn 出口（窗隐 · ⛔ 各处手写 creationflags）。真源载不到 ⇒ 本地等价。"""
    if _PROC is not None:
        return _PROC.run_hidden(cmd, **kw)
    kw["creationflags"] = int(kw.get("creationflags", 0) or 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(cmd, **kw)


if sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BS = chr(92)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
STOPPER = os.path.join(u"scripts", u"win_pa", u"pa_nowindow.py")
#: ⛔ 动之「点名」（**一处定形** —— 双保险 ∧ ⛔ 静默 · 与 `make_update.py:NEVER` 同族）
NEVER = (u"config/.env", u"config/secrets.yaml", u"scripts/win_pa/ClawsJoyPA_PA_Boot.xml")
NEVER_PREFIX = (u"data/", u"logs/", u".git/")
#: 起服之待（秒）—— 探 `/health` 之窗。⭐ **与壳同窗**（`shell/main.js` 之 `waitHealth(120000)`）：
#:   昔 `40 s` ⟷ 壳 `120 s` ⇒ 慢起（向量库 ／ 杀软扫新件 ／ 冷盘）必判败而回滚，而服或旋起
#:   ⇒「一直失败」之形（pm_1715 §三.1⒜）。一处定形（⛔ 二处之窗各异）。
HEALTH_WAIT_S = 120.0
#: 探中之心跳（秒）—— 每此久印一行「已 N s ／ 窗 M s」（承「凡等待必有进度 ＋ 时长」· ⛔ 刷屏）
PROBE_TICK_S = 10.0
#: 回滚后「验旧版之服已重起」之短窗（秒）—— pm_1713 §二.2（唯「探得」方称「回」）
RESTART_WAIT_S = 12.0

#: 器之输出落件（**一处定形** · pm_1799 §二.2）：`<upd_dir>/log-<目标版>.txt`
LOG_STEM = u"log-"


class _Sink(object):
    u"""器之输出**落件** ＋ 「首败」之录（**一处定形** · pm_1799 §二.1 ／ §二.2）。

    由（一手 · 净机页内 `rc=2` 之查）：器之真因**全机无一处记着** ——
      ⒜ 端起器时 `stdout=DEVNULL, stderr=DEVNULL` ⇒ 器印之 `[FAIL]` 全弃；
      ⒝ 终态之册唯泛辞（`update_run.finish` 之默认 `note`）。
    ⇒ 今：器**自落**其输出（端之 `DEVNULL` 弃不掉它）∧ 录**首行 `[FAIL]` 之原辞**
      ⇒ 终态之 `note_why` 载之（逐条可查 · ⛔ 泛辞）。

    ⚠ **一路一柄**：stdout ／ stderr **共**此 sink —— 二柄同写一径 ⇒ 各自之偏移互覆。
    """

    def __init__(self):
        self.path = None
        self.fh = None
        self.buf = []
        self.pending = u""
        self.first_fail = u""

    def open_at(self, path):
        u"""落件之开（⛔ 阻器 —— 落不成 ⇒ 降「唯屏」· 照实）。"""
        if self.fh is not None or not path:
            return
        self.path = path
        try:
            d = os.path.dirname(path)
            if d:
                os.makedirs(d, exist_ok=True)
            self.fh = io.open(path, u"w", encoding=u"utf-8", newline=u"\n")
        except OSError:
            self.fh = None
            return
        try:
            if self.buf:
                self.fh.write(u"".join(self.buf))
            self.buf = []
            self.fh.flush()
        except OSError:
            pass

    def feed(self, s):
        if s is None:
            return
        if self.fh is None:
            self.buf.append(s)
        else:
            try:
                self.fh.write(s)
                self.fh.flush()
            except OSError:
                pass
        self._scan(s)

    def _scan(self, s):
        u"""录**首行** `[FAIL]`（原辞 · 一处）。"""
        t = self.pending + s
        lines = t.split(u"\n")
        self.pending = lines.pop()
        for l in lines:
            if l.lstrip().startswith(u"[FAIL]") and not self.first_fail:
                self.first_fail = l.strip()

    def flush(self):
        if self.fh is not None:
            try:
                self.fh.flush()
            except OSError:
                pass

    def close(self):
        self.flush()
        if self.fh is not None:
            try:
                self.fh.close()
            except OSError:
                pass
            self.fh = None


_SINK = _Sink()


class _Tee(object):
    u"""原流 ＋ sink 之双写（**唯此一处** · 承「一处定形」）。"""

    encoding = u"utf-8"
    errors = u"replace"

    def __init__(self, stream, sink):
        self.stream = stream
        self.sink = sink

    def write(self, s):
        try:
            self.stream.write(s)
        except Exception:                                     # noqa: BLE001 — 屏 ⛔ 阻器
            pass
        self.sink.feed(s)
        return len(s) if s else 0

    def flush(self):
        try:
            self.stream.flush()
        except Exception:                                     # noqa: BLE001
            pass
        self.sink.flush()

    def isatty(self):
        try:
            return bool(self.stream.isatty())
        except Exception:                                     # noqa: BLE001
            return False

    def fileno(self):
        return self.stream.fileno()


def _add_core(root):
    for p in (root, HERE):
        if p not in sys.path:
            sys.path.insert(0, p)


def say(i, n, msg, t0=None):
    el = (u"（%.1f s）" % (time.time() - t0)) if t0 else u""
    print(u"[更新] %d/%d %s%s" % (i, n, msg, el), flush=True)


#: 器之「败于何处」＋「是否已动盘」（**一处定形** · pm_1799 §二.1）
#:   —— 终态之 note ／ note_why 由此出：⛔ 泛辞（承「失败即报根」）。
#:   ⭐ pm_1848 §三.3：加 `noop`（「已是最新 ⇒ 未动一物」之实）∧ `reissue` ／ 二戳
#:   （同版号之新册 ⇒ 可装 ∧ 明书）—— ⛔ 以「版号同」充「同物」（旧病）。
_DIAG = {u"step": u"", u"from": None, u"to": None, u"touched": False, u"rolled_back": False,
         u"noop": False, u"reissue": False, u"stamp_from": None, u"stamp_to": None}


def mark(step):
    u"""记「今在何步」（败时即报之 · ⛔ 事后追猜）。"""
    _DIAG[u"step"] = step


def fail_why(rc):
    u"""终态之「因」（**逐条可查** · pm_1799 §二.1）：败于何步 ＋ 首行 `[FAIL]` 之原辞
    ＋ 是否已动盘／已回滚 ＋ rc ＋ 日志之径（⛔ 泛辞）。"""
    if int(rc) == 0:
        return u""
    bits = []
    if _DIAG[u"step"]:
        bits.append(u"败于「%s」" % _DIAG[u"step"])
    if _SINK.first_fail:
        bits.append(_SINK.first_fail)
    if _DIAG[u"touched"]:
        bits.append((u"已回滚至 %s" % (_DIAG[u"from"] or u"原态")) if _DIAG[u"rolled_back"]
                    else u"已动盘 · ⛔ 未回滚")
    else:
        bits.append(u"未动盘")
    bits.append(u"rc=%d" % int(rc))
    if _SINK.path:
        bits.append(u"日志：%s" % _SINK.path)
    return u" ｜ ".join(bits)


def final_note(rc, a):
    u"""终态之「辞」（**如实** · pm_1799 §二.4）：成 ⇒ 「已就位 ＋ 下一步」；
    败 ⇒ 载**败步 ＋ 回滚之实**（⛔ 含混之「若已动盘 ⇒ …」）。
    ⚠ 自动起服之路（`--no-restart` ⛔ 给）⇒ 仍走 `update_run` 之默认辞 ——
      **唯二例外**（承 pm_1848 §三.3）：ⓐ 同版号之重发（`reissue` ⇒ 默认辞将误书
      「已是最新」，故须明书二戳）；ⓑ 「已是最新 ⇒ 未动一物」（`noop` ⇒ ⛔ 书「已就位」）。"""
    if int(rc) == 0:
        if _DIAG.get(u"reissue"):
            tail = (u"· 请关窗重开 ClawsJoy PA（∨ 菜单「重启服务」）以生效"
                    if getattr(a, u"no_restart", False) else u"")
            return (u"已就位（同版号之新册 · 重发）：%s ｜ 戳 %s ⇒ %s%s"
                    % (_DIAG.get(u"to") or u"新册", _DIAG.get(u"stamp_from") or u"⛔ 读",
                       _DIAG.get(u"stamp_to") or u"⛔ 读", tail))
        if _DIAG.get(u"noop"):
            return (u"已是最新（%s）· ⛔ 动一物（承 pm_1848 §三.3）"
                    % (_DIAG.get(u"to") or _DIAG.get(u"from") or u"—"))
        if getattr(a, u"no_restart", False):
            return (u"已就位（%s ⇒ %s）· 请关窗重开 ClawsJoy PA（∨ 菜单「重启服务」）以生效"
                    % (_DIAG[u"from"] or u"（旧包）", _DIAG[u"to"] or u"新册"))
        return None
    tail = ((u"已回滚至 %s" % (_DIAG[u"from"] or u"原态")) if _DIAG[u"rolled_back"]
            else (u"已动盘 · ⛔ 未回滚" if _DIAG[u"touched"] else u"未动盘"))
    return (u"未成（rc=%d）· 败于「%s」· %s"
            % (int(rc), _DIAG[u"step"] or u"前置", tail))


def _log_open(root, version):
    u"""落件之开（**一处定形**）：`<upd_dir>/log-<目标版>.txt` —— ⛔ 静默（印其径）。"""
    _SINK.open_at(os.path.join(upd_dir(root), LOG_STEM + str(version) + u".txt"))
    if _SINK.path:
        print(u"[更新] 器之输出落件：%s" % _SINK.path, flush=True)


def _mark_restart(root, to_version):
    u"""器之「**停之前**」之相位落盘（**一处** · pm_1790 §二.2）。

    由（一手 · 老板所见「版本更新无效」）：本器第 ⑥ 步停网关 ⇒
      **应答之服即死** ⇒ 面（`POST /v9/pa/update` 之 `action:status`）**无从问**
      ⇒ 那约 40 s 之空窗，面唯能显「更新面未答」（而非「正在重启」）。
    → 停**之前**落盘（`restart` ＋ `from` ／ `to` ／ `started_at`）⇒ 新进程起后**续读**
      ⇒ 相位**跟进程可察**。落盘之实体 ＝ `core/lib/update_run.py::restart`（一处定形）。

    ⚠ 相位是「面」之利 · ⇔ 「换」之要 ⇒ **⛔ 阻器**；然⛔ **静默**
      （落不成 ⇒ 面将退「未答」—— 顾客须知是器之失，⛔ 让其反复点）。
    """
    try:
        from core.lib import update_run as _ur
    except Exception as e:                                    # noqa: BLE001 — 照实报因
        print(u"[更新] ⚠ restart 相位⛔ 落：载 update_run 败（%s: %s）—— 面将退「更新面未答」"
              % (type(e).__name__, e), flush=True)
        return
    path, note = _ur.restart(root, to_version=to_version)
    print(u"[更新] 相位 restart 已落盘（面跨空窗可察）：%s%s"
          % (path, (u"｜%s" % note) if note else u""), flush=True)


def never(rel):
    u"""⛔ 动之点名 ⇒ 因 ∨ 空串（**一处定形**）。"""
    if rel in NEVER:
        return u"点名（密钥 ／ 机器相关）"
    for p in NEVER_PREFIX:
        if rel.startswith(p):
            return u"点名之前缀（%s）" % p
    return u""


def upd_dir(root=None, env=None):
    u"""态 ／ 备份之落处（**一处定形**）：`%LOCALAPPDATA%\\ClawsJoyPA\\update`；
    无 ⇒ `<装根>/data/pa/update`。⛔ 入装根之 `data/` 为要（承 pm_1620 §三.8 之正控）。"""
    env = os.environ if env is None else env
    la = (env.get(u"LOCALAPPDATA") or u"").strip()
    if la:
        return os.path.join(la, u"ClawsJoyPA", u"update")
    return os.path.join(root or ROOT, u"data", u"pa", u"update")


def stage_dir(version, root=None, env=None):
    return os.path.join(upd_dir(root, env), u"stage", str(version))


def backup_dir(version, root=None, env=None):
    return os.path.join(upd_dir(root, env), u"backup", str(version))


def cur_version(root):
    u"""本机之版（**一处出** · 承 `build_info`）⇒ `(str | None, note)`。"""
    from core.lib import build_info as BI
    d, note = BI.read(root)
    return ((d or {}).get(u"version"), note)


def cur_stamp(root):
    u"""装根之「造刻」（**一处出** · 承 pm_1848 §三.3）：`version.json` 之 `built_at`。

    由（一手 · 本夜）：`cur_version` 唯返版号 ⇒ **同版号之重发**（戳 ⛔ 同）与「已是最新」
    **不可分** ⇒ 误判「⛔ 动」⇒ 连 `--force` 亦不可装（旧器 `:560` 之早返）。
    """
    from core.lib import build_info as BI
    d, note = BI.read(root)
    return ((d or {}).get(u"built_at"), note)


def load_manifest(a, root):
    u"""取清单（本机文件 ∨ 源）⇒ `(man | None, note, why, src)`。"""
    from core.lib import update_manifest as UM
    from core.lib import update_source as US
    src = US.load(root, os.environ)
    if a.src:
        src = dict(src)
        src[u"url"] = a.src
        src.setdefault(u"origin", {})
        src[u"origin"] = dict(src.get(u"origin") or {})
        src[u"origin"][u"url"] = u"cli:--src"
    if a.manifest:
        try:
            with io.open(a.manifest, encoding=u"utf-8-sig") as fh:
                man = json.loads(fh.read())
        except Exception as e:                                # noqa: BLE001 — 照实报因
            return None, u"清单 ⛔ 读：%s（%s）" % (a.manifest, type(e).__name__), u"read", src
        ok, probs = UM.validate(man)
        if not ok:
            return None, u"清单之形 ⛔ 合：%s" % u"；".join(probs[:4]), u"shape", src
        return man, u"", u"", src
    man, note, why = UM.fetch(src)
    return man, note, why, src


def fetch_all(man, src, dest, timeout=None):
    u"""逐件下 ⇒ `(files | None, rows)`。**唯下 `add` ／ `mod`**（`del` 无件可下）。
    `dest` 之树按**装根相对之径**落（供逐件校 ＋ 替换）。"""
    from core.lib import update_manifest as UM
    rows = []
    want = [e for e in man.get(u"files") or [] if e.get(u"mode") in (u"add", u"mod")]
    t0 = time.time()
    got = 0
    for i, e in enumerate(want, 1):
        raw, note, why = UM.fetch_file(src, e[u"path"], timeout=timeout or UM.FETCH_TIMEOUT)
        if raw is None:
            return None, rows + [u"[FAIL] 下件 %d/%d ⛔ 得：%s — %s（%s）"
                                 % (i, len(want), e[u"path"], note, why)]
        got += len(raw)
        p = os.path.join(dest, e[u"path"].replace(u"/", os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, u"wb") as fh:
            fh.write(raw)
        rows.append(u"    下 %d/%d %-52s %8d B" % (i, len(want), e[u"path"], len(raw)))
    rows.append(u"[OK] 下毕：%d 件 ／ %d B（%.2f MB）｜%.1f s"
                % (len(want), got, got / 1048576.0, time.time() - t0))
    return want, rows


def verify_all(man, staged):
    u"""逐件校（sha256 ＋ size ⇒ **不重下** · 唯读盘）⇒ `(ok, rows)`。"""
    from core.lib import update_manifest as UM
    rows = []
    bad = 0
    for e in man.get(u"files") or []:
        if e.get(u"mode") == u"del":
            continue
        p = os.path.join(staged, e[u"path"].replace(u"/", os.sep))
        if not os.path.isfile(p):
            rows.append(u"[FAIL] 缺件：%s" % e[u"path"])
            bad += 1
            continue
        raw = io.open(p, u"rb").read()
        if len(raw) != e[u"size"] or UM.sha256_bytes(raw) != e[u"sha256"]:
            rows.append(u"[FAIL] 印 ⛔ 合：%s（期 %s ／ 实 %s · %d B）"
                        % (e[u"path"], e[u"sha256"][:16], UM.sha256_bytes(raw)[:16], len(raw)))
            bad += 1
    rows.append(u"[%s] 逐件校：%d 件 ／ 瑕 %d" % (u"OK" if bad == 0 else u"FAIL",
                                              len([e for e in man[u"files"] if e[u"mode"] != u"del"]), bad))
    return (bad == 0), rows


def ctl(root, act, timeout=180):
    u"""起停（**唯引装根之器** —— ⛔ 本器另写一套）⇒ `(rc | None, out)`；⛔ 在 ⇒ `(None, 因)`。

    ⭐ **与「根」绑定**（承规七 · pm_1712 §三.3⒜）：以 `cwd=root` 起 —— 器之配置 ／ 数据仓
      皆按 CWD 解；若随调用者之 CWD（壳 ／ 器 ／ 他处）⇒ 解到别处 ⇒ 起而 ⛔ 听本根之端口。
    """
    p = os.path.join(root, STOPPER)
    if not os.path.isfile(p):
        return None, u"未见 %s（⛔ 起停 ⇒ 报「停而可换」之支）" % STOPPER
    try:
        r = run_hidden([sys.executable, u"-X", u"utf8", u"-B", p, act],
                           cwd=(root or None),
                           capture_output=True, text=True, encoding=u"utf-8",
                           errors=u"replace", timeout=timeout)
    except Exception as e:                                    # noqa: BLE001 — 照实报因
        return None, u"%s: %s" % (type(e).__name__, e)
    return r.returncode, ((r.stdout or u"") + (r.stderr or u"")).strip()


def locked(path):
    u"""占用之判（**器取**）—— 试以追加开之。"""
    if not os.path.isfile(path):
        return False
    try:
        with io.open(path, u"ab"):
            return False
    except OSError:
        return True


def backup(root, entries, bdir):
    u"""备份（**唯将动之件**）⇒ `(rows, rollback | None)`；其记 ＝ `rollback.json`（反替换之凭）。"""
    rows = []
    rec = []
    for e in entries:
        tgt = os.path.join(root, e[u"path"].replace(u"/", os.sep))
        it = {"path": e[u"path"], "mode": e[u"mode"], "existed": os.path.isfile(tgt)}
        if it["existed"]:
            bdst = os.path.join(bdir, e[u"path"].replace(u"/", os.sep))
            os.makedirs(os.path.dirname(bdst), exist_ok=True)
            with io.open(bdst, u"wb") as fh:
                fh.write(io.open(tgt, u"rb").read())
            it["backup"] = bdst
        rec.append(it)
        rows.append(u"    备 %-52s %s" % (e[u"path"], u"有" if it["existed"] else u"无（新件）"))
    with io.open(os.path.join(bdir, u"rollback.json"), u"w", encoding=u"utf-8", newline=u"") as fh:
        fh.write(json.dumps({"files": rec}, ensure_ascii=False, indent=1))
    rows.append(u"[OK] 备份：%d 件 → %s" % (len(rec), bdir))
    return rows, {"files": rec}


def apply_all(entries, root, staged):
    u"""原子替换（**同卷** —— 先落 `<target>.new` ⇒ `os.replace`）⇒ `(ok, rows, done)`。"""
    rows = []
    done = []
    for e in entries:
        rel = e[u"path"]
        tgt = os.path.join(root, rel.replace(u"/", os.sep))
        try:
            if e[u"mode"] == u"del":
                if os.path.isfile(tgt):
                    os.remove(tgt)
                done.append(e)
                rows.append(u"    删 %s" % rel)
                continue
            os.makedirs(os.path.dirname(tgt), exist_ok=True)
            new = tgt + u".new"
            with io.open(new, u"wb") as fh:
                fh.write(io.open(os.path.join(staged, rel.replace(u"/", os.sep)), u"rb").read())
            os.replace(new, tgt)
            done.append(e)
            rows.append(u"    换 %-52s %s" % (rel, e[u"mode"]))
        except Exception as ex:                               # noqa: BLE001 — 照实报因
            rows.append(u"[FAIL] %s ⛔ 换：%s: %s" % (rel, type(ex).__name__, ex))
            return False, rows, done
    rows.append(u"[OK] 替换：%d 件（原子 · 同卷 os.replace）" % len(done))
    return True, rows, done


def rollback(root, rec, rows):
    u"""反替换（**唯已动之件**）⇒ 尽复原 ＋ fail-loud（承 pm_1620 §三.5）。"""
    back = 0
    for it in (rec or {}).get(u"files") or []:
        tgt = os.path.join(root, it[u"path"].replace(u"/", os.sep))
        try:
            if it.get(u"existed") and it.get(u"backup") and os.path.isfile(it[u"backup"]):
                with io.open(tgt, u"wb") as fh:
                    fh.write(io.open(it[u"backup"], u"rb").read())
                back += 1
            elif os.path.isfile(tgt):
                os.remove(tgt)
                back += 1
        except Exception as ex:                               # noqa: BLE001 — 照实报因
            rows.append(u"    ⚠ 复原 %s 败：%s" % (it[u"path"], type(ex).__name__))
        # ⚠ 原子替换之半成品（`<件>.new`）⇒ 一并清（本席一手 · 沙箱反控 P2 所见：
        #   回滚毕而 `.new` 独留 ⇒ 「树净」⛔ 全）。
        try:
            if os.path.isfile(tgt + u".new"):
                os.remove(tgt + u".new")
        except Exception:                                     # noqa: BLE001 — 残件⛔ 阻回滚
            pass
    rows.append(u"[回滚] 已复原 %d 件（并清 `.new` 之残）" % back)
    return rows


def _root_port(root):
    u"""`<root>` 之端口（**与根绑定** · 一处定形）—— 唯取真源之薄径读（`port_lite`）；
    ⛔ 以进程之 CWD 之配置充之（见 `probe_health` 之病）。⛔ 得 ⇒ raise。"""
    import port_lite
    return port_lite.read_port(root)


def probe_health(root, port=None, wait_s=HEALTH_WAIT_S):
    u"""探 `<root>` 之 `/health`（**起服之正控**）⇒ `(ok, rows)`；⛔ 得 ⇒ 照实报因 ＋ 去处。

    ⭐ **端口与「根」绑定**（承 pm_1684 §一 一手所逮之跨根险 · TD f202f89）：
      昔之误 —— `port = gateway_port()` 经 `unified_config`，其按 **CWD** 解件 ⇒
      器自他处起（沙箱副本 · 端口 8994）而 CWD 在活端之树 ⇒ 竟探 `5102`（**活端之答**）
      ⇒ 「他根之健康」充「本根之正控」＝「未知 ⛔ 充已知」之族
      ⇒ 正控假绿；反则活端不答 ⇒ 假红（无端回滚）。
      今唯取 `<root>` 之薄径读（`port_lite.read_port(root)` —— ⛔ CWD ／ ⛔ env ／ ⛔ 字面）。
      显式 `port` ⇒ 仍优先（供齿 ／ 试）。
    ⭐ **身份对证**（`/health.build.path` ⟷ `<root>/version.json`）：端口若为他根之服所占
      （同端口之二根）⇒ 一问即辨 —— 不符 ⇒ **拒**（⛔ 以其健康充本根之正控）。
    """
    import urllib.request
    if port is None:
        try:
            port = _root_port(root)
        except Exception as e:                                # noqa: BLE001 — fail-loud
            return False, [u"[FAIL] 端口取不得（须与根绑定）：%s: %s ⇒ 去处：看 %s"
                           % (type(e).__name__, e,
                              os.path.join(root, u"config", u"system", u"system_unified.yaml"))]
    url = u"http://127.0.0.1:%s/health" % port
    want = os.path.normcase(os.path.join(root, u"version.json"))
    t0 = time.time()
    # ⭐ pm_1715 §三.1⒜：**首行先印**（⛔ 静默等 · 其后每 `PROBE_TICK_S` 一行心跳）——
    #   故首行 ⛔ 入 `rows`（⛔ 二次印 · 免 「一事二声」）。
    print(u"[..] 探 %s（窗 %.0f s）" % (url, wait_s), flush=True)
    rows = []
    last = u""
    nxt = t0 + PROBE_TICK_S
    while time.time() - t0 < wait_s:
        try:
            with urllib.request.urlopen(url, timeout=5.0) as r:
                d = json.loads(r.read().decode(u"utf-8"))
            got = (d.get(u"build") or {}).get(u"path")
            if got and os.path.normcase(str(got)) != want:
                rows.append(u"[FAIL] 探得之服⛔ 本根：/health.build.path=%s ⟷ 本根 %s"
                            u" ⇒ 拒（⛔ 以他根之健康充本根）" % (got, want))
                return False, rows
            rows.append(u"[OK] /health 200 ｜status=%s ｜version=%s ｜%.1f s"
                        % (d.get(u"status"), d.get(u"version"), time.time() - t0))
            return True, rows
        except Exception as e:                                # noqa: BLE001 — 续试
            last = u"%s: %s" % (type(e).__name__, e)
            now = time.time()
            if now >= nxt:                                # ⭐ 心跳：⛔ 静默等（承「凡等待必有进度 ＋ 时长」）
                print(u"[..] 探 %s 已 %.0f s ／ 窗 %.0f s（末：%s）"
                      % (url, now - t0, wait_s, last[:60]), flush=True)
                nxt = now + PROBE_TICK_S
            time.sleep(1.5)
    rows.append(u"[FAIL] /health ⛔ 达（%.1f s）｜%s ⇒ 去处：看 logs\\gateway_%s_console.log"
                % (time.time() - t0, last, port))
    return False, rows


def run(a):
    from core.lib import update_manifest as UM
    root = os.path.abspath(a.root)
    _add_core(root)
    mark(u"取清单（源之声明）")
    man, note, why, src = load_manifest(a, root)
    if man is None:
        print(u"[FAIL] 清单 ⛔ 得：%s（%s）" % (note, why))
        print(u"       ⇒ 去处：核 %s（源之声明）∨ --src" % src.get(u"file"))
        return 2
    t = UM.totals(man)
    cur, cnote = cur_version(root)
    stamp, _snote = cur_stamp(root)
    _DIAG[u"from"] = cur
    _DIAG[u"to"] = man[u"version"]
    _log_open(root, man[u"version"])
    say(1, 10, u"清单：v%s（基 %s · %s）｜件 %d（add %d ／ mod %d ／ del %d）｜%d B（%.2f MB）"
        % (man[u"version"], man[u"base_version"], man[u"channel"], t[u"n"],
           t[u"add"], t[u"mod"], t[u"del"], t[u"bytes"], t[u"bytes"] / 1048576.0))
    say(1, 10, u"本机：版 %s（%s）｜源 %s" % (cur or u"⛔ 读", cnote or u"—", src.get(u"url")))
    if man[u"channel"] != src.get(u"channel"):
        print(u"[FAIL] 通道 ⛔ 合：清单 %s ≠ 本机 %s（⛔ 跨档 · 承 pm_1620 §三.9）"
              % (man[u"channel"], src.get(u"channel")))
        return 2
    man_stamp = str(man.get(u"built_at") or u"")
    if cur and str(cur) == str(man[u"version"]):
        # ⭐ pm_1848 §三（一手 · 本夜三出同版号 9.0.8）：旧判**唯比版号** ⇒ 同版号之新册
        #   （重发）与「已是最新」不可分 ⇒ 误判「⛔ 动」（连 `--force` 亦不可 · 旧 `:563` 更在其后）。
        #   判据 ＝ 装根 `version.json` 之 `built_at` vs 册之 `built_at`：
        #     戳**同**      ⇒ 已是最新 ⇒ ⛔ 动（照旧）；
        #     戳 **⛔ 同**（含任一戳⛔读）⇒ 认「同版号之新册（重发）」⇒ **可装** ∧ 明书二戳。
        if str(stamp or u"") and man_stamp and str(stamp) == man_stamp:
            _DIAG[u"noop"] = True               # ⭐ 早返之实（承 pm_1848 §三.3：⛔ 书「已就位」）
            say(2, 10, u"已是最新（%s · 戳 %s）⇒ ⛔ 动" % (cur, stamp))
            return 0
        _DIAG[u"reissue"] = True
        _DIAG[u"stamp_from"] = stamp
        _DIAG[u"stamp_to"] = man.get(u"built_at")
        say(2, 10, u"同版号之新册（重发）：%s ｜ 装根之戳 %s ⟷ 册之戳 %s ⇒ 可装（承 pm_1848 §三）"
            % (cur, stamp or u"⛔ 读", man_stamp or u"⛔ 读"))
    elif cur and str(cur) != str(man[u"base_version"]) and not a.force:
        print(u"[FAIL] 基础版 ⛔ 符：本机 %s ≠ 清单之 base_version %s" % (cur, man[u"base_version"]))
        print(u"       ⇒ 去处：取整包（∨ 确知可升 ⇒ --force）")
        return 2
    if not cur:
        say(2, 10, u"⚠ 本机之版号 ⛔ 读（旧包 ∨ 未装）⇒ 基础 ⛔ 可验 —— 照实续（承 pm_1620 §三.11 之演练）")
    for e in man[u"files"]:
        nv = never(e[u"path"])
        if nv:
            print(u"[FAIL] 清单含⛔ 动之件：%s（%s）⇒ 拒（承 pm_1620 §三.8 之铁律）" % (e[u"path"], nv))
            return 2
    if not a.go:
        print(u"[--] 干跑（⛔ 动盘）—— 加 --go 真办｜将动 %d 件（%d B）"
              % (t[u"n"], t[u"bytes"]))
        return 0
    stg = a.staged or stage_dir(man[u"version"], root)
    os.makedirs(stg, exist_ok=True)
    mark(u"逐件下（取件）")
    want, rows = fetch_all(man, src, stg)
    print(u"\n".join(rows))
    if want is None:
        return 2
    mark(u"逐件校（sha256 ＋ size）")
    ok, rows = verify_all(man, stg)
    print(u"\n".join(rows))
    if not ok:
        print(u"[FAIL] 逐件校 ⛔ 合 ⇒ **整体 ⛔ 落**（⛔ 半途之半成品 · 承 pm_1620 §三.3）")
        return 2
    entries = man[u"files"]
    bdir = backup_dir(man[u"version"], root)
    os.makedirs(bdir, exist_ok=True)
    mark(u"备份（装根之外）")
    rows, rec = backup(root, entries, bdir)
    print(u"\n".join(rows))
    if not a.no_restart:
        # ⭐ pm_1790 §二.2：**停之前**落 `restart` 相位（非则停后面无从察）
        mark(u"停服务")
        _mark_restart(root, man[u"version"])
        rc, out = ctl(root, u"stop")
        if rc is None:
            say(6, 10, u"⚠ 停：%s" % out)
        elif rc != 0:
            print(u"[FAIL] 停 ⛔ 成（rc=%s）⇒ 拒（恐换而不成）\n%s" % (rc, out))
            return 2
        else:
            say(6, 10, u"停成（先停后换）")
    locked_files = [e[u"path"] for e in man[u"files"] if locked(os.path.join(root, e[u"path"].replace(u"/", os.sep)))]
    if locked_files:
        print(u"[FAIL] 件被占（%d 件：%s…）⇒ 拒（恐换而不成）" % (len(locked_files), locked_files[0]))
        if not a.no_restart:
            ctl(root, u"start")
        return 2
    mark(u"换件（原子替换）")
    _DIAG[u"touched"] = True                # ⭐ 自此**已动盘**（败 ⇒ 必报之）
    ok, rows, done = apply_all(entries, root, stg)
    print(u"\n".join(rows))
    if not ok:
        rows = rollback(root, rec, [])
        _DIAG[u"rolled_back"] = True            # ⭐ 回滚之实（终态须报）
        print(u"\n".join(rows))
        print(u"[FAIL] **已回滚至 `%s`**（fail-loud · 承 pm_1620 §三.5）" % (cur or u"原态"))
        if not a.no_restart:
            ctl(root, u"start")
        return 2
    if not a.no_restart:
        mark(u"起服务")
        rc, out = ctl(root, u"start")
        # ⭐ pm_1712 §三.3⒞（「重启：成」之假绿）：起令之 rc ⛔ 为「服已起」之据 ——
        #   唯其下之探活（`probe_health`）方是；故此处 ⛔ 称「成」。
        say(9, 10, u"起服令 rc=%s%s ⇒ 待探活（⛔ 以 rc 0 称「起」）"
            % (rc, u"" if rc == 0 else u"（%s）" % out[:80]))
        mark(u"探活（/health 正控）")
        ok, rows = probe_health(root)
        print(u"\n".join(rows))
        if not ok:
            rows = rollback(root, rec, [])
            _DIAG[u"rolled_back"] = True        # ⭐ 回滚之实（终态须报）
            print(u"\n".join(rows))
            print(u"[FAIL] 起服之正控 ⛔ 过（起令 rc=%s）⇒ **已回滚至 `%s`**" % (rc, cur or u"原态"))
            # ⭐ pm_1713 §二.2（探败之支 ⛔ 重起 ⇒ 服留「停」之态 · 老板之面必断）：
            #   回滚毕 ⇒ 以旧版之树再起重服 —— 唯「探得」方称「回」；⛔ 留「停」而不言。
            rc2, out2 = ctl(root, u"start")
            ok2, rows2 = probe_health(root, wait_s=RESTART_WAIT_S)
            print(u"\n".join(rows2))
            if ok2:
                print(u"[回滚] 服已重起（旧版之树 · 探得）⇒ 面可续用")
            else:
                print(u"[⚠] 回滚后之服 ⛔ 答探活（起令 rc=%s）⇒ 服今在「停」之态；"
                      u"去处：看 %s ∨ 关窗重开 ClawsJoy PA" % (rc2, os.path.join(root, u"logs")))
            return 2
    try:
        from core.lib import update_check as UC
        UC.refresh(root)
    except Exception:                                         # noqa: BLE001 — 刷态 ⛔ 阻成
        pass
    if _DIAG.get(u"reissue"):
        say(10, 10, u"成（同版号之新册 · 重发）：%s ｜ 戳 %s ⇒ %s"
            % (man[u"version"], _DIAG.get(u"stamp_from") or u"⛔ 读",
               _DIAG.get(u"stamp_to") or u"⛔ 读"))
    else:
        say(10, 10, u"成：%s ⇒ %s" % (cur or u"（旧包）", man[u"version"]))
    if a.json:
        out = {"ok": True, "from": cur, "to": man[u"version"], "files": t,
               "backup": bdir, "staged": stg}
        if _DIAG.get(u"reissue"):       # ⭐ pm_1848 §三.3：机读之体亦载「重发 ＋ 二戳」
            out[u"reissue"] = True
            out[u"stamp_from"] = _DIAG.get(u"stamp_from")
            out[u"stamp_to"] = _DIAG.get(u"stamp_to")
        print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


def self_test():
    u"""自证（⛔ 出网 · ⛔ 动真盘）：守 ／ 形 ／ `add` 之校 ／ **`del` 一路之删 · 备 · 回滚**
    ／ 「已是最新（未动一物）」∧「同版号之重发」之辞（皆正反控 · pm_1848 §三.3）。"""
    import tempfile
    from core.lib import update_manifest as UM
    ok = True
    ok &= (never(u"data/v9/x.json") != u"")
    ok &= (never(u"config/.env") != u"")
    ok &= (never(u"core/pa/x.py") == u"")
    print(u"[%s] 正反控：⛔ 动之名点（data/ ／ .env ／ 常件）" % (u"OK" if ok else u"FAIL"))
    tmp = tempfile.mkdtemp(prefix=u"pa_upd_st_")
    man = {"version": u"9.0.1", "base_version": u"9.0.0", "channel": u"internal",
           "built_at": u"2026-10-07T00:00:00+0800",
           "files": [{"path": u"core/a.txt", "sha256": UM.sha256_bytes(b"hi"), "size": 2, "mode": u"add"},
                     {"path": u"core/gone.txt", "sha256": u"", "size": 0, "mode": u"del"}]}
    stg = os.path.join(tmp, u"stage")
    os.makedirs(os.path.join(stg, u"core"))
    io.open(os.path.join(stg, u"core", u"a.txt"), u"wb").write(b"hi")
    v_ok, v_rows = verify_all(man, stg)
    ok &= v_ok
    print(u"[%s] 正控：逐件校（%s）" % (u"OK" if v_ok else u"FAIL", u"／".join(v_rows)))
    man2 = json.loads(json.dumps(man))
    man2["files"][0]["sha256"] = u"0" * 64
    b_ok, _r = verify_all(man2, stg)
    ok &= (not b_ok)
    print(u"[%s] 反控：印 ⛔ 合 ⇒ ⛔ 落" % (u"OK" if not b_ok else u"FAIL"))
    # ⭐ pm_1757 §一.2 ／ §二⒞.5（承 pm_1745 §二 · pm_1747 §三.2⒞）：补 `del` 一路之正反控。
    #   ⚠ 昔之盲（一手所逮）：`man` 已载 `del` 一件而正反控**唯跑 `verify_all`**，而 `verify_all`
    #   遇 `del` 即 `continue` ⇒ `backup` ／ `apply_all` ／ `rollback` 之 `del` 支**全未覆**
    #   ⇒ **自证绿 ⛔ 证该路可用**（假绿 —— 与「以器之绿充事之实」同族）。
    dman = {"version": u"9.0.2", "base_version": u"9.0.1", "channel": u"internal",
            "built_at": u"2026-10-07T00:00:00+0800",
            "files": [{"path": u"core/gone.txt", "sha256": u"", "size": 0, "mode": u"del"}]}
    d0, _p0 = UM.validate(dman)
    dx = json.loads(json.dumps(dman))
    dx["files"][0]["sha256"] = u"0" * 64
    d_sha, _p1 = UM.validate(dx)
    dy = json.loads(json.dumps(dman))
    dy["files"][0]["size"] = 1
    d_size, _p2 = UM.validate(dy)
    r_ok = bool(d0) and (not d_sha) and (not d_size)
    ok &= r_ok
    print(u"[%s] 反控：`del` 之形（携 `sha256` ⇒ %s ／ 携 `size` ⇒ %s ／ 正形 ⇒ %s）"
          % (u"OK" if r_ok else u"FAIL", u"拒" if not d_sha else u"纳",
             u"拒" if not d_size else u"纳", u"纳" if d0 else u"拒"))
    droot = os.path.join(tmp, u"droot")
    os.makedirs(os.path.join(droot, u"core"))
    dtgt = os.path.join(droot, u"core", u"gone.txt")
    io.open(dtgt, u"wb").write(b"bye")
    want = UM.sha256_bytes(b"bye")
    dbdir = os.path.join(tmp, u"dbak")
    os.makedirs(dbdir)
    _dr, drec = backup(droot, dman[u"files"], dbdir)
    dit = ((drec or {}).get(u"files") or [{}])[0]
    d_back = bool(dit.get(u"backup")) and os.path.isfile(dit.get(u"backup") or u"")
    d_ok, _a1, _a2 = apply_all(dman[u"files"], droot, tmp)
    d_del = bool(d_ok) and not os.path.isfile(dtgt)
    rollback(droot, drec, [])
    dback = io.open(dtgt, u"rb").read() if os.path.isfile(dtgt) else b""
    d_res = (UM.sha256_bytes(dback) == want)
    p_ok = (dit.get(u"existed") is True) and d_back and d_del and d_res
    ok &= p_ok
    print(u"[%s] 正控＋回滚：`del` 目标在 ⇒ 备（%s）⇒ 删（%s）⇒ 复原（印%s）"
          % (u"OK" if p_ok else u"FAIL", u"有" if d_back else u"无",
             u"成" if d_del else u"在", u"合" if d_res else u"⛔"))
    eroot = os.path.join(tmp, u"eroot")
    os.makedirs(os.path.join(eroot, u"core"))
    ebdir = os.path.join(tmp, u"ebak")
    os.makedirs(ebdir)
    _er, erec = backup(eroot, dman[u"files"], ebdir)
    eit = ((erec or {}).get(u"files") or [{}])[0]
    e_ok, _b1, _b2 = apply_all(dman[u"files"], eroot, tmp)
    n_ok = bool(e_ok) and (eit.get(u"existed") is False)
    ok &= n_ok
    print(u"[%s] 正控二：`del` 目标本缺 ⇒ 备「无」∧ 删不误（`ok`=%s）"
          % (u"OK" if n_ok else u"FAIL", e_ok))
    # ⭐ pm_1799 §二.1 ／ §二.2 ／ §二.4（**真因可读 ＋ 辞如实**）：昔之盲（一手 · 净机 rc=2）——
    #   器之真因**全机无一处记着**：端弃器之流（`DEVNULL`）∧ 终态唯泛辞。
    #   ⇒ 正控＋反控逐条钉之（⛔ 自陈）。
    _ns = type("_NS", (), {"no_restart": True})()
    n_ok = final_note(0, _ns) or u""
    nl_ok = (u"已就位" in n_ok) and (u"关窗重开" in n_ok)
    ok &= nl_ok
    print(u"[%s] 正控三：成（`--no-restart`）之辞 ＝ %s" % (u"OK" if nl_ok else u"FAIL", n_ok))
    _save = dict(_DIAG)
    _DIAG.update({u"step": u"探活（/health 正控）", u"from": u"9.0.6", u"touched": True,
                  u"rolled_back": True})
    _sf = _SINK.first_fail
    _SINK.first_fail = u"[FAIL] 起服之正控 ⛔ 过（起令 rc=0）⇒ **已回滚至 9.0.6**"
    w_ok = fail_why(2)
    _SINK.first_fail = _sf
    _DIAG.update(_save)
    wk = (u"败于「探活" in w_ok) and (u"[FAIL] 起服之正控" in w_ok) and (u"已回滚至 9.0.6" in w_ok) \
        and (u"rc=2" in w_ok)
    ok &= wk
    print(u"[%s] 正控四：败因可读（%s）" % (u"OK" if wk else u"FAIL", w_ok))
    nn = final_note(2, _ns) or u""
    nn_ok = (u"未成（rc=2）" in nn) and (u"败于「" in nn)
    ok &= nn_ok
    print(u"[%s] 正控五：败之辞如实（%s）" % (u"OK" if nn_ok else u"FAIL", nn))
    f_ok = (fail_why(0) == u"")
    ok &= f_ok
    print(u"[%s] 反控一：rc=0 ⇒ ⛔ 报因（空 · 免泛辞）" % (u"OK" if f_ok else u"FAIL"))
    z_ok = final_note(0, type("_NS", (), {"no_restart": False})()) is None
    ok &= z_ok
    print(u"[%s] 反控二：自动起服之路 ⇒ **⛔ 夺** `update_run` 之辞（返 None）" % (u"OK" if z_ok else u"FAIL"))
    _sink = _Sink()
    _lp = os.path.join(tmp, u"log-9.0.1.txt")
    _sink.open_at(_lp)
    _sink.feed(u"[更新] 1/10 明细\n")
    _sink.feed(u"[FAIL] 印 ⛔ 合：core/a.txt（期 x ／ 实 y · 2 B）\n")
    _sink.feed(u"尾话\n")
    _sink.close()
    _body = io.open(_lp, encoding=u"utf-8").read() if os.path.isfile(_lp) else u""
    l_ok = (u"[FAIL] 印 ⛔ 合：core/a.txt" in _body) and (u"尾话" in _body) \
        and (_sink.first_fail == u"[FAIL] 印 ⛔ 合：core/a.txt（期 x ／ 实 y · 2 B）")
    ok &= l_ok
    print(u"[%s] 正控六：输出落件（%s · %d B · 首败 ＝ %s）"
          % (u"OK" if l_ok else u"FAIL", _lp, len(_body.encode(u"utf-8")), _sink.first_fail))
    _w1 = os.path.join(tmp, u"log-a.txt")
    _w2 = _Sink()
    _w2.open_at(_w1)
    _w2.feed(u"[FAIL] 早\n")
    _w2.feed(u"[FAIL] 晚\n")
    _w2.close()
    w2_ok = (_w2.first_fail == u"[FAIL] 早")
    ok &= w2_ok
    print(u"[%s] 反控三：**首**行 FAIL（⛔ 末行）—— 首 ＝ %s" % (u"OK" if w2_ok else u"FAIL", _w2.first_fail))
    # ⭐ pm_1848 §三.3：**早返**（已是最新 ⇒ ⛔ 动一物）∧ **重发**（载二戳）之辞 —— 正控。
    #   由：旧默认辞 `update_run.finish` 于 `from ≡ to` 恒书「已是最新」⇒ 重发之真装被
    #   **反书成未动**（假辞 · 承「⛔ 不实之辞入屏」）。
    _s7 = dict(_DIAG)
    _DIAG.update({u"noop": True, u"from": u"9.0.8", u"to": u"9.0.8", u"stamp_to": u"S2"})
    _n7 = final_note(0, type("_NS", (), {"no_restart": True})()) or u""
    _n7_ok = (u"已是最新" in _n7) and (u"⛔ 动一物" in _n7) and (u"已就位" not in _n7)
    ok &= _n7_ok
    print(u"[%s] 正控七：早返之辞（已是最新 ∧ ⛔ 动一物）＝ %s" % (u"OK" if _n7_ok else u"FAIL", _n7))
    _DIAG.update(_s7)
    _s8 = dict(_DIAG)
    _DIAG.update({u"reissue": True, u"to": u"9.0.8", u"stamp_from": u"S1", u"stamp_to": u"S2"})
    _n8 = final_note(0, type("_NS", (), {"no_restart": False})()) or u""
    _n8_ok = ((u"重发" in _n8) and (u"S1" in _n8) and (u"S2" in _n8)
              and (u"已是最新" not in _n8))
    ok &= _n8_ok
    print(u"[%s] 正控八：重发之辞（载二戳 · ⛔ 书「已是最新」）＝ %s" % (u"OK" if _n8_ok else u"FAIL", _n8))
    _DIAG.update(_s8)
    return 0 if ok else 2



def _tail_stream(a):
    u"""尾话之去处：`--json` ⇒ **stderr**（护「JSON 为末行」之机读之约 · 承 pm_1620 之回执）；否则 ⇒ stdout。"""
    return sys.stderr if a.json else sys.stdout


def _tail(a, rc, t0):
    u"""尾话（**一处定形** · 承 pm_1762 §二.2）：昔生于 `pa-update.cmd` 之 `python -c` 字面 ⇒
    其副本在用户机**永冻**（随 `.cmd` 而止）⇒ 今移入本器（**随版本更新**）。

    ⚠ 干跑 ⛔ 称「成」（承「一名一义」：未动盘 ⇒ 「演毕」）。
    """
    sec = int(time.time() - t0)
    if rc == 0 and not a.go:
        line = u"[PA] 演毕（⛔ 动盘）—— 加 `--go` 真办"
    elif rc == 0 and _DIAG.get(u"noop"):
        # ⭐ pm_1848 §三.3：早返之实**明书**（承「⛔ 以『已就位』之似做充『未动』」）
        line = (u"[PA] 成（未动一物 —— 已是最新 %s · 戳 %s）"
                % (_DIAG.get(u"to") or _DIAG.get(u"from") or u"—", _DIAG.get(u"stamp_to") or u"—"))
    elif rc == 0:
        line = u"[PA] 成 —— 若上文言「已是最新」⇒ 未动一物。"
    else:
        line = u"[PA] [FAIL] ⛔ 成 —— 看上之诸行（若已回滚，诸件当复其旧；服之态见上）"
    o = _tail_stream(a)
    o.write(u"[PA] elapsed %d s\n" % sec)
    o.write(u"[PA] exit=%d\n" % rc)
    o.write(line + u"\n")
    o.flush()


def main(argv=None):
    ap = argparse.ArgumentParser(description=u"应用增量包（甲-P0 之器二）")
    ap.add_argument(u"--root", default=ROOT)
    ap.add_argument(u"--src", default=None, help=u"更新源之根（覆声明 · 承「源须可配」）")
    ap.add_argument(u"--manifest", default=None, help=u"本机之清单（离线之径）")
    ap.add_argument(u"--staged", default=None, help=u"已下之树（供试）")
    ap.add_argument(u"--force", action="store_true")
    ap.add_argument(u"--no-restart", action="store_true")
    ap.add_argument(u"--go", action="store_true")
    ap.add_argument(u"--json", action="store_true")
    ap.add_argument(u"--self-test", action="store_true")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.root)
    _add_core(root)
    if a.self_test:
        return self_test()
    # ⭐ pm_1799 §二.2（**器之输出落件**）：端以 `DEVNULL` 起本器 ⇒ 昔之 FAIL 全弃
    #   ⇒ 真因无一处可查（净机 rc=2 之病）。今本器**自落**其输出（原流 ＋ sink）⇒ 端弃不掉。
    _so, _se = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = _Tee(_so, _SINK), _Tee(_se, _SINK)
    try:
        return _real_main(a, root)
    finally:
        sys.stdout, sys.stderr = _so, _se
        _SINK.close()


def _real_main(a, root):
    # ⭐ pm_1684 §四：器为「跑」之态之**唯一写方**
    #   （起 ⇒ running；终 ⇒ done ／ failed）—— 端（`POST /v9/pa/update`）唯读之
    #   ⇒ 跨「停 → 换 → 起」可察终态（网关自停 ⇒ 本进程内 ⛔ 可察）。
    #   ⚠ 惟真办（`--go`）落态：干跑 ⛔ 占「跑」之名（承「一名一义」）。
    _ur = None
    if a.go:
        try:
            from core.lib import update_run as _ur                       # noqa: N806
        except Exception:                                             # noqa: BLE001 — 态 ⛔ 阻器
            _ur = None
    if _ur is not None:
        _ur.begin(root)
    _t0 = time.time()                                        # ⭐ 尾话之「时长」之源（一处出）
    try:
        rc = run(a)
    except SystemExit:
        raise
    except BaseException as _e_run:                          # noqa: BLE001 — 照实报因
        # ⭐ pm_1793 §一（一手 · 本席之新病）：器若**崩**（⛔ 返）⇒ 其下之 finish 到不了
        #   ⇒ 盘上之 restart（_mark_restart 所落）／running 相位**长挂**
        #   ⇒ 面恒显「正在重启…」（唯 STALE_S ＝ 30 min 后自愈）—— 误报。
        #   ⇒ 崩亦须**收相位**（落 failed ＋ 原样报因 ／ 承「失败即报根」）。
        rc = 2
        print(u"[失败] 器崩（%s: %s）⇒ 相位已收（落 failed · 免得面长挂「正在重启」）"
              % (type(_e_run).__name__, _e_run), flush=True)
    if _ur is not None:
        # ⭐ pm_1799 §二.1 ／ 承 pm_1790 §二.3（**to 起时定死**）：清单一旦取到 ⇒ `to` 即其版；
        #   `--no-restart` 之路 ⛔ 走 `restart()` ⇒ 昔 `to` 落回「今之盘号」＝ `from`
        #   ⇒ 「从哪升到哪」不可考（9.0.7 ⇒ 9.0.7 之假记）。
        _ur.finish(root, rc, note=final_note(rc, a), note_why=fail_why(rc),
                   to_version=(_DIAG[u"to"] or None))
    _tail(a, rc, _t0)                                        # ⭐ 尾话：随版本更新（承 pm_1762 §二.2）
    return rc


if __name__ == u"__main__":
    sys.exit(main())
