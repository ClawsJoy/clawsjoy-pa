# -*- coding: utf-8 -*-
u"""DshHarness —— HarnessPort 之 **DSH adapter**（H2：真 harness 之最简收编）。

【本件解决什么】把现有 CLI 面 `dsh --profile headless <task>` 收进 `HarnessPort` 之下：
  · probe：`shutil.which("dsh")` ＋ `dsh --version`（⛔ 谎报可用）；
  · run：以 `dsh --profile headless <task>` 起一次（cwd ／ timeout ／ env 照 spec）；
  · canonical `RunRecord` 归 **PA 账**（`RunLedger` · 可注入）—— DSH 之会话格式 ⛔ 解析、
    ⛔ 进 canonical 字段；`harness_meta` **只**载 `profile ／ rc ／ stderr_tail`；
  · resume：headless ⛔ 历史回放 ⇒ `history_replay=False` **显式**（§四.4 · ⛔ 假回放）；
  · cancel ／ stream ／ permissions ／ cost ／ audit ／ team：按 port 语义（见各法之注）。

【边界（§四.1 ／ H5）】
  · ⛔ import dsh ／ paseo ／ obsidian（无 Python SDK 依赖）；调用唯 `shutil.which` ＋ `_proc`；
  · 子进程**唯**经 `core.pa._proc.run_hidden`（窗隐唯一出口 · PM 2026-10-05 令）；
    ⛔ 经 shell（命令为 argv 列表 ⇒ 无 shell 展开）；
  · ⛔ 起真模型（测试以注入 runner 替身）；本件 ⛔ 写盘、⛔ 解析输出为账。

【H2】fake-run（注入 runner）⇒ canonical RunRecord 落 PA 侧 RunLedger ⇒ `ledger.dump()` 即
  交 `core.pa.ledger` ／ vault 之接线点（本批只到内存账 · 真落件属后续期）。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import uuid

from core.pa import _proc  # ⭐ 窗隐唯一出口（PM 2026-10-05 令）· ⛔ 各写 creationflags
from core.pa.harness.port import (
    AuditResult,
    Cost,
    HarnessError,
    PermissionState,
    ProbeResult,
    RunHandle,
    RunLedger,
    RunRecord,
    RunSpec,
    StreamEvent,
    TeamState,
    UnknownRun,
    UnknownSession,
    _now_iso,
)

DSH_PROFILE = "headless"

DSH_PROBE_TIMEOUT = 5.0

DSH_DEFAULT_TIMEOUT = 120.0

STDERR_TAIL_MAX = 500

STREAM_TEXT_MAX = 8000

#: PA 账 `harness_meta` 之**唯一**允许键（⛔ 增 —— 会话格式等私物 ⛔ 进 canonical 域）
DSH_META_FIELDS = ("profile", "rc", "stderr_tail")


class DshUnavailable(HarnessError):
    u"""`dsh` ⛔ 在位（shutil.which 空）⇒ run 前**显错**（⛔ 造 failed 记录冒充「跑过」）。"""


def _text(value):
    u"""子进程输出（str ／ bytes ／ None）⇒ str（⛔ 抛）。"""
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", "replace")
    return str(value)


def _tail(text, limit=STDERR_TAIL_MAX):
    u"""只留末 `limit` 字（⛔ 大段原文进账 · 仍可辨末因）。"""
    text = _text(text)
    return text if len(text) <= limit else text[-limit:]


class DshHarness:
    u"""`HarnessPort` 之 DSH CLI 实现（`dsh --profile headless <task>`）。

    注入点（H2 之可测性）：
      · `ledger`：PA 侧 `RunLedger`（缺省自立内存账；与 PA 共用时传入同一本）；
      · `runner`：缺省 `core.pa._proc.run_hidden`（窗隐）；测试注入替身 ⇒ ⛔ 真起进程；
      · `exe`：缺省 `shutil.which("dsh")`；测试可直给假径；
      · `env`：叠加于 `os.environ` 之上（⛔ 替换整 env —— 子进程仍得 PATH 等）。
    """

    name = "dsh"

    def __init__(self, ledger=None, *, exe=None, runner=None, env=None,
                 profile=DSH_PROFILE, default_timeout=DSH_DEFAULT_TIMEOUT):
        if ledger is None:
            ledger = RunLedger()
        if not isinstance(ledger, RunLedger):
            raise ValueError("DshHarness.ledger 须为 RunLedger（今 %s）" % type(ledger).__name__)
        self.ledger = ledger
        self.profile = str(profile or DSH_PROFILE)
        self.default_timeout = float(default_timeout)
        self._exe_override = str(exe) if exe else ""
        self._runner = runner if runner is not None else _proc.run_hidden
        self._env_overrides = dict(env or {})
        self._lock = threading.RLock()
        self._events = {}
        self._handles = {}
        self._sessions = {}

    def __repr__(self):
        return "<DshHarness exe=%r profile=%s runs=%d>" % (
            self._resolve_exe(), self.profile, self.ledger.count())

    # ---------------------------- 小器 ----------------------------

    def _resolve_exe(self):
        u"""dsh 之全径：显给者优先；否则 `shutil.which("dsh")`（空 ⇒ 未接）。"""
        if self._exe_override:
            return self._exe_override
        try:
            return shutil.which("dsh") or ""
        except Exception:
            return ""

    def _build_env(self):
        u"""子进程 env ＝ 本进程 env（**剥离 PA 的云端 key**）＋ DSH 专用 key／显给叠加。

        P2-2：PA 自己的 DEEPSEEK/OPENAI/… key **不再**漏给 DSH；
        DSH 只能用自己 credential store，或 PA 单独配置的 PA_DSH_DEEPSEEK_API_KEY。
        """
        env = dict(os.environ)
        for _k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "GLM_API_KEY", "ANTHROPIC_API_KEY"):
            env.pop(_k, None)
        try:
            from core.pa import dsh_credentials as _DC
            _DC.ensure_loaded()
            _k = _DC.get_key()
            if _k:
                env["DEEPSEEK_API_KEY"] = _k
        except Exception:
            pass
        env.update(self._env_overrides)
        return env

    # ---------------------------- 探 ----------------------------

    def probe(self):
        u"""`shutil.which("dsh")` ＋ `dsh --version` —— 可用性 ／ 版本 ／ 刻（⛔ 谎报）。"""
        exe = self._resolve_exe()
        at = _now_iso()
        if not exe:
            return ProbeResult(
                harness=self.name, available=False, version="", at=at,
                detail="dsh ⛔ 在 PATH（shutil.which 空）",
                meta={"exe": "", "rc": None, "stderr_tail": ""},
            )
        rc, out, err = None, "", ""
        try:
            proc = self._runner(
                [exe, "--version"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=DSH_PROBE_TIMEOUT, env=self._build_env(),
            )
            rc = getattr(proc, "returncode", None)
            out = _text(getattr(proc, "stdout", ""))
            err = _text(getattr(proc, "stderr", ""))
        except subprocess.TimeoutExpired:
            err = "TIMEOUT（%ss 到）" % DSH_PROBE_TIMEOUT
        except Exception as exc:
            err = "%s: %s" % (type(exc).__name__, str(exc)[:200])
        version = (out.strip().splitlines() or [""])[0].strip()
        available = bool(rc == 0 and version)
        detail = ("dsh --version ⇒ %s" % version if available
                  else "dsh --version 未证：rc=%s ／ %s" % (rc, _tail(err)))
        return ProbeResult(
            harness=self.name, available=available, version=version, at=at, detail=detail,
            meta={"exe": exe, "rc": rc, "stderr_tail": _tail(err)},
        )

    # ---------------------------- 跑 ----------------------------

    def run(self, spec):
        u"""起一次 `dsh --profile headless <task>`；完 ⇒ canonical `RunRecord` 落 PA 账。

        ⛔ 解析输出为账（stdout／stderr 只入增量与 `stderr_tail`）；⛔ 经 shell；
        超时 ／ 非零 rc ／ 起进程失败 ⇒ **status=failed 且仍落账**（H2：PA 侧必有记录）。
        """
        spec = RunSpec.from_any(spec)
        exe = self._resolve_exe()
        if not exe:
            raise DshUnavailable("dsh ⛔ 在 PATH（shutil.which 空）⇒ ⛔ 假跑")
        with self._lock:
            started_at = _now_iso()
            run_id = "pa-run-%s" % uuid.uuid4().hex[:12]
            session_id = "dsh-headless-%s" % uuid.uuid4().hex[:12]
            if spec.resume_id:
                if spec.resume_id not in self._sessions:
                    raise UnknownSession("DshHarness 无此 session：%r" % (spec.resume_id,))
                session_id = spec.resume_id
            cmd = [exe, "--profile", self.profile, spec.task]
            timeout = float(spec.timeout) if spec.timeout and spec.timeout > 0 else self.default_timeout
            rc, stdout, stderr = None, "", ""
            timed_out, spawn_error = False, ""
            try:
                proc = self._runner(
                    cmd, cwd=(spec.cwd or None), timeout=timeout,
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    env=self._build_env(),
                )
                rc = getattr(proc, "returncode", None)
                stdout = _text(getattr(proc, "stdout", ""))
                stderr = _text(getattr(proc, "stderr", ""))
            except subprocess.TimeoutExpired as exc:
                timed_out = True
                stdout = _text(getattr(exc, "stdout", ""))
                stderr = _text(getattr(exc, "stderr", ""))
                marker = "TIMEOUT（%ss 到）" % timeout
                stderr = ("%s ／ %s" % (stderr.strip(), marker)) if stderr.strip() else marker
            except Exception as exc:
                spawn_error = "%s: %s" % (type(exc).__name__, str(exc)[:200])
                stderr = spawn_error
            status = "ok" if (rc == 0 and not timed_out and not spawn_error) else "failed"
            ended_at = _now_iso()
            record = RunRecord(
                run_id=run_id,
                harness=self.name,
                session_id=session_id,
                model=spec.model,
                cwd=spec.cwd,
                started_at=started_at,
                ended_at=ended_at,
                status=status,
                cost=Cost(tokens=0, cny=0.0, turns=1),
                artifacts=(),
                harness_meta={
                    "profile": self.profile,
                    "rc": rc,
                    "stderr_tail": _tail(stderr),
                },
            )
            self.ledger.append(record)
            events = self._events_for(run_id, cmd, timeout, stdout, stderr, status, rc)
            handle = RunHandle(
                run_id=run_id,
                session_id=session_id,
                harness=self.name,
                history_replay=False,
                stream=tuple(events),
            )
            self._events[run_id] = tuple(events)
            self._handles[run_id] = handle
            self._sessions[session_id] = run_id
            return handle

    def _events_for(self, run_id, cmd, timeout, stdout, stderr, status, rc):
        u"""增量之形：start ⇒ stdout ／ stderr ⇒ done ／ error（⛔ 解析为账）。"""
        events = []

        def _emit(kind, text, data=None):
            events.append(StreamEvent(
                run_id=run_id, seq=len(events) + 1, at=_now_iso(),
                kind=kind, text=_tail(text, STREAM_TEXT_MAX), data=data or {},
            ))

        _emit("start", "dsh --profile %s 起（timeout=%ss）" % (self.profile, timeout),
              {"argv": list(cmd[:-1]), "task_chars": len(cmd[-1])})
        if stdout.strip():
            _emit("stdout", stdout)
        if stderr.strip():
            _emit("stderr", stderr)
        _emit("done" if status == "ok" else "error", "rc=%s" % (rc,))
        return events

    # ---------------------------- 续 ----------------------------

    def resume(self, session_id):
        u"""headless ⛔ 历史回放 ⇒ 只返续柄且 `history_replay=False` **显式**（§四.4）。

        ⛔ 落 RunRecord（未跑任务）；未知 session ⇒ UnknownSession（⛔ 假续）。
        """
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("resume(session_id) 须为非空字符串")
        with self._lock:
            if session_id not in self._sessions:
                raise UnknownSession("DshHarness 无此 session：%r" % (session_id,))
            run_id = "pa-run-%s" % uuid.uuid4().hex[:12]
            handle = RunHandle(run_id=run_id, session_id=session_id, harness=self.name,
                               history_replay=False, stream=())
            self._handles[run_id] = handle
            self._events[run_id] = ()
            return handle

    # ---------------------------- 停 ----------------------------

    def cancel(self, run_id):
        u"""v1 之 run **同步**（返回即已结束）⇒ 已知 run 恒 False（⛔ 谎报已停）。

        未知 run ⇒ UnknownRun。真「1s 内停」须 Popen 期实现（后续期 · ⛔ 本件假充）。
        """
        with self._lock:
            known = (run_id in self._handles) or self.ledger.has(run_id)
        if not known:
            raise UnknownRun("DshHarness 无此 run_id：%r" % (run_id,))
        return False

    # ---------------------------- 增量 ----------------------------

    def stream(self, run_id):
        with self._lock:
            events = self._events.get(run_id)
        if events is None:
            raise UnknownRun("DshHarness 无此 run_id：%r" % (run_id,))
        return events

    # ---------------------------- 门 ----------------------------

    def permissions(self):
        u"""headless **非交互** ⇒ 无人可批 ⇒ 待批即拒（`ask` 不可用 · ⛔ 假装可批）。

        本值只自报 adapter 之能力（⛔ PA 授权源 —— 真门在 PA doors／policy）。
        """
        return PermissionState(
            harness=self.name,
            level="headless",
            allowed_tools=(),
            pending=(),
            gates={"run": "allow", "write": "deny", "network": "deny", "spawn": "deny"},
            note="DSH headless 非交互 ⇒ 待批即拒；真授权在 PA doors/policy（⛔ 本件作授权源）",
        )

    # ---------------------------- 成本 ----------------------------

    def cost(self, run_id):
        u"""DSH headless ⛔ 回报成本 ⇒ canonical 记录为零值（`tokens=0, cny=0, turns=1`）。"""
        return self.ledger.get(run_id).cost

    # ---------------------------- 审计 ----------------------------

    def audit(self, run_id):
        rec = self.ledger.get(run_id)
        return AuditResult(
            run_id=rec.run_id,
            status=rec.status,
            receipt_sha16=rec.receipt_sha16,
            artifacts=rec.artifacts,
            harness_meta=dict(rec.harness_meta),
            started_at=rec.started_at,
            ended_at=rec.ended_at,
        )

    # ---------------------------- 团队（可选） ----------------------------

    def team(self):
        u"""**可选**能力：v1 ⛔ team（DSH Agent Team 收编属迁移步 3）⇒ 显式 available=False。"""
        return TeamState(
            harness=self.name,
            available=False,
            reason="DshHarness v1 ⛔ team（DSH Agent Team 收编属迁移步 3）",
            meta={"optional": True},
        )
