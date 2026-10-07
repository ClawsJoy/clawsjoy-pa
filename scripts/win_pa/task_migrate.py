# -*- coding: utf-8 -*-
u'''task_migrate.py —— 计划任务之「形」自检 ＋ 迁移（pm_1877 §二 之令 · 归 9.0.11 · 技术总监席 f202f89 · 2026-10-08）。

【病（一手 · pm_1877 §一）】全仓 `schtasks /create` 之**唯一**落点 ＝
  `scripts/win_pa/install_win_pa.py:477`（**安装器** · 一手复）⇒ 任务之形**唯安装时定一次**
  ⇒ 净机（数日前所装）之任务**仍旧形**（裸 `cmd` ／ 裸 `python.exe`）⇒ 其宿主 `svchost`
  （**无控制台**）起控制台子系统之子 ⇒ Windows **新开**一控制台窗 ＝「CMD 闪屏」
  ⇒ ⭐ 本批（9.0.10）之闪屏修**在净机 ⛔ 生效**（其**脚本**已新 ∧ 其**任务**仍旧）。

【治（**一处定形**）】读本机之 `ClawsJoy_*` 任务（`schtasks /query /tn 〈名〉 /xml ONE`）⇒
  凡 `Command` ⛔ 为 `wscript.exe`（＝旧形）⇒ **迁**：逐任务备份 XML ⇒ 按新形重注册 ⇒ **回读校验**。
  ⭐ **唯动 `Command` ／ `Arguments`** —— 以**旧 XML 之往返**改之（`Triggers` ／ `Settings` ／
  `Principals` ／ `RegistrationInfo` **逐行不动**）⇒ ⛔ 以 `/create /tr` 重建（那会重置其余 ·
  承 pm_1877 §二.2⒝）。形已新 ⇒ **no-op**（**幂等** · ⛔ 每次更新皆重注册 · 承 §二.1⒞）。

⚠ 迁移败 ⇒ **照实报**（⛔ 静默）∧ ⛔ **阻更新** ∧ ⛔ 回滚已装之载荷（**二者独立** · 承 §二.1⒟）。
⚠ ⛔ 注册**新**任务 —— 那是安装器之职（`install_win_pa.task_items()`）；本器唯**迁既存者**。

用法：
  python -X utf8 scripts/win_pa/task_migrate.py                 # 干跑（⛔ 动机）
  python -X utf8 scripts/win_pa/task_migrate.py --go            # 真迁
  python -X utf8 scripts/win_pa/task_migrate.py --go --names <名>   # 唯迁某几件（⛔ 扫全）
  python -X utf8 scripts/win_pa/task_migrate.py --self-test     # 自证（离机 · 假跑器）
'''
import argparse
import json
import os
import re
import sys
import tempfile
import time
import xml.dom.minidom

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
V9 = os.path.dirname(os.path.dirname(HERE))
BS = chr(92)
DQ = chr(34)
SQ = chr(39)
PREFIX = BS + u'ClawsJoy_'
SHELL_VBS = os.path.join(HERE, u'静默启动.vbs')
SHELL_HOST = u'wscript.exe'
BOM16 = bytes([255, 254])
BOM8 = bytes([239, 187, 191])

RESTORE_CMD = u'schtasks /create /tn 〈名〉 /xml 〈备份件〉 /f'

try:
    from _proc import run_hidden as _run_hidden
except Exception:                                                   # noqa: BLE001 — 照实退朴素形
    _run_hidden = None


def run(cmd, **kw):
    u'''跑一条外部命令 ⇒ CompletedProcess（**恒并窗隐** · 一处定形 · 承 scripts/win_pa/_proc.py）。'''
    if _run_hidden is not None:
        return _run_hidden(cmd, **kw)
    import subprocess as _sp
    kw['creationflags'] = (int(kw.get('creationflags', 0) or 0)
                           | int(getattr(_sp, 'CREATE_NO_WINDOW', 0) or 0))
    return _sp.run(cmd, **kw)



RE_COMMAND = re.compile(u'<Command[^>]*>(.*?)</Command>', re.S)
RE_ARGUMENTS = re.compile(u'<Arguments[^>]*>(.*?)</Arguments>', re.S)


def xml_escape(s):
    u'''文本内容之转义（`&` ／ `<` ／ `>` —— 引号于内容中合法 ⇒ ⛔ 转）。'''
    return (s or u'').replace(u'&', u'&amp;').replace(u'<', u'&lt;').replace(u'>', u'&gt;')


def xml_unescape(s):
    return ((s or u'').replace(u'&lt;', u'<').replace(u'&gt;', u'>')
            .replace(u'&quot;', DQ).replace(u'&apos;', SQ).replace(u'&amp;', u'&'))


def parse_action(xml_text):
    u'''取 `(Command 之值, Arguments 之值 ∨ None)` ⇒ 无 `<Command>` ⇒ `(None, None)`。'''
    m = RE_COMMAND.search(xml_text or u'')
    if not m:
        return None, None
    a = RE_ARGUMENTS.search(xml_text)
    return xml_unescape(m.group(1)), (xml_unescape(a.group(1)) if a else None)


def normalize_command(command):
    u'''Command 之值 ⇒ **去外层引号**（schtasks 常书 `"C:\\Program Files\\…\\python.exe"`）——
    ⛔ 否则重打包时会把原引号再包一层（⇒ 子进程之 argv 讹 · 一手：我 1877 之真机探逮）。
    内层之引号**属路径之实** ⇒ ⛔ 去。'''
    c = (command or u'').strip()
    if len(c) >= 2 and c[0] == DQ and c[-1] == DQ:
        c = c[1:-1]
    return c


def host_of(command):
    return os.path.basename(normalize_command(command)).lower()


def is_new_form(command):
    u'''新形之判据**唯一** ＝ 宿主为 `wscript.exe`（与 `install_win_pa.silent_task_cmd` 同形）。'''
    return host_of(command) == SHELL_HOST


def quote(x):
    x = u'' if x is None else str(x)
    return DQ + x.replace(DQ, BS + DQ) + DQ


def split_argv(s):
    u'''Windows 式之切（引号内之空白 ⛔ 断）⇒ 去外层引号 · 去空片。'''
    out = []
    cur = []
    q = False
    for ch in (s or u''):
        if ch == DQ:
            q = not q
            cur.append(ch)
        elif ch in u' \t' and not q:
            if cur:
                out.append(u''.join(cur))
                cur = []
        else:
            cur.append(ch)
    if cur:
        out.append(u''.join(cur))
    res = []
    for t in out:
        if len(t) >= 2 and t[0] == DQ and t[-1] == DQ:
            t = t[1:-1]
        if t:
            res.append(t)
    return res


def build_new_action(argv, vbs=None):
    u'''新形之动作 ⇒ `(Command, Arguments)`（⛔ 另造 · 与 `silent_task_cmd` 同物）。'''
    vbs = vbs or SHELL_VBS
    parts = [u'//B', quote(vbs)] + [quote(x) for x in argv]
    return SHELL_HOST, u' '.join(parts)


def xml_ok(text):
    u'''旧 ／ 新 XML 之**合形**判（⛔ 以坏件覆盖好件 —— 承 pm_1877 §二.2 之反控）。'''
    if not (text or u'').strip():
        return False, u'为空'
    try:
        xml.dom.minidom.parseString(text.encode('utf-16', 'xmlcharrefreplace'))
        return True, u''
    except Exception as e:                                          # noqa: BLE001 — 照实报因
        return False, u'%s: %s' % (type(e).__name__, str(e)[:80])


def plan_migration(xml_text, vbs=None, need_vbs=True):
    u'''**纯函数**（⛔ 触机）：旧 XML ⇒ `(verdict, new_xml ∨ None, why)`。
    verdict ∈ `migrated` ／ `noop` ／ `reject`。'''
    vbs = vbs or SHELL_VBS
    ok, why = xml_ok(xml_text)
    if not ok:
        return u'reject', None, u'旧 XML ⛔ 合形（%s）⇒ ⛔ 迁' % why
    cmd, args = parse_action(xml_text)
    if not cmd:
        return u'reject', None, u'无 `<Command>` 元素 ⇒ 形不可辨（⛔ 动）'.replace(u'`', u'')
    if is_new_form(cmd):
        return u'noop', xml_text, u'已新形（Command ＝ wscript.exe）⇒ ⛔ 动'
    if need_vbs and not os.path.isfile(vbs):
        return u'reject', None, u'静默壳 ⛔ 在：%s' % vbs
    argv = [normalize_command(cmd)] + split_argv(args or u'')
    new_cmd, new_args = build_new_action(argv, vbs)
    m = RE_COMMAND.search(xml_text)
    out = xml_text[:m.start(1)] + xml_escape(new_cmd) + xml_text[m.end(1):]
    m2 = RE_ARGUMENTS.search(out)
    if m2:
        out = out[:m2.start(1)] + xml_escape(new_args) + out[m2.end(1):]
    else:
        m3 = RE_COMMAND.search(out)
        i = out.index(u'</Command>', m3.start())
        out = out[:i] + u'<Arguments>' + xml_escape(new_args) + u'</Arguments>' + out[i:]
    ok2, why2 = xml_ok(out)
    if not ok2:
        return u'reject', None, u'新 XML ⛔ 合形（%s）⇒ ⛔ 迁' % why2
    return u'migrated', out, u'旧形 %s ⇒ 新形 %s' % (cmd, new_cmd)


def _auto_decode(raw):
    u'''按候选**严格**试译 ⇒ `(text, enc)`（⛔ 硬编码 ／ ⛔ 猜）。

    ⚠ `schtasks` 之输出码页**随「调用者之控制台输出码页」而变** —— 一手（我 1877）：本机
      `GetACP=936` ∧ 我之会话 `GetConsoleOutputCP=65001` ⇒ 其 `/fo csv` 与 `/xml` 之输出**皆 UTF-8**
      （`cp936` 于 `0xae` 即败）；而既报之患 ／ 无控制台之更新路（服务所起）⇒ 或落 ANSI。
      ⇒ ⭐ 唯**自动辨**方通（utf-8 先 —— 最具体：cp936 之汉字极罕为合法 utf-8）。
    ⚠ 承 pm_1877 §二.4 我一手之器病：硬编码 utf-8 译 ANSI ⇒ 中文任务名讹 ⇒ `/query /tn` 以讹名问 ⇒ rc=1。
    '''
    if isinstance(raw, str):
        return raw, 'utf-8'
    b = raw or b''
    if b[:2] == BOM16:
        return b.decode('utf-16'), 'utf-16'
    if b[:3] == BOM8:
        return b.decode('utf-8-sig'), 'utf-8-sig'
    for enc in ('utf-8', 'mbcs', 'cp936'):
        try:
            return b.decode(enc), enc
        except (UnicodeDecodeError, LookupError):
            continue
    return b.decode('utf-8', 'replace'), 'utf-8'


def decode_xml(raw):
    u'''`schtasks /xml` 之输出之译码 ⇒ `(text, enc)`（自动辨 · 见 `_auto_decode`）。'''
    return _auto_decode(raw)


def encode_like(text, enc):
    u'''按 `enc` 回写（备份 ⇄ 新件皆用之 ⇒ 与所读之码页同 ⇒ 逐字节可复原）。'''
    if enc == 'utf-16':
        return text.encode('utf-16')
    if enc == 'utf-8-sig':
        return text.encode('utf-8-sig')
    if enc in ('mbcs', 'cp936'):
        return text.encode(enc, 'replace')
    return text.encode('utf-8')
def _attr(x):
    return DQ + str(x) + DQ


def _synth_old(name, tr):
    u'''造一件**旧形**之 XML（唯自证 ／ 齿用 —— ⛔ 触真任务）。'''
    toks = split_argv(tr)
    cmd = toks[0] if toks else u''
    args = u' '.join(toks[1:])
    return (u'<?xml version=' + _attr(u'1.0') + u' encoding=' + _attr(u'UTF-16') + u'?>'
            + u'<Task version=' + _attr(u'1.2') + u'>'
            + u'<RegistrationInfo><URI>' + xml_escape(name) + u'</URI></RegistrationInfo>'
            + u'<Triggers><TimeTrigger><StartBoundary>2026-01-01T00:00:00</StartBoundary>'
            + u'</TimeTrigger></Triggers>'
            + u'<Principals><Principal id=' + _attr(u'Author') + u'>'
            + u'<LogonType>InteractiveToken</LogonType></Principal></Principals>'
            + u'<Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>'
            + u'<DisallowStartIfOnBatteries>true</DisallowStartIfOnBatteries></Settings>'
            + u'<Actions><Exec><Command>' + xml_escape(cmd) + u'</Command>'
            + u'<Arguments>' + xml_escape(args) + u'</Arguments>'
            + u'<WorkingDirectory>' + xml_escape(os.path.dirname(cmd)) + u'</WorkingDirectory>'
            + u'</Exec></Actions></Task>')


def _decode_ansi(raw):
    u'''`schtasks` 之**文本**（`/fo csv`）之译码 ⇒ `text`（自动辨 · 见 `_auto_decode`）。'''
    return _auto_decode(raw)[0]


def list_tasks(prefix=None, runner=None, dups=None):
    u'''扫本机之 `〈prefix〉*` 任务 ⇒ 名之 list（`schtasks /query /fo csv /nh` · **去重**）。

    ⚠ schtasks 之文本输出码页**随调用者之控制台输出码页而变**（一手：我之会话为 UTF-8 ∧ 后台或为 ANSI）
      ⇒ ⛔ 硬编码（`_decode_ansi` 自动辨）—— 一手：我 1877 之器病即硬编码 utf-8 ⇒ 中文名讹 ⇒ `/query /tn` 以讹名问 ⇒ rc=1）。
    ⚠ 同名多行（一手：\\ClawsJoy_PA_HealthCheck 曾二行）⇒ 去重 ∧ 明书（承「凡报 N 处须先逐处列毕再数」）。'''
    prefix = PREFIX if prefix is None else prefix
    runner = runner or run
    r = runner(['schtasks', '/query', '/fo', 'csv', '/nh'], capture_output=True)
    raw = _decode_ansi(r.stdout)
    names = []
    seen = set()
    dup = []
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith(DQ):
            continue
        nm = line.split(DQ)[1]
        if not nm.startswith(prefix):
            continue
        if nm in seen:
            if nm not in dup:
                dup.append(nm)
            continue
        seen.add(nm)
        names.append(nm)
    if dups is not None:
        dups.extend(dup)
    return names


def query_xml(name, runner=None):
    u'''读一任务之 XML ⇒ `(bytes ∨ None, why)`。'''
    runner = runner or run
    r = runner(['schtasks', '/query', '/tn', name, '/xml', 'ONE'], capture_output=True)
    if r.returncode != 0:
        return None, u'query rc=%s' % r.returncode
    return (r.stdout or b''), u''


def restore_cmd(name, bak):
    u'''复原之路（**一条命令** · 承 pm_1877 §二.2⒟）—— ⛔ 手改。'''
    return u'schtasks /create /tn %s /xml %s /f' % (name, bak)


def migrate(root=None, dry=True, names=None, runner=None, backup_root=None,
            vbs=None, now=None, prefix=None):
    u'''扫 ／ 判 ／ 迁。⇒ `(rc, lines, report)`。rc 0 ＝ 皆成 ∨ no-op；2 ＝ 有败 ∨ 有不可迁。

    ⚠ **迁移败 ⛔ 抛**（照实报 · 由调用者定是否阻更新 —— 承 pm_1877 §二.1⒟）。'''
    root = root or V9
    vbs = vbs or SHELL_VBS
    runner = runner or run
    stamp = now or time.strftime('%Y%m%d_%H%M%S')
    dups = []
    scanned = list(names) if names is not None else list_tasks(prefix=prefix, runner=runner, dups=dups)
    rep = {'root': root, 'dry': bool(dry), 'vbs': vbs, 'bak': None, 'scanned': scanned,
           'dups': dups,
           'migrated': [], 'noop': [], 'rejected': [], 'failed': [], 'backup_files': []}
    lines = []
    if dups:
        lines.append(u'[task-migrate] ⚠ 重名 %d 件（同名多行 ⇒ 已去重 · 唯处理一次）：%s'
                     % (len(dups), u' ｜ '.join(dups)))
    if not scanned:
        lines.append(u'[task-migrate] 扫得 %s* 之任务 0 件 ⇒ 无物可迁（⛔ 注册新任务 —— 那是安装器之职）'
                     % (prefix if prefix is not None else PREFIX))
        return 0, lines, rep
    bdir = backup_root or os.path.join(root, 'logs', 'task_xml_bak')
    rep['bak'] = bdir
    lines.append(u'[task-migrate] 扫得 %d 任务 ｜ 壳 %s ｜ 备份 %s ｜ %s'
                 % (len(scanned), vbs, bdir, u'干跑（⛔ 动机）' if dry else u'真办'))
    for nm in scanned:
        raw, why = query_xml(nm, runner=runner)
        if raw is None:
            rep['failed'].append((nm, u'读 XML 败：%s' % why))
            lines.append(u'  %-30s 读 XML 败（%s）⇒ 照实报' % (nm, why))
            continue
        text, enc = decode_xml(raw)
        verdict, new_xml, why = plan_migration(text, vbs=vbs)
        if verdict == u'noop':
            rep['noop'].append(nm)
            lines.append(u'  %-30s no-op ｜ %s' % (nm, why))
            continue
        if verdict == u'reject':
            rep['rejected'].append((nm, why))
            lines.append(u'  %-30s ⛔ 不可迁 ｜ %s' % (nm, why))
            continue
        if dry:
            rep['migrated'].append(nm)
            lines.append(u'  %-30s 将迁（干跑 · ⛔ 动机）｜ %s' % (nm, why))
            continue
        bp = os.path.join(bdir, u'%s.%s.bak.xml' % (os.path.basename(nm), stamp))
        try:
            os.makedirs(bdir, exist_ok=True)
            with open(bp, 'wb') as f:
                f.write(encode_like(text, enc))
            with open(bp, 'rb') as f:
                _back = f.read()
            if _back != encode_like(text, enc):
                raise RuntimeError(u'备份回读 ⛔ 合形')
        except Exception as e:                                          # noqa: BLE001 — 照实报因
            rep['failed'].append((nm, u'备份败：%s: %s' % (type(e).__name__, str(e)[:70])))
            lines.append(u'  %-30s ⛔ 备份败（%s）⇒ ⛔ 迁（承 pm_1877 §二.2⒜）'
                         % (nm, str(e)[:70]))
            continue
        rep['backup_files'].append(bp)
        tmp = None
        try:
            fd, tmp = tempfile.mkstemp(suffix='.xml', prefix='tm1877_')
            os.close(fd)
            with open(tmp, 'wb') as f:
                f.write(encode_like(new_xml, enc))
            r = runner(['schtasks', '/create', '/tn', nm, '/xml', tmp, '/f'], capture_output=True)
            if r.returncode != 0:
                raise RuntimeError(u'/create rc=%s' % r.returncode)
            raw2, why2 = query_xml(nm, runner=runner)
            if raw2 is None:
                raise RuntimeError(u'回读败：%s' % why2)
            t2, _e2 = decode_xml(raw2)
            c2, _a2 = parse_action(t2)
            if not is_new_form(c2):
                raise RuntimeError(u'回读 ⛔ 合形（Command ＝ %s）' % (c2 or u'⛔ 读'))
            rep['migrated'].append(nm)
            lines.append(u'  %-30s 迁成 ｜ %s' % (nm, why))
            lines.append(u'      复原：%s' % restore_cmd(nm, bp))
        except Exception as e:                                          # noqa: BLE001 — 照实报因
            rep['failed'].append((nm, u'%s: %s' % (type(e).__name__, str(e)[:90])))
            lines.append(u'  %-30s ⛔ 迁败（%s）⇒ 照实报 ∧ ⛔ 阻更新（承 pm_1877 §二.1⒟）'
                         % (nm, str(e)[:90]))
        finally:
            if tmp and os.path.isfile(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
    rc = 2 if (rep['failed'] or rep['rejected']) else 0
    lines.append(u'[task-migrate] 果：迁 %d ｜ no-op %d ｜ ⛔ 不可迁 %d ｜ 败 %d ⇒ rc=%d'
                 % (len(rep['migrated']), len(rep['noop']), len(rep['rejected']),
                    len(rep['failed']), rc))
    for nm, why in rep['rejected']:
        lines.append(u'  ⛔ 不可迁（明书其名 ＋ 因）：%s ｜ %s' % (nm, why))
    return rc, lines, rep

class _R(object):
    u'''subprocess 之最小仿（⛔ 真跑）。'''
    def __init__(self, rc, out):
        self.returncode = rc
        self.stdout = out
        self.stderr = b''


TXT_CRLF = b'\r\n'


class _Fake(object):
    u'''假跑器（**离机** · ⛔ 触真任务）—— 只认 schtasks 之四形（query ／ query /xml ／ create /xml ／ create /tr）。'''
    def __init__(self, state, sticky=False, enc='utf-8', dup_names=None):
        self.state = dict(state)
        self.sticky = sticky
        self.enc = enc
        self.dup_names = set(dup_names or [])
        self.calls = []

    def creates(self):
        return [c for c in self.calls if '/create' in c]

    def __call__(self, cmd, **kw):
        self.calls.append(list(cmd))
        if not cmd or cmd[0] != 'schtasks':
            return _R(1, b'')
        if '/query' in cmd and '/xml' in cmd:
            nm = cmd[cmd.index('/tn') + 1]
            if nm not in self.state:
                return _R(1, b'')
            return _R(0, self.state[nm].encode('utf-16'))
        if '/query' in cmd:
            body = b''
            for nm in sorted(self.state):
                row = (DQ + nm + DQ).encode(self.enc, 'replace') + TXT_CRLF
                body += row
                if nm in self.dup_names:
                    body += row
            return _R(0, body)
        if '/create' in cmd and '/xml' in cmd:
            nm = cmd[cmd.index('/tn') + 1]
            if self.sticky:
                return _R(0, b'')
            with open(cmd[cmd.index('/xml') + 1], 'rb') as f:
                self.state[nm] = f.read().decode('utf-16')
            return _R(0, b'')
        if '/create' in cmd:
            nm = cmd[cmd.index('/tn') + 1]
            self.state[nm] = _synth_old(nm, cmd[cmd.index('/tr') + 1])
            return _R(0, b'')
        return _R(1, b'')


def _seg(t, tag):
    i = t.index(u'<' + tag + u'>')
    j = t.index(u'</' + tag + u'>') + len(tag) + 3
    return t[i:j]


def selftest():
    u'''自证（**离机** · 假跑器 ＋ 临时目录 ⇒ ⛔ 触真任务 ／ ⛔ 触本仓）—— 正控 ／ 一处定形 ／ 幂等 ／ 反控 ×5。'''
    import tempfile as _tf
    ok = True

    def res(label, got, want):
        nonlocal ok
        hit = (got == want)
        ok = ok and hit
        print(u'  %s %s ⇒ %s（期 %s）' % (u'OK ' if hit else u'X  ', label, got, want))

    tmp = _tf.mkdtemp(prefix=u'tm1877_st_')
    vbs = os.path.join(tmp, u'静默启动.vbs')
    with open(vbs, 'wb') as f:
        f.write(b'MOCK')
    py = os.path.join(tmp, u'python.exe')
    with open(py, 'wb') as f:
        f.write(b'MOCK')
    tname = BS + u'ClawsJoy_PA_MigTest'
    old = _synth_old(tname, quote(py) + u' -X utf8 -B ' + quote(os.path.join(tmp, u'probe.py')))

    print(u'[自证 1 判形（纯函数）]')
    res(u'wscript 之宿主 ⇒ 新形', is_new_form(u'C:' + BS + u'Windows' + BS + u'system32' + BS + u'WSCRIPT.EXE'), True)
    res(u'python.exe ⇒ 旧形', is_new_form(u'C:' + BS + u'py' + BS + u'python.exe'), False)
    res(u'新形之 XML ⇒ noop',
        plan_migration(_synth_old(tname, quote(u'C:' + BS + u'WSCRIPT.EXE') + u' //B x'), vbs=vbs)[0],
        u'noop')

    print(u'[自证 2 正控 · 真迁 ＋ 备份 ＋ 回读]')
    f1 = _Fake({tname: old})
    rc, lines, rep = migrate(root=tmp, dry=False, names=[tname], runner=f1, vbs=vbs)
    res(u'旧形 ⇒ 迁（rc）', rc, 0)
    res(u'migrated', rep['migrated'], [tname])
    res(u'rejected ／ failed 皆空', (rep['rejected'], rep['failed']), ([], []))
    c2, a2 = parse_action(f1.state[tname])
    res(u'新形之 Command', host_of(c2), u'wscript.exe')
    res(u'新形之 Arguments 首片', a2[:3], u'//B')
    res(u'备份 1 枚 ∧ 落 logs/task_xml_bak',
        (len(rep['backup_files']), os.path.basename(os.path.dirname(rep['backup_files'][0]))),
        (1, u'task_xml_bak'))
    with open(rep['backup_files'][0], 'rb') as f:
        _bk = f.read()
    res(u'备份逐字节 ＝ 旧 XML（同 enc）', _bk == encode_like(old, 'utf-16'), True)
    res(u'报中载复原之路', any(u'schtasks /create /tn' in l for l in lines), True)

    print(u'[自证 3 一处定形 · 三段逐行不动]')
    res(u'Principals 一字不动', _seg(f1.state[tname], u'Principals'), _seg(old, u'Principals'))
    res(u'Settings 一字不动', _seg(f1.state[tname], u'Settings'), _seg(old, u'Settings'))
    res(u'Triggers 一字不动', _seg(f1.state[tname], u'Triggers'), _seg(old, u'Triggers'))
    res(u'WorkingDirectory 照旧',
        _seg(f1.state[tname], u'WorkingDirectory'), _seg(old, u'WorkingDirectory'))

    print(u'[自证 4 幂等 · 再跑 ⇒ ⛔ 动]')
    before = len(f1.creates())
    rc2, _l2, rep2 = migrate(root=tmp, dry=False, names=[tname], runner=f1, vbs=vbs)
    res(u'再跑 rc 0', rc2, 0)
    res(u'no-op', rep2['noop'], [tname])
    res(u'⛔ 再 /create', len(f1.creates()) - before, 0)

    print(u'[自证 5 反控 · 不可迁 ⇒ 报因（⛔ 假成功）]')
    f2 = _Fake({tname: u'<Task><Actions><Exec><Path>x</Path></Exec></Actions></Task>'})
    rc3, _l3, rep3 = migrate(root=tmp, dry=False, names=[tname], runner=f2, vbs=vbs)
    res(u'无 Command ⇒ rc 2', rc3, 2)
    res(u'rejected 之名', [n for n, _w in rep3['rejected']], [tname])
    res(u'⛔ /create', len(f2.creates()), 0)
    f2b = _Fake({tname: u'<Task><Actions>'})
    rc3b, _l3b, rep3b = migrate(root=tmp, dry=False, names=[tname], runner=f2b, vbs=vbs)
    res(u'旧 XML 坏 ⇒ rc 2 ∧ 因指合形',
        (rc3b, any(u'合形' in w for _n, w in rep3b['rejected'])), (2, True))

    print(u'[自证 6 反控 · 壳 ⛔ 在 ⇒ 拒]')
    f3 = _Fake({tname: old})
    rc4, _l4, rep4 = migrate(root=tmp, dry=False, names=[tname], runner=f3,
                             vbs=os.path.join(tmp, u'no_such.vbs'))
    res(u'壳 ⛔ 在 ⇒ rc 2', rc4, 2)
    res(u'其因指「静默壳」', any(u'静默壳' in w for _n, w in rep4['rejected']), True)

    print(u'[自证 7 反控 · 回读 ⛔ 合形 ⇒ 咬（⛔ 假绿）]')
    f4 = _Fake({tname: old}, sticky=True)
    rc5, _l5, rep5 = migrate(root=tmp, dry=False, names=[tname], runner=f4, vbs=vbs)
    res(u'注册「成」而未动 ⇒ rc 2', rc5, 2)
    res(u'其因指「回读」', any(u'回读' in w for _n, w in rep5['failed']), True)

    print(u'[自证 8 反控 · 备份不可用 ⇒ ⛔ 迁]')
    f5 = _Fake({tname: old})
    blocker = os.path.join(tmp, u'blk')
    with open(blocker, 'wb') as f:
        f.write(b'x')
    rc6, _l6, rep6 = migrate(root=tmp, dry=False, names=[tname], runner=f5, vbs=vbs,
                             backup_root=os.path.join(blocker, u'sub'))
    res(u'备份败 ⇒ rc 2', rc6, 2)
    res(u'⛔ /create（无备份 ⛔ 迁）', len(f5.creates()), 0)
    res(u'其因指备份', any(u'备份' in w for _n, w in rep6['failed']), True)

    print(u'[自证 9 干跑 ⇒ ⛔ 动机]')
    f6 = _Fake({tname: old})
    rc7, _l7, rep7 = migrate(root=tmp, dry=True, names=[tname], runner=f6, vbs=vbs)
    res(u'干跑 ⇒ rc 0 ∧ 将迁 ∧ ⛔ /create', (rc7, rep7['migrated'], len(f6.creates())), (0, [tname], 0))

    print(u'[自证 10 扫 0 件 ⇒ 无物可迁（⛔ 注册新任务）]')
    f7 = _Fake({})
    rc8, lines8, _rep8 = migrate(root=tmp, dry=False, runner=f7, vbs=vbs)
    res(u'扫 0 ⇒ rc 0', rc8, 0)
    res(u'⛔ /create', len(f7.creates()), 0)
    res(u'其辞指「无物可迁」', any(u'无物可迁' in l for l in lines8), True)

    print(u'[自证 11 译码（⛔ 硬编码）· utf-8 ／ ANSI 之名皆正 ∧ 重名去重]')
    cn = BS + u'ClawsJoy_' + u'内容工坊_日报'
    res(u'utf-8 之名 ⇒ 译正', _decode_ansi(cn.encode('utf-8')), cn)
    res(u'ANSI(mbcs) 之名 ⇒ 译正', _decode_ansi(cn.encode('mbcs')), cn)
    res(u'utf-16 之 XML ⇒ enc 判对', decode_xml(cn.encode('utf-16'))[1], 'utf-16')
    f8 = _Fake({cn: old}, enc='utf-8', dup_names={cn})
    res(u'utf-8 之 list（重名 ⇒ 去重）', list_tasks(runner=f8), [cn])
    fa = _Fake({cn: old}, enc='mbcs', dup_names={cn})
    _dp = []
    res(u'ANSI 之 list（去重 ∧ 明书重名）',
        (list_tasks(runner=fa, dups=_dp), _dp), ([cn], [cn]))
    fg = _Fake({cn: old}, enc='mbcs')
    _dp2 = []
    res(u'ANSI 之单件（⛔ 伪重名）', (list_tasks(runner=fg, dups=_dp2), _dp2), ([cn], []))
    res(u'引号之 wscript ⇒ 仍判新形',
        is_new_form(DQ + u'C:' + BS + u'Windows' + BS + u'system32' + BS + u'WSCRIPT.EXE' + DQ), True)
    _qold = re.sub(u'<Command>[^<]*</Command>',
                   lambda _m: u'<Command>' + DQ + py + DQ + u'</Command>',
                   _synth_old(tname, py + u' -X utf8 -B ' + quote(os.path.join(tmp, u'probe.py'))), count=1)
    _vq, _nxq, _wq = plan_migration(_qold, vbs=vbs)
    res(u'引号之 Command ⇒ 新形 ⛔ 双层引号（一手：我 1877 真机探）',
        (_vq, (BS + DQ) not in _nxq, _nxq.count(py)), (u'migrated', True, 1))

    print(u'[总判] %s' % (u'PASS' if ok else u'FAIL'))
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--self-test', dest='selftest', action='store_true')
    ap.add_argument('--root')
    ap.add_argument('--names', nargs='*')
    ap.add_argument('--vbs')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--go', action='store_true')
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    rc, lines, rep = migrate(root=a.root, dry=not a.go, names=a.names, vbs=a.vbs)
    print(u'\n'.join(lines))
    if not a.go:
        print(u'[--] 干跑（⛔ 动机）—— 加 --go 真迁')
    print(u'⭐ 复原之路（一条命令 · 逐任务之备份件见上）：%s' % RESTORE_CMD)
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    return rc


if __name__ == '__main__':
    sys.exit(main())
