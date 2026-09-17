# 深挖任务失控根因分析（2026-08-30 后端日志）

> 任务: "深挖 Claude 训练 Claude / Anthropic IPO 原文细节"
> 现象: Agent 写了 30+ 个临时脚本(data/tmp/*.py), 触发 55 次/h 写审批, 用户被迫确认数十次,
>       5+ 轮预算耗尽后用户取消。核心工作(读原文)实际只完成极少。
> 后端日志: [FAILURE_CHANNEL] notify_boss 聚合抑制(41→55次/h) / [DUP_READ_STOP]×3 / [WRITE_GATE] 数十次 / heredoc 未修改提示×N

---

## 根因链（按严重度）

### R1【最高】临时脚本审批轰炸 — 写审批粒度错位
- 后端日志: `[WRITE_GATE] 写操作待确认: write_file data/tmp/decode_gn.py` 出现 **数十次**;
  `[FAILURE_CHANNEL] notify_boss 聚合抑制(41→55次/h)` — 每小时 55 次"等待老板确认"
- Agent 为解码 Google News URL 写了 decode_segs/decode_gn/decode_all/filter_rss/... **30+ 个临时脚本**,
  每个 data/tmp/*.py 都触发一次审批卡片
- 根本问题: **调试型临时脚本(data/tmp/)与核心写操作(项目文件)用同一审批粒度**
  harness 语义: 沙箱内自由执行, 审批只针对越权/关键操作; V9 把"写个调试脚本"和"改生产代码"同等对待
- 后果: 用户被审批淹没, Agent 被迫逐卡确认, 真正的工作(读原文)没时间做

### R2【高】死胡同不收敛 — 无方向漂移检测
- Agent 陷入"解码 Google News 混淆 URL"(CBMi... base64) — 写了 10+ 个解码脚本、下载 googlenewsdecoder 库
- 但 browse_web/fetch_web 本可直接跟随重定向读到原文 — 这是技术死胡同
- 系统无"任务漂移检测": Agent 从"读 2 篇文章"漂移到"逆向 Google News 编码", 无人阻止
- 探索止损(EXPLORE_STOP)只针对 list_dir/read_file 无产出, 不覆盖"换工具绕行"型迷失

### R3【中】重复读防护被绕行 — DUP_READ_STOP 触发但 Agent 换工具继续
- 后端日志: `[DUP_READ_STOP] ... 重复读 data/tmp x3` ×3(decoderv2.py/data/tmp/urls_core.txt)
- Agent 每次被 stop 后换 execute_command python3 -c 继续读同一文件 — **读防护只拦 read_file, 不拦绕行**
- 与 R1 叠加: 绕行又产生新临时脚本 → 新审批 → 循环放大

### R4【中】heredoc 未写检测只提示不阻止
- 后端日志: `[系统] heredoc 执行成功但目标文件未被修改...改用 write_file` 出现 **多次**
- 检测存在但只是 stderr 提示, Agent 忽略继续; 没有"同类失败 N 次强制换路"机制

### R5【低】写文件语法回滚循环
- `write_file 已写入失败 语法检查失败，已自动回滚: unterminated string literal` 出现多次
- Agent 生成的 python 脚本反复语法错误(TS 模板字面量转义问题), 写失败 → 改 → 再写 → 再失败
- 每次失败后重新审批, 放大 R1

---

## 根本性解决方案（对齐 harness: 沙箱内自由, 越权才审批）

### F1【核心】临时调试文件免审批 — 审批粒度分级
- data/tmp/ 下的 write_file/execute_command 写操作 **默认放行**(调试脚本, 无风险)
- 审批只针对: docs/reports/ 报告、config/ 配置、项目根文件、SOP 镜像(已有)
- 实现: ApprovalGuard 检查 path 是否 data/tmp/ 开头 → 是则直接放行
- 效果: 消除 90% 的审批轰炸; Agent 写调试脚本不再打断

### F2【核心】任务漂移检测 — 死胡同收敛
- 新增: 连续 N 次(如 8)工具调用无"实质产出"(无成功 read_file 到新文件/无最终写文档) → 注入
  "[系统] 已连续 N 次工具调用无实质进展。请评估当前方向: 若在死胡同, 换更直接的方式
  (如 browse_web 直接访问原文, 而不是解码 URL)。"
- 与探索止损区别: 探索止损针对"读目录", 漂移检测针对"绕行/逆向/过度工程"

### F3【中】读防护覆盖绕行
- DUP_READ_STOP 后, 同 session 内 read_file + execute_command(python -c 读) 同一目标文件 累计计数
- 绕行读同一文件 ≥5 次 → 同样触发 stop

### F4【中】heredoc 未写检测升级为计数
- heredoc "未修改"提示出现 3 次以上 → 强制改用 write_file(line 模式), 注入明确指引

### F5【低】写文件语法错误重试计数
- write_file 语法回滚同文件 ≥3 次 → 提示"请用更简单的单行脚本, 或改用 heredoc 分块写入"

---

## 实施优先级
本轮落地 F1(审批分级, 收益最大) + F2(漂移检测)。F3/F4/F5 是 F1/F2 的配套, 视效果决定。
