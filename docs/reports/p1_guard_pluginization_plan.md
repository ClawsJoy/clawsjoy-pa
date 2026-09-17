# P1 守卫插件化可行性评估与实施方案

> 日期：2026-08-18 | 状态：设计稿（只读分析 + 设计, 不实施）
> 依据：P0 容器(V9Context + 服务注册 + 工具注册表)已完成; 本方案把散落内联守卫收编为 tools/pre-execute 插件
> 前提：双路径(bridge_loop vs execute_agent_task)审批语义差异由**作用域**表达, 不强制合并代码

---

## 一、当前守卫盘点(实证)

### 1.1 双路径入口分叉

| 路径 | 入口 | 触发方式 | 审批语义 |
|---|---|---|---|
| **主聊天** | `_v9_bridge_loop`(agent_gateway_enhanced.py L1790) | `v9_agent_chat` 直接调用(L3680 SSE / L3727 同步) | **锚点A 写审批**(pending_writes) |
| **子任务** | `_execute_agent_task`(L3088/3119 线程) | 计划确认后异步 / 长线任务 | **免审批**(架构隔离声明) |

两路径**都**经 `tool_router._execute_sandbox_tool`(11 处调用点)执行工具 → tool_router 内守卫对两路径统一生效。

### 1.2 守卫清单(按位置)

| # | 守卫 | 位置 | 逻辑摘要 | 返回语义 |
|---|---|---|---|---|
| G1 | **锚点A 写审批** | bridge_loop L1922-1969 | write_file/write_large/edit_file 未确认 → 记 pending_writes, 返回 write_pending 状态 | **状态机**(前端卡片) |
| G2 | **锚点B 路径越权** | bridge_loop L1850-1882 | 写类工具路径逃逸沙箱 → 直接拒绝 + escalation_blocked | 硬拒绝 |
| G3 | **锚点B 高危命令** | bridge_loop L1978-2010 | execute_command 触发 _detect_sys_escape → 拒绝 + escalation_blocked | 硬拒绝 |
| G4 | **plan_pending 计划确认** | bridge_loop L1884-1920 | ≥2 文件或 ≥3 意图未确认 → 暂停 + plan_pending 状态 | **状态机** |
| G5 | **ask 通道** | bridge_loop L1826-1842 | 检测 ask 式提问 → 返回 ask 状态 | **状态机** |
| G6 | **重复工具提醒** | execute_agent_task L1206-1212 | repeat_tool_reminder.observe 3/5/8 → 注入 system 消息 | 观察(已插件化) |
| G7 | **递归检测** | execute_agent_task L1218-1228 | check_recursion → pause 时暂停任务 | 状态机(paused) |
| G8 | **连续同工具追踪** | execute_agent_task L1230-1246 | ≥3 次连续同工具 → 注入 system 提示 | 观察 |
| G9 | **配额检查** | tool_router L139-147 | check_tool_quota → 超限拒绝 quota_exhausted | 硬拒绝 |
| G10 | **模式检查** | tool_router L148-158 | minimal 模式禁用 list/search/query → 拒绝 | 硬拒绝 |
| G11 | **强制工具校验** | tool_router L160-165 | 修改任务禁读工具 → 拒绝 | 硬拒绝 |
| G12 | **§4.1/§4.3 禁则** | tool_router execute_command 分支 | _*.py 临时脚本 / open() 直写 → 拒绝 forbidden | 硬拒绝 |
| G13 | **§4.2 禁则** | write_file 插件内 L9-16 | 禁写共享配置文件 → 拒绝 forbidden | 硬拒绝 |
| G14 | **连续失败暂停** | tool_router `_with_tool_flow` | ≥5 注入提示 / ≥8 强制暂停 | 后置观察+状态 |
| G15 | **审计+tool_flow** | tool_router `_with_tool_flow` | record_tool_flow + audit_tool_call | 后置观察 |
| G16 | **SSE 进度(tool_steps)** | bridge_loop | 每工具调用收集 tool_steps → 前端进度 | 展示(非守卫) |

---

## 二、可行性评估

### 2.1 可直接收编(行为不变)✅

| 守卫 | 挂载点 | 理由 |
|---|---|---|
| G9 配额 | tools/pre-execute | 纯函数判断, 返回 deny+reason 即拒绝, 无状态依赖 |
| G10 模式 | tools/pre-execute | 同上 |
| G11 强制工具校验 | tools/pre-execute | 读 messages 判任务类型, 只读 |
| G12 §4.1/§4.3 禁则 | tools/pre-execute | 纯字符串匹配, 返回 forbidden |
| G13 §4.2 禁则 | tools/pre-execute | 从 write_file 插件移到 guard(纯路径判断) |
| G6 重复提醒 | tools/post-execute(观察) | 已模块化, 只需从函数调用改为监听器 |
| G15 审计+flow | tools/post-execute + tools/result | `_with_tool_flow` 装饰器逻辑原样搬入 |
| G2/G3 锚点B | tools/pre-execute | 路径/命令逃逸判断是纯函数, 拒绝语义=deny |

**关键**:以上 9 个守卫**不涉及状态机**,收编后返回结构(`{"success": False, "error": ..., "forbidden"/"quota_exhausted"/"escalated"...}`)由 guard 的 deny payload 原样携带, 前端兼容。

### 2.2 有状态机依赖(需透传, 不可简单收编)⚠️

| 守卫 | 状态 | 依赖 | 收编策略 |
|---|---|---|---|
| G1 锚点A 写审批 | `_pending_writes[session_id]` + write_pending 状态 | 前端渲染 write_pending 卡片 → 用户确认 → 重新提交 | guard 返回 `{"deny": True, "status": "write_pending", "pending_write": {...}}`; 确认流程由 **bridge 层持有**(不在 guard 内) |
| G4 plan_pending | `_plan_pending[session_id]` + plan_pending 状态 | 前端 plan_pending 卡片 → 确认后异步执行 | 同上: guard 只**检测并返回 plan_pending**, 状态存储/确认留在调用方 |
| G7 递归暂停 | `_paused_breakpoints` + paused 状态 | 暂停后等老板决定 | guard 返回 paused 状态, 由调用方 `_save_state("paused")` + 返回 |

**核心洞察**:这 3 个守卫的**检测逻辑**可以收编(纯判断),但**状态机结果(write_pending/plan_pending/paused)必须透传给调用方**,由调用方(主聊天 bridge 或子任务 executor)决定如何返回给前端。设计:guard deny payload 携带 `status` 字段, 调用方按 status 分支处理。

### 2.3 需跨 guard 顺序保证(注册序敏感)🔒

| 顺序约束 | 理由 |
|---|---|
| G9 配额 → G10 模式 → G11 强制 → G12/G13 禁则 → G2/G3 越权 | 配额先于一切(资源保护); 模式/强制/禁则先于越权(业务语义); 越权最后(安全兜底) |
| G1 锚点A → G2 越权 | 写审批应先于路径越权检查(未确认的写不查越权) — 或相反? 现状: bridge 先查越权(G2)再查审批(G1) |

**注**:现状顺序是 bridge 内 G2→G1(先越权后审批); 收编后注册序必须**精确复现现状顺序**, 否则行为变化。见 §3.2 注册表。

### 2.4 应留在原处(不宜插件化)❌

| 守卫 | 理由 |
|---|---|
| G5 ask 通道 | 不是工具级守卫, 是 **LLM 输出检测**(agent/pre-step 后), 与工具执行无关 |
| G8 连续同工具追踪 | 与 G6 重复提醒功能重叠(旧逻辑), P1 保留, P2 由 repeat_tool_reminder 统一收敛后删除 |
| G16 SSE tool_steps | 是**展示层**(前端进度), 非守卫; 保留在 bridge_loop |
| G14 连续失败暂停 | 依赖**工具结果**(post-execute), 但含"保存断点+强制暂停"状态机 → 部分收编(计数部分), 暂停动作留调用方 |

---

## 三、P1 实施方案

### 3.1 Guard 插件清单

```python
# core/gateway/guards/ 新目录(P1 新增)
core/gateway/guards/
  __init__.py
  base.py          # ToolGuard 基类(复用 V9Plugin, 定义 pre_execute/name)
  quota_guard.py       # G9  配额
  mode_guard.py        # G10 模式
  forced_tool_guard.py # G11 强制工具校验
  forbidden_guard.py   # G12+G13 §4.1/§4.2/§4.3 禁则(合并)
  escape_guard.py      # G2+G3 锚点B 路径/命令越权
  approval_guard.py    # G1  锚点A 写审批(状态机透传)
  plan_guard.py        # G4  计划确认(状态机透传)
  recursion_guard.py   # G7  递归暂停(状态机透传)
  reminder_guard.py    # G6  重复提醒(观察)
  audit_guard.py       # G15 审计+tool_flow(观察)
  failure_pause_guard.py # G14 连续失败(计数部分)
```

**ToolGuard 基类**:
```python
class ToolGuard(V9Plugin):
    """工具守卫: 挂 tools/pre-execute(可拒绝) 或 tools/post-execute(观察)"""
    name: str = ""
    order: int = 0          # 注册顺序(见执行顺序注册表)
    event: str = "tools/pre-execute"

    def apply(self, ctx, scope=None):
        ctx.on(self.event, self._handler, scope=scope.key if scope else None)
        return self

    def _handler(self, payload):
        return self.check(payload)   # 返回 None=放行, dict=拒绝/观察结果

    def check(self, payload): raise NotImplementedError
```

### 3.2 执行顺序注册表(精确复现现状)

```python
# core/gateway/guards/registry.py
GUARD_ORDER = [
    # tools/pre-execute 顺序(现状 bridge: G2越权→G1审批→G4计划; exec: G6提醒→G7递归)
    # 统一顺序(两路径共享, 差异由 scope 挂载决定):
    ("quota_guard", 10),            # G9  配额(最先)
    ("mode_guard", 20),             # G10 模式
    ("forced_tool_guard", 30),      # G11 强制工具校验
    ("forbidden_guard", 40),        # G12+G13 禁则
    ("escape_guard", 50),           # G2+G3 锚点B 越权
    ("approval_guard", 60),         # G1 锚点A 写审批
    ("plan_guard", 70),             # G4 计划确认
    ("recursion_guard", 80),        # G7 递归
    # tools/post-execute(观察)
    ("reminder_guard", 100),        # G6 重复提醒
    ("audit_guard", 110),           # G15 审计+flow
    ("failure_pause_guard", 120),   # G14 连续失败计数
]

def mount_guards(ctx, scope_key=None, include=None):
    """按注册表挂载守卫。include 过滤(如子任务 scope 不挂 approval/plan)。"""
    for name, order in GUARD_ORDER:
        if include and name not in include:
            continue
        cls = _GUARD_CLASSES[name]
        guard = cls()
        guard.order = order
        ctx.mount(guard, scope=scope_key)
```

**关键**:waterfall 按注册序执行——`ctx.waterfall("tools/pre-execute", payload)` 返回首个 deny。注册表 order 即守卫执行顺序, 精确复现现状(配额→模式→强制→禁则→越权→审批→计划→递归)。

### 3.3 双路径收敛策略(不强制合并, 共享框架)

```python
# 主聊天 bridge_loop: 挂全部守卫(含审批/计划/递归)
mount_guards(ctx, include=[
    "quota_guard", "mode_guard", "forced_tool_guard", "forbidden_guard",
    "escape_guard", "approval_guard", "plan_guard", "recursion_guard",
    "reminder_guard", "audit_guard", "failure_pause_guard",
])

# 子任务 scope: 挂子集(免审批/免计划 — 审批语义差异由作用域表达)
sub_scope = f"{session_id}_{task_id}"
mount_guards(ctx, scope_key=sub_scope, include=[
    "quota_guard", "mode_guard", "forced_tool_guard", "forbidden_guard",
    "escape_guard", "recursion_guard", "reminder_guard", "audit_guard",
    "failure_pause_guard",
])
# 不挂 approval_guard / plan_guard → 子任务写直接放行(与现状"子任务免审批"一致)
```

**调用方改造**(bridge_loop / execute_agent_task 各保留一层薄分发):
```python
# 两路径共用: 工具调用前
_deny = v9ctx.waterfall("tools/pre-execute", {
    "tool": _bfn, "args": _bargs, "user_id": user_id, "session_id": session_id,
    "sandbox_base": _sb_task3, "messages": messages,
}, scope=scope_key)
if _deny is not None:
    # 按 _deny["status"] 分支: write_pending/plan_pending/escalation_blocked/paused/forbidden/quota
    return _handle_deny(_deny, ...)
```

**差异点处理**:
| 现状差异 | 收编后 |
|---|---|
| bridge 有 approval_guard / plan_guard | 子任务 scope 不挂这两个 → 天然免审批 |
| bridge 的 tool_steps 收集 | 保留在 bridge(展示层, 不插件化) |
| exec 的 `_save_state("paused")` | recursion_guard 返回 paused, exec 调用方执行保存 |

### 3.4 分步实施顺序(每步可验证)

| 步骤 | 内容 | 验证 |
|---|---|---|
| **S1** | 建 `guards/` 目录 + ToolGuard 基类 + 顺序注册表 + 空实现 | 单元测试: 注册表顺序、基类挂载 |
| **S2** | 收编**无状态守卫**(G9/G10/G11/G12/G13)到 tool_router: 保留原 if 分支, 新增 guard 并行, **对比输出一致**后删原分支 | 6 工具回归(禁则/配额/模式全触发) |
| **S3** | 收编**锚点B**(G2/G3): escape_guard 挂 pre-execute; 删 bridge 内联 | bridge E2E: 越权写入/高危命令仍拦截 |
| **S4** | 收编**观察守卫**(G6/G15/G14计数): reminder/audit/failure_pause 挂 post-execute; `_with_tool_flow` 装饰器体搬入 audit_guard | 审计记录/提醒/暂停回归 |
| **S5** | 收编**状态机守卫**(G1/G4/G7): approval/plan/recursion guard 返回 status; 调用方按 status 分支 | 主聊天写审批 E2E + 子任务免审批 E2E + 递归暂停 E2E |
| **S6** | 双路径统一入口: bridge 与 exec 共用 `_deny_handle` 薄层; 删 bridge/exec 内联 if | 全量回归 + live E2E |

**每步独立提交, 可回滚**。

### 3.5 风险清单 + 回滚方案

| # | 风险 | 等级 | 缓解 | 回滚 |
|---|---|---|---|---|
| 1 | **审批状态机透传破坏**: write_pending 卡片前端依赖 pending_write 结构 | 高 | guard deny payload 原样携带 pending_write/plan_pending; S5 用真实 E2E 验证 | 还原 approval_guard 挂载 = 恢复内联 |
| 2 | **守卫顺序变化**: 现状 bridge 先越权后审批, 统一注册表若顺序错 → 行为变 | 高 | 注册表 order 精确复现; S2-S3 逐守卫对比输出 | 回退 GUARD_ORDER |
| 3 | **子任务意外审批**: 若子任务 scope 误挂 approval_guard → 子任务卡死 | 高 | scope 挂载清单显式排除; S5 E2E 覆盖子任务写 | 移除 scope 挂载 |
| 4 | **waterfall 短路误伤**: 某 guard 返回 dict 被误判为 deny | 中 | ToolGuard 约定: 观察守卫挂 post-execute(不短路); pre-execute 只挂可拒绝守卫 | — |
| 5 | **messages 全局依赖**: G11 强制校验读 messages(全局单例) | 中 | P2 迁 scope 前, guard 经 payload 接收 messages 引用(不直接 import) | — |
| 6 | **_with_tool_flow 装饰器拆除回归**: 审计/flow 记录丢失 | 中 | S4 先并行(装饰器+guard 都记), 对比后再删装饰器 | 保留装饰器 |
| 7 | **exec 路径的 _shared_msgs hack**: 同步消息供模式判定 | 中 | P1 不动此 hack; S6 统一入口时评估 | — |
| 8 | **性能**: 每工具调用多一层 waterfall 分发 | 低 | waterfall 是纯内存 dict 遍历(µs 级); 实测对比 | — |

**全局回滚**: 每个守卫独立提交; 出问题 `git revert` 该提交即恢复内联(guard 与内联并存期间互不干扰)。

---

## 四、结论

- **9 个守卫可直接收编**(G2/G3/G6/G9/G10/G11/G12/G13/G15) — 无状态依赖
- **3 个守卫需状态机透传**(G1/G4/G7) — 检测收编, 状态处理留调用方
- **3 个留在原处**(G5 ask/G8 连续同工具/G16 tool_steps) — 非工具级守卫或展示层
- **核心机制**: 双路径共享 guard 框架, 审批差异由 **scope 挂载清单**表达(子任务不挂 approval/plan) — 不强制合并代码
- **6 步实施, 每步可验证可回滚**; 风险集中在审批状态机透传(S5)与守卫顺序(注册表)

> P1 完成后: 守卫全部从执行循环剥离 → `execute_agent_task`/bridge_loop 工具循环显著瘦身 → 新守卫=写一个 ToolGuard 插件 + 注册表加一行。
