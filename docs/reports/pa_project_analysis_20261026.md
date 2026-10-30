# PA（主权 Agent）项目代码核查与总结分析

- 日期: 2026-10-26
- 核查范围: `core/pa/**`（46 模块）、`web/pa/**`（27 面 + core/boot）、PA 相关测试、`data/v9/pa` 运行态、git 工作树
- 方法: 静态阅读 + 结构统计 + 冒烟测试 + 运行态观测（**未跑全量测试**）
- 基线: `HEAD 8e23b02`（2026-10-09 08:42）· 工作树 15 改 / 330 未跟踪
- 性质: 只读核查，未改任何产品代码

---

## 一、结论摘要

**一句话**：PA 已经从一个"文件型小助手"长成了一个**有真实主权语义的个人执行体**（身份归一、绑形回环、fail-closed 权限档、有据才答、回执留痕），但它的**工程形态没有跟上语义的成长**——HTTP 面挤在一个 4,828 行的文件里，异常处理大面积宽捕，决策依据（2,288 份 `_pm` 文件）在版本控制之外，前端有一个 4,620 行的"自述"巨物。

**判断**：方向对、语义真、治理重、形态旧。当前更像"一个高纪律的个人系统"，还不是"可交付的主权产品"。

### 健康度评分（本次核查）

| 维度 | 分 | 依据 |
|---|---:|---|
| 产品方向与主权语义 | 8.5 | 主权四层、有据才答、拍板点、口径单、回执——都是真机制不是口号 |
| 身份与安全边界 | 6.5 | 绑形默认 127.0.0.1、身份由装根铸一次、远端不可定身份；但 PA 内部无 owner 级授权 |
| 内核与分层 | 6.5 | `PaCore` 纯逻辑 + 面件分工；但 `gateway_routes.py` 4,828 行 |
| 状态与一致性 | 7.0 | `state_out` 原子写 + fail-closed；仅 6 处显式锁，仍为文件型状态 |
| 可观测与可追溯 | 8.0 | receipts / feedback / decision / caliber / grants 全留痕 |
| 可维护性 | 4.0 | 宽捕 315、`except: pass` 42、414 处 `pm_` 引用、`selfdesc.js` 4,620 行 |
| 测试 | 7.0 | 139 个 PA 测试文件、1,061 条可收集；基线台账记 42 红 |
| 交付卫生 | 3.5 | 4 周 356 次提交；15 改 + 330 未跟踪；23.8MB 备份残骸；2,288 份决策文件在仓外 |
| **综合** | **6.4 / 10** | 语义成熟度显著高于工程成熟度 |

---

## 二、核查证据（可复算）

| 指标 | 实测 |
|---|---|
| 后端 PA 模块 | 46 个 `.py`，**16,925 行** |
| 最大后端文件 | `gateway_routes.py` **4,828 行 / 273KB / 88 条路由 / 75 个 def** |
| 次大 | `env_face.py` 1,099 行、`sys_face.py` 933、`mailer.py` 865、`agent_invoke.py` 666 |
| 前端 | `web/pa/` 27 个面 + `core.js` + `boot.js` = **14,156 行**（不含备份） |
| 前端最大件 | `faces/selfdesc.js` **4,620 行 / 330KB**；`tasks.js` 1,662；`more.js` 922 |
| 路由 | 88 条（GET 43 / POST 44 / 混合 1），**0 个认证装饰器** |
| 异常 | `except Exception` **315 处**；下一句 `return`（可见）135、`pass`（吞）**42**、仅日志 15 |
| 子进程 | 14 处 `subprocess` 引用，`shell=True` 0 处 |
| 锁 | 仅 6 处显式锁；状态仍以文件为主 |
| 状态写 | `write_state()` 9 处；裸 `open(...,"w/a")` 11 处、`json.dump` 1 处 |
| 测试 | PA 相关测试文件 **139** 个；`-k pa_` 收集 **1,061** 条（全仓 2,951） |
| 提交 | 全仓 **417** 次；2026-09-29 以来 **356** 次 |
| 运行态数据 | `data/v9/pa` **671 文件 / 5.2MB**；`env_notes` **560 份**（每 30 分钟一对 json+md，10-05 → 10-15） |
| 备份残骸 | 全仓 `.before_*` **3,824 个 / 151.2MB**（已 gitignore，但占盘且干扰阅读）；其中 `web/pa` 333 个 / 23.8MB |
| 决策档案 | `_pm/` **2,288 个文件**（**已 gitignore**）；代码内 `pm_` 引用 **414 处 / 96 个 id** |

---

## 三、做对了什么（具体，不是客套）

### 3.1 身份归一：从"每个浏览器一枚 id"到"装根铸一次"

`core/pa/identity.py` 的注释把病根写得很清楚：本机 `data/v9/pa` 曾积 **16 枚 id**——真身份 1 枚（197KB 会话史）+ 验跑空壳 15 枚（各 289B）。铸它的不是机器，是**每一个浏览器上下文**。

治法也是对的：

- 身份由装根铸一次（`owner.json`），浏览器 localStorage 只是 **hint**；
- 认领规则防"丢史"：未立 owner ∧ hint 为 `web_*` ∧ threads 非空 ⇒ 认旧值为 owner；
- **远端不可定身份**：`whoami` 对非环回直接 403（`gateway_routes.py:2945`）；
- owner.json 坏 ⇒ 409（fail-loud，不回落空身份）。

这是"主权"应有的样子：身份是**本机事实**，不是请求参数。

### 3.2 绑形：0.0.0.0 从默认改成显式选项

`core/gateway/boot.py:16-30` 把监听址收敛到 `_bind_host()`，默认 `127.0.0.1`，跨机须显式 `CJ_PA_BIND`。注释直接点名旧病："此处硬编 0.0.0.0 ⇒ 局网可达（netstat 见 0.0.0.0:5102）"。

**本次核查实测**：网关当前监听 `127.0.0.1:5102`（PID 19348），无 `CJ_PA_BIND`。已修正。

### 3.3 权限档：把"损坏即放宽"改成 fail-closed

`core/pa/permission.py` 的注释是一份很好的事故复盘：此前"文件存在但不可用（损坏 JSON／非法 level／空文件）"被静默忽略并回落 `标准`，而 `只读 < 标准` ⇒ **损坏即放宽**。现在读写统一走 `state_out`，坏 ⇒ 抛。

这是"主权系统"最该有的反射：**失败必须朝更严的方向倒**。

### 3.4 产品语义是真的

- **有据才答**：`/v9/pa/ask` 先检索，检索不到只许说"查不到"，不许给数字；
- **自述面**：`selfdesc.js` 专门解决"问它是谁 / 有哪些工具"时退化成知识库机器人的问题；
- **拍板点**：采纳/小改/大改/退回/暂缓，不是"确认/取消"；
- **口径单**：`caliber/change` 必填 id/status/owner/why，把"改口径"从改源码变成记一条；
- **回执与反馈**：`receipts.py` / `feedback_store.py` / `dispatch/receipt` 形成闭环。

### 3.5 判据文化下沉到了测试

139 个 PA 测试文件，覆盖到"屏上唯人话""工程之据入 title""四行之真渲"这种细节。`tests/unit/test_gateway_bind_1802.py` 直接钉绑定默认值，`test_pa_provider_keys_1613.py` 钉远端拒绝。**测试密度是这个项目最硬的资产之一**。

---

## 四、主要问题（按严重度）

### P0-1 ｜ HTTP 面没有分层，88 条路由挤在一个文件

`gateway_routes.py` 4,828 行、273KB、88 条路由、75 个 def。即使 37% 是注释/docstring，仍有 **2,598 行代码**。后果：

- 任何路由改动都要在 4,828 行里定位；
- 路由与业务逻辑混住（很多 `try/except` 直接写在路由里）；
- 无法按域做权限/限流/审计的统一切面。

对照：`core/pa/` 其余 45 个模块合计 12,097 行——**一个文件占了整个 PA 后端的 28.5%**。

### P0-2 ｜ 异常处理与"fail-loud"文化自相矛盾

- `except Exception` **315 处**；
- 其中 **42 处**下一句就是 `pass`（静默吞掉）；
- 仅 135 处把错误变成可见返回。

典型例子（`agent_invoke.py` 一带就有 10 余处 `except Exception: return ""` / `return []` / `return {}`）。对主权系统而言，**"读不到"与"没有"必须可区分**——这正是项目自己在 `state_out` / `threads` / `caliber_store` 里坚持的纪律，却在别处大面积破例。

### P0-3 ｜ 授权只到"JWT 层"，PA 内部没有 owner/角色校验

现状是两层：

1. **全局闸**（`core/lib/security_middleware.py`）：环回放行；非环回强制 `Authorization: Bearer <JWT>`，并把 claims 的 user_id 注入 body；`/v9/sandbox/*` 仅环回。
2. **路由级环回闸**：仅 **8/88** 条（`update`、`whoami`、`providers/key` ×2、`sys/snapshot`、`sys/<panel>`、`sys/act`、`attach`）。

**残差风险**：一旦有人拿到一枚有效 JWT，下列高风险面没有任何 owner/角色判据——

- `POST /v9/pa/permission`（改权限档）
- `POST /v9/pa/proxy/approve`（批准破坏性端点）
- `POST /v9/pa/act`（本机动作直派）
- `POST /v9/pa/agent/invoke`（调起 agent）
- `POST /v9/pa/deliver/mail`（发信）
- `POST /v9/pa/vault/set`（改 vault 根）

且**没有一条"全量路由必须有 guard"的不变量测试**（现有测试只钉了 bind 与 provider key 两处）。在单机单人模型下这是"可接受"，在主权模型下这是"缺口"。

### P1-1 ｜ 决策档案在版本控制之外，代码可读性依赖仓外资料

代码里有 **414 处 `pm_<id>` 引用、96 个不同 id**（如 `pm_1858`、`pm_1802`）。这些决策文件在 `_pm/`（**2,288 个文件**），而 `_pm/` 被 `.gitignore:152` 忽略。

后果：clone 下来的人看到"承 pm_1858 §四.1"，**无从查证**；代码评审无法判断"这条约束当初为什么立"。这不是文档多少的问题，是**关键上下文不可携带**。

### P1-2 ｜ 前端出现 4,620 行的"自述"巨物

`web/pa/faces/selfdesc.js`：4,620 行 / 330KB，仅 5% 注释，**4,308 行是代码**。里面装着：

- 自述类问句规则表；
- 权限四层的口径文案；
- **一个递归下降的算式自查器**（`paSelfChkEval`，明确不用 eval）。

把"回答质量判定 + 算术核验"放在一个前端 face 里，意味着：换壳即丢、无法被后端复用、无法被 Python 测试直接覆盖。`tasks.js` 1,662 行、`more.js` 922 行也在同一量级。

### P1-3 ｜ 交付卫生：高频提交 + 长期未提交并存

- 全仓 417 次提交，**2026-09-29 以来 356 次**（约每天 12 次）；
- 但 `HEAD` 停在 **2026-10-09**，工作树仍有 **15 个已跟踪文件被改 + 330 个未跟踪**；
- `MEMORY.md` 的 retired 件到 **10-22**，说明 10-09 之后仍有产出未入库；
- **全仓 3,824 个 `.before_*` / 151.2MB** 备份（已 ignore，但严重干扰阅读与检索）；其中 `web/pa` 333 个 / 23.8MB；
- `env_notes` **560 份**（10 天、每 30 分钟），未见保留/清理策略。

### P2 ｜ 其他

- `data/v9/pa` 混合了状态、日志、快照、归档，无分层目录；
- 只有 6 处显式锁，文件型状态在多线程 Flask 下靠"原子写 + 单写者"约定；
- 版本号 `pyproject` 为 9.0.11，但历史文档里同时出现 v5 / v9 / 0.11.x，对外口径不唯一；
- 2026-09-29 我出的 `docs/design/v9_pa_frontend_refactor_design.md` 已被 `web/pa/faces/*` 的实际实现越过（模块名与边界都不同），该件应标记 superseded，否则又是一枚"会过期的靶"。

---

## 五、架构评估

### 5.1 实际分层（比文档更清楚）

```
web/pa.html（604 行骨架）
  └─ web/pa/core.js（238）＋ boot.js（59）＋ faces/*.js（27 面 · 13,859 行）
        └─ HTTP /v9/pa/*（88 条 · 全在 gateway_routes.py 4,828 行）
              └─ core/pa/*（45 模块 · 12,097 行：identity / profile / dialog / dispatch /
                    caliber / grants / endpoint_guard / receipts / env_face / sys_face / ...）
                    └─ data/v9/pa/*（文件型状态 · state_out 原子出口）
```

**好边界**：`PaCore` 仍是纯逻辑入口；面件按域切分（authz/caliber/session/tasks/today/sys/...）；`state_out` 是唯一状态出入口（9 处调用）。

**坏边界**：HTTP 层没有域切分；前端有两个"上帝模块"（`selfdesc`、`tasks`）；后端 `env_face` / `sys_face` 各近千行且宽捕密集（33 处 / 33 处）。

### 5.2 与 2026-09 的对比

| 项 | 2026-09-29 | 2026-10-26 |
|---|---|---|
| PA 后端模块 | 27 个 / 约 5.4k 行 | 46 个 / 16.9k 行 |
| 路由 | 43 条 | 88 条 |
| 前端 | 单文件 2,727 行 | 27 面 + core/boot，14.2k 行 |
| 身份 | user_id 即身份 | owner.json 铸一次 + 远端 403 |
| 绑定 | 0.0.0.0 | 127.0.0.1（显式才放宽） |
| 测试 | 少量 | 139 个 PA 测试文件 |

**结论：一个多月里，语义层完成了三次关键跃迁（身份、绑形、fail-closed），代价是体量翻了三倍而分层没有同步。**

---

## 六、建议（按投入产出排序）

### 6.1 立刻（1–2 天）

1. **清卫生**：全仓 `.before_*`（3,824 个 / 151.2MB，其中 `web/pa` 333 个 / 23.8MB）移出工作区；给 `env_notes` 加保留策略（如保留 7 天 / 最多 200 对）。
2. **落积压**：把 15 个已跟踪改动按主题分 3–5 次提交；330 个未跟踪里挑出真代码（`projects_face.py`、新测试）入库，`MEMORY.md.retired_*` 归入 `.gitignore`。
3. **修测试入口**：默认 `pytest` 的 `C:\Users\flybo\AppData\Local\Temp\pytest-of-flybo` 权限不可用（`WinError 5`），导致 `test_pa_core.py` 7 条全部 error；加 `--basetemp` 后 **7 passed**。这是环境问题，但会让所有人误判"测试坏了"。

### 6.2 近期（1–2 周）

4. **拆 `gateway_routes.py`**：按域拆成 `routes/pa/{identity,session,profile,dispatch,env,sys,deliver,feedback}`，每个 blueprint 只做 HTTP 适配；业务逻辑留在 `core/pa`。目标：单文件 ≤ 800 行。
5. **补一层授权**：在 blueprint 级统一 `_owner_required`（或 capability 声明），把 `permission` / `proxy/approve` / `act` / `agent/invoke` / `deliver/mail` / `vault/set` 纳入；**加一条不变量测试**：扫描所有写路由，断言每条都有 guard 标记。
6. **异常分级**：把 315 处 `except Exception` 分成"预期降级（可见返回）"与"缺陷（应上抛）"；42 处 `pass` 逐条改成可见（日志或返回 `degraded` 标记）。可先写一个 AST 扫描器，把 42 处列成清单逐条销账。

### 6.3 中期（1–2 月）

7. **决策入库**：从 `_pm/` 抽出被代码引用的 96 个 id，落到 `docs/decisions/pm-<id>.md`（一页一条：决定/理由/影响文件）；剩余 2,192 份不进库，但建索引。
8. **前端减重**：`selfdesc.js` 拆为 `selfdesc/rules.js`（规则表）+ `selfdesc/check.js`（算式核验）+ `selfdesc/answer.js`（拼答）；算式核验建议下沉到后端（可被 Python 测试直接覆盖）。
9. **数据分层**：`data/v9/pa/{state,log,snapshot,archive}` 四目录，迁移一次并留对照表。

---

## 七、验收指标（机器可判）

| # | 指标 | 当前 | 目标 |
|---|---|---:|---:|
| 1 | 单文件最大行数（后端） | 4,828 | ≤ 800 |
| 2 | `except Exception` 中 `pass` 占比 | 42/315 = 13% | ≤ 2% |
| 3 | 写路由有 guard 标记的比例 | 8/88（且仅环回） | 100% |
| 4 | 代码内 `pm_` 引用可解析率 | ≈ 0%（`_pm` 未入库） | ≥ 90% |
| 5 | 前端单文件最大行数 | 4,620 | ≤ 800 |
| 6 | 默认 `pytest` 可跑 | 否（tmp 权限） | 是 |
| 7 | 全量测试红数 | 42（10-06 台账） | 0 |
| 8 | 工作树未跟踪文件 | 330 | ≤ 20 |
| 9 | 备份/快照占用 | 151.2MB + 560 份 | 有保留策略 |

---

## 八、本件边界

- 本次**未跑全量测试**（默认 pytest tmp 不可用；只做了 `test_pa_core.py` 的冒烟与 `--collect-only`）。
- 未审 `core/pa` 之外的网关主体（`agent_gateway_enhanced.py`）与 `engine/`；PA 的安全结论以全局中间件 + PA 路由为界。
- 文中行号/计数为 2026-10-26 快照，**会漂**；结论以文件与模式为准。
- 未评价 `_pm/` 内的决策内容本身（只评价其"在仓外"这一事实）。

---

## 附录 A：关键证据索引

| 结论 | 证据 |
|---|---|
| 绑形默认环回 | `core/gateway/boot.py:16-40` |
| 全局 JWT 闸 | `core/lib/security_middleware.py:23-70` |
| 环回判据 | `core/pa/gateway_routes.py:384` |
| 环回仅 8 路由 | `gateway_routes.py:2325,2945,3254,3270,4693,4704,4724,4748` |
| 身份归一 | `core/pa/identity.py:1-25`；`gateway_routes.py:2945` |
| 权限 fail-closed | `core/pa/permission.py:1-55` |
| 状态原子出口 | `core/pa/state_out.py`；`write_state()` 9 处 |
| 自述巨物 | `web/pa/faces/selfdesc.js`（4,620 行 / 330,048 B） |
| 备份残骸 | `.gitignore:145`；`web/pa/**/.before_*` 333 个 / 23.8MB |
| 决策仓外 | `.gitignore:152`（`_pm/`）；`_pm/` 2,288 文件 |
| 测试基线 | `tests/baseline/failure_ledger.json`（记 42 failed / 2,393 passed · 2026-10-06） |
