# -*- coding: utf-8 -*-
r"""probe_alive.py -- PA 网关「存活探针」（P5 稿 · 2026-10-05 · 技术总监席）

来由（记事 · 病单 P5）：
  · 2026-10-05 晨：网关 `08:43:50` **静默死**（console 无 `traceback` · pid 消失）；
    我一手复其生命期印：今日 `nowindow start` **25 段**，其中 **9 段**尾以
    「💭 进入梦境」无后继「📚 整理记忆」终 ⇒ ⭐ **死于 dreaming**（正控：`E↔T` 距中位 `60 s`）。
  · 故本器**外置**（⛔ 进程内）· **报刻** · **死即告**（`pid 文件 ⟷ /health` 双向对）。
  · ⭐ 并立：**起停 ／ 自死 皆须留痕**（谁 ／ 刻 ／ `pid` ／ 因 ／ 日志尾）⇒ 本器为**唯一落痕口**。

落点（归平台线）：`scripts\win_pa\probe_alive.py`
用法：
  python -X utf8 scripts\win_pa\probe_alive.py                  # 探一次（给人看 ＋ 落痕）
  python -X utf8 scripts\win_pa\probe_alive.py --quiet          # 只落痕（供计划任务）
  python -X utf8 scripts\win_pa\probe_alive.py --note start --by 技术总监 --why <因>   # 起留痕（谁／刻／pid／因）
  python -X utf8 scripts\win_pa\probe_alive.py --note stop --by <席> --target-pid <被停之 pid>   # ⭐ 停服留痕（承 PM 046 §四.4）
  python -X utf8 scripts\win_pa\probe_alive.py --self-test

退出码：0 = 活 ｜ 2 = 死 ∨ 陈旧 ∨ 半死（**死即告**）｜ 1 = 探针自身错 ｜ 3 = 用法错

判据：
  甲. **双向对**：`logs\win_pa.pid` 之 pid **真在**（`OpenProcess` ＋ `STILL_ACTIVE`）⟷ `/health` 200
      四态：活 ／ 死（pid ⛔ 在 ∧ 端口 ⛔ 在）／ 陈旧 pid（pid ⛔ 在 ∧ 端口在 ⇒ 疑他实例）／ 半死（pid 在 ∧ 端口 ⛔ 在）
  乙. **梦境未完**：console 段（按 `=== nowindow start` 切）内逐 agent 配「💭 进入梦境 ↔ 📚 整理记忆」
      ⇒ 段尾留「进入」者 ＝ **死时在 dreaming**（正控：`E↔T` 距窄 · 我一手 8940 对中 8935 落 `60 s` 桶）
  丙. **留痕**：`logs\win_pa_life.jsonl`（`ts` ／ `state` ／ `pid` ／ `dream_pending` ／ `tail`）

⚠ 界：本器**唯只读**网关（⛔ 起停）｜⛔ 碰凭据｜⛔ 写 `data\`。
"""
import argparse
import datetime
import json
import os
import re
import socket
import sys
import urllib.request

if sys.stdout is not None:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HOST = '127.0.0.1'
TAIL_BYTES = 2 * 1024 * 1024
SESS_RE = re.compile(r'^=== nowindow start (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) ===$')
LINE_RE = re.compile(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[([^\]]+)\] \[INFO\] (.*)$')
DREAM_IN = u'\U0001f4ad \u8fdb\u5165\u68a6\u5883'
DREAM_TIDY = u'\U0001f4da \u6574\u7406\u8bb0\u5fc6'
ALIVE_STATES = ('alive',)
STATES_CN = {'alive': u'活', 'dead': u'死', 'stale_pid': u'陈旧 pid（疑他实例）',
             'half_dead': u'半死（pid 在 · 端口 ⛔ 在）', 'health_bad': u'端口在 · /health 非 200',
             'no_pidfile': u'无 pid 文件'}


def resolve_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def now_iso():
    return datetime.datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M:%S%z')


def caller_chain():
    """调用者：父 pid ＋ cmdline（⭐ 2026-10-05 承 PM 046 §四.4：「谁起」须落痕）。"""
    out = {'ppid': None, 'parent_name': None, 'parent_cmdline': None, 'err': None}
    try:
        import psutil
        pa = psutil.Process(os.getpid()).parent()
        if pa is not None:
            out['ppid'] = pa.pid
            try:
                out['parent_name'] = pa.name()
            except Exception:
                pass
            try:
                cl = pa.cmdline()
                out['parent_cmdline'] = ' '.join(cl)[:300] if cl else None
            except Exception:
                pass
    except Exception as e:
        out['err'] = '%s: %s' % (type(e).__name__, e)
    return out


def read_tail(path, nbytes=TAIL_BYTES):
    if not os.path.exists(path):
        return u''
    with open(path, 'rb') as f:
        f.seek(0, os.SEEK_END)
        n = f.tell()
        f.seek(max(0, n - nbytes))
        return f.read().decode('utf-8', 'replace')


def read_pid(path):
    if not os.path.exists(path):
        return None
    try:
        return int(open(path, encoding='ascii').read().strip())
    except Exception:
        return None


def pid_alive(pid):
    if not pid:
        return False
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, int(pid))       # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            if not k.GetExitCodeProcess(h, ctypes.byref(code)):
                return False
            return code.value == 259                     # STILL_ACTIVE
        finally:
            k.CloseHandle(h)
    except Exception:
        return False


def tcp_open(port, timeout=1.5):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        return s.connect_ex((HOST, port)) == 0
    finally:
        s.close()


def http_health(port, timeout=3):
    try:
        with urllib.request.urlopen('http://%s:%d/health' % (HOST, port), timeout=timeout) as r:
            return (r.status == 200), (r.read().decode('utf-8', 'replace')[:120])
    except Exception as e:
        return False, u'（%s: %s）' % (type(e).__name__, e)


def last_session(text):
    seg = None
    for raw in text.split('\n'):
        l = raw.strip('\r').strip()
        m = SESS_RE.match(l)
        if m:
            seg = (m.group(1), [])
            continue
        if seg is None:
            continue
        g = LINE_RE.match(l)
        if g:
            seg[1].append((g.group(1), g.group(2), g.group(3)))
    return seg


def dream_pending(events):
    op = {}
    for ts, ag, msg in events:
        if msg.startswith(DREAM_IN):
            op[ag] = ts
        elif msg.startswith(DREAM_TIDY):
            op.pop(ag, None)
    return sorted(op.items(), key=lambda kv: kv[1])


def judge(pidfile_pid, pid_ok, port_open, health_ok, pending):
    reasons = []
    if pidfile_pid is None:
        state = 'no_pidfile'
    elif pid_ok and port_open and health_ok:
        state = 'alive'
    elif pid_ok and not port_open:
        state = 'half_dead'
    elif not pid_ok and port_open:
        state = 'stale_pid'
    elif pid_ok and port_open and not health_ok:
        state = 'health_bad'
    else:
        state = 'dead'
    if state != 'alive':
        reasons.append(u'状态＝%s' % STATES_CN.get(state, state))
    if pending and state != 'alive':
        reasons.append(u'死时在 dreaming（梦境未完：%d 个 agent 之「进入梦境」无后继「整理记忆」⇒ 首 %s）'
                       % (len(pending), pending[0][1]))
    if not pending and state != 'alive':
        reasons.append(u'梦境已配平（⛔ 死于 dreaming）⇒ 死因另寻（无 traceback ⇒ 恐 C 级崩 ／ 停服路）')
    rc = 0 if state in ALIVE_STATES else 2
    return state, reasons, rc


def collect(root, port_default=5102):
    pidfile = os.path.join(root, 'logs', 'win_pa.pid')
    try:
        sys.path.insert(0, root)
        from core.lib.port_config import gateway_port
        port = int(gateway_port())
    except Exception:
        port = port_default
    # ⭐ pm_1453 §三.4：名随端口（旧码硬编 5102 ⇒ 端口改后名实不符）
    console = os.path.join(root, 'logs', 'gateway_%d_console.log' % port)
    pidfile_pid = read_pid(pidfile)
    pid_ok = pid_alive(pidfile_pid)
    open_ = tcp_open(port)
    ok_h, hb = (False, u'') if not open_ else http_health(port)
    text = read_tail(console)
    seg = last_session(text)
    pending = dream_pending(seg[1]) if seg else []
    tail = [l.strip('\r') for l in text.split('\n') if l.strip()][-6:]
    return dict(pidfile_pid=pidfile_pid, pid_ok=pid_ok, port=port, port_open=open_,
                health_ok=ok_h, health_body=hb, session=(seg[0] if seg else None),
                pending=pending, tail=tail, console=console, pidfile=pidfile)


def life_path(root):
    return os.path.join(root, 'logs', 'win_pa_life.jsonl')


def append_life(root, rec):
    p = life_path(root)
    if os.path.exists(p) and os.path.getsize(p) > 2 * 1024 * 1024:
        os.replace(p, p + '.1')
    with open(p, 'ab') as f:
        f.write((json.dumps(rec, ensure_ascii=False) + u'\n').encode('utf-8'))
    return p


def last_life(root):
    p = life_path(root)
    if not os.path.exists(p):
        return None
    last = None
    for raw in open(p, 'rb').read().decode('utf-8', 'replace').split('\n'):
        if raw.strip():
            last = raw
    try:
        return json.loads(last) if last else None
    except Exception:
        return None


def selftest():
    hits = []

    def say(ok, name):
        print(u'  %s %s' % (u'✓' if ok else u'✗', name))
        hits.append(bool(ok))

    st, rs, rc = judge(123, True, True, True, [])
    say(st == 'alive' and rc == 0, u'正控：pid 在 ＋ 端口在 ＋ /health 200 ⇒ 活（rc=0）')
    st, rs, rc = judge(123, False, False, False, [])
    say(st == 'dead' and rc == 2 and any(u'死' in x for x in rs), u'反例：pid ⛔ 在 ∧ 端口 ⛔ 在 ⇒ 死（rc=2）')
    st, rs, rc = judge(123, False, True, True, [])
    say(st == 'stale_pid' and rc == 2 and any(u'陈旧' in x for x in rs), u'反例：陈旧 pid（pid ⛔ 在 ∧ 端口在）⇒ rc=2')
    st, rs, rc = judge(123, True, False, False, [])
    say(st == 'half_dead' and rc == 2, u'反例：半死（pid 在 ∧ 端口 ⛔ 在）⇒ rc=2')
    st, rs, rc = judge(None, False, False, False, [])
    say(st == 'no_pidfile' and rc == 2, u'反例：无 pid 文件 ⇒ rc=2')
    p7 = [(u'chat_agent', u'2026-10-05 08:43:16')] * 7
    st, rs, rc = judge(123, False, False, False, p7)
    say(rc == 2 and any(u'dreaming' in x for x in rs), u'反例：梦境未完 ＋ 死 ⇒ 报「死时在 dreaming」')
    st, rs, rc = judge(123, False, False, False, [])
    say(rc == 2 and any(u'配平' in x for x in rs), u'正控：梦境配平 ＋ 死 ⇒ ⛔ 报 dreaming（死因另寻）')
    fx = (u'=== nowindow start 2026-10-05 08:42:01 ===\n'
          u'[2026-10-05 08:43:16] [chat_agent] [INFO] ' + DREAM_IN + u' (第1次)\n'
          u'[2026-10-05 08:43:16] [code_agent_v4] [INFO] ' + DREAM_IN + u' (第1次)\n'
          u'[2026-10-05 09:10:00] [chat_agent] [INFO] ' + DREAM_TIDY + u'...\n'
          u'[2026-10-05 09:10:00] [code_agent_v4] [INFO] ' + DREAM_TIDY + u'...\n')
    seg = last_session(fx)
    say(seg[0] == u'2026-10-05 08:42:01' and dream_pending(seg[1]) == [],
        u'正控：段识别 ＋ 配对（2 进 2 整 ⇒ 未配 0）')
    fx2 = fx.replace(u'[2026-10-05 09:10:00] [code_agent_v4] [INFO] ' + DREAM_TIDY + u'...\n', u'')
    say(len(dream_pending(last_session(fx2)[1])) == 1, u'反例：删一条「整理记忆」⇒ 未配 1（须点名）')
    fx3 = fx + u'=== nowindow start 2026-10-05 09:19:23 ===\n'
    say(last_session(fx3)[0] == u'2026-10-05 09:19:23' and last_session(fx3)[1] == [],
        u'正控：取**末段**（新 start 后旧事件不计）')
    ch = caller_chain()
    say(ch.get('ppid') == os.getppid(), u'正控：调用者之父 pid ＝ os.getppid()（err=%s）' % (ch.get('err') or u'—'))
    n, t = sum(1 for c in hits if c), len(hits)
    print(u'=== 探针自测 %d/%d 通过（%s）===' % (n, t, u'rc=0' if n == t else u'rc=2'))
    return 0 if n == t else 2


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--root', default=u'')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--note', default=u'', choices=[u'', u'start', u'stop'])
    ap.add_argument('--by', default=u'')
    ap.add_argument('--why', default=u'')
    ap.add_argument('--target-pid', dest='target_pid', type=int, default=0)
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return selftest()
    root = a.root or resolve_root()
    try:
        if a.note:
            if not a.by:
                print(u'[用法错] --note 须并给 --by（谁）（rc=3）')
                return 3
            rec = {'ts': now_iso(), 'event': a.note, 'by': a.by, 'why': a.why,
                   'pidfile_pid': read_pid(os.path.join(root, 'logs', 'win_pa.pid')),
                   'target_pid': (a.target_pid or None), 'caller': caller_chain()}
            p = append_life(root, rec)
            print(u'[留痕] %s ／ %s ／ pid=%s ／ 因=%s ⇒ %s'
                  % (rec['ts'], rec['event'], rec['pidfile_pid'], rec['why'] or u'—', p))
            return 0
        c = collect(root)
        state, reasons, rc = judge(c['pidfile_pid'], c['pid_ok'], c['port_open'], c['health_ok'], c['pending'])
        rec = {'ts': now_iso(), 'event': u'probe', 'state': state,
               'pidfile_pid': c['pidfile_pid'], 'pid_alive': c['pid_ok'], 'port': c['port'],
               'port_open': c['port_open'], 'health': c['health_ok'], 'session': c['session'],
               'dream_pending': [{'agent': ag, 'ts': ts} for ag, ts in c['pending'][:7]],
               'caller': caller_chain(), 'tail': c['tail']}
        prev = last_life(root)
        changed = (prev is None or prev.get('state') != state or prev.get('pidfile_pid') != c['pidfile_pid']
                   or prev.get('event') != u'probe')
        if changed or a.force:
            append_life(root, rec)
        if not a.quiet:
            print(u'[探] 刻=%s ／ pid 文件=%s ／ pid 真在=%s ／ 端口 %d=%s ／ /health=%s ／ 段=%s'
                  % (rec['ts'], c['pidfile_pid'], c['pid_ok'], c['port'], c['port_open'],
                     c['health_ok'], c['session']))
            print(u'[梦境] 未完 %d 个%s' % (len(c['pending']),
                                        (u'（' + u' · '.join(u'%s@%s' % (ag, ts) for ag, ts in c['pending'][:7]) + u'）')
                                        if c['pending'] else u''))
            print(u'[判] %s%s ｜ %s' % (STATES_CN.get(state, state),
                                        u'' if rc == 0 else u'（死即告）',
                                        u' · '.join(reasons) if reasons else u'—'))
            if rc != 0:
                print(u'[日志尾] ' + u' ⟂ '.join(c['tail'][-3:]))
            print(u'[痕] %s（%s）' % (life_path(root), u'已记' if (changed or a.force) else u'同态 · ⛔ 重记'))
        return rc
    except Exception as e:
        print(u'[探针自身错] %s: %s（rc=1）' % (type(e).__name__, e))
        return 1


if __name__ == '__main__':
    sys.exit(main())