# V9 提交发布任务失败分析（2026-08-30）

> 任务: 提交发布（把 fanqie_hepairenshu.mp4 发布到抖音并回填链接）
> 会话特征: 5 轮 × 32 工具上限全部耗尽, 最终未完成发布; 大量重复读取与无效探索。
> 分析基于本轮会话日志 + 代码核实(browser_local 白名单 / search_vault / EscapeGuard / sandbox_ops / 递归计数)。

---

## 一、Agent 行为观察

### 阶段 1（轮 1-2）: 探索迷失, 32 上限被低价值调用耗尽
- 任务核心是"打开抖音发布页上传视频", 但前两轮 60+ 调用几乎全是 list_dir/read_file/execute_command 目录侦察。
- **全盘 find 找视频**: `find / -name "fanqie_hepairenshu.mp4"` — 根目录遍历被拦(正确), 但 data/videos 在第 1 轮第 2 个 list_dir data 就已暴露, Agent 没有直接列 data/videos。
- **臆测不存在路径**: `data/vault/Reviews/...`、`data/vault/Prompts/...`(vault 从不在沙箱 data/vault/), 以及 `/mnt/d/vault/...` 绝对路径(越权被拦)。
- **跨轮重复读取同一批文件**: draft_weiren.md / script_weiren.md / promotion_log.md / fanqie_fawen_leixing_diagnosis.md 在轮 1/2/3 反复读取 — 跨轮 dup_read 计数被 turn_id 重置, 防重复失效。
- **工具内查询失败后放弃**: "search 未返回内容片段。改用行范围读取沙箱内 SOP 副本" — 说明 obsidian_knowledge search 结果缺内容, Agent 转去越权读沙箱副本。

### 阶段 2（轮 3）: 进入发布页, 但达人中心不可达
- 抖音发布页 navigate 通过白名单成功; 视频已复制到 /mnt/c/Users/<user>/Downloads/(符合 SOP Windows 路径要求)。
- 但先尝试 `daren.fanqienovel.com`(番茄达人中心)被白名单拦截 — **回填环节的平台根本不可达**。

### 阶段 3（轮 4-5）: 表单操作反复失败
- evaluate 写保护拦截(正确行为, 但 Agent 反复尝试用 evaluate 做交互)。
- evaluate 递归误报: 相同 expression 前缀 `(() => { const progress = ...` 多次调用被判"同一路径重复"。
- fill 超时(Locator.fill Timeout 8000ms): 发布页选择器不匹配或页面未就绪。
- 每轮 32 上限反复耗尽, 只推进一点点。

---

## 二、V9 系统 Bug（代码已核实）

### B1【高·功能缺陷】browser_local 白名单缺番茄达人中心
- `core/lib/v8/browser_local.py` 白名单: xiaohongshu/douyin/bilibili/zhihu/fanqieopen.com/**kol.fanqieopen.com**/weixin/weibo
- **缺 daren.fanqienovel.com**(番茄达人中心) — 而番茄推广 SOP 明确"登录态: 番茄达人中心(用户 02901157)"。
- 影响: "提交发布+回填发文"闭环的第一步(达人中心)就无法访问, 任务必然失败。

### B2【高·功能缺陷】obsidian_knowledge 工具未被正确使用
- 日志大量 `obsidian_knowledge()` 空参调用 + 一次 `未知知识键` 报错。
- 上轮已加 read 动作, 但 Agent 要么不知道 read 存在(schema 未感知), 要么 sop_key 传错(传了完整路径/带 .md 文件名)。
- search 结果只有 preview(100 字符)无内容字段 — Agent 明确抱怨"未返回内容片段"。

### B3【中·误导文案】越权读报错成"写入"
- `cat /mnt/d/...`(读取)被 sandbox_ops 报"禁止在沙箱外**写入**文件" — 文案不分读写, Agent 困惑(它明明在读)。
- `_check_sandbox_read` 的拦截文案("禁止读取系统路径")与 L1210 的写文案混用。

### B4【中·防护失效】跨轮 dup_read 计数被重置
- `dupread_{sid}_{turn}` 以 turn_id 为 key, 每轮重置 → 跨轮重复读取同一文件无防护。
- 本次 3 轮重复读同一批 fanqie 文件即证据。

### B5【中·递归误报】evaluate 探针被当重复路径
- 递归计数按 `browser_local:evaluate:<expression前50字符>` 指纹。
- 探针类表达式(如 `(() => { const progress = ...`)天然共享前缀 → 同功能多次调用误判"同一路径"。

### B6【低·显示混乱】目标进度 total 跳变 32 → 160
- 轮 1 显示 0/32, 轮 2 起 34/160 — goal total 语义对用户不透明(计划任务 32 vs 无计划 160)。

### B7【低·预算分配】32 工具上限被探索耗尽
- 探索止损(EXPLORE_THRESHOLD=5)本次未触发(list_dir 都有"产出"), 关键写动作无预算空间。

---

## 三、修复建议（按优先级）

| 优先级 | 修复 | 文件 |
|---|---|---|
| P0 | 白名单加 `daren.fanqienovel.com`(+ 子域) | core/lib/v8/browser_local.py |
| P0 | obsidian_knowledge search 结果加 content 字段; read 报错区分"未知键/vault未启用"; schema 引导 Agent 用 read | precision_inject.py / gateway_helpers.py / tool_router.py |
| P1 | 越权读命令文案改"禁止读取沙箱外路径"(读写分文案) | sandbox_ops.py / sandbox_util.py |
| P1 | dup_read 计数改 session 级(跨轮有效) | agent_gateway_enhanced.py |
| P1 | evaluate 递归指纹排除 action 前缀(按 action 分桶计数) | agent_gateway_enhanced.py / browser_local.py |
| P2 | 系统提示引导: "读 SOP 用 obsidian_knowledge(read), 不要 cat/read_file" | agent_gateway_enhanced.py |

---

## 四、结论

本次任务失败是**系统缺陷(B1 白名单缺达人中心) + Agent 工具使用不熟练(B2 不用 read) + 探索迷失(B3/B4/B5 放大)** 三者叠加:
1. 核心平台(达人中心)不可达 → 即使 Agent 走对流程也无法完成"回填"环节;
2. Agent 不知道用 obsidian_knowledge(read) 读 SOP → 浪费 20+ 调用尝试越权读取;
3. 越权误报文案 + 跨轮重复读取 + evaluate 误伤 → 32 上限被无意义调用耗尽。
