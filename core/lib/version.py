# -*- coding: utf-8 -*-
u"""⭐ 版本号之「一处定形」（承 pm_1384 §三.5：`/` 报 `6.0.0` ⟷ 仓 `9.0.0` ⇒ 归一）。

病：产品版号在仓内**各自硬编**者三处 ——
  · `routes/static.py:117`（**活**：线上 `/` 即此）                  ⇒ 旧字面 `6.0.0`
  · `core/web/health.py:20`（⚠ **死码**：`health_bp` 全仓 0 处注册）⇒ 旧字面 `6.0.0`
  · `core/routes/system_routes.py:31`（`/health`）                  ⇒ 旧字面 `6.0.0`
⟷ 包版 `pyproject.toml` 之 `[project].version` ≡ 本模块之 `__version__`（见下）；⛔ 各处再书
⇒ **演示时对不上**（净机首屏之 `/` 与仓之包版相歧 ⇒ 承 pm_1384 §三.5）。

正解：⛔ 各处再书；⇒ 本模块之 `__version__` ＝ **唯一真源**
（诸面 `from core.lib.version import SERVICE_NAME, __version__`）。
⚠ 本模块**不读文件**（⛔ 导入期 IO ／ ⛔ 静默回落 —— 承「⛔ 装成可用」）；
  ⟷ `pyproject.toml` 之一致由 `tests/unit/test_version_single_source.py` **以器核**（⛔ 人记）。
"""

__version__ = u"9.4.0"

SERVICE_NAME = u"ClawsJoy Gateway"


def service_info():
    u"""`/` 之报体（逐字承旧形：service ＋ version）—— **一处出**。"""
    return {"service": SERVICE_NAME, "version": __version__}
