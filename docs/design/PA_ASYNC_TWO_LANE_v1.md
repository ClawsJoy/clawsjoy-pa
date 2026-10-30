# PA 异步两车道设计 v1（对话不阻塞 / 执行排队）

| 项 | 值 |
|---|---|
| 文档 | docs/design/PA_ASYNC_TWO_LANE_v1.md |
| 状态 | Draft（待评审；本件只设计，不实现） |
| 日期 | 2026-10-31 |
| Owner | PA / DSH |
| 关联 | task-144；turn_registry、run_id、/v9/agent/chat、/v9/cancel、HarnessPort v1 |
| 目标读者 | PA 后端、前端、DSH 适配层实现者 |

## 0 摘要

现状：PA 一次执行占用一个长 HTTP/SSE 回合；执行中用户再发消息会被 entry._single_run_guard
判 busy 并直接返回（entry.py 455-505），前端 agentRunning 为真时 agentSend 直接 return
（web/static/js/chat.js:151）；停止按钮只置取消标志并关 turn_registry，若工具/模型在飞，
用户看到「停无效」或长时间无终态。

本设计把 PA 会话拆成两条车道：

1. 对话 lane（D）：不排队、不占执行 WIP；负责即时聊天、解释、改写、确认与转交执行。
2. 执行 lane（E）：单主（全进程 WIP=1）FIFO 队列；负责长任务、工具、Harness；可排队、可取消。

验收口径：执行中对话框仍可输入并得到回答；执行提交永远受理并立即返回 run_id（忙则为 queued +
position）；停止在队列态立即终态、在运行态在检查点内收敛为 cancelled；所有终态可查询、可追溯。

## 1 现状与问题（一手锚点）

| 锚点 | 现状 | 问题 |
|---|---|---|
| core/gateway/v9_chat/entry.py::_single_run_guard（455-505） | 检测到心跳未超时的 RUNNING/DETACHED turn 即返回 status=busy | 第二条消息被硬拒，无法对话 |
| core/gateway/turn_registry.py | 持久 7 态 CREATED/RUNNING/DETACHED/COMPLETED/FAILED/CANCELLED/STALE，心跳 + stale 扫描 | 只有回合生命周期，无队列/待执行概念 |
| routes/v9_chat.py | /v9/agent/chat 同步调 run_chat_entry，stream 走 SSE | 请求与执行同寿，长任务占住 HTTP |
| routes/session.py::v9_cancel_session（47-68） | request_cancel + 立即 finish_turn(CANCELLED) | 关 turn 快，但执行线程仍可能在工具中；无队列取消 |
| web/static/js/chat.js::agentSend（138-172） | agentRunning 为真直接 return；停止靠 AbortController + /v9/cancel | 输入被全局禁用；停止只中断流，不保证执行终态 |
| core/pa/harness/port.py | HarnessPort v1：probe/run/resume/cancel/stream/permissions/cost/audit/team；RunRecord 含 run_id/status/cost/artifacts | PA 尚无队列承接 Harness 执行 |

结论：不是加一个线程就能解决，必须有明确两车道 + 单主队列 + 可查询终态。

## 2 范围

### 2.1 本设计覆盖

- 运行状态机（含失败、取消、重启、stale）。
- 对话 lane 与执行 lane 的职责、所有权、并发边界。
- 单主 FIFO 队列、持久化、幂等、背压。
- 取消/停止 API 与终态语义（含 turn_registry 关闭时机）。
- HTTP/SSE/轮询 API 契约、UI 契约、DSH HarnessPort 边界。
- 失败态与验收测试矩阵（供实现直接照做）。

### 2.2 非目标（v1 明确不做）

- 不做多进程/多机分布式队列；PA 单进程内单 worker。
- 不做多 session 并行执行；对话 lane 可并发，执行 lane 仍 WIP=1。
- 不做硬杀进程/回滚外部副作用；取消是协作式，工具在飞时允许完成当前工具。
- 不改 HarnessPort v1 接口，不把 DSH SDK/进程模型引入 PA core。
- 不实现多租户鉴权；沿用 PA 现有本机约束。

## 3 术语与所有权

| 术语 | 定义 |
|---|---|
| Lane D（对话） | 即时对话请求；不占执行队列、不持有执行锁、不调用写工具 |
| Lane E（执行） | 长任务；全局单 worker 顺序消费；可排队、可取消 |
| run_id | PA 一次执行尝试的不可变标识（建议 uuid4 hex；与 turn_key 一对一） |
| run record | 六态运行记录（queued/running/done/failed/cancelled；idle 为车道空闲哨兵） |
| turn | turn_registry 的持久回合记录（内部 7 态，生命周期与心跳） |
| queue entry | 尚未被 worker 取走的执行请求；含 position/client_request_id |
| 单主 | 全进程同时最多一个 running run；不是每 session 一个 |

所有权铁律：

1. 执行状态唯一写者 = execution worker；API 只投递命令（submit/cancel）与读快照。
2. 对话 lane 只追加 dialog 事件，不改 run record、不改队列、不发 cancel。
3. 队列所有者 = PA 进程内的 QueueManager；HarnessPort 只执行单个 run，不管理队列。
4. UI 不拥有状态；UI 只渲染 API 返回的 state，禁止以本地 agentRunning 猜测。

## 4 状态机

### 4.1 车道级与 run 级

- 车道级 idle：队列空且无 running；这是 UI 默认显示，不是某条 run 的状态。
- run 级六态：queued → running → done/failed/cancelled；queued 可直接 cancelled；running 可被取消。
- 每提交一次执行产生一个 run_id；idle 时提交直接 running，忙时 queued。

#### 4.1.1 六态定义

| 状态 | 含义 | 是否终态 | 可查询字段 |
|---|---|---|---|
| idle | 车道空闲：无 running 且队列空（UI 默认态，非 run record） | — | queue_depth=0 |
| queued | 已受理、尚未被 worker 取走 | 否 | position、queue_depth、created_at |
| running | worker 正在执行；可能同时 cancel_requested=true | 否 | progress、tool_steps、cancel_requested |
| done | 执行成功并验收完成 | 是 | output、artifacts、cost |
| failed | 异常/超时/重启/取消无法收敛 | 是 | error、code、partial output |
| cancelled | 用户取消（队列立即或运行检查点收敛） | 是 | cancel_requested、cancelled_at、reason |

补充：idle 由车道/UI 合成，不写入 run record；run record 一经创建只会在
queued/running/done/failed/cancelled 之间转移。

示意（run 级）：

    [accepted]
        |
        +--> queued --(worker 取头)--> running --(ok)------> done
        |                               |
        |                               +--(异常/超时)----> failed
        |                               |
        |                               +--(cancel 收敛)--> cancelled
        +--> cancelled  (queued 时取消，立即终态)

### 4.2 转移表

| 当前 | 触发 | 下一态 | 副作用/条件 |
|---|---|---|---|
| idle | submit（worker 空闲） | running | 建 run_id/turn；发 start 事件；占执行锁 |
| idle | submit（有 running/queued） | queued | 入队尾；position=队列长度；返回 202 |
| queued | worker 取头 | running | 出队；position 清 0；turn 置 RUNNING |
| queued | cancel | cancelled | 立即出队；无 turn；发 cancelled 事件 |
| queued | 停机/清理 | cancelled | 持久化标 cancelled，reason=shutdown |
| running | harness 成功 + 验收 | done | 收尾、turn COMPLETED、释放执行锁、唤醒 worker |
| running | harness 失败/异常/超时 | failed | 保留 error；turn FAILED；释放锁 |
| running | cancel 受理 | running（cancel_requested=true） | 置标志、关 turn_registry 为 CANCELLED、必要时 port.cancel；worker 检查点退出 |
| running+cancel_requested | worker 收敛 | cancelled | 终态；turn 已是 CANCELLED；释放锁 |
| 任意终态 | 再次 cancel/查询 | 同态 | 幂等，禁止重开；重试必须新 run_id |
| running | 进程重启/心跳超时 | failed（reason=process_restart/stale） | 启动扫描；队列中 queued 仍保留 |

强制不变量：

- 同一时刻 running 数只能是 0 或 1。
- 终态不可逆；重试是新 run_id，禁止复用旧 run_id。
- 每个 run 必须有且只有一个终态事件（done/failed/cancelled）。
- queued 不出现在 turn_registry 的 active 集合；running 才建 turn。
- cancel 不应导致两个执行重叠：旧 worker 退出前，QueueManager 禁止取下一个。

### 4.3 与 turn_registry 的映射

| run 六态 | turn_registry 7 态 | 说明 |
|---|---|---|
| queued | 无（不建） | 队列自有记录，避免 active 守卫误判 busy |
| running | CREATED/RUNNING | worker 取头时建；心跳照旧 |
| running+cancel_requested | CANCELLED（立即关） | 停心跳、active 守卫立即可见终态；worker 仍持有执行锁直到退出 |
| done | COMPLETED | 正常收尾 |
| failed | FAILED | 异常/超时/进程重启 |
| cancelled | CANCELLED | 队列取消或运行取消收敛 |
| （无） | DETACHED/STALE | 既有客户端断开/重启语义保留；启动扫描将 stale run 标 failed |

说明：cancel 时先关 turn_registry（承 routes/session.py:57-64 的修），但执行锁不立即释放；
这样用户立刻看到非 RUNNING，又不会因关 turn 就放行下一发造成并发执行。

## 5 两条车道

### 5.1 Lane D：对话 lane

职责：

- 用户任意消息的即时回应（闲聊/解释/改写/确认/把任务转交执行）。
- 可读最近对话与 exec 进度快照（只读），回答现在在做什么/排队第几。
- 可由用户一句话转交执行：返回已准备执行卡片，由 UI 显式点执行（禁止自动二次提交）。

边界：

- 禁止调用写工具/执行任务/改 run 状态；只允许只读上下文与轻量检索（可选，v1 可先不做工具）。
- 禁止占用全局执行锁；禁止入执行队列。
- 本地 model 优先（无 key 可用本地 Ollama）；失败显式报错，不静默降级。
- 超时预算：首 token 10s、整轮 60s（可配）；超时给明确错误，不影响执行 lane。

并发：

- dialog 线程池上限 2（每会话最多 1 个在飞，避免自己抢自己）；对话请求之间无全局锁。
- 对话事件写 session log，lane=dialog；不触碰 PA run record。

### 5.2 Lane E：执行 lane

职责：

- 消费单主 FIFO 队列；构建 RunSpec，调用 HarnessPort（DSH/Mock/API）执行。
- 维护六态 run record、turn_registry、进度事件、终态、错误。
- 响应 cancel 请求（协作式检查点）。

边界：

- 全进程单 worker；禁止双开第二个 worker（除非显式运维开关）。
- 禁止直接服务用户对话；对话由 Lane D 负责。
- 不抢占 dialog 的用户输入；执行期间 dialog 消息可插话，但执行在自己的事件流里继续。
- 工具在飞时取消不保证中断当前工具；见第 7 节。

### 5.3 共享会话与事件顺序

统一事件日志（复用 session_log 或新增 run_events 表；推荐后者 + UI 合并）：

| 字段 | 类型 | 说明 |
|---|---|---|
| seq | int | 会话内单调递增；跨 lane 唯一排序键 |
| session_id | str | 会话 |
| run_id | str/null | 执行事件必填；对话事件 null |
| lane | dialog/execution/system | 车道 |
| type | str | message/delta/progress/tool/state/done/error |
| data | object | 载荷（见 API） |
| ts | ISO8601 | 本地时区 |

规则：

- 每个 lane 只写自己的事件类型；UI 按 seq 合并渲染，禁止按到达时间重排。
- 执行输出作为 assistant 消息落历史；run_id 附在元数据，前端可折叠运行详情。
- 对话插话不进入执行 messages；执行上下文在 run 启动时快照，运行中不被对话框污染。
- 同一 session 的历史写入仍走 session_log 单写入出口；若无法复用，新增事件表由 QueueManager 串行写。

## 6 单主队列

### 6.1 数据结构

    queue = deque[QueueEntry]
    QueueEntry {
      run_id: str,
      session_id: str,
      user_id: str,
      client_request_id: str,   # 幂等键
      task: str,
      model: str,
      permission_level: str,
      enqueued_at: ISO,
      position: int,             # 1-based 派生值
      state: "queued"
    }

- 全进程一个 FIFO；多 session 同一队列，先到先执行（v1 不做优先级/公平调度）。
- 每 session 最多 3 个 queued；全局最多 20；超限返回 429，错误明示，禁止静默丢弃。
- worker 取头前确认执行锁空闲；取头后 position 不再对外（running 的 position=0/null）。

### 6.2 执行锁与 worker

- 单独 threading.Lock 表示执行锁，禁止用 turn_registry 的 active 作为唯一锁（取消时要先关 turn）。
- 单 worker 线程循环：wait 队列/停止信号 → 取 entry → 建 run/turn → 执行 → 终态 → notify。
- 终态后 release 执行锁并 notifyAll；排队请求的 position 重新计算。
- 进程退出：worker 收到 shutdown 信号，queued 标 cancelled（reason=shutdown）并持久化；running 等收尾或标 failed。

### 6.3 持久化与重启

- 持久化文件：data/v9/pa/async_queue.json（原子写：tmp + os.replace；含 schema_version）。
- 每次 enqueue/dequeue/cancel 落盘；running 记录在单独 run record 文件中（或 SQLite）。
- 启动恢复：
  - queued 原样恢复（保留 enqueued_at/顺序），worker 重新开始；
  - 旧 running 一律标 failed（error=process_restart），对应 turn_registry 标 FAILED/STALE；
  - 禁止自动重跑旧任务（避免重复副作用）；用户可显式 retry（新 run_id）。
- 多进程/多实例：v1 不支持；检测到同一 data 根第二个写者时拒绝启动队列（fail-loud）。

### 6.4 幂等

- client_request_id 由前端生成（uuid4），同一 key 重复提交返回原 run_id 与当前 state，禁止重复入队。
- 进程重启后幂等索引从持久化文件恢复；已终态的同 key 仍返回原终态。
- run_id 由服务端生成；未来可支持客户端指定但必须校验唯一性。

## 7 停止/取消语义

### 7.1 两态入口

| 提交时状态 | cancel 行为 | 返回 | 终态收敛 |
|---|---|---|---|
| queued | 立即从队列摘除 | 200，state=cancelled | 同请求内完成 |
| running | 置 cancel_requested，发协作取消 | 200，state=running，cancelling=true | 下个检查点（毫秒级）；工具在飞则等当前工具结束 |
| done/failed/cancelled | 幂等 | 200，原 state | 不变 |

### 7.2 运行中取消的步骤

1. API 校验 run 存在、属于该 session/user，置 cancel_requested=true（持久化）。
2. 立即关闭该 run 的 turn_registry 为 CANCELLED（停心跳，active 守卫不再见 RUNNING）。
3. 调 HarnessPort.cancel(run_id)（若 adapter 支持）；调用失败只记日志，仍走协作检查。
4. worker 在检查点检测：每轮 LLM 调用前、每次工具调用前、工具返回后、SSE 发送前。
5. 收敛：worker 完成当前不可中断动作后落 cancelled 终态，发 cancelled 事件，释放执行锁。
6. QueueManager 只有在 worker 释放锁后才取下一个；禁止因 turn 已关就提前开下一个。

### 7.3 真实停止的验收口径

- 停止按钮和 API 必须使 queued 立即终态；running 在一个检查点内进入 cancelled。
- 当前工具在飞时，UI 必须显示「停止中（当前工具完成后停止）」；禁止假装已停。
- 若超过 stop_grace_s（默认 30s）未收敛：run 标 failed（error=cancel_stuck），执行锁仍由 worker 持有；
  QueueManager 进入 paused 健康态（队列不取新），UI 显式告警；禁止直接开下一个造成并发。
- 终态后 UI 才清 agentRunning；心跳停止、turn_registry 终态、队列 position 重排同时可见。
- 外部副作用不回滚（发消息/写文件/点网页）；取消只保证 PA 停止继续动作，不保证撤销已发生动作。

### 7.4 与现有停止路径的兼容

- 保留 POST /v9/cancel/<session_id>：语义 = 取消该 session 的当前 active run（或排队头），
  并关闭该 session 所有非终态 turn；返回实际取消的 run_id 列表。
- 新 UI 优先用 run_id 精确取消，避免误停同 session 的另一个 run（v1 每 session 只保证一个执行，
  但队列允许多个，取消要精确到 run_id）。

## 8 API 契约

通用：

- JSON UTF-8；本机调用；沿用 PA 现有本机/owner 边界；禁止 token。
- 所有时间 ISO8601；错误统一 {ok:false,error,code,detail?,run_id?}。
- 受理执行类请求一律先持久化再返回；返回后进程崩溃仍可恢复。

### 8.1 对话 lane

    POST /v9/agent/dialog
    body: {user_id, session_id, messages:[{role,content}], model?, stream?, client_msg_id?}
    200 application/json 或 text/event-stream
    JSON: {ok:true, message_id, text, model, lane:"dialog"}
    SSE : event: dialog_delta  data: {"text":"..."}
          event: dialog_done   data: {"message_id":...,"model":...}
    Error: 400 参数; 503 dialog_model_unavailable; 504 dialog_timeout

- 该端点永不被执行队列阻塞；执行中仍可调用。
- 对话不产生 run_id；只写 lane=dialog 事件。
- stream 断开不影响执行 lane。

### 8.2 执行提交

    POST /v9/agent/runs
    body: {user_id, session_id, client_request_id, task,
           messages?, model?, permission_level?, cwd?, timeout?}
    202 Accepted
    {ok:true, run_id, state:"running"|"queued", position:0|N,
     queue_depth, created_at, client_request_id}

- 永不以 busy/409 拒绝；忙时 queued + position。
- 参数校验失败 400；队列超限 429 queue_full；同 client_request_id 返回 200/202 同 run 幂等。
- 提交后 run_id 必可立即查询；running 表示已被 worker 占有。

### 8.3 进度查询

    GET /v9/agent/runs/{run_id}?after_seq=N
    200
    {ok:true, run_id, state, cancel_requested,
     position, progress:{done,total,percent,phase,last_tool},
     tool_steps:[...], output:"", error:null,
     events:[{seq,type,data,ts}], next_after_seq, updated_at}

- 轮询间隔 500ms（可退避 500/1000/2000ms）；after_seq 用于增量，禁止重复传全量。
- state=queued 时带 position；running 时 position=0/null。
- 未知 run 404 unknown_run；跨 session 查询 403（若启用 owner 校验）。
- events 保留最近 N=200 条 + 完整 history 落盘；超出用 next_after_seq 分页。

### 8.4 取消

    POST /v9/agent/runs/{run_id}/cancel
    200 {ok:true, run_id, state:"cancelled"|"running",
         cancel_requested:true, stop:"immediate"|"cooperative"}

- queued：立即 cancelled，position 重排。
- running：cancel_requested=true；最终由查询得到 cancelled。
- 终态幂等；未知 404；禁止通过取消接口删除历史。

### 8.5 队列列表

    GET /v9/agent/runs?session_id=...&state=queued|running|done|failed|cancelled&limit=50
    200 {ok:true, runs:[{run_id,state,position,session_id,created_at,updated_at}], queue_depth}

用于刷新页面后恢复排队/运行状态。

### 8.6 兼容端点

| 旧 | 新行为 | 迁移 |
|---|---|---|
| POST /v9/agent/chat | 默认转发 Lane D（对话）；body lane="execute" 时转发 POST /v9/agent/runs 并返回其 202 | 旧执行客户端改传 lane=execute；一版后移除兼容 |
| POST /v9/cancel/<session_id> | 取消该 session 的 active run（和排队头） | 保留；新 UI 用 run_id 精确取消 |
| GET /v9/task/status | 投影为最新 run 的 state/progress（兼容旧前端） | 保留只读；新 UI 用 runs 查询 |
| GET /v9/task/save_progress | 保留只写 .agent_state 的旧行为 | 不由新队列调用 |

## 9 UI 契约

### 9.1 布局

- 顶部固定状态条：空闲 / 排队第 N / 执行中 / 停止中；右侧显示 run 摘要。
- 对话区：用户与 dialog 消息即时显示；执行输出以执行卡片展示（进度、工具步骤、折叠详情）。
- 输入区：文本框始终 enabled；发送按钮始终可用（空文本除外）。

### 9.2 交互

| 用户动作 | 前端行为 |
|---|---|
| 输入框回车 | 调 POST /v9/agent/dialog；执行中同样可用；不设置全局 agentRunning 禁用输入 |
| 点执行 | 用当前文本调 POST /v9/agent/runs；立即插入 queued/running 卡片；输入框继续可用 |
| 执行中继续聊天 | 正常 dialog；回答可引用快照（当前执行到…） |
| 点停止 | 调 run cancel；按钮变停止中并禁用重复点击；禁止立即清卡片为 idle |
| 刷新页面 | 从 localStorage 取 last_run_id + GET /v9/agent/runs；恢复状态条/卡片/排队位置 |
| 排队中取消 | 调 cancel；卡片立即 cancelled；位置重排 |
| 执行失败 | 卡片显示 error 与 code；提供重试（新 run_id）；禁止自动重试 |

### 9.3 状态渲染规则

- queued：显示排队第 N；禁止显示转圈为执行中；可取消。
- running + cancel_requested=false：执行中 + 停止按钮。
- running + cancel_requested=true：停止中；说明当前工具可能完成；保持卡片直到终态。
- done/failed/cancelled：终态；停止按钮消失；失败/取消原因可见。
- dialog 请求失败：气泡红字 + 原因；不影响执行卡片。
- 输入不禁用；只有执行按钮在空文本时禁用。禁止用 agentRunning 阻止 agentSend。

### 9.4 轮询/连接

- 执行进度用轮询（500ms，退避至 2s）；v1 不依赖执行 SSE（Flask 线程模型简单可靠）。
- 对话框可用 SSE；断线重连只影响该对话请求。
- 页面隐藏时降频（2s）；恢复可见立即拉一次。
- 所有 API 失败按 code 显示人话；网络失败保留重试按钮，禁止伪造完成。

## 10 与 DSH HarnessPort 的边界

### 10.1 分工

| 层 | 负责 | 不负责 |
|---|---|---|
| PA QueueManager/Lane E | run_id、队列、六态、cancel 标志、事件、UI API | 不实现 harness 内部执行 |
| HarnessPort v1（core/pa/harness/port.py） | 单个 run 的 probe/run/resume/cancel/stream/permissions/cost/audit/team | 不管理 PA 队列、不决定 UI 状态 |
| DSH adapter（core/pa/harness/dsh.py） | 调 DSH/Codex 进程/SDK，归一 RunRecord 与 stream 事件 | 不向 PA 暴露 DSH session 格式；不反向 import PA 路由 |
| Mock adapter | 无 DSH 时测试/降级 | 不冒充真实能力 |

### 10.2 字段映射

- RunSpec：task/cwd/tools/permission_level/timeout/model/resume_id 直接来自 QueueEntry（缺省空）。
- RunRecord：PA 落自己的 run record 时保留 port 返回的 run_id 到 harness_meta.external_run_id；
  cost/artifacts/receipt_sha16 原样入 PA 账；harness_meta 是唯一容纳 harness 私有字段处。
- 状态：port ok→done；failed→failed；cancelled→cancelled；超时/异常→failed（保留 error）。
- stream：port 事件类型 start/log/stdout/stderr/artifact/done/error 映射到 API events type；
  UI 不依赖 DSH 原始格式。
- cancel：PA cancel → port.cancel(harness run_id)；port 不支持或失败则记日志，仍按检查点收敛。

### 10.3 不可用/隔离

- 提交/启动前 probe；harness_unavailable 则该 run failed（code=harness_unavailable），队列继续。
  禁止让 run 无限 queued 假装在跑。
- PA core 禁止 import dsh/paseo；只经 HarnessPort；无 WSL 依赖；DSH 进程崩溃只影响当前 run。
- DSH 侧若实现自己的排队/并发，PA 侧仍强制 WIP=1（PA 的队列是唯一入口）；DSH 内部队列只能作为执行细节，不得绕过 PA run 状态。
- 账本：RunRecord 落 PA RunLedger/证据账；取消/失败也落终态，禁止只记成功。

## 11 失败态与边界情况

| 场景 | 状态/HTTP | 行为 | UI |
|---|---|---|---|
| 执行中提交第二个任务 | 202 queued | 入队、position | 显示排队第 N；输入仍可聊天 |
| 队列满 | 429 queue_full | 拒绝入队，返回上限 | 显示队列已满，稍后重试 |
| 重复 client_request_id | 200/202 同 run | 幂等 | 同一卡片，不重复提交 |
| dialog 模型不可用/超时 | 503/504 | 显式错误；execution 不受影响 | 红字原因，可重试 |
| harness 不可用 | run failed | code=harness_unavailable；队列继续 | 失败卡片 + 重试 |
| harness 崩溃/异常 | failed | 保留 error/status；释放锁 | 失败原因；不自动重跑 |
| 取消时工具在飞 | running+cancel_requested | 等当前工具完成 → cancelled | 停止中提示；禁止假停止 |
| 取消超过 grace 未收敛 | failed code=cancel_stuck | 执行锁仍占用；队列 paused | 告警；禁止开新执行 |
| 进程重启（queued） | queued 恢复 | 重新排队 | 刷新后继续显示排队 |
| 进程重启（running） | failed process_restart | turn FAILED/STALE；不自动重跑 | 失败卡片；可重试新 run |
| SSE/轮询断线 | 不变 | 可重连查询 | 保留状态；不误判失败 |
| 未知/越权 run_id | 404/403 | 不泄露详情 | 明确提示 |
| 队列持久化写失败 | 500 queue_persist_failed | 拒绝受理（fail-loud） | 可重试；禁止假装已受理 |
| 同一 data 根第二个进程 | 启动失败 | 队列 fail-loud | 运维显式处理 |

## 12 实现拆分与验收矩阵（供直接排期）

建议新增（实现阶段，本设计不写码）：

| 模块/件 | 职责 |
|---|---|
| core/gateway/async_queue.py | QueueEntry、FIFO、position、持久化、幂等、limit |
| core/gateway/run_state.py | 六态 run record、事件 seq、终态守卫、启动恢复 |
| core/gateway/v9_chat/dialog_lane.py | Lane D：模型调用、事件、并发限 |
| core/gateway/v9_chat/execution_lane.py | Lane E：worker、HarnessPort、检查点、cancel |
| routes/agent_async.py | 第 8 节 API（dialog/runs/query/cancel/list） |
| web/static/js/async_lane.js | 状态条、执行卡片、轮询、停止、刷新恢复 |
| 测试 | 见下表 |

验收矩阵（实现完成时必须全绿）：

| # | 用例 | 断言 |
|---|---|---|
| A1 | 执行中发 dialog | 200 且有回答；run 仍 running；无 busy |
| A2 | 空闲提交执行 | 202；state=running；run_id 可查 |
| A3 | 运行中提交执行 | 202；state=queued；position=1；无 409 |
| A4 | 两个排队 | FIFO；worker 只跑一个；第二个取头后 position 重排 |
| A5 | queued 取消 | 200 cancelled；队列移除；不建 turn |
| A6 | running 取消 | 200；turn_registry 立即 CANCELLED；检查点后 cancelled；不并发开下一个 |
| A7 | 停止中刷新 | 恢复 running+cancel_requested；终态后卡片 cancelled |
| A8 | 进程重启 | queued 恢复；旧 running→failed process_restart；禁止自动重跑 |
| A9 | 重复提交 | 同 run_id；只一条队列记录 |
| A10 | 队列满 | 429 queue_full；已有 run 不受影响 |
| A11 | harness probe 失败 | run failed harness_unavailable；队列继续 |
| A12 | 对话模型失败 | 503/504；execution 状态不变 |
| A13 | 轮询增量 | after_seq 不重复、不乱序；seq 单调 |
| A14 | 取消终态幂等 | 二次 cancel 仍 cancelled；无新事件重复 |
| A15 | 旧兼容 | /v9/agent/chat lane=dialog 正常；lane=execute 得 202；/v9/cancel 可停当前 run |

## 13 待评审决策

1. 队列持久化用 JSON 还是 SQLite（建议 JSON v1，量小、可读；上量后迁 SQLite）。
2. 队列是否允许同 session 多个 queued（建议最多 3，执行仍全局单主）。
3. 执行进度用轮询还是也为执行提供 SSE（建议 v1 轮询，后续可加 SSE）。
4. 停止 grace 默认 30s 是否合适（应大于最长小工具、小于用户耐心；工具超时可更长）。
5. 是否需要 v2 硬杀/进程隔离（v1 不做；cancel_stuck 显式告警）。
6. 旧 /v9/agent/chat 的兼容窗口（建议一版；lane=execute 过渡）。

## 14 附录：现有一手锚点

- core/gateway/v9_chat/entry.py::_single_run_guard（455-505）——并发 busy 当前实现。
- core/gateway/turn_registry.py——7 态、心跳、STALE、active_turns。
- routes/session.py::v9_cancel_session（47-68）——cancel + 立即 finish_turn。
- routes/v9_chat.py——/v9/agent/chat 薄路由。
- routes/task.py——/v9/task/status 现有投影。
- web/static/js/chat.js::agentSend/agentStop（138 起）——前端阻塞与停止现状。
- core/pa/harness/port.py——HarnessPort v1 方法/RunSpec/RunRecord/stream 事件。
- core/gateway/run_id.py——run_id 定义与事件链出口。

（完）
