# PA 成熟度审查（2026-11-01）

> 来源：Cursor Canvas「PA 成熟度审查」＋ 2026-11-01 本机抽样。
> 对照：docs/second_brain、docs/design，以及 D:\clawsjoy_v9 代码。
> 性质：迭代目标参考，不是验收通过证明，也不是自动度量。
> 版本抽样：pyproject.toml = 9.2.2。

## 总判

D:\clawsjoy_v9 现在是**能发、能停、能排队的本机 Agent 工作台原型**，还不是产品文档里的「老板数字幕僚长」。

执行车道（runs）相对最熟；产品壳、记忆入口、仓库卫生都不熟。  
整理应先收口**表面与发送链**，而不是继续加功能。

## 成熟度（0–10，人工对照）

| 维度 | 现状 | 目标 |
|---|---:|---:|
| 整体产品态 | 7 | 10 |
| 发送·停止·队列 | 3 | 8 |
| 前端产品壳 | 2 | 7 |
| 目标对齐 | 4 | 10 |
| 后端结构 | 5 | 8 |
| 前端结构 | 3 | 8 |
| 第二大脑 | 5 | 9 |
| 仓库卫生 | 2 | 7 |
| 文档一致 | 3 | 8 |
| 桌面壳 | 6 | 7 |

## 产品目标（仓内已定）

一句话：PA 是本地第二大脑——读笔记/文件、记得住、能动手但有门禁、做完给回执；**不是又一个 ChatGPT，也不是工程控制台**。

最小闭环：

装 → 选文件夹 → 模型就绪 → 5 分钟内带出处的结果 → 回执 → 第二天还回来

用户只关心五件事：做了没有、做到哪、能不能停、凭什么、能不能恢复。

明确不做：发币、先做 GEO、先做链上记账、用 CI 绿或「路由存在」冒充产品可用。

10-31 报告称 P0–P2 用户路径验收通过，实际覆盖的是：本地无 key 本地聊、/v9/agent/runs 受理、停止、刷新恢复、多席 API——不是「选目录 → 问本周笔记 → 出处 + 待办 + 写回」的 5 分钟首胜。

## 代码实际长什么样

| 层 | 现状 |
|---|---|
| 桌面壳 | Electron shell/：起本机服务、托盘、载荷/壳双更新 |
| 前端 | 无打包器。web/pa.html 串 30+ 个 faces/*.js，全局函数 + localStorage |
| 后端 | Flask。路由拆成 pa_routes_*，但 gateway_routes.py 仍是兼容大门 |
| 内核 | PaCore 仍是 2026-09 的 JSON 文件 MVP（画像/账本/事件） |
| 记忆 | 另有 notes.py + SQLite，再加 notebooks |
| 执行 | run_queue / RunService 与 harness/（DSH CLI）并列，聊天主路径历史上走 v9_chat |

版本叙事已分叉：pyproject 9.2.2、ClawsJoy_PA.md 9.0.36、10-31 验收 9.0.76。

## 为什么说「不成熟」

1. **目标对齐弱（约 4/10）**  
   验收过的是本地聊天/停止/队列，不是 5 分钟笔记首胜。07_下一步_5分钟首胜.md 要的杀手场景还没成为首页。

2. **前端是工程台，不是产品壳（约 3/10）**  
   - core.js 仍自称 v0.2，8 个模式（电影/3D/游戏等预留）。  
   - 新窗 window.js（约 1500 行）和旧 composer /「更多」抽屉并存。  
   - faces.json 停在 10-07，没登记 window / summon / brain / live。  
   - 顶栏堆本体检、载荷更新、壳更新、密钥、留言——运维面压过 Today。  
   - pa.html 里还有大段内联 first_run 脚本和工单注释。

3. **后端拆了文件，没拆职责（约 5/10）**  
   - pa_routes_common.py 约 800 行，重复 import。  
   - RunService 文件头写明：不接路由 / DSH / 聊天。  
   - 两车道设计 PA_ASYNC_TWO_LANE_v1.md 仍是 Draft。  
   - classify.py（笔记自动整理）和 classifier.py（L1–L4 出机分级）两套同名概念。  
   - 记忆至少四套：PaCore JSON、notes、notebooks、前端 localStorage 线程。

4. **发送链多路**  
   - 陪伴：/v9/pa/dialog。  
   - 办事：声称只走 /v9/agent/runs，send.js 仍留 /v9/agent/chat SSE；cards.js 仍调用该端。  
   - DSH 无本地 provider，只能 cloud DeepSeek；无 key 已 400——fail-closed 是对的，但「PA+DSH > 1」还没成立。  
   - 注：work/dev 主路已 return sendAgentViaRuns；旧 SSE 分支主要残留，不是主路径，但确实是多路。

5. **仓库卫生差（约 2/10）**  
   覆盖前 .before_<hash> 进源码树；还有 .tmp_pa_*_chrome、.tmp_payload_*.log。大量测试以工单号命名（1808、3433），像过程档案。

6. **文档互相打架**  
   18_产品路线 把 DSH 放 P2、先做 MCP；定义 v2 把 DSH 当运行时核心。21_笔记本 写 NotebookLM 骨架已做；00_产品核心 仍写导入/首跑/记忆弱。两边可能都局部真，但没有一份 Current 状态。

## 问题清单（整理优先级，不是 CVE）

| ID | 级 | 域 | 问题 |
|---|---|---|---|
| dual-ui | P0 | 前端 | 新旧窗双轨并存 |
| send-paths | P0 | 前后端 | 发送链仍多路 |
| first-win | P0 | 产品 | 5 分钟首胜未成为主路径 |
| memory-split | P1 | 后端 | 记忆四套，没有一个产品对象 |
| route-facade | P1 | 后端 | 路由拆了壳，公共件仍是单体 |
| hygiene | P1 | 仓库 | 侧车备份与临时产物进仓 |
| docs-drift | P1 | 文档 | 版本与路线互相打架 |
| comment-wall | P2 | 前端 | 注释与工单压过界面代码 |
| dsh-local | P2 | 执行 | DSH 不能当默认本地执行器 |

## 建议整理顺序（先收口，再加功能）

1. **卫生闸**：.before_*、.tmp_pa_*_chrome、payload 日志移出主树；冻结再写侧车进仓。（本机第 0 步已执行：移出 2,686 件到隔离区，补 .gitignore。）
2. **一张产品面**：新窗为唯一默认；旧 8 模式 DOM/boot 进回退旗，不再双 CSS 双发送。
3. **一条发送链**：产品只暴露 dialog（陪伴）+ agent/runs（办事）；删除 chat SSE 静默代码。
4. **把 RunService 接到办事主路径**；两车道从 Draft 变成「执行中仍可聊」的用户可见行为。
5. **记忆收口**：Today/Summon 只打 notes+notebooks；PaCore JSON 降为内部账，不跟用户抢入口。
6. **重做首跑**：选文件夹 → 一句示例问本周笔记 → 三条出处 + 待办，替换 first_run 工程墙。
7. **后端薄门**：gateway_routes 只做兼容别名；pa_routes_common 去掉重复 import，按簇切开公共件。
8. **文档单源**：一份 Current.md 写版本/默认模型/已验路径/明确未做；旧 reports 标归档。

## 不要在整理时做的事

- 不要加 GEO/链上。产品核心已列为非目标；84–89 号报告会把注意力拉开。
- 不要先上框架重写。先删双轨、收发送、收记忆；React/打包器可等唯一窗稳定之后。
- 不要拆掉 runs 契约。10-31 已验的 queued/cancel/restore 是目前最值钱的一块，整理应围着它收口，而不是另起聊天。

## 相对扎实、不要拆的资产

- grants 读面/授权面、owner_guard、本机密钥
- /v9/agent/runs 的 queued / cancel / restore 契约
- 本地优先与 fail-closed 语义

## 本机落地记录（2026-11-01）

- 卫生第 0 步：主树 .before_* / .tmp_* / 临时 Chrome profile 移出 2,686 件到
  D:\clawsjoy_v9_quarantine\20261101-124433；未删使用者文件。
- 单一现状源：docs/Current.md（版本 9.2.2、默认 Ollama、localm 可选、DSH 独立 key）。
- 下一步 gate：一张产品面 + 一条发送链；先不动 runs 契约。

## 判断依据

docs/second_brain/00、07、18、20、21、ClawsJoy_PA.md；  
docs/design 定义 v2 / 技术栈 / 两车道 / DSH_CLOUD_ONLY；  
docs/reports/PA_ACCEPTANCE_P0_P2_20261031.md；  
core/pa/*、web/pa.html、web/pa/faces/*、shell/package.json。
