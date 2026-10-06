# -*- coding: utf-8 -*-
'''Win-PA 无窗口起停器 (CW line / CodexWindows / 2026-10-03)

老板 2026-10-03 令: 准「改成无窗口起法 (CREATE_NO_WINDOW)」-- 不留要人管的黑窗口.

用法:
    python scripts\\\\win_pa\\\\pa_nowindow.py start
    python scripts\\\\win_pa\\\\pa_nowindow.py stop
    python scripts\\\\win_pa\\\\pa_nowindow.py status

纪律:
  1. 端口真源 = config/system/system_unified.yaml (core.lib.port_config.gateway_port())
  2. 端口占用判据 = TCP 连测 (WSL2 转发端口在 netstat 里看不见 LISTENING)
  3. 起法 = CREATE_NO_WINDOW | DETACHED_PROCESS | CREATE_BREAKAWAY_FROM_JOB
     (2026-10-05 061 §一.3 真脱离: 不受起者 job 连坐; 若 job 不许 breakaway 则降级并大声告警)
     (2026-10-05 062 §一: ⒜ breakaway 被拒 => 派已注册之计划任务 ⒝ 拉起(真脱离); ⒝ 回程以派遣标记认亲(免环))
    ; stdout/stderr 追加 logs\\gateway_<端口>_console.log（名随端口 · pm_1453 §三.4）
  4. 用 python -u 起 (块缓冲会让 console 日志假零)
  5. PID 记 logs\\\\win_pa.pid (停时不靠 netstat)
  6. 起/查前 os.chdir(ROOT) -- 配置按 CWD 解析; 从别处起 ⇒ [未配置 ⇒ 拒启] (2026-10-05 事故)
  7. 起前先跑 preflight_start.py (P4): rc != 0 => NOT starting, human reasons passed through (046 裁)
'''
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PIDFILE = os.path.join(ROOT, 'logs', 'win_pa.pid')
STOPPED = os.path.join(ROOT, 'logs', 'win_pa.stopped.json')   # ⭐ 058 §一.4：停刻之痕（起服窗以时间记）
LIFELOG = os.path.join(ROOT, 'logs', 'win_pa_life.jsonl')
PREFLIGHT = os.path.join(ROOT, 'scripts', 'win_pa', 'preflight_start.py')
APP = 'agent_gateway_enhanced.py'
FLAGS = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
BREAKAWAY = getattr(subprocess, 'CREATE_BREAKAWAY_FROM_JOB', 0x01000000)   # ⭐ 061 §一.3
START_TASK = os.environ.get('PA_START_TASK') or chr(92) + 'ClawsJoy_PA_Start_Once'   # ⭐ 062 §一(⒝)
TASK_MARK = os.path.join(ROOT, 'logs', 'win_pa.task_dispatch.json')   # 派遣标记(⒝ 回程认亲 · 免环)


def gateway_port():
    sys.path.insert(0, ROOT)
    from core.lib.port_config import gateway_port as _gp
    return int(_gp())


def console_path():
    u"""⭐ pm_1453 §三.4：console 之名**随端口** —— 旧码硬编 `gateway_5102_console.log`
    ⇒ 端口改后**名实不符**（本刻 `5103` 之日志仍旧名 · 老板照拄必惑）。
    惰性（⛔ 于 import 期求端口：真源未配 ⇒ `fail-loud` 会炸 import）。"""
    return os.path.join(ROOT, 'logs', 'gateway_%d_console.log' % gateway_port())


def tcp_open(port, host='127.0.0.1', timeout=1.5):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        return s.connect_ex((host, port)) == 0
    finally:
        s.close()


def life_append(rec):
    """⭐ 058 §一.4：起停之痕入 logs\\win_pa_life.jsonl（与 probe_alive 同册 · 同 JSONL 形）。"""
    try:
        if os.path.exists(LIFELOG) and os.path.getsize(LIFELOG) > 2 * 1024 * 1024:
            os.replace(LIFELOG, LIFELOG + '.1')
        with open(LIFELOG, 'ab') as f:
            f.write((json.dumps(rec, ensure_ascii=False) + chr(10)).encode('utf-8'))
        return True
    except Exception as e:
        print('[WARN] life log: %s' % e)
        return False


def read_pid():
    if not os.path.exists(PIDFILE):
        return None
    try:
        return int(open(PIDFILE, encoding='ascii').read().strip())
    except Exception:
        return None


def run_preflight():
    """起前自检（P4）: rc != 0 => 不 spawn, 人话因透传（承 046 四.1）。"""
    cmd = [sys.executable, '-X', 'utf8', PREFLIGHT, '--root', ROOT]
    try:
        r = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except Exception as e:
        return 1, '[FAIL] preflight runner error: %s: %s' % (type(e).__name__, e)
    return r.returncode, (r.stdout or b'').decode('utf-8', 'replace')

def _job_probe(pid, job=None):
    """⭐ 062 §二：两问分列 —— any=「在某个 job」(IsProcessInJob(pid, NULL))
    ⟷ directed=「在本器所持之 job」(IsProcessInJob(pid, job))。
    ⛔ 单以 any 判「未脱」=误：计划任务起之进程 any=True 而其已脱出起者(062 正控实证)。
    ⚠ directed 唯于 job 句柄可得时有效(本器自建之 job)；他人起出之无名 job 无句柄 => 报 None。"""
    out = {'any': None, 'directed': None}
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(0x1000, False, int(pid))
        if not h:
            return out
        r = ctypes.c_int(0)
        if k32.IsProcessInJob(h, None, ctypes.byref(r)):
            out['any'] = bool(r.value)
        if job:
            r2 = ctypes.c_int(0)
            if k32.IsProcessInJob(h, job, ctypes.byref(r2)):
                out['directed'] = bool(r2.value)
        k32.CloseHandle(h)
    except Exception:
        pass
    return out


def _in_job(pid):
    """⛔ 旧名保留(兼容) => 唯报 any。"""
    return _job_probe(pid)['any']


def cmd_detach_child():
    """内部：为 detach-probe 扮演「起者」—— 自 spawn 一哑进程（带／不带 BREAKAWAY）并报其 pid。"""
    print(chr(114)+chr(101)+chr(97)+chr(100)+chr(121), flush=True)
    time.sleep(1.2)   # 等父先把本进程归入 job（免 race）
    _flag = (len(sys.argv) > 2 and sys.argv[2] == '1')
    p = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(60)'],
                         creationflags=FLAGS | (BREAKAWAY if _flag else 0))
    print(p.pid, flush=True)
    time.sleep(60)
    return 0


def cmd_detach_probe():
    """⭐ 起服器「真脱离」之自证（061 §一.3 之硬形）。
    正控 = 含 BREAKAWAY 之子 ⇒ job 终止后犹存；负控 = 不含 ⇒ 随之亡。
    ⛔ 动网关（唯以本器自 spawn 之哑进程为样）。"""
    import ctypes
    import subprocess as _sp
    k32 = ctypes.windll.kernel32
    print('[INFO] self pid=%d job=%s' % (os.getpid(), _job_probe(os.getpid())))
    _p = read_pid()
    if _p:
        print('[INFO] pidfile pid=%d job=%s' % (_p, _job_probe(_p)))
        print('[INFO] directed=None 之界: 无名 job 无句柄(⛔ 公开 API 取自身 job 句柄之法) => 他人起出者唯 any 可报')

    class _IO(ctypes.Structure):
        _fields_ = [('a', ctypes.c_uint64), ('b', ctypes.c_uint64), ('c', ctypes.c_uint64),
                    ('d', ctypes.c_uint64), ('e', ctypes.c_uint64), ('f', ctypes.c_uint64)]

    class _BASIC(ctypes.Structure):
        _fields_ = [('p1', ctypes.c_int64), ('p2', ctypes.c_int64), ('LimitFlags', ctypes.c_uint32),
                    ('m1', ctypes.c_size_t), ('m2', ctypes.c_size_t), ('m3', ctypes.c_uint32),
                    ('m4', ctypes.c_size_t), ('m5', ctypes.c_uint32), ('m6', ctypes.c_uint32)]

    class _EXT(ctypes.Structure):
        _fields_ = [('Basic', _BASIC), ('io', _IO), ('pm', ctypes.c_size_t), ('jm', ctypes.c_size_t),
                    ('pp', ctypes.c_size_t), ('pj', ctypes.c_size_t)]

    rc = 0
    for label, flag in (('negative(no BREAKAWAY)', '0'), ('positive(BREAKAWAY)', '1')):
        job = k32.CreateJobObjectW(None, None)
        info = _EXT()
        info.Basic.LimitFlags = 0x00000800      # JOB_OBJECT_LIMIT_BREAKAWAY_OK
        _ok = k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))
        try:
            st = _sp.Popen([sys.executable, os.path.abspath(__file__),
                          '_detach-child', flag], stdout=_sp.PIPE,
                          creationflags=getattr(_sp, 'CREATE_NO_WINDOW', 0), text=True)
        except OSError as e:
            print('[FAIL] %s: starter spawn: %s' % (label, e))
            k32.CloseHandle(job)
            rc = 2
            continue
        _ok2 = k32.AssignProcessToJobObject(job, int(st._handle))
        _ready = (st.stdout.readline() or '').strip()
        _line = (st.stdout.readline() or '').strip()
        _child = int(_line) if _line.isdigit() else -1
        time.sleep(0.6)
        k32.TerminateJobObject(job, 1)
        time.sleep(1.5)
        def _alive(pp):
            h = k32.OpenProcess(0x00100000 | 0x1000, False, int(pp))
            if not h:
                return False
            a = k32.WaitForSingleObject(h, 0) == 0x102
            k32.CloseHandle(h)
            return a
        print('[%s] jobset=%s assign=%s ready=%s starter=%d child=%d starter_alive=%s child_alive=%s'
              % (label, bool(_ok), bool(_ok2), _ready, st.pid, _child, _alive(st.pid), _alive(_child)))
        print('          directed(定向问 本器 job): starter=%s child=%s  (对照 any: starter=%s child=%s)'
              % (_job_probe(st.pid, job)['directed'], _job_probe(_child, job)['directed'],
                 _job_probe(st.pid)['any'], _job_probe(_child)['any']))
        _want = label.startswith('negative')
        if _alive(_child) != (not _want):
            rc = 2
        k32.CloseHandle(job)
        for _q in (st.pid, _child):
            if _q and _alive(_q):
                _sp.run(['taskkill', '/F', '/PID', str(_q)], capture_output=True,
                        creationflags=getattr(_sp, 'CREATE_NO_WINDOW', 0))
        try:
            st.kill()
        except Exception:
            pass
    print('[总判] %s' % ('PASS' if rc == 0 else 'FAIL'))
    return rc

def _task_guard():
    """⭐ 062 §一：判「本进程系由计划任务拉起」 —— ⛔ 免「派遣⇒被拒⇒再派遣」之环。
    据一：派遣标记(180 s 内为真 · 用后即删)。据二：父进程名为 svchost.exe。"""
    try:
        if os.path.exists(TASK_MARK):
            _rec = json.load(open(TASK_MARK, encoding='utf-8'))
            if time.time() - float(_rec.get('epoch') or 0) < 180:
                try:
                    os.remove(TASK_MARK)
                except Exception:
                    pass
                return True
    except Exception:
        pass
    try:
        import psutil
        return psutil.Process(os.getpid()).parent().name().lower() == 'svchost.exe'
    except Exception:
        return False


def start_via_task():
    """⭐ 062 §一(⒝)：以已注册之计划任务起 —— 由计划服务拉 ⇒ ⛔ 属起者之 job。"""
    try:
        with open(TASK_MARK, 'w', encoding='utf-8') as _f:
            json.dump({'ts': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'epoch': time.time(),
                       'by': 'pa_nowindow.start', 'task': START_TASK}, _f, ensure_ascii=False)
    except Exception as _e:
        print('[FAIL] task-dispatch marker: %s' % _e)
        return 1
    _r = subprocess.run(['schtasks', '/run', '/tn', START_TASK], stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    print('[INFO] schtasks /run %s -> rc=%s %s'
          % (START_TASK, _r.returncode, (_r.stdout or b'').decode('utf-8', 'replace').strip()))
    if _r.returncode != 0:
        print('[FAIL] 计划任务起服失败 —— 请查 schtasks /query /tn %s /v' % START_TASK)
        return _r.returncode
    _port = gateway_port()
    _t0 = time.time()
    while time.time() - _t0 < 120:
        if tcp_open(_port):
            try:
                with urllib.request.urlopen('http://127.0.0.1:%d/health' % _port, timeout=3) as _rr:
                    if _rr.status == 200:
                        print('[OK] 由计划任务起 · /health 200 after %.1f s · pid=%s'
                              % (time.time() - _t0, read_pid()))
                        return 0
            except Exception:
                pass
        time.sleep(1.0)
    print('[FAIL] 已派遣但 120 s 内 /health 未通 —— 查 logs' + chr(92) + ('gateway_%d_console.log' % _port))
    return 1


def cmd_start():
    os.chdir(ROOT)
    _via_task = _task_guard()   # ⭐ 062 §一: 派遣之回程(用后即删 · 免环)
    rc, out = run_preflight()
    if rc != 0:
        if u'端口已被占用' in out:
            port = gateway_port()
            print('[STOP] port %d already answers TCP -- not starting a second one.' % port)
            print('       first look at  paseo-pm\\_端口归属登记_v1.md  and agree who owns it.')
            return 2
        print('[FAIL] preflight not passed (rc=%d) -- NOT starting (avoid bare traceback then silent death)' % rc)
        for _ln in out.splitlines():
            if ('[FAIL]' in _ln) or ('[总判]' in _ln) or ('[自检器异常]' in _ln):
                print('       ' + _ln.strip())
        return rc
    print('[OK] preflight passed (rc=0)')
    port = gateway_port()
    print('[INFO] gateway port = %d  (source: config/system/system_unified.yaml)' % port)
    if tcp_open(port):
        print('[STOP] port %d already answers TCP -- not starting a second one.' % port)
        print('       first look at  paseo-pm\\\\_端口归属登记_v1.md  and agree who owns it.')
        return 2
    lf = open(console_path(), 'ab', buffering=0)
    lf.write(('=== nowindow start ' + time.strftime('%Y-%m-%d %H:%M:%S') + ' ===' + chr(10)).encode('utf-8'))
    _argv = [sys.executable, '-X', 'utf8', '-u', APP]
    _kw = dict(cwd=ROOT, stdout=lf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    _detach = 'breakaway'
    try:
        p = subprocess.Popen(_argv, creationflags=FLAGS | BREAKAWAY, **_kw)
    except OSError as _e:
        print('[WARN] CREATE_BREAKAWAY_FROM_JOB refused (winerror=%s)' % getattr(_e, 'winerror', None))
        if _via_task:
            _detach = 'detached-only(task)'
            print('       => 系由计划任务拉起(job 不许 breakaway) => 以 FLAGS 起(⛔ 再派遣 · 免环)')
            p = subprocess.Popen(_argv, creationflags=FLAGS, **_kw)
        else:
            print('       => 起者 job 不许 breakaway => 派计划任务起(062 §一 ⒝ · ⛔ detached-only 之连坐)')
            return start_via_task()
    open(PIDFILE, 'w', encoding='ascii').write(str(p.pid))
    print('[OK] started pid=%d (no window) at %s  detach=%s'
          % (p.pid, time.strftime('%Y-%m-%d %H:%M:%S'), _detach))
    print('[OK] console log: %s' % console_path())
    print('[OK] boot takes ~30s; probes fail before that')
    # ⭐ 058 §一.4（裁）：起服成本以**时间**记 —— 「不可用窗」＝ 停刻 → 起刻（钱面 0 ／ 用户面 0）。
    _gap_s = None
    try:
        if os.path.exists(STOPPED):
            _st = json.load(open(STOPPED, encoding='utf-8'))
            _gap_s = round(time.time() - float(_st.get('epoch') or 0), 3)
            print('[INFO] unavailable window (stop -> start) = %.1f s  (stopped_at=%s)'
                  % (_gap_s, _st.get('ts')))
    except Exception as e:
        print('[WARN] restart-window: %s' % e)
    _boot_s = None
    _wait = 0
    for _i, _a in enumerate(sys.argv):
        if _a == '--wait':
            _wait = int(sys.argv[_i + 1]) if _i + 1 < len(sys.argv) else 90
    if _wait:
        _t0 = time.time()
        while time.time() - _t0 < _wait:
            if tcp_open(port):
                try:
                    with urllib.request.urlopen('http://127.0.0.1:%d/health' % port, timeout=3) as _r:
                        if _r.status == 200:
                            _boot_s = round(time.time() - _t0, 3)
                            print('[OK] /health 200 after %.1f s (boot window)' % _boot_s)
                            break
                except Exception:
                    pass
            time.sleep(1.0)
    life_append({'ts': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'event': 'start',
                 'pid': p.pid, 'port': port, 'gap_s': _gap_s, 'boot_s': _boot_s,
                 'detach': _detach, 'via_task': _via_task,
                 'caller': {'ppid': os.getppid()}})
    return 0


def cmd_stop():
    pid = read_pid()
    if pid is None:
        print('[STOP] no pid file %s -- nothing to stop' % PIDFILE)
        return 3
    try:
        import psutil
        pr = psutil.Process(pid)
        cl = ' '.join(pr.cmdline())
        if APP not in cl:
            print('[STOP] pid %d is not %s (cmdline=%s) -- refusing' % (pid, APP, cl[:120]))
            return 4
        pr.terminate()
        pr.wait(timeout=20)
        print('[OK] stopped pid=%d at %s' % (pid, time.strftime('%Y-%m-%d %H:%M:%S')))
    except Exception as e:
        print('[WARN] stop pid %d: %s' % (pid, e))
    finally:
        try:
            os.remove(PIDFILE)
        except Exception:
            pass
        # ⭐ 058 §一.4：停刻之痕（供 cmd_start 算「不可用窗」；⛔ 起服窗以时间记 · 钱面为 0）
        try:
            _now = time.time()
            with open(STOPPED, 'w', encoding='utf-8') as _f:
                json.dump({'ts': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'epoch': _now,
                           'pid': pid, 'by': 'cmd_stop'}, _f, ensure_ascii=False)
            life_append({'ts': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'event': 'stop',
                         'pid': pid, 'epoch': _now, 'caller': {'ppid': os.getppid()}})
        except Exception as e:
            print('[WARN] stop trace: %s' % e)
    return 0


def cmd_status():
    os.chdir(ROOT)
    port = gateway_port()
    up = tcp_open(port)
    print('[INFO] port %d tcp_open=%s (judged by TCP connect, NOT netstat LISTENING)' % (port, up))
    if up:
        try:
            with urllib.request.urlopen('http://127.0.0.1:%d/health' % port, timeout=3) as r:
                print('[OK] /health %d %s' % (r.status, r.read().decode('utf-8')[:120]))
        except Exception as e:
            print('[WARN] /health: %s' % e)
    print('[INFO] pid file = %s -> %s' % (PIDFILE, read_pid()))
    return 0 if up else 1


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'
    fn = {'start': cmd_start, 'stop': cmd_stop, 'status': cmd_status,
          'detach-probe': cmd_detach_probe,
          '_detach-child': cmd_detach_child}.get(cmd)
    if fn is None:
        print(__doc__)
        sys.exit(5)
    sys.exit(fn())
