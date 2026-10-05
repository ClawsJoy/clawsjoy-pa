# -*- coding: utf-8 -*-
"""A3 · 会话创建即 seed（DS 裁 #27 ＝「会话创建时 seed」；DS 裁 A3 三问：缩 scope / LIVE 树 / 不硬链接）。

为什么有这个件
--------------
`sandbox_seed.py` 的写入器与校验器**早已存在，却零调用者** ⇒「未 seed」是系统性现象。
真因（我方实证，DS 已认）：旧 `check_seed` 把 manifest **锚在沙箱** ⇒ 要求「沙箱自 seed 后零变」；
而**沙箱是工作区、设计上会被写** ⇒ **接了就自锁**（PA 第一次写文件后，下一回合必被 seed 门拦死）。
⇒ DS 裁 (i)：**锚点移到源**（`source_path` 可读 ＋ `source_manifest_hash`），沙箱侧 manifest **只作读数**。

本件职责（薄，只做接线）
------------------------
`ensure_seeded(user_id, session_id)`：
  1) 已 seeded ⇒ **幂等**直接返回（不重复拷贝）；
  2) 否则 `seed_sandbox(...)`（copy=True；scope=SEED_SCOPE；exclude=SEED_EXCLUDE ⇒ 实测 ≈21 MB/会话，
     而照字面全 scope 是 **2.17 GB / 86,355 files** ⇒ 不符 #27「首用不卡」）；
  3) **落痕**由 `seed_sandbox` 写（source_path / seed_at / commit / scope / exclude /
     source_manifest_hash（判定锚）＋ manifest_hash、file_count（沙箱侧读数））；
  4) 任何失败 ⇒ **抛**（调用方 fail-loud，不得静默继续；`L-48` 互链）。

开关
----
  `V9_SEED_ON_CREATE=0`  ⇒ 调用方跳过本件（回滚 = 环境变量，不改代码）；
  `V9_SEED_SOURCE=<path>` ⇒ 覆盖 seed 源（默认 = 本件向上三层，即**跑的那棵树**根）。
"""
import os
import subprocess
from pathlib import Path
from core.gateway import _proc as _proc  # ⭐ 窗隐唯一出口（PM 2026-10-05 令 · ⛔ 各写 creationflags）


def source_root():
    """seed 源（DS 裁：用 LIVE 树）。默认 = 本件向上三层 ⇒ 永远是「跑的那棵树」的根。"""
    env = str(os.environ.get("V9_SEED_SOURCE") or "").strip()
    if env:
        return env
    return str(Path(__file__).resolve().parents[2])


def _commit_of(src):
    try:
        r = _proc.run_hidden(["git", "-C", str(src), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
        return (r.stdout or "").strip()[:40] if r.returncode == 0 else ""
    except Exception:
        return ""


def sandbox_of(user_id, session_id, root="data/projects"):
    return Path(str(root)) / str(user_id) / str(session_id) / "clawsjoy_dev"


def ensure_seeded(user_id, session_id, source_path=None):
    """返回 {'created','status','sandbox','record','source'}；**失败即抛**（fail-loud）。"""
    from core.gateway.sandbox_seed import check_seed, seed_sandbox

    sb = sandbox_of(user_id, session_id)
    _cur = check_seed(sb)
    if _cur.get("ok"):
        return {
            "created": False,
            "status": "already_seeded",
            "sandbox": str(sb),
            "record": None,
            "check_status": _cur.get("status"),
        }

    src = str(source_path or source_root())
    if not Path(src).is_dir():
        raise RuntimeError("seed 源不可读：%s" % src)

    sb.mkdir(parents=True, exist_ok=True)
    rec = seed_sandbox(sb, src, commit=_commit_of(src))

    _after = check_seed(sb)
    if not _after.get("ok"):
        raise RuntimeError("seed 后自检未过：%s" % str(_after.get("reason"))[:200])
    return {"created": True, "status": "seeded", "sandbox": str(sb), "record": rec, "source": src}
