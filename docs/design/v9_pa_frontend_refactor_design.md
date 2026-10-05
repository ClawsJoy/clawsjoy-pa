# V9 PA 前端重构设计 — 模块划分 · 路由契约 · 迁移顺序

- 日期: 2026-09-29
- 状态: 设计文档(先出方案, 待评审后实施; 落地前不改任何产品代码)
- 范围: `web/pa.html`(现 **2,727 行 / 186KB 单文件**) → `web/static/pa/*.js` 模块化 + `pa-api` 统一请求层 + `pa-store` 单一状态真源
- 上位: `docs/design/v9_frontend_modular_split_design.md`(workbench 拆分, 已落地 `web/static/js/` 10 个模块)
- 口径: 本文**不复述后端字段级取值**(本仓 S1 单一真源); 字段真源 = `core/pa/gateway_routes.py`(其 `/v9/pa/*` 路由 43 条)

---

## 一、现状盘点

### 1.1 已有基础(无需新建)

- **模块化先例已存在**: workbench 已按 7 步拆出 `web/static/js/` 10 个 IIFE 模块, 约定为
  `<script defer src="/web/static/js/x.js">` + `(function(global){ ...; global.fn = fn })(window);`;
  依赖 `window.DSH_API`(api-client.js) 与 `window.__APP_STATE`。
- **统一请求层已存在但未接 PA**: `web/dashboard/api-client.js`(265 行) 已实现
  `{ok, data, error:{code,message}}` 统一返回、鉴权头预留(`Authorization/X-Session-Id/X-User-Id`)、baseURL 双模式; **`pa.html` 未引用**。
- **状态可见化契约已存在**: `PA_STATE_DEF`(10 键: idle/running/model/tool/approval/verifying/done/failed/stopped/blocked) + 阈值 30s/90s + 终态不计时; 是判据真源。
- **卡片统一出口已存在**: `PA_CARD_DEF` → `paRenderCard` → 固定容器 `#paCards`(**不写 `#thread`**, 批221 事故结论)。
- **前端已有真浏览器复检**: `tools/pa_frontend_readiness.py`(Playwright, 非脚本注入; `window.paSetState` 观察器记录状态迁移)。
- **已有前端判据测试**: `tests/pes/test_m2a_frontend_outlet.py`(函数层 node 跑真源码 + 静态层读源码 + 边界层)、`tests/integration/test_frontend_protocol.py`(前后端 status 覆盖比对)。

### 1.2 缺口

| 缺口 | 现状(可核) | 影响 |
|---|---|---|
| 单文件无边界 | `web/pa.html` 2,727 行, 内联 CSS+JS, 153 个顶层函数 | 任何改动都是全局风险; 评审只能整文件读 |
| 无统一请求层 | `pa.html` 24 处裸 `fetch`, `user_id` 拼接与错误处理各自为政 | 错误被吞/超时无感; 后端三态语义无法统一消费 |
| 状态多源互相同步 | `state`(内存 L422) + `localStorage['pa_state']`(saveState L589) + `window.__APP_STATE`(syncPaSession L746) + 服务端 `data/v9/pa/threads_<uid>.json`; 另有 `pa_cfg`/`pa_panels` 两键 | 刷新丢状态; 谁权威不明确; `syncThreads` 已退化为 no-op |
| **已建未接线** | 43 条 `/v9/pa/*` 中 **21 条已接, 22 条未接**(见 §4.4) | 主权面(授权/口径/审核/分派)在后端已建, 界面上**看不到、够不着** |
| 卡片不持久化 | `#paCardsHint` 明示"刷新后清空" | **待批写操作刷新即消失**; 与"授权必须可恢复"相冲 |
| 权限双源 | 模式提示 `#modePerm` 与配置 Tab `cfgPerm` 各写一份 | 显示值与实际档位可能不一致(静默类风险) |
| 判据锚点硬定位 | 测试以 `PA_CARD_DEF` 起、`paWriteDecide(` 止抽取卡片区 | 拆分会碰测试, 必须同步改抽取方式而非改判据 |

### 1.3 量化基线(落地后回归用)

| 指标 | 当前 |
|---|---|
| `web/pa.html` 行数 / 字节 | 2,727 行 / 186,058 B |
| 顶层函数 | 153 |
| 裸 `fetch` 调用点 | 24(19 个 PA 端点 + 5 个跨域外部端点) |
| 已接 PA 路由 / 未接 | 21 / 22 |
| 前端模块文件 | 0(PA 页) |

---

## 二、目标与非目标

### 2.1 目标

1. **边界**: `pa.html` 只留骨架(HTML + 少量内联初始化), 逻辑全部进 `web/static/pa/*.js`;
2. **契约**: 所有网络调用经 `pa-api`, 错误码/超时/三态统一处理, **不吞**;
3. **真源**: 一个 `paStore` 管状态, localStorage 只有一个落盘出口;
4. **可验证**: 每一步都能用 `pa_frontend_readiness.py` + 既有 pes/integration 测试复检;
5. **可延续**: 模块约定与 `web/static/js/` 完全一致(同一加载方式、同一 window 挂载纪律), 不引入构建链。

### 2.2 非目标(明确不做)

- **不引入 React/Vue/打包器**: 本项目 local-first、单机 Flask 静态托管、离线可跑; 引入 Node 构建链会与部署链冲突。
- **不改后端路由与字段**: 本件只动前端; 后端缺的接口另开件。
- **不改判据本身**: 现有测试的判据(白名单/未知字段上报/无时间调用/统一出口)**一字不改**, 只同步"抽取锚点"。
- **不做视觉改版**: 设计 token(`:root` 变量)与卡片语义保持不变; 新增面板沿用同一套 token。

---

## 三、模块划分

### 3.1 目录与加载

```
web/pa.html                       # 骨架: 布局 + <script defer> 清单 + 内联初始化(仅 __PA_BOOT 步骤表)
web/static/pa/
  pa-api.js         # 统一请求层(PA 域): base/user_id/session/超时/错误码/SSE 复用
  pa-store.js       # 单一状态真源: state + paRun(10 态) + 订阅 + 唯一落盘出口
  pa-shell.js       # 顶栏/抽屉/折叠/Tab/引导(_boot)
  pa-state-view.js  # PA_STATE_DEF + paSetState/paBeat/paRenderState/setBusy(观察锚点)
  pa-archive.js     # 归档迁移/配额/导出/清理(含 W-08/W-09 判据区)
  pa-files.js       # 左栏项目文件 + 本地客户端启动/probeConn
  pa-kb.js          # 知识库↔沙箱映射面板
  pa-ppt.js         # 产物卡/PPT 缩略图墙/批注
  pa-side.js        # 右栏: 画像/待办/配置/建档
  pa-timeline.js    # 计划 + 时间轴 + 拍板点
  pa-chat.js        # 会话流 + MD 渲染 + SSE + 发送/停止
  pa-cards.js       # 统一卡片出口(判据区, 最后拆)
web/static/css/pa.css             # 从 pa.html <style> 原样抽出(先只搬不改)
```

加载顺序(全部 `defer`, 模块只定义不执行; 初始化由 `pa.html` 末尾的内联 `__PA_BOOT` 逐项调用, 保持 `_boot` fail-loud 语义):

```html
<script defer src="/web/static/pa/pa-api.js"></script>
<script defer src="/web/static/pa/pa-store.js"></script>
<script defer src="/web/static/pa/pa-state-view.js"></script>
<script defer src="/web/static/pa/pa-shell.js"></script>
<script defer src="/web/static/pa/pa-archive.js"></script>
<script defer src="/web/static/pa/pa-files.js"></script>
<script defer src="/web/static/pa/pa-kb.js"></script>
<script defer src="/web/static/pa/pa-ppt.js"></script>
<script defer src="/web/static/pa/pa-side.js"></script>
<script defer src="/web/static/pa/pa-timeline.js"></script>
<script defer src="/web/static/pa/pa-chat.js"></script>
<script defer src="/web/static/pa/pa-cards.js"></script>
```

### 3.2 映射表(现区 → 目标模块)

| 目标模块 | 现 `pa.html` 行区(函数) | 主要函数 | 主要依赖 | window 导出 |
|---|---|---|---|---|
| `pa-api.js` | 新增 | `paGet/paPost/paSSE/paErrText` | 无(仅 `fetch`) | `window.PA_API` |
| `pa-store.js` | 新增 + L422 状态区 + L589 `saveState` | `getState/setState/subscribe/persist` | `PA_API`(仅迁移函数用) | `window.PA_STORE` |
| `pa-state-view.js` | L1824-1895 | `PA_STATE_DEF/PA_TERMINAL/paSetState/paBeat/paRenderState/setBusy` | `PA_STORE` | `paSetState/paRenderState` |
| `pa-shell.js` | L2471-2661 | `switchTab/paPanels/paApplyPanels/paSetPanel/togglePanel/toggleTop/toggleDrawer/closeDrawers` | `PA_STORE`(panels) | 全部(内联 onclick) |
| `pa-archive.js` | L443-688 | `paArchive*/paQuota*/paMigrateArchiveToServer/paExportArchive/paArchiveCleanup/paParseStateTolerant` | `PA_API/PA_STORE` | `paExportArchive/paArchiveCleanup` |
| `pa-files.js` | L1897-1948 + L2516-2546 | `probeConn/paStartLocalClient/renderFileSource/loadFiles` | `PA_API` | `loadFiles/paStartLocalClient` |
| `pa-kb.js` | L896-1046 | `paKb*(24 个)/renderKbPanel` | `PA_API` | `paKbCopy/paKbRequestMirror` |
| `pa-ppt.js` | L1510-1775 | `detectOutputs/renderOutputCard/downloadOutput/pptComments*/renderPptWall/loadPptWall/buildPptThumb/uploadDeckThumbs/exportDeckThumbs/paMcp` | `PA_API` | `downloadOutput/exportDeckThumbs/togglePptCommentForm` |
| `pa-side.js` | L2483-2632 | `loadSide/renderSide/doneTodo/toggleTodoView/loadDoneTodos/loadCfg/saveCfg/loadFieldsForm/renderFieldsForm/collectValues/saveFields/setCollectMsg` | `PA_API/PA_STORE` | `doneTodo/toggleTodoView/saveFields/loadSide` |
| `pa-timeline.js` | L1210-1509 | `stageOf/semantic*/bucketOf/planOf/boardNode/fmtElapsed/finalizeNode/nodeEvidenceLine/startPlan/renderTimeline/tickPlan/onTaskDone/openBoard/paDecide*/confirmDecision/sendReviseToPA/startPlanTimer/stopPlanTimer` | `PA_API/PA_STORE` | `openBoard/paDecide/paDecideConfirm/paDecideCancel` |
| `pa-chat.js` | L740-1210 + L1948-2050 + L1792-1874 | `curUser/curSession/syncPaSession/esc/paMd*/addMsg/addLog/paRunLog/receipt/_ensureLogToggle/paSend/sendPA/sendAgent/readSSE/paAskGate/recordPaTurn/paLooksLikeKnowledgeQuestion` | `PA_API/PA_STORE` | 内联 onclick 入口(send/clearChat 等) |
| `pa-cards.js` | L2188-2436(**判据区**) | `PA_CARD_DEF/paCardFilter/paSyncCardsHint/paDismissCard/paRenderCard/paLoadPesBlocks/renderPaWriteCard/paWriteDecide/paStop` | `PA_API/PA_STORE` | `paDismissCard/paWriteDecide/paStop` |

> 注: 行区为**当前**位置(2026-09-29), 仅作迁移定位用; 落地时以函数名为准(行号会漂)。

### 3.3 window 契约(内联 onclick 兼容)

内联 `onclick` 决定了哪些函数必须挂在 `window`。**规则: 模块内导出最小集, 其余保持模块私有**; `pa.html` 中每一处内联 `onclick` 对应一条 window 挂载, 由 §8 静态判据核对(不允许"模块有函数但 onclick 找不到")。

### 3.4 模块依赖规则(硬约束)

1. `pa-api` / `pa-store` **不依赖任何业务模块**(被依赖方);
2. 业务模块之间**不得横向调用**, 需要共享的通过 `PA_STORE` 或事件订阅;
3. 业务模块**不得直接写 `localStorage`**(唯一出口 = `pa-store.persist()`, 对应现有 `saveState()` 的失败上报纪律);
4. 业务模块**不得直接 `fetch`**(唯一出口 = `pa-api`);
5. 卡片渲染**只能经 `paRenderCard` 进 `#paCards`**, 不写 `#thread`(沿用批221 结论)。

---

## 四、路由契约

### 4.1 分层(按主权语义, 不按路径字母序)

| 层 | 含义 | 端点 |
|---|---|---|
| **L0 只读投影** | 读不改变任何一侧; 空 = 不适用而非接线坏 | `context` `profile(GET)` `ledger(GET)` `dialog(GET)` `threads(GET)` `dispatch/history` `decision/log` `permission(GET)` `caliber(GET)` `proxy/gate` `kb_mapping` `archive/<id>` `roster*` |
| **L1 写面** | 落账/落痕, 均须可回溯 | `profile(POST)` `sediment` `dialog(POST)` `turn` `ledger/add` `ledger/done` `decision` `plan` `ppt/comments(POST)` `artifact/thumbs` `permission(POST)` `caliber/change` `vault/sync` `archive(POST)` `roster/upsert` |
| **L2 执行与门** | 会碰外部/本机/权限, **必须过门** | `dispatch` `act` `proxy` `proxy/approve` `ask` `audit/preflight` `audit/postcheck` `local_client/start` `caliber/check` |
| (停用) | 单线程口径, 明确拒绝 | `threads(POST)` → 返回 `ok:false` + 说明, **前端不得再调** |

### 4.2 统一消费契约(前端侧)

```js
// pa-api.js 对外语义(不是后端字段的复述, 只定前端如何消费)
{
  ok:    true|false,     // 后端 ok 字段; 缺失/非 200 ⇒ false
  data:  object|null,    // 原样透传, 前端不得据非白名单字段造状态
  err:   { code, message, http } | null
}
```

三条**不许**(对应现有事故类型):

1. **不吞**: L0 空结果要显式说"没有/不适用", 不得渲染空卡冒充成功; 后端 404/409 要**原样可见**;
2. **不造**: 前端不得自造倒计时/撤销窗口/状态(判据已禁 `Date.now()/setInterval` 于卡片区);
3. **不复述**: 字段清单不在前端硬编码(画像表单已走 `profile/schema`, 是正确先例; `collectValues` 不得反向写死字段名)。

### 4.3 调用矩阵(模块 → 路由)

| 模块 | L0 读 | L1 写 | L2 执行/门 | 状态 |
|---|---|---|---|---|
| `pa-chat` | `dialog` `context` | `dialog` `turn` | `ask` `agent/chat`* | 已接 |
| `pa-timeline` | — | `plan` `decision` | — | 已接 |
| `pa-cards` | `pes/runs`* | — | `cancel/<id>`* | 部分(卡片不持久) |
| `pa-side` | `context` `ledger` `permission` `profile/schema` | `ledger/done` `profile` `permission` | — | 已接 |
| `pa-kb` | `kb_mapping` | — | — | 已接 |
| `pa-ppt` | `ppt/comments` | `ppt/comments` `artifact/thumbs` | `proxy` | 已接 |
| `pa-files` | `local_client/status` `sandbox/list`* | — | `local_client/start` | 已接 |
| `pa-archive` | — | `archive` | — | 已接 |
| **新增 授权面板** | `proxy/gate` `permission` | `permission` | `proxy/approve` | **待接** |
| **新增 口径面板** | `caliber` | `caliber/change` | `caliber/check` | **待接** |
| **新增 审核证据** | `dispatch/history` `decision/log` | — | `audit/preflight` `audit/postcheck` | **待接** |
| **新增 分派/编队** | `roster` `roster/find` | `roster/upsert` | `dispatch` `act` | **待接** |

`*` = 非 `/v9/pa/*` 的跨域依赖(`/v9/agent/chat` `/v9/sandbox/{read,list}` `/v9/pes/runs` `/v9/cancel/<id>`), 同层封装但**不属 PA 契约**, 单独标注以免混淆归属。

### 4.4 已建未接线清单(22 条, 即"够不着的能力")

| # | 路由 | 层 | 建议落点 |
|---|---|---|---|
| 1 | `GET /v9/pa/profile` | L0 | pa-side(与 context 去重: 二选一为真源) |
| 2 | `POST /v9/pa/sediment` | L1 | pa-side(手动沉淀入口) |
| 3 | `GET /v9/pa/dialog` | L0 | pa-chat(刷新后从服务端恢复会话, 替代纯 localStorage) |
| 4 | `POST /v9/pa/threads` | 停用 | **不接**(保持拒绝) |
| 5 | `POST /v9/pa/ledger/add` | L1 | pa-side(**当前 UI 无法新增待办**) |
| 6 | `POST /v9/pa/dispatch` | L2 | 分派面板 |
| 7-10 | `GET /v9/pa/roster` `/roster/find` `/roster/<id>` `POST /roster/upsert` | L0/L1 | 编队面板 |
| 11 | `GET /v9/pa/proxy/gate` | L0 | **授权面板** |
| 12 | `POST /v9/pa/proxy/approve` | L2 | **授权面板** |
| 13 | `GET /v9/pa/caliber` | L0 | **口径面板** |
| 14 | `POST /v9/pa/caliber/change` | L1 | **口径面板**(必填 id/status/owner/why) |
| 15 | `POST /v9/pa/caliber/check` | L2 | 产物渲染前预检 |
| 16 | `POST /v9/pa/audit/preflight` | L2 | **审核证据** |
| 17 | `POST /v9/pa/audit/postcheck` | L2 | **审核证据** |
| 18 | `POST /v9/pa/act` | L2 | 本地动作直派 |
| 19 | `GET /v9/pa/dispatch/history` | L0 | **审核证据** |
| 20 | `POST /v9/pa/vault/sync` | L1 | pa-side(Obsidian 同步按钮) |
| 21 | `GET /v9/pa/decision/log` | L0 | **审核证据**(拍板留痕) |
| 22 | `GET /v9/pa/archive/<id>` | L0 | pa-archive(按 id 取正文, 与 POST 配对) |

---

## 五、状态与真源

### 5.1 现状四源

```
state(内存) ─────────────────┐
localStorage['pa_state'] ────┤  saveState() / syncPaSession() 互相同步
window.__APP_STATE ──────────┤  syncThreads() 已 no-op(批189·#3)
服务端 threads_<uid>.json ───┘  (POST /v9/pa/archive)
```

### 5.2 目标: 一源一出口

| 数据 | 权威 | 本地角色 | 落盘出口 |
|---|---|---|---|
| 会话线程索引/activeThread | **服务端**(archive / dialog GET) | 缓存 | `pa-store.persist()` |
| 会话正文 | **服务端**(`/v9/pa/turn` `dialog GET`) | 缓存 | 同上 |
| 模式/面板折叠/配置 | 本地 | 权威 | `persist()`(键沿用 `pa_state`/`pa_panels`/`pa_cfg`) |
| 运行状态(10 态) | **后端事件驱动** | 派生(不落盘) | — |
| 卡片(待批/待核验) | **服务端投影**(run_id 可查) | 派生 | — |

**纪律**(沿用现有注释的教训): 唯一落盘出口 = `pa-store.persist()`, 且失败必须上报; 归档区**不得**出现 `.splice(/.pop(/.shift(/removeItem(`(现有 W-08 判据, 迁移时逐字保留)。

### 5.3 卡片持久化(独立成步, 不混在拆分里)

现状"卡片不持久化"对**授权**是缺陷: 待批写操作刷新即消失, 而后端 pending 可能仍在。
目标: 卡片改为**服务端投影 + 本地只存 dismissed 集合**; 刷新后按 run_id 重新拉取。此改动须单独出件(涉及后端是否有稳定查询点), 本文只登记为阶段 B 的第 3 步。

---

## 六、迁移顺序

### 阶段 A: 纯拆分(行为零变化, 每步可复检)

| 步 | 模块 | 理由(自洽度优先) | 验证点 |
|---|---|---|---|
| 0 | `pa-api.js` + `pa-store.js` + `pa.css`(**先造尺, 不接线**) | api/store 是被依赖方; 先立约束再搬件 | 新文件加载无 console 错; `pa_frontend_readiness.py` 仍全绿 |
| 1 | `pa-shell.js` | 纯 DOM + 本地状态, 无网络 | Tab/抽屉/折叠往返; `pa_panels` 持久化不变 |
| 2 | `pa-state-view.js` | **观察锚点**, 必须保持 `window.paSetState` | readiness 脚本状态迁移记录条数不变 |
| 3 | `pa-archive.js` | 迁移/配额已有判据区(W-08/W-09) | W-08/W-09 + X-11 迁移判据全绿 |
| 4 | `pa-files.js` | 依赖 api, 无跨模块 | 文件列表/连接探测/启动按钮 |
| 5 | `pa-kb.js` | 25 个函数自成一体 | kb 面板三态(已镜像/过期/缺失)渲染 |
| 6 | `pa-ppt.js` | 产物/批注自成一体 | 缩略图墙 + 批注读写 |
| 7 | `pa-side.js` | 画像/待办/配置/建档 | 表单由 `profile/schema` 驱动, 保存/驳回可见 |
| 8 | `pa-timeline.js` | 计划与拍板 | 时间轴节点/拍板五选项/回执 |
| 9 | `pa-chat.js` | 核心会话流 | 发送/流式/停止/知识问答门 |
| 10 | `pa-cards.js` | **判据区, 最后拆** | `test_m2a_frontend_outlet` 三层全绿(同步改抽取锚点) |
| 11 | `pa.html` 收口 | 只留骨架 + `__PA_BOOT` 步骤表 | 全部 `_boot` 步骤仍 fail-loud; 无内联业务函数 |

**每步的固定动作**(对齐 workbench 拆分法): 抽函数出内联 → 建模块文件 + window 挂载 → 删除内联副本(防重复定义覆盖) → 浏览器刷新验证该模块功能 + 全站无 console 错 → `python tools/pa_frontend_readiness.py` 截图留档 → 提交。

### 阶段 B: 主权面板接线(拆分完成后, 独立分批)

| 步 | 内容 | 依据路由 | 说明 |
|---|---|---|---|
| B1 | **授权面板**(右栏新 Tab) | `proxy/gate` `proxy/approve` `permission` | 列出当前长期授权(scene/路径/TTL/授予时间/撤销) + 端点门状态; 权限档**单一真源**(消 `modePerm` 与 `cfgPerm` 双源) |
| B2 | **口径面板** | `caliber` `caliber/change` `caliber/check` | 变更单必填 id/status/owner/why; 先渲染"改前值"再提交 |
| B3 | **卡片持久化** | `pes/runs` + 后端待批查询点 | 刷新不丢待批/待核验 |
| B4 | **审核证据** | `audit/preflight` `audit/postcheck` `dispatch/history` `decision/log` | 一个"这次任务碰了什么"的可导出回执 |
| B5 | **分派/编队** | `roster*` `dispatch` `act` | 按能力找人 → 派活 → 审核 |
| B6 | 会话服务端恢复 | `dialog(GET)` `archive/<id>` | 替代纯 localStorage 正文缓存 |

---

## 七、风险与兼容

| 风险 | 具体点 | 缓解 |
|---|---|---|
| 判据锚点错位 | `test_m2a_frontend_outlet` 以 `PA_CARD_DEF` → `paWriteDecide(` 抽取; 拆分后字符串落在不同文件 | 第 10 步**只改测试的读取路径**(改为读 `web/static/pa/pa-cards.js`), 判据内容一字不改 |
| 静态抽取区间漂移 | 现注释明确警告"复述区块边界原文会把抽取起点提前导致判据变红" | `pa-archive.js` 迁移时**整段搬运**, 不整理注释 |
| 内联 onclick 失效 | 模块内导出遗漏 | §8 判据: 扫描 `pa.html` 内联 `onclick="fn(` 与模块 `global.fn` 求差集 |
| defer 顺序 | 模块先于内联执行, 模块只定义不 init | 初始化统一放 `pa.html` 末尾 `__PA_BOOT`, 保持现 `_boot` 逐项 fail-loud |
| 双源状态更隐蔽 | store 与 localStorage 各写一半 | §3.4 硬约束 3 + §8 判据(业务模块内 `localStorage` 出现次数 = 0) |
| 范围蔓延 | 拆着拆着改功能 | 阶段 A **行为零变化**; 功能全部推入阶段 B 分批 |
| 单文件体积假降 | CSS 未抽或模块仍互相引用 | §8 判据: `pa.html` 行数上限与模块数下限 |

---

## 八、验收(机器判据, 可复算)

| # | 判据 | 检查方式 |
|---|---|---|
| 1 | `pa.html` 无业务函数(仅骨架 + `__PA_BOOT`) | 静态扫描 `pa.html` 内 `function ` 数 ≤ 引导所需 |
| 2 | 无裸 `fetch` | 业务模块内 `fetch(` 出现次数 = 0; 仅 `pa-api.js` 允许 |
| 3 | 无裸 `localStorage` | 业务模块内 = 0; 仅 `pa-store.js` 允许 |
| 4 | 内联 onclick 全覆盖 | `pa.html` 内联函数名集合 ⊆ 各模块 `global.*` 导出并集 |
| 5 | 卡片唯一出口 | `pa-cards.js` 内无 `#thread` 写入; 卡片只进 `#paCards` |
| 6 | 卡片区无时间调用 | 沿用现有判据(`Date.now(/new Date(/setInterval(/getTime(` 为 0) |
| 7 | 状态契约不变 | `PA_STATE_DEF` 键集合 = 迁移前(10 键), 只增不改 |
| 8 | 前端状态覆盖后端 | `test_frontend_protocol` 类型比对仍绿 |
| 9 | 真浏览器可达 | `tools/pa_frontend_readiness.py` 全绿 + 状态迁移条数 ≥ 迁移前 |
| 10 | 归档/配额判据 | W-08/W-09/X-11 判据逐条绿 |

---

## 九、本件边界

- 本文只出**方案**(模块划分/路由契约/迁移顺序), **不落地**; 阶段 A 第 0 步之前不碰产品代码。
- 本文不复述后端字段级取值与数值(端口/阈值/字段表), 真源分别见 `core/pa/gateway_routes.py`、`core/lib/port_config.py`、`web/pa.html` 的 `PA_STATE_DEF`。
- 行区与函数计数为 2026-09-29 实测快照, **行号会漂**; 落地以函数名为锚。
- 阶段 B 的 B3(卡片持久化)可能需要后端新增稳定查询点, 是否成立由后端件裁定, 本文只登记依赖。

---

## 附录 A: 模块 → 路由(机读, 供复算器逐行对账)

```
# 模块                     路由(层)                                                                    状态
pa-chat                   /v9/pa/dialog(L0/L1) /v9/pa/context(L0) /v9/pa/turn(L1) /v9/pa/ask(L2)      已接
pa-timeline               /v9/pa/plan(L1) /v9/pa/decision(L1)                                         已接
pa-cards                  /v9/pes/runs(*) /v9/cancel/<id>(*)                                         部分
pa-side                   /v9/pa/context(L0) /v9/pa/ledger(L0) /v9/pa/permission(L0/L1) /v9/pa/profile/schema(L0) /v9/pa/profile(L1) /v9/pa/ledger/done(L1)   已接
pa-kb                     /v9/pa/kb_mapping(L0)                                                       已接
pa-ppt                    /v9/pa/ppt/comments(L0/L1) /v9/pa/artifact/thumbs(L1) /v9/pa/proxy(L2)       已接
pa-files                  /v9/pa/local_client/status(L0) /v9/pa/local_client/start(L2) /v9/sandbox/list(*)   已接
pa-archive                /v9/pa/archive(L1)                                                          已接
[待接]授权面板             /v9/pa/proxy/gate(L0) /v9/pa/proxy/approve(L2) /v9/pa/permission(L0/L1)     待接
[待接]口径面板             /v9/pa/caliber(L0) /v9/pa/caliber/change(L1) /v9/pa/caliber/check(L2)        待接
[待接]审核证据             /v9/pa/audit/preflight(L2) /v9/pa/audit/postcheck(L2) /v9/pa/dispatch/history(L0) /v9/pa/decision/log(L0)   待接
[待接]分派编队             /v9/pa/roster(L0) /v9/pa/roster/find(L0) /v9/pa/roster/<id>(L0) /v9/pa/roster/upsert(L1) /v9/pa/dispatch(L2) /v9/pa/act(L2)   待接
[待接]会话恢复             /v9/pa/dialog(L0) /v9/pa/archive/<id>(L0)                                   待接
[停用]                    /v9/pa/threads(POST)                                                         不接
```
