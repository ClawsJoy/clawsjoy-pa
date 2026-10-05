# -*- coding: utf-8 -*-
u"""_proc.py —— `core/gateway` 之子进程**唯一出口**：一律不带控制台窗（Windows）。

⭐ 2026-10-05（PM b136893 令 · 承 `1040 §五` 之批 A）：`core/gateway/**` 之 subprocess
   一律经本器 ⇒ `run_hidden` ／ `popen_hidden`（⛔ 逐处打补丁 · ⛔ 各写一套）。

⭐ **唯此一处实现** ＝ `core/pa/_proc.py`；本器**按文件路径**载之，⛔ 走 `from core.pa import _proc`：
   那会执行 `core/pa/__init__.py`（拉 `pa_core` ＋ `vault_brain`）⇒ ① 有副作用
   ② 有**循环导入**之险（`core/pa/**` → `core/gateway/**` → 回 `core/pa`）③ 无谓。
   按路径载 ⇒ **零副作用 ／ 零环 ／ 仍单源**（实测 `core.pa._proc` 之边际成本 ≈ 0 ——
   重者乃 `core/__init__.py`，凡 `core.*` 皆已付）。

口径（同真源）：`creationflags` **并**（⛔ 覆盖）· 非 Windows 退化 `0` · 签名与 `subprocess` 同形。
载不到真源 ⇒ **明报**（⛔ 静默退化 —— 少一旗即少一闸）。
"""
import importlib.util as _ilu
import os as _os

_CANON = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "pa", "_proc.py")
_spec = _ilu.spec_from_file_location("_pa_proc_canonical", _CANON)
if _spec is None or _spec.loader is None:
    raise ImportError(u"窗隐真源不可载（缺件？）：%s" % _CANON)
_m = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_m)

NO_WINDOW = _m.NO_WINDOW
run_hidden = _m.run_hidden
popen_hidden = _m.popen_hidden
call_hidden = _m.call_hidden
CANON_SHA16 = None  # 真源之印（惰性：调用方自行取 _m 之源）
