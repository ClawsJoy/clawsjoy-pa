---
type: design
tags: [Computer Use, Agent, a11y, VLM, 学习循环, SOP, 设计]
created: 2026-09-04
status: draft-待确认
---

# V9 Computer Use Agent 正式设计（网页先行；a11y 枚举 + 语义选择 + DOM 执行 + 学习循环 + SOP）

> 依据 POC 已验证事实：① a11y 枚举+LLM 选序号 100%（14/14）；② 纯文本 qwen2.5:7b 即可语义匹配（不需要 VLM）；③ 输入框标签必须稳定语义（占位文本不得当名字）；④ 执行用 DOM 选择器坐标零误差。范围：网页（本地软件后续）；浏览器后端：browser_local（agent_client 真用户 profile，登录态平台）优先 + playwright_browser（headless，通用页）兜底。

## 1. 工具定义

### 1.1 browser_enumerate（只读，枚举层）

入参：url?（可选先导航）/ scope=viewport|page / roles?=[button,input,link,select,textarea,...] / max_items?（默认 40）/ iframe_shadow?（默认 false）

输出 items[]，每项：
- id：稳定序号（LLM 只回这个）
- role：button/link/input/select/textarea/checkbox/...（可交互性来源）
- label：稳定语义名（§2.1 标签策略产物；不进占位文本内容）
- sel：可执行 CSS 选择器（id > data-testid/data-cy/name > 父链 nth ≤5）
- bbox：{center:{x,y},w,h}（引擎侧；仅展示/视觉兜底画框，绝不进 LLM 提示词）
- tag + label_source（aria/label/placeholder/描述）

枚举规则：候选集 button、a[href]、input(text/search/tel/email/url/number)、textarea、select、[role=button/link/searchbox/textbox/combobox]、contenteditable；剔除不可见/不可交互/过小；去重；同源 iframe 与 open shadow root 递归（默认关）；超上限按可视面积截断并提示过滤。

### 1.2 browser_act（write 类，执行层）

入参：action=click|fill|press|select_option|hover|type|screenshot；id|index（来自最新 enumerate）；value?；verify?

执行管线：解析 id→sel → 重新定位（locator 唯一性校验；失配/多匹配自动 re-enumerate 一次）→ wait_for visible(≤5s) → 动作（fill 先 clear 再 type，输入后回读 value）→ verify 断言（url_contains / text_visible / field_value / element_state）→ 返回 {success, evidence:{url,title,head} }。失败存截图+原因，不静默。

### 1.3 browser_observe（只读，循环验证）

入参：check=url_contains|text_visible|element_exists|field_value；目标值 → 返回 bool + 证据头。供多步流程中每步后校验与完成判定用（避免整页重读）。

### 1.4 工具边界（对齐 V9 守卫）
- enumerate/observe = read 类（沿用现有豁免规则）；act(click/fill/type/press/select) = write 类：登录态平台白名单内直接执行；未白名单页按现审批；高风险（提交/发布/删除/付费）前置 ask 老板
- EscapeGuard/递归守卫：browser_hybrid 以 url+action 参与递归标识；同页 enumerate 带快照 hash 缓存防重复烧 token
- 超时：enumerate ≤10s、act ≤15s/动作、总工具超时沿用 320s 配置

## 2. 语义匹配层（选择器大脑）

### 2.1 标签质量策略（POC 失败根因根治）

优先级：① aria-label / aria-labelledby；② 关联 label(for=/包裹)；③ title/alt；④ button/a：innerText 截 40；⑤ input/textarea/select：placeholder 仅当静态描述性；⑥ 否则 role 稳定描述（input→文本输入框/搜索框按 type+name 前缀；textarea→多行输入框；纯图标→相邻文本提示）。

占位内容化检测：含人名/机构/数字或 >24 字符或滚动轮换 → placeholder_content=true，主标签降级为稳定描述，原文只进 debug 字段。

### 2.2 选择方式（两种模式，默认 A）

模式 A（Agent 内联，零额外延迟）：Agent 在自身上下文读清单文本 → 直接给 browser_act 传 id。引擎只做值域与 role 校验。

模式 B（关键动作双检）：browser_act 前，网关用本地 qwen2.5:7b（POC 已证纯文本足够）对同一 (intent, 打乱顺序的清单) 独立选一次；两次一致才执行；冲突 → 返回候选对比让 Agent 裁决，仍歧义 → vision 回退。

### 2.3 Prompt 模板（正式固化）

[system] 你是网页自动化元素选择器。给定任务意图与网页可交互元素清单（序号|类型|稳定名称），选出唯一目标元素。规则：只输出 1 个整数，不得解释；依据=类型(role)+稳定名称，占位文本只是示例内容、不作依据；找不到输出 0。

[user] 意图：{intent}
清单：
{items_text：每行 N|role|label}
目标元素序号：

解析：严格整数；0=找不到 → 返回 Agent 并附相近候选（枚举层文本相似 top3）供人工/换意图；越界或非整数 → 附错重试 1 次。

### 2.4 role 校验 + vision 回退
- 校验表：click→button/link/checkbox/radio/menuitem；fill→textbox/combobox/input/textarea/contenteditable；select→listbox/select；press Enter→button/form。不满足拒绝重选。
- 回退：无稳定名称或双检冲突 → 截图 + 把 id 画到 bbox（编号 overlay）→ qwen2.5vl 看图选号；仍歧义 → ask 老板。
- 遥测：每选择记录 准确/错选/找不到/双检拦截，按周聚合决定模型与策略。

## 3. 执行层要点

- 点击路径只用 DOM 选择器；bbox 仅用于：展示、vision overlay 画框、显式坐标兜底（默认关，canvas/拖拽且用户允许才用并打 audit 标记）
- SPA 漂移：act 前重新定位 + 失配自动 re-enumerate 一次
- 输入安全：fill 先 clear；type 后回读 value 校验；敏感输入不写日志
- 完成证据：verify 断言真值 + 截图留痕（对齐 R13/R15 无证据不得报完成）

## 4. 学习循环（Agent 级编排，防假完成/防烧 token）

### 4.1 单任务状态机
开目标 → 分解子目标（每子目标含可验证完成条件）→ [enumerate → 选(§2) → act → observe 验证]×n → 子目标全验 → 完成/失败上报。

### 4.2 完成判定
- 完成条件必须来自目标推导并在任务开头显式列出（含失败判据），例如「提交后 URL 含 success 且页含『已提交』」；
- 硬断言（observe 真值）优先；无硬断言→用户确认；无证据地宣称完成 = 假完成（沿用 R13/R15 守卫语义，学习循环不豁免）。

### 4.3 操作序列记录（每次成功与失败都记）
data/computer_use/plans/{task_id}.jsonl，每条：{step,intent,id,sel,role,label,action,value,verify_result,evidence,url}；失败另记失败类别：选择错/执行错/风控/选择器失效/超时/歧义。

### 4.4 失败重试上限（防无限循环）
- 单步重试 ≤2：先 re-enumerate + 换策略（双检 / vision / 同义意图改写）；
- 任务级：连续 3 步失败或失败步累计 >3 → 停止并输出失败报告（已尝试/失败分类/建议下一步），不静默重试。

### 4.5 学会判定与 SOP 生成
- 同一页面流程成功 ≥2 次（第 1 次跑通、第 2 次稳定）→ 触发 SOP 生成器：从 plan log 提炼（URL 前置 → 步骤序列：意图 + 选择锚点(role+label 语义 + sel 建议) + 动作 + 验证点 + 失败提示）；
- SOP 只存可复用操作骨架，不存登录态/密钥/敏感内容；
- 同一流程中途失败但已能复现步骤 → 生成「半成品 SOP」+ 失败已知，人工补全后转正。

### 4.6 SOP 写入与复用（Obsidian）
- 写入：vault 新目录 ComputerUseSOPs/（与现有 SOPs/ 平台规范分开，避免 update_sop 镜像冲突；可全局 search）；用 obsidian_knowledge write_note（folder=ComputerUseSOPs）或新增 update_cu_sop action（实施时二选一）；
- 复用：新任务按 URL/意图前缀命中 SOP → 注入步骤作为执行草案（目标=照做+逐点校验）；若执行与 SOP 不符 → 更新 SOP 或提示人工介入；
- 失败模式沉淀：新失败类别 → append_pitfall 记入避坑清单（防再犯，已有通道）。

## 5. SOP 格式（正式模板）

---
type: cu-sop
target_url: https://...
task: 一句话任务
verified: 2026-09-04
success_runs: 2
steps: 3
tags: [ComputerUse, SOP]
---
# CU-SOP：{任务名}

## 前置
- 入口 URL：...；触发意图：包含「...」
- 登录态：需要/不需要；风控提示：...

## 步骤
1. 意图：在搜索框输入关键词
   锚点：role=input(textbox) + label=搜索/搜索框（sel 建议 #kw / #chat-textarea）
   动作：fill {query}；验证：输入回读 == {query}
2. 意图：提交搜索
   锚点：role=button + label=百度一下/搜索（sel #su / #chat-submit-button）
   动作：click；验证：url 含 wd={query}
3. ...

## 失败已知
- 占位文本滚动新闻式 → 用稳定描述重选（勿选新闻链接）
- 滑块验证码 → 人工或切真实 profile

变量用 {花括号} 占位；选择锚点 = 语义(role+label) + sel 建议双键，sel 失效自动降级为语义重选。

## 6. 分阶段实施计划

P1 基础库（纯函数可单测）：a11y_dom.py — 枚举/label 策略/占位内容化检测/选择器生成；HTML fixture 单测（25 元素样例、占位伪装案例、iframe/shadow、图标按钮）。验收：标签策略矩阵全过。

P2 工具接线（playwright 后端）：browser_enumerate / browser_act / browser_observe + strict schema + 守卫接入 + 路由；集成测试：真开百度 enumerate 命中 #chat-textarea 且 label 稳定、#chat-submit-button；act fill/click 触发正确请求。

P3 语义选择：§2.2 模式 A/B + §2.3 模板 + role 校验 + 双检（本地 qwen2.5:7b，mock 单测逻辑）+ vision overlay 回退（qwen2.5vl）；agent_system.md 引导；10 意图×2 模型实测（目标 ≥95%）。

P4 学习循环 + SOP：plan log（§4.3）、完成判定/重试上限（§4.2/4.4）、SOP 生成器（§4.5）→ write_note 写 vault ComputerUseSOPs/；命中复用（§4.6）；失败类别入避坑清单。

P5 E2E 验收 + 试点切换：选一条真实浏览器任务（建议 zhihu/xhs 草稿填写或 B 站上传某一步）用新链路完整跑通 2 次 → 生成首条 CU-SOP；遥测首周；治理记录（v9_architecture_governance_v2.md 追加实施轮）；live 同步 + 重启。

验收指标：网页元素枚举 ≥20/页；选择准确率 ≥95%（10 意图×2 模型）；任务执行成功率（不含风控）≥90%；0 次坐标点击（除显式兜底）；SOP 生成→复用成功率有首周数据；失败分类有分布报告。

## 7. 风险与回退

| 风险 | 缓解 |
|---|---|
| SPA/DOM 漂移 | act 前重定位 + re-enumerate |
| 反爬/滑块 | headless 遇验证码提示人工或切 browser_local 真 profile |
| 纯图标无文本 | 相邻文本 + vision overlay |
| nth 选择器脆弱 | id/data-* 优先 + 唯一性校验 + 语义双键降级 |
| 双检成本 | 仅关键动作；本地 7B 极廉；清单快照 hash 缓存 |
| SOP 过期/元素改版 | verified 日期 + 复用不符即更新或人工介入 |
| 误点风险 | role 校验 + 白名单 + 高风险 ask + 完成证据链 |

## 8. 待确认决策点

1. SOP 存放：ComputerUseSOPs/ 新目录（默认） vs 并入现有 SOPs/；
2. 双检默认开还是仅高风险开（成本 vs 安全）；
3. P5 试点任务选哪条（zhihu/xhs 草稿 vs B 站上传）；
4. 实施顺序 P1→P5 是否照此推进。
