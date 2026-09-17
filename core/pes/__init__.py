# -*- coding: utf-8 -*-
"""V9-PES · **V9 Personal Execution System** —— Windows 版第一版架构。

对应文档：``PA_V9 总任务书 · 工程版 v1``（2026-09-17）。

架构固定为 **五层 + 三层外围**（总任务书 §3.1 / §3.2，术语修正 ③）：

| 层 | 模块 | 职责 |
|---|---|---|
| **State Integrity** | :mod:`core.pes.state_integrity` | 状态唯一读写出口：容错读 / 原子写 / 完整性判定 / 资格与运行态分离 |
| **Execution Contract** | :mod:`core.pes.contract` | 在既有 ``core.gateway.task_contract``（P0-负三）**上补字段**，不新造第二套 |
| **Capability Registry** | :mod:`core.pes.capability_registry` | 能力清单 + 门禁 + 风险等级；**未注册 = 拒绝**（fail-closed） |
| **Audit** | :mod:`core.pes.audit` | 独立 append-only 留痕 + 哈希链；**缺 run_id 的条目不合格** |
| **Memory** | :mod:`core.pes.memory` | 偏好 / 结论 / 上下文来源（session_id·workspace·project） |

外围：``windows``（Storage/进程/Shell 的 Windows 底座）、
``authorization``（权限模型：**两套授权 + 转换层**）、``run_registry``（汇总态，PA 独占写）。

**三条纪律**（总任务书原文）：
1. Contract 在既有 P0-负三 上补字段，**不新造第二套契约**；
2. 五层里**必须有 Audit**；
3. 状态所有权三层硬边界 —— **执行态（v9 单写者）/ 汇总态（PA 独占写、append-only）/
   上下文来源（每条资产带 session_id·workspace·project）**，**PA 对执行态只读不改**。

**MVP 落点**：本版只交付 **M1（状态可信）** 的可运行实现，
以及 M2（任务闭环）所需的最小件；**不追求功能数量**。
"""

from __future__ import annotations

__version__ = "1.0.0"
ARCH_NAME = "V9 Personal Execution System"
ARCH_SHORT = "V9-PES"

#: 五层固定清单（术语修正 ③：必须有 Audit）
CORE_LAYERS = (
    "State Integrity",
    "Execution Contract",
    "Capability Registry",
    "Audit",
    "Memory",
)

#: 三层外围
EDGE_LAYERS = ("UI", "Agent", "Storage")

#: 状态所有权三层（硬边界）
OWNERSHIP_TIERS = ("execution", "summary", "context_source")

__all__ = [
    "__version__",
    "ARCH_NAME",
    "ARCH_SHORT",
    "CORE_LAYERS",
    "EDGE_LAYERS",
    "OWNERSHIP_TIERS",
]