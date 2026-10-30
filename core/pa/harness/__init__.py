# -*- coding: utf-8 -*-
u"""PA HarnessPort v1（`core/pa/harness/`）。

规则（62_PA_HarnessPort_v1 §四.1）：**core/pa 只 import 本包之 `port`**；adapter（mock ／
dsh ／ paseo ／ …）⛔ 由本件隐式引入 —— 否则「core/pa 只依赖接口」落空（H5 之齿）。
⇒ 本件**唯**导出 `port.py` 之公共名；`MockHarness` 须显式：

    from core.pa.harness.mock import MockHarness

`core/pa/harness/__init__.py` 自身 ⛔ import dsh ／ paseo ／ obsidian（H1 ／ H5）。
"""

from core.pa.harness.port import (
    HARNESS_METHODS,
    PA_HARNESS_PORT_VERSION,
    PERMISSION_GATES,
    RUN_RECORD_FIELDS,
    RUN_SPEC_FIELDS,
    RUN_STATUSES,
    STREAM_KINDS,
    AuditResult,
    Cost,
    HarnessError,
    HarnessPort,
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
    UnsupportedCapability,
    canonical_json,
    sha16,
)

__all__ = [
    "HARNESS_METHODS",
    "PA_HARNESS_PORT_VERSION",
    "PERMISSION_GATES",
    "RUN_RECORD_FIELDS",
    "RUN_SPEC_FIELDS",
    "RUN_STATUSES",
    "STREAM_KINDS",
    "AuditResult",
    "Cost",
    "HarnessError",
    "HarnessPort",
    "PermissionState",
    "ProbeResult",
    "RunHandle",
    "RunLedger",
    "RunRecord",
    "RunSpec",
    "StreamEvent",
    "TeamState",
    "UnknownRun",
    "UnknownSession",
    "UnsupportedCapability",
    "canonical_json",
    "sha16",
]
