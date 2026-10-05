# -*- coding: utf-8 -*-
u"""_proc.py —— `core/pa` 之子进程**唯一出口**：一律不带控制台窗（Windows）。

⭐ 2026-10-05（PM b136893 令 · 老板「**现在还是 CMD 弹窗**」）：
  真凶 ＝ 读面时 spawn 子进程**未带** `CREATE_NO_WINDOW`。
  物证（PM 一手 · conhost 计数）：70 秒新开 10 个控制台，其父命令行**逐字**命中
  `paseo agent ls --json`（`env_face.py` ／ `agent_scan.py`）与
  `xintong_tick.py --json --all`（`resume_face.py:168`）。

律（承「一处定形」· ⛔ 逐处打补丁）：**凡 `core/pa/**` 之 subprocess 调用 ⇒ 皆调本器**
（`run_hidden` ／ `popen_hidden`）；⛔ 各写一套 `creationflags`。

口径：
  - `creationflags` 唯 Windows 有 ⇒ 以 `getattr(subprocess, "CREATE_NO_WINDOW", 0)` 取值
    ⇒ 非 Windows 退化 `0`（⛔ 抛 · ⛔ 平台判断散在 call site）。
  - 调用方**已给** `creationflags` ⇒ **并**（`|`）· ⛔ 覆盖。
  - `CREATE_NO_WINDOW` 与 `CREATE_NEW_CONSOLE` ／ `DETACHED_PROCESS` 互斥（后随者胜）
    —— 本器不主动加后二者；调用方自决处照实留字。
  - ⛔ 动 stdout／stderr／stdin／cwd ／ timeout 等（签名与 `subprocess.run` 同形 · 唯加窗隐）。
"""
import subprocess

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _merge_flags(kw):
    u"""把 `CREATE_NO_WINDOW` **并**进调用方已给之 `creationflags`（⛔ 覆盖 · ⛔ 丢）。"""
    kw["creationflags"] = int(kw.get("creationflags", 0) or 0) | NO_WINDOW
    return kw


def run_hidden(cmd, **kw):
    u"""`subprocess.run` 之窗隐替身（签名同 · 唯 `creationflags` 恒并 `CREATE_NO_WINDOW`）。"""
    return subprocess.run(cmd, **_merge_flags(kw))


def popen_hidden(cmd, **kw):
    u"""`subprocess.Popen` 之窗隐替身。"""
    return subprocess.Popen(cmd, **_merge_flags(kw))


def call_hidden(cmd, **kw):
    u"""`subprocess.call` 之窗隐替身（今无 call site ⇒ 备而不用）。"""
    return subprocess.call(cmd, **_merge_flags(kw))
