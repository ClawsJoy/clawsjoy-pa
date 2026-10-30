# -*- coding: utf-8 -*-
r"""9.0.13 P0 之齿 —— **可写根迁出安装根**（task-14 · 9.0.12 装 Program Files 起不来之修）。

病（一手 · 2026-10-28 · PM 69 号件）：
  9.0.12 装 Program Files 后 `pa_nowindow.py` 把 PID ／ stopped ／ life ／ task ／ console
  全指 `ROOT\logs`（装根只读）⇒ 普通用户 WinError 5 ⇒ preflight 4/8 FAIL ⇒ 壳起不来。
修（本批）：三根 `PA_DATA_DIR` ／ `PA_LOG_DIR` ／ `PA_VEC_DIR`（缺省
  `%LOCALAPPDATA%\ClawsJoyPA\{data,logs,vec}`）；运行态全落 `PA_LOG_DIR`；preflight
  三处分栏可写且显因；子进程 env 注入；core 数据根 `CLAWSJOY_DATA_DIR`、向量根
  `get_vector_root()`（env `PA_VEC_DIR`）；网关日志 ／ 检索缓存 ⛔ 相对 CWD。

判据（本档）：
  R1 正控：三根缺省皆在 `%LOCALAPPDATA%\ClawsJoyPA` 下（⛔ 装根）；env 覆 ⇒ 逐字生效；
  R2 正控：`child_env()` 注入三根 ＋ `CLAWSJOY_DATA_DIR` ＝ `PA_DATA_DIR` ＋ 禁 `.pyc`；
  R3 正控／反控：`probe_writable()` 可写 ⇒ 绿；不可写 ⇒ 红 ＋ 点名径/env ＋ 修之门；
  R4 正控／反控：装根隔离 —— 三根在装根外 ⇒ 绿；落「只读装根」内 ⇒ 红（9.0.12 之病）；
  R5 正控：`pa_nowindow` 运行态（pid/stopped/life/task/console）皆落 `PA_LOG_DIR`（源齿）；
  R6 正控：`preflight_start.collect()` 三根分栏皆在 ∧ 装根隔离栏在（器取 · ⛔ 起服）；
  R7 正控：`config_helper.get_vector_root()` 认 env `PA_VEC_DIR`（与 pa_paths 同 env 名）；
  R8 正控：`vector_knowledge_center` ／ `memory_vector` 用 `get_vector_root()`（源齿）；
  R9 正控：网关日志落 `PA_LOG_DIR` ∧ 检索缓存走 `retrieval_cache_file()`（源齿）；
  R10 端到端：从**冒装根**（config 副本 ＋ core 目录联接）跑 preflight ⇒ rc 0 ∧ 三根 PASS ∧
     装根隔离 PASS ∧ 装根**无 logs/data/vec 之新件**（安装根 0 写）；
  R11 反控（昔之病）：装根**拒写**（icacls deny）后 `<装根>\logs` 探写 ⇒ WinError 5；
      同环境下 `PA_LOG_DIR` 指用户目录 ⇒ preflight 仍 rc 0（＝本批之修）；
      而 `PA_LOG_DIR` 仍指装根 ⇒ preflight rc 2 且点名 logs 根不可写（⛔ 静默）。

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_writable_roots_9013.py -q
⛔ 起服 ／ ⛔ 动用户真实 %LOCALAPPDATA%（皆以 env 指临时目录）；端到端唯 preflight（⛔ spawn 网关）。
"""
from __future__ import annotations

import io
import os
import shutil
import socket
import subprocess
import sys
import types

import pytest

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WPA = ROOT / "scripts" / "win_pa"
sys.path.insert(0, str(WPA))
sys.path.insert(0, str(ROOT))

import pa_paths as PP  # noqa: E402
import pa_nowindow as PN  # noqa: E402

BS = chr(92)
PASS = "[PASS]"
FAIL = "[FAIL]"


# ---------------------------------------------------------------- R1 缺省／覆
def test_R1_default_roots_under_localappdata_not_install_root():
    la = os.path.join(os.environ.get(u"TEMP", u"."), u"p4_default_la")
    r = PP.roots({u"LOCALAPPDATA": la})
    for n, sub in ((u"data", u"data"), (u"logs", u"logs"), (u"vec", u"vec")):
        assert r[n][u"path"] == os.path.join(la, u"ClawsJoyPA", sub), (n, r[n])
        assert r[n][u"default"] is True
        assert not PP.is_inside(r[n][u"path"], str(ROOT)), (n, r[n])


def test_R1b_env_override_verbatim_and_source_named():
    t = os.path.join(os.environ.get(u"TEMP", u"."), u"p4_ovr")
    e = {u"LOCALAPPDATA": t, u"PA_DATA_DIR": os.path.join(t, u"d"),
         u"PA_LOG_DIR": os.path.join(t, u"l"), u"PA_VEC_DIR": os.path.join(t, u"v")}
    r = PP.roots(e)
    assert r[u"data"][u"path"] == os.path.join(t, u"d") and not r[u"data"][u"default"]
    assert r[u"logs"][u"path"] == os.path.join(t, u"l")
    assert r[u"vec"][u"path"] == os.path.join(t, u"v")
    assert r[u"logs"][u"source"].startswith(u"env:PA_LOG_DIR")


def test_R1c_userprofile_fallback_when_localappdata_missing():
    up = os.path.join(os.environ.get(u"TEMP", u"."), u"p4_up")
    r = PP.resolve(u"logs", {u"USERPROFILE": up})
    assert r[u"path"] == os.path.join(up, u"AppData", u"Local", u"ClawsJoyPA", u"logs"), r


# ---------------------------------------------------------------- R2 子进程 env
def test_R2_child_env_injects_roots_and_no_pyc():
    la = os.path.join(os.environ.get(u"TEMP", u"."), u"p4_child_la")
    e = PP.child_env({u"LOCALAPPDATA": la, u"KEEP": u"1"})
    assert e[u"KEEP"] == u"1"
    assert e[PP.ENV_DATA] == os.path.join(la, u"ClawsJoyPA", u"data")
    assert e[PP.ENV_LOG] == os.path.join(la, u"ClawsJoyPA", u"logs")
    assert e[PP.ENV_VEC] == os.path.join(la, u"ClawsJoyPA", u"vec")
    assert e[PP.DATA_ROOT_ENV] == e[PP.ENV_DATA], u"core get_data_root() 之真口须 ＝ PA_DATA_DIR"
    assert e[PP.NO_PYC_ENV] == u"1"
    assert e[PP.FEEDBACK_DIR_ENV] == os.path.join(la, u"ClawsJoyPA", u"data", u"pa", u"feedback")
    assert e[PP.UI_STATE_ENV] == os.path.join(la, u"ClawsJoyPA", u"data", u"ui_state.json")
    e2 = PP.child_env({u"LOCALAPPDATA": la})
    assert PN.child_env({u"LOCALAPPDATA": la}) == e2, u"pa_nowindow.child_env 须委 pa_paths（一处定形）"


# ---------------------------------------------------------------- R3 可写之判
def test_R3_probe_writable_ok_and_reason_names_the_door(tmp_path):
    ok, why, note = PP.probe_writable(str(tmp_path / u"ok"), env_name=u"PA_LOG_DIR", source=u"test")
    assert ok is True and u"可写" in why, why
    blk = tmp_path / u"blocker"
    blk.write_bytes(b"x")
    bad, why2, _n = PP.probe_writable(str(blk / u"sub"), env_name=u"PA_LOG_DIR", source=u"env:PA_LOG_DIR=x")
    assert bad is False and u"不可写" in why2
    assert u"PA_LOG_DIR" in why2 and u"修之门" in why2, why2
    assert str(blk) in why2, why2


# ---------------------------------------------------------------- R4 装根隔离
def test_R4_install_root_guard():
    import preflight_start as P
    t = os.path.join(os.environ.get(u"TEMP", u"."), u"p4_guard")
    outside = {u"LOCALAPPDATA": t}
    ok, why, _ = P.probe_install_root(os.path.join(t, u"install_nope"), PP.roots(outside))
    assert ok is True and u"装根外" in why, why
    inside_env = {u"PA_DATA_DIR": os.path.join(t, u"install_nope", u"data"),
                  u"PA_LOG_DIR": os.path.join(t, u"install_nope", u"logs"),
                  u"PA_VEC_DIR": os.path.join(t, u"install_nope", u"vec")}
    bad, why2, _ = P.probe_install_root(os.path.join(t, u"install_nope"), PP.roots(inside_env))
    assert bad is False and u"只读装根" in why2 and u"修之门" in why2, why2


# ---------------------------------------------------------------- R5 pa_nowindow 运行态
def test_R5_pa_nowindow_runtime_state_under_log_dir(monkeypatch, tmp_path):
    logd = tmp_path / u"logs_root"
    monkeypatch.setenv(u"PA_LOG_DIR", str(logd))
    assert PN.pidfile() == str(logd / u"win_pa.pid")
    assert PN.stopped_file() == str(logd / u"win_pa.stopped.json")
    assert PN.lifelog_file() == str(logd / u"win_pa_life.jsonl")
    assert PN.task_mark_file() == str(logd / u"win_pa.task_dispatch.json")
    monkeypatch.setattr(PN, u"port_lite", lambda: types.SimpleNamespace(read_port=lambda _root: 5199))
    assert PN.console_path() == str(logd / u"gateway_5199_console.log")


def test_R5b_pa_nowindow_source_has_no_install_root_logs():
    src = io.open(str(WPA / u"pa_nowindow.py"), encoding=u"utf-8").read()
    assert u"os.path.join(ROOT, 'logs'" not in src, u"运行态 ⛔ 得再指装根 logs"
    assert u"pa_paths.log_path" in src and u"pa_paths.ensure_roots" in src
    assert u"sys.dont_write_bytecode = True" in src, u"装根只读 ⇒ 本进程亦 ⛔ 落 .pyc"


def test_R5c_run_preflight_env_carries_roots(monkeypatch):
    seen = {}

    class _R(object):
        returncode = 0
        stdout = b""

    def _run(cmd, **kw):
        seen[u"cmd"] = cmd
        seen[u"kw"] = kw
        return _R()

    monkeypatch.setattr(PN.subprocess, u"run", _run)
    rc, out = PN.run_preflight()
    assert rc == 0
    env = seen[u"kw"][u"env"]
    for k in (PP.ENV_DATA, PP.ENV_LOG, PP.ENV_VEC, PP.DATA_ROOT_ENV, PP.NO_PYC_ENV):
        assert k in env, k
    assert env[PP.DATA_ROOT_ENV] == env[PP.ENV_DATA]


# ---------------------------------------------------------------- R6 preflight collect
def test_R6_preflight_collect_has_three_roots_and_install_guard(monkeypatch):
    import preflight_start as P
    import tempfile
    # ⚠ 本仓 pytest basetemp 落 ROOT\_tmp ⇒ ⛔ 用 tmp_path（会落装根内 ⇒ 装根隔离栏必红）；
    #   以系统临时目录（装根外）为三根 —— 正控须与「装根外」之约同形。
    base = tempfile.mkdtemp(prefix=u"p4_r6_")
    monkeypatch.setenv(u"PA_DATA_DIR", os.path.join(base, u"d"))
    monkeypatch.setenv(u"PA_LOG_DIR", os.path.join(base, u"l"))
    monkeypatch.setenv(u"PA_VEC_DIR", os.path.join(base, u"v"))
    monkeypatch.setattr(P, u"resolve_port", lambda root: (5199, u"test"))
    monkeypatch.setattr(P, u"probe_python", lambda: (True, u"ok", u""))
    monkeypatch.setattr(P, u"probe_deps", lambda: (True, u"ok", u""))
    monkeypatch.setattr(P, u"probe_config_port", lambda root: (True, u"ok", u""))
    monkeypatch.setattr(P, u"probe_port", lambda port: (True, u"ok", u""))
    monkeypatch.setattr(P, u"probe_ollama", lambda: (True, u"ok", u""))
    monkeypatch.setattr(P, u"probe_vector_db", lambda kb, src=u"": (True, u"ok", u""))
    monkeypatch.setattr(P, u"resolve_vector_kb", lambda root: (str(base), u"test"))
    try:
        _port, _src, items = P.collect(str(ROOT))
    finally:
        shutil.rmtree(base, ignore_errors=True)
    names = [n for n, _v in items]
    for k in (u"data 根可写（PA_DATA_DIR）", u"logs 根可写（PA_LOG_DIR）",
              u"vec 根可写（PA_VEC_DIR）", u"安装根只读（运行根隔离）", u"向量库可写"):
        assert k in names, (k, names)
    assert all(ok for _n, (ok, _r, _x) in items), [i for i in items if not i[1][0]]


# ---------------------------------------------------------------- R7 core 向量根
def test_R7_config_helper_vector_root_env_contract(monkeypatch, tmp_path):
    from core.lib import config_helper as CH
    assert CH.VECTOR_ROOT_ENV == PP.ENV_VEC, u"env 名须一处定形（pa_paths ⇔ config_helper）"
    monkeypatch.delenv(CH.VECTOR_ROOT_ENV, raising=False)
    monkeypatch.setenv(CH.DATA_ROOT_ENV, str(tmp_path / u"data"))
    assert CH.get_vector_root() == str(tmp_path / u"data" / u"vector_kb"), u"缺 env ⇒ 旧形"
    vec = tmp_path / u"vec"
    monkeypatch.setenv(CH.VECTOR_ROOT_ENV, str(vec))
    assert CH.get_vector_root() == str(vec), u"env PA_VEC_DIR ⇒ 同名之根（⛔ 旧形）"
    monkeypatch.setenv(CH.VECTOR_ROOT_ENV, u"rel/vec")
    assert CH.get_vector_root() == str(ROOT / u"rel" / u"vec"), u"相对值 ⇒ 按仓根拼（⛔ 按 CWD）"


# ---------------------------------------------------------------- R8 消费者
def test_R8_vector_consumers_use_get_vector_root():
    for rel in (u"core/lib/vector_knowledge_center.py", u"core/lib/memory_vector.py"):
        src = io.open(str(ROOT / rel), encoding=u"utf-8").read()
        assert u"get_vector_root" in src, rel
        assert u'f"{get_data_root()}/vector_kb"' not in src, (rel, u"仍以 data_root 拼向量库")


# ---------------------------------------------------------------- R9 网关 ／ 检索缓存
def test_R9_gateway_logs_and_cache_are_rooted_out_of_cwd():
    src = io.open(str(ROOT / u"agent_gateway_enhanced.py"), encoding=u"utf-8").read()
    assert u"PA_LOG_DIR" in src, u"网关日志须落 PA_LOG_DIR"
    code = u"\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith(u"#"))
    assert u'"logs/gateway.log"' not in code and u"'logs/gateway.log'" not in code, u"⛔ 相对 CWD 写日志"
    assert u'os.path.join(_log_dir, "gateway.log")' in code, u"须以绝对径立 handler"
    ss = io.open(str(ROOT / u"core/gateway/shared_state.py"), encoding=u"utf-8").read()
    assert u"def retrieval_cache_file()" in ss
    sp = io.open(str(ROOT / u"core/gateway/state_persist.py"), encoding=u"utf-8").read()
    assert u"retrieval_cache_file()" in sp
    assert u"_RETRIEVAL_CACHE_FILE" not in sp, u"旧相对常量须退场"
    assert u'data/v8/retrieval_cache.json' not in ss.split(u"def retrieval_cache_file")[1][:400], \
        u"检索缓存 ⛔ 字面相对径"


# ---------------------------------------------------------------- R10／R11 端到端
def _free_port():
    s = socket.socket()
    s.bind((u"127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _mk_fake_install(tmp_path):
    u"""冒装根：config 副本 ＋ core 目录联接（⛔ 复制 1GB；⛔ 动真仓）。"""
    import yaml
    fake = tmp_path / u"ProgramFiles" / u"ClawsJoyPA"
    fake.mkdir(parents=True)
    shutil.copytree(str(ROOT / u"config"), str(fake / u"config"))
    port = _free_port()
    p = fake / u"config" / u"system" / u"system_unified.yaml"
    d = yaml.safe_load(io.open(str(p), encoding=u"utf-8")) or {}
    d.setdefault(u"services", {}).setdefault(u"gateway", {})[u"port"] = port
    io.open(str(p), u"w", encoding=u"utf-8").write(yaml.safe_dump(d, allow_unicode=True, sort_keys=False))
    r = subprocess.run([u"cmd", u"/c", u"mklink", u"/J", str(fake / u"core"), str(ROOT / u"core")],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        pytest.skip(u"mklink /J 不可用 ⇒ 跳端到端：" + ((r.stdout or u"") + (r.stderr or u""))[:200])
    return fake, port


def _cleanup_fake(fake):
    subprocess.run([u"cmd", u"/c", u"rmdir", str(fake / u"core")], capture_output=True, timeout=120)
    shutil.rmtree(str(fake), ignore_errors=True)


def _child_env(tmp_path, **extra):
    e = dict(os.environ)
    for k in (PP.ENV_DATA, PP.ENV_LOG, PP.ENV_VEC, PP.DATA_ROOT_ENV):
        e.pop(k, None)
    e[PP.NO_PYC_ENV] = u"1"
    e[u"LOCALAPPDATA"] = str(tmp_path / u"localappdata")
    e[u"APPDATA"] = str(tmp_path / u"appdata")
    e.update({k: str(v) for k, v in extra.items()})
    return e


def _run_preflight(fake, env):
    return subprocess.run([sys.executable, u"-X", u"utf8", u"-B",
                           str(WPA / u"preflight_start.py"), u"--root", str(fake)],
                          capture_output=True, text=True, encoding=u"utf-8", errors=u"replace",
                          cwd=str(fake), env=env, timeout=300)


def _deny_write(path):
    u"""装根**只读**之模拟（＝ Program Files 之常形：根目录拒建，子件仍可读 —— ⛔ 继承 ⇒ ⛔ 连带毁 import）。"""
    r = subprocess.run([u"icacls", str(path), u"/deny", u"Everyone:(AD,WD)"],
                       capture_output=True, text=True, timeout=120)
    return r.returncode == 0


def _undeny_write(path):
    subprocess.run([u"icacls", str(path), u"/remove:d", u"Everyone"],
                   capture_output=True, text=True, timeout=120)


def test_R10_preflight_passes_with_user_roots_and_writes_nothing_to_install_root(tmp_path):
    fake, port = _mk_fake_install(tmp_path)
    try:
        roots = tmp_path / u"userroots"
        env = _child_env(tmp_path, PA_DATA_DIR=roots / u"data", PA_LOG_DIR=roots / u"logs",
                         PA_VEC_DIR=roots / u"vec")
        r = _run_preflight(fake, env)
        out = (r.stdout or u"") + (r.stderr or u"")
        assert r.returncode == 0, (r.returncode, out[-1600:])
        for tag in (u"data 根可写（PA_DATA_DIR）", u"logs 根可写（PA_LOG_DIR）",
                    u"vec 根可写（PA_VEC_DIR）", u"安装根只读（运行根隔离）"):
            assert tag in out, (tag, out[-1200:])
        assert u"[总判] PASS" in out, out[-1200:]
        assert (roots / u"logs").is_dir() and (roots / u"data").is_dir() and (roots / u"vec").is_dir()
        assert not (fake / u"logs").exists() and not (fake / u"data").exists() and not (fake / u"vec").exists(), \
            u"安装根 0 写（⛔ 见 logs/data/vec）"
        assert sorted(x.name for x in fake.iterdir()) == [u"config", u"core"], \
            u"安装根须唯 config ／ core（无新件）：%s" % [x.name for x in fake.iterdir()]
    finally:
        _cleanup_fake(fake)


def test_R11_old_install_root_logs_fail_but_user_roots_pass(tmp_path):
    fake, port = _mk_fake_install(tmp_path)
    ud = tmp_path / u"userroots2"
    try:
        if not _deny_write(fake):
            pytest.skip(u"icacls deny 不可用 ⇒ 跳反控")
        try:
            # 反控（9.0.12 之病）：装根拒写后 <装根>\logs 探写 ⇒ WinError 5
            ok, why, _n = PP.probe_writable(str(fake / u"logs"), env_name=u"PA_LOG_DIR",
                                            source=u"test:legacy-ROOT-logs")
            assert ok is False, u"装根拒写后仍可写 ⇒ 齿 ⛔ 真（环境异常）"
            assert (u"权限不足" in why) or (u"WinError 5" in why), why
            # 正控：同一只读装根，PA_LOG_DIR 指用户目录 ⇒ preflight rc 0
            env = _child_env(tmp_path, PA_DATA_DIR=ud / u"data", PA_LOG_DIR=ud / u"logs", PA_VEC_DIR=ud / u"vec")
            r = _run_preflight(fake, env)
            out = (r.stdout or u"") + (r.stderr or u"")
            assert r.returncode == 0, (r.returncode, out[-1600:])
            assert u"logs 根可写（PA_LOG_DIR）" in out, out[-1200:]
            # 反控：PA_LOG_DIR 仍指只读装根 ⇒ rc 2 ＋ 点名 logs 根不可写（⛔ 静默）
            env2 = _child_env(tmp_path, PA_DATA_DIR=ud / u"d2", PA_LOG_DIR=fake / u"logs", PA_VEC_DIR=ud / u"v2")
            r2 = _run_preflight(fake, env2)
            out2 = (r2.stdout or u"") + (r2.stderr or u"")
            assert r2.returncode == 2, (r2.returncode, out2[-1600:])
            assert u"logs 根可写（PA_LOG_DIR）" in out2, out2[-1600:]
            assert (u"权限不足" in out2) or (u"WinError 5" in out2), out2[-1600:]
        finally:
            _undeny_write(fake)
    finally:
        _cleanup_fake(fake)
