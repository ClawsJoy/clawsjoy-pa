# V9 架构治理 v2 — heredoc 禁写落地 + 剩余根治方向设计

> 日期: 2026-08-30 · 关联: v9_vs_harness_full_compare_20260830.md · v9_runaway_task_rootcause.md
> 状态: Phase 1(heredoc 禁写) + R1(token 水位轮次) + R2(读缓存幂等/压缩保留用户) + R3(write_file reason + 批量审批) 全部已实施上线

---

## 0. 本文档目标

上一份对比报告(v9_vs_harness_full_compare)给出 5 条根治方向。本次先落地其中最
明确的**能力边界收敛**类问题(heredoc 写文件绕过 write_file 保护链), 再给出剩余
三条方向的**可实施设计**, 每条含: 现状 → 根因 → 方案 → 改动点 → 风险与回滚。

---

## Phase 1（已实施）: heredoc 写项目文件硬禁止

### 现状问题
- V9 写保护链(write_file 相似度/审批/SOP 镜像保护)只覆盖「write_file」与
  execute_command 的**直接**写命令分类; heredoc(「cat > f <<EOF」、「python3 <<EOF」
  + 「open('f','w')」)可整段绕过保护链直接落盘项目文件。
- 与 harness 对比: harness 工具即边界, 无第二写路径; V9 execute_command 是「能力
  一切」, 写路径多、保护分散。

### 方案（已落地, 2026-08-30）
「core/gateway/security.py」的「_SYS_ESCAPE_PATTERNS」新增 4 条 heredoc 模式:

| 模式 | 覆盖 | 命中理由 |
|---|---|---|
| A1 重定向 heredoc | cat > f <<EOF / python3 ... > f <<EOF / bash > f <<EOF | heredoc 写项目文件(重定向) |
| A2 tee heredoc | tee f <<EOF | heredoc 写项目文件(tee) |
| B python heredoc 内写 | python3 - <<EOF + open('f','w'/'a'/'x'/'wb'...) / Path(f).write_text/write_bytes | heredoc 内 python 写文件 |
| C shell heredoc 体内重定向 | bash <<EOF 体内 > f / >> f | heredoc 脚本体内写文件 |

- **豁免**: 「data/tmp/」前缀(调试区)与「/dev/null|stdout|stderr」(合法丢弃)。
- **生效面**: 3 处执行路径全部走「_detect_sys_escape」 — EscapeGuard(registry),
  「_check_sandbox_read」(execute_command.py L39 / sandbox_ops.py L1181 /
  tool_router.py L321)。「_SYS_ESCAPE_PATTERNS」是单点, 全线生效。
- **测试**: 「tests/unit/test_workspace_guard_fixes.py」新增
  「test_heredoc_write_project_file_blocked」/「test_heredoc_data_tmp_and_read_allowed」,
  回归 732 passed(基线 730 + 2)。

### 验证矩阵(手工/单测已覆盖)
| 命令 | 期望 |
|---|---|
| cat>docs<<EOF | 拦截 ✅ |
| python3 <<EOF + open('docs/x.py','w') | 拦截 ✅ |
| bash <<EOF + echo x > docs/x.sh | 拦截 ✅ |
| cat > data/tmp/x.py <<EOF | 放行 ✅ |
| python3 <<EOF + open('data/tmp/x.py','w') | 放行 ✅ |
| 纯读取 heredoc / python -c 写 /tmp | 放行 ✅ |

### 用户影响与后续
- Agent 若再尝试 heredoc 写文件, 会收到「高危命令被拦截: heredoc 写项目文件」并
  被引导用 write_file。若出现反复撞墙(如写报告), 由 drift 检测 + 提示注入兜底。

---

## R1（已实施, 2026-08-30）: 轮次限制弹性化 — token 预算取代硬轮次截断

### 现状
execution_policy.yaml 的 execution_budget 段:
- max_bridge_rounds: 16     # bridge_loop 每任务轮次上限(硬)
- max_total_tools: 32       # 总工具数硬上限
- goal_max_turns: 5         # goal 级续跑上限(硬)
- per_task_token_budget: 500000  # 已有 token 预算(但只在超限后降级, 不用于轮次弹性)

「_v9_bridge_loop」L3038-3041: for _bridge_round in range(_max_bridge_rounds) —
到 16 轮**强制中断**, 即使任务接近完成、上下文还远未饱和。

### 根因
- 轮次上限是「墙」不是「水位」: 与 harness 的 continuous-operations 定位相反,
  harness 按 token/成本控制, 不按调用次数硬掐。
- 硬截断制造**伪失败**: 16 轮刚好做完大半 → 被掐 → 下一 goal turn 重来 → 重复
  计费, 且用户看到「任务中断」而非「任务完成」。

### 方案: token 水位预算驱动
1. **预算改为 token 水位**: 将 max_bridge_rounds 语义从「第 16 轮强制 break」
   改为「软阈值」——「_calc_token_budget」已存在(L3057), 每轮结束估算
   「_tg_estimate(messages, tools)」, 对比 per_task_token_budget(默认 50 万
   token 已有配置)。
2. **不再强制 break**: 移除 range(_max_bridge_rounds) 硬界, 改为
   while True + 终止条件:
   - 任务自报完成 / 用户停止 → 正常退出;
   - 本轮 token 估算 ≥ per_task_token_budget → 停止并输出阶段总结
     (而非中断报错);
   - 「_v9_daily_cost_exceeded」降级逻辑保留(成本红线仍是硬保护)。
3. **goal_max_turns 联动**: goal 续跑条件从「轮数 < 5」改为「累计 token < 预算」。
4. **max_total_tools 保留但调宽**: 作为防失控第二道闸(默认 32 偏紧, 建议 48~64),
   不再作为常规终止路径——它只拦「无限循环」型失控(F1/F2 复盘案例)。

### 改动点
- agent_gateway_enhanced.py 的「_v9_bridge_loop」(L2930 起): 轮次循环条件替换;
- config/v9/execution_policy.yaml: execution_budget 注释更新 + max_total_tools
  调宽; 新增 soft_token_ceiling 说明;
- goal_state.py: goal total/turn 语义改为 token 驱动(需与「_write_turn_end」
  L2682 联动)。

### 风险与回滚
- 风险: 无硬轮次后, 单任务最长运行时间上升 → 需依赖 per_task_token_budget
  与工具超时(tool_timeout_ms 已有)兜底; 观察 [COST_LOG] 单任务成本。
- 回滚: 配置改回 max_bridge_rounds: 16 即可(保留该键作为硬上限开关, 默认关闭)。

---

## R2（已实施, 2026-08-30）: 上下文真实性 — read_file 缓存幂等, 不做激进压缩

### 现状
- 「_compress_messages」(message_assembler) / compaction_threshold: 0.8:
  上下文超预算按比例压缩, 大量压缩后 Agent 丢失细节(用户反馈「agent 行为太夸张、
  前后不一致」)。
- read_file 有「_is_repeat_read_attempt」(重复读检测)但**无内容缓存**: 同一文件
  反复读 → 每次全量进上下文 → 撑爆预算 → 触发压缩。

### 根因
- 压缩是「事后补救」, 且压缩后的摘要丢真实细节(与 harness 的
  read_file→缓存→幂等返回不同: harness 同文件重复读返回缓存+不变签名,
  Agent 不需要重新消化)。
- 真实性问题本质: 上下文里**重复信息多**(同文件多轮重读、同一工具输出反复
  注入), 而非信息本身多。

### 方案: 读缓存 + 幂等 + 只压旧工具输出
1. **read_file 内容缓存(幂等)**:
   - 新增 session 级「_file_cache: {path_md5: {content_hash, content, ts}}」,
     并入现有 state 持久化;
   - 同 session 内重复读同一路径: 若文件未变(mtime/content_hash 相同), 返回
     cached=true 结果且**不再追加进 messages**(或只追加一行「已读缓存: path
     (内容同上次)」);
   - 文件变更(写工具执行后)失效对应缓存条目。
2. **压缩只针对旧工具输出**:
   - 「_compress_messages」改为只压缩「≥ N 轮前的工具输出」(harness 做法),
     保留最近轮次的原始工具输出与所有用户消息;
   - compaction_threshold 语义从「全量压缩」改为「只压旧区」。
3. **重复读引导**: 「_is_repeat_read_attempt」命中时, 提示注入改为
   「该文件内容已在上下文中(路径), 直接使用, 无需重读」。

### 改动点
- core/gateway/path_utils.py / 「_execute_sandbox_tool」(read_file 分支):
  缓存读写 + 失效钩子(写工具后清 path 缓存);
- core/gateway/message_assembler.py 的「_compress_messages」: 旧区压缩策略;
- agent_gateway_enhanced.py L3867/3884(压缩触发点): 按新策略执行。

### 风险与回滚
- 风险: 缓存命中判断需准确(文件变更必须失效, 否则 Agent 读旧内容);
  用 content_hash 而非仅 mtime。
- 回滚: 配置开关 read_cache_enabled: false 即回退。

---

## R3（已实施, 2026-08-31）: 审批内联 — write_file 补 reason 字段 + 批量审批

### 现状
- 写审批卡片只有 path + content_preview, **无「为什么写/写给谁」**; Agent 每次
  写文件都要单独弹卡, 多文件任务(如一次生成 10 个模块)审批 10 次, 打断节奏。
- harness 对比: harness 写审批含 justification, 且支持批量/一键确认。

### 方案
1. **write_file schema 增加 reason(必填)字段**:
   - 工具 schema 声明 reason: string(写该文件的理由, 给老板审批看);
   - ApprovalGuard 卡片展示 reason; reason 空 → 直接拒绝并提示补理由(引导
     Agent 说明意图, 减少「随手写」行为)。
2. **批量审批**:
   - 同轮多个写请求 → 合并为一张「批量审批卡」(每项含 path/reason/preview);
   - 审批动作支持 approve_all / approve_selected[ids] / reject;
   - 「_pending_writes」按批量组组织, 「_resume_bridge_after_approval」逐项
     回填 mark_file_approved(含 cmd: 指纹, 与现有逻辑兼容)。
3. **审批上下文注入**: 批量卡发出前, 把「本次要写的全部文件+理由」汇总注入
   Agent, 让其先自查(减少无效审批)。

### 改动点
- core/gateway/gateway_helpers.py 的「_get_default_tools」(write_file schema);
- core/gateway/guards/registry.py 的 ApprovalGuard(批量卡 + reason 校验);
- agent_gateway_enhanced.py 的「_handle_write_approval」/「_resume_bridge_after_approval」
  (批量动作解析);
- 前端审批卡片渲染(需与 GUI 联调)。

### 风险与回滚
- 风险: 批量卡一次展示多文件, 用户可能「不看就全批」; 需默认逐项勾选, 全批需
  显式动作。
- 回滚: schema 加字段是向后兼容(缺 reason 时按旧逻辑提示), 可逐步放开。

---

## 优先级建议(执行顺序)

| 优先级 | 项 | 理由 | 依赖 |
|---|---|---|---|
| ✅ 已完成 | Phase 1 heredoc 禁写 | 堵住保护链最大旁路 | — |
| ✅ 已完成 | R1 token 水位轮次 | 消除伪失败/重复计费; 轮次护栏 16→100, budget_limit 改正常收尾, goal_info 加 token 字段 | — |
| ✅ 已完成 | R2 读缓存幂等 + 用户保留压缩 | read_file 内容 hash 幂等+写后失效; 压缩保留所有 user 消息 | — |
| ✅ 已完成 | R3 审批内联 | write_file schema 加 reason(必填); ApprovalGuard 收集 reason; 同轮多写合并批量卡(approve_all/approve_selected/reject); 批量上下文注入 | — |

> 建议 R1+R2 同批实施: R1 放宽轮次后, 上下文增长更快, R2 恰好对冲;
> R3 独立, 可随时穿插。

---

## 附: 与 harness 的对应关系

| V9 现状 | Harness 对应 | 本稿方向 |
|---|---|---|
| heredoc 可写项目文件 | 工具即边界, 单写路径 | Phase 1: 禁 heredoc 写, 收敛到 write_file |
| 16 轮硬截断 | token/成本水位控制 | R1: token 预算弹性轮次 |
| 重复读全量进上下文 + 激进压缩 | read 缓存幂等, 只压旧区 | R2: 缓存 + 旧区压缩 |
| 无理由单张审批卡 | justification + 批量确认 | R3: reason 字段 + 批量审批 |

---

## 2026-08-31 修复记录: R1+R2 上线后暴露的 3 个问题

> 触发: 任务「还有哪些未完成」消耗 508345 tokens 触发水位, 且 execute_command 读文件绕过 R2 缓存。

### 问题 1: execute_command 读文件绕 R2 缓存(已修复)
- 现象: Agent 用 python3 -c open().read() 读同一文件 3 次, read_file 缓存不生效
- 根因: R2 缓存只加在 read_file 工具路径, execute_command 是独立执行路径
- 修复: bridge_loop tool 结果 append 前检测纯读文件命令(python -c open/cat),
  提取路径+内容 hash 与 _read_content_cache(同一 session 缓存)比对, 命中替换为
  短提示「已读缓存 path 内容与上次一致」, 不再重复注入全文。
- 验证: 单测 test_exec_read_dedup_logic + E2E 真实命令 3 次读(2、3 次去重) PASS

### 问题 2: token 508345 异常高(已修复)
- 根因链: 上下文窗口 65536 → 预算 61536 → 压缩阈值 0.8x61K≈49K。上下文堆积到
  近 49K 才压缩 → 每轮 LLM input ≈46K x 11 轮 ≈ 50 万。且 keep=8 保留大 tool 输出,
  压缩不彻底反复膨胀。
- 修复: compaction_threshold 0.8 → 0.6(≈37K 提前压缩)。R2 去重减少重复注入。
- 验证: test_compaction_threshold_config / test_compaction_trigger_logic 更新 PASS

### 问题 3: token 水位触发后假完成(已修复)
- 根因: budget_limit 返回的 _bmsg_guard 是系统指令文本(请输出总结),
  前端可能渲染为最终回复 → 用户看到「✅ 任务完成」但实际未回答。
- 修复: _bmsg_guard 改为明确「⚠️ 预算不足, 任务未完全完成」+ 已完成/未完成
  区分模板; 配合 status: token_water 供前端识别。
- 验证: test_token_water_guard_message_honest PASS

---

## 2026-08-31 R4: obsidian_knowledge 全 vault 检索修复

> 触发: Agent 报告「公众号未登记」，实际 vault 存在 微信公众号/公众号.md（用户手动目录）。

### 根因
- _scan_vault 只扫 Reviews/SOPs/Pitfalls 三目录
- _KNOWLEDGE_FILES 只配 4 个固定 SOP + 避坑清单
- 用户手动目录(微信公众号/ 我的知乎 等)与 Clippings 自动剪藏检索不到

### 修复(已上线)
1. _scan_vault 递归扫 vault 根下全部 .md(排除 .obsidian/Templates)，带 sub 分类与 rel_path
2. 三目录保留 sub 优先级(SOPs 1.25/Pitfalls 1.2/Reviews 0.75)，其余目录归 general(权重默认)
3. list_knowledge_files 返回完整目录树(66 个 .md 全列，固定 SOP 保留 key 兼容)
4. _resolve_knowledge_path/read_knowledge_file 支持任意 vault 相对路径(如 微信公众号/公众号.md、Clippings/xxx)，防 ../ 逃逸
5. search_vault 结果带 rel_path(Agent read 直接用)

### 验证
- 单测 4 个(test_r4_scan_vault_recursive/read_any_vault_path/search_finds_manual_dir/list_full_tree) + 全量 746 passed
- E2E: Agent search「公众号」→ read 微信公众号/公众号.md 成功(exists: true)，返回公众号后台剪藏内容
- live 同步 + gateway 重启健康

---

## 2026-08-31 R5: browser_local 任务上下文爆炸修复(527K/11次调用)

> 触发: 11 次 browser_local 消耗 527K tokens 触发预算, 每轮 input 48K。

### 根因(量化取证)
- 每轮 derive_messages 投影**全部历史事件**: 3935 条 tool_result 跨任务累积(目标任务只 11 条)
- browser_local 每次调用后 _audit 写一条 role=system 审计回显(含完整命令)进 SessionLog → 被投影进上下文
- browser_local extract/evaluate 结果不截断(可能整页 DOM)

### 修复(已上线)
1. derive_messages 过滤 browser_local 审计回显(source=browser_local) — 审计保留在事件层, 不进模型上下文
2. browser_local _handle_result 截断大结果(>4000 保留头尾各 2000 + TRUNCATED 标记)
3. derive_messages(last_task_only=True) 任务级上下文隔离 — 只投影最近一次真实用户消息(source=user_input)之后的事件; bridge_loop 每轮启用

### 验证
- 单测 3 个(test_r5_derive_filters_browser_audit/last_task_only/browser_result_truncation) + 全量 749 passed
- E2E: 新任务 9414 tokens 完成(对比之前 48K/轮、527K/任务)
- live 同步 + gateway 重启健康

---

## 2026-08-31 草稿箱系统实施完成(6 步)

> 方案: draft_box_feasibility_20260831.md → 已实施。Agent 只产出内容+格式化, 写 Obsidian 草稿箱; 用户审核后手动发布。

### 实施内容
1. **目录+模板**: vault 草稿箱/{公众号,小红书,知乎,B站,抖音}/+assets、已发布/、平台规范/(5 平台 frontmatter 模板)
2. **插件化**: core/plugins/draft_box/ (base.py + 5 平台插件; 图片复制 assets, 视频相对路径引用)
3. **工具扩展**: obsidian_knowledge 新增 write_draft/mark_published/list_drafts 三个 action
4. **旧草稿迁移**: zhihu(2)/xhs(1+cover)/wechat(1)/bilibili(脚本+视频引用) → 草稿箱
5. **SOP 更新**: 平台规范/ 5 文件 + platform_publish_workflow.md 追加草稿箱流程
6. **端到端验证**: Agent write_draft → Obsidian 可见 → mark_published → 已发布/ + status/published/post_url 更新

### 验证
- 单测 4 个(test_draftbox_write_and_publish/video_reference/plugin_registry/obsidian_schema) + 全量 753 passed
- E2E: Agent 通过 obsidian_knowledge 完成 写草稿→list→mark_published 全链路
- live 同步 + gateway 重启健康

---

## 2026-08-31 R6: 公众号封面任务失控修复(507K tokens/假完成)

> 触发: 生成公众号封面任务消耗 507714 tokens 触发预算, Agent 反复重试字体探测。

### 根因(4 项, 全部修复)
1. **fc-list 只读命令被误判 write**: _classify_command 默认分支把 2>/dev/null 当写
   → 字体探测被审批门拦 → Agent 反复重试(已修: 豁免 stderr 丢弃重定向 + _READ_CMDS 加 fc-list/curl)
2. **obsidian_knowledge 落 <no-path> 被递归误判杀**: _extract_tool_path 不识别 obsidian 参数
   → 5 次合法调用被判重复操作 → Agent 合法操作被杀 → 更多重试(已修: action+目标 作递归 key)
3. **沙箱无中文字体认知缺失**: 实际有 wqy-microhei.ttc, 但 Agent 不知道 → 反复探测被拦的 /usr/share/fonts
   (已修: 沙箱边界提示加入字体路径指引, PIL 直接用)
4. **write_file 空 path 无效审批**: Agent 幻觉发空 write_file() → 审批通过后执行失败
   (已修: ApprovalGuard 缺 path 直接拒绝, 不进审批)

### 验证
- 单测 4 个(test_r6_*) + 全量 757 passed
- E2E: 重现封面任务 → Agent 直接用 wqy 字体生成 cover_900x383.png + write_draft 成功, 无失控
- live 同步 + gateway 重启健康

---

## 2026-09-01 R7: mark_published 任务失控修复(验证链接死循环)

> 触发: 用户回传 post_url 后, Agent 不执行 mark_published 反而 browse/fetch 验证链接,
> 网络全失败(沙箱无 zhihu 访问) → 连续失败 8 次暂停 → 假完成。

### 根因
- obsidian_knowledge 的 tool description 缺草稿箱动作说明: Agent 从描述看不到
  write_draft/mark_published 语义, 收到 post_url 后惯性去验证链接真实性,
  但沙箱无法访问 zhihu → browse/fetch/browser_local 全失败 → 连续失败暂停
- 用户只回链接未选草稿时, Agent 未用 list_drafts 推断/默认最新草稿

### 修复
- 更新 tool description: 明确 write_draft/mark_published/list_drafts 语义 +
  「mark_published 是本地文件操作, 直接传用户给的 post_url 即可, 不要用 browse/fetch 验证链接」

### 验证
- 单测 3 个(test_r7_schema_guides_local/mark_published_relative_path/nonexistent) + 全量 760 passed
- E2E: 重现 mark_published → Agent 一次 obsidian_knowledge 调用完成(published+post_url+移入已发布/), 无失败无暂停
- live 同步 + gateway 重启健康

---

## 2026-09-01 多模态学习系统实施完成

> 设计: obsidian_learning_system_design_20260901.md → 已实施。收件箱文件 → 转录/提取 → 学习笔记。

### 实施内容
1. **目录**: vault 收件箱/ + 学习笔记/{视频,音频,图片,PDF}/ + assets/
2. **管线**: core/plugins/media_processor.py — video/audio→faster-whisper(CPU int8)转录→LLM 总结;
   pdf→PyPDF2 提取→LLM 总结; image→复制原文件(OCR 后续)。写笔记+原文件复制 assets/ 嵌入
3. **工具扩展**: obsidian_knowledge 新增 process_media(file_path, media_type, title) action + schema
4. **whisper**: faster-whisper base CPU int8(无 GPU), 中文支持, 模型加载 1.7s; LLM 不可用兜底截断

### 验证
- 单测 4 个(test_r8_*) + 全量 764 passed
- E2E: Agent 通过 process_media 处理 PDF → 学习笔记/PDF/ 笔记(frontmatter+嵌入) + assets/ 归档
- live 同步 + gateway 重启健康

---

## 2026-09-01 视觉 Agent 配置更新 + llava 图片理解接入

> vision_agent: moondream/11434 → llava:latest/11435; process_media 图片分支从占位改为 llava 读图。

### 内容
1. config/agents/vision_agent/config.yaml: model=llava:latest, endpoint=11435
2. media_processor.py 新增 _describe_image_llava(base64 + /api/generate), 图片分支生成描述→LLM 总结→笔记
3. llava:latest 已在 11435 加载(4.7GB), 无 GPU 本地推理

### 验证
- 单测 3 个(test_r9_config/llava_describe/agent_v4) + 全量 767 passed
- E2E: Agent process_media(image) → llava:latest 读图 → 学习笔记/图片/ 笔记(含描述+原图嵌入)
- live 同步 + gateway 重启健康

---

## 2026-09-01 收件箱 YouTube 字幕补齐 + 降级覆盖 bug 修复

> process_youtube: 检测收件箱/ YouTube 剪藏(source_url 含 youtube)→ 已有字幕跳过 → yt-dlp+whisper 转录 → 移入学习笔记/视频/。

### 环境限制(已验证)
- yt-dlp 2026.07 可解析(format 140), 但实际下载被 YouTube 403(JS challenge/IP 风控)
- 环境 HTTP_PROXY=127.0.0.1:7890 但代理未监听 → yt-dlp 需绕代理(env -u HTTP_PROXY + remote-components)
- 本地视频/音频转录可行(faster-whisper CPU): bilibili_kaoyan_ai.mp4 转录 565 字符

### 实现
1. media_processor.process_youtube: URL 提取(youtu.be/shorts/watch) + 字幕检测(transcript:true/原文转录章节→跳过)
2. yt-dlp 绕死代理下载音频 → whisper 转录 → 字幕写入笔记(frontmatter transcript:true + 原文转录章节)
3. 下载失败(403) → 降级标注「需手动下载视频」(frontmatter transcript:false + 字幕补齐待办)
4. obsidian_knowledge 新增 process_youtube action

### Bug 修复(E2E 发现)
- process_youtube 降级分支带 note_path 时覆盖原剪藏文件(Clippings 内容丢失)
- 修复: 降级**总是新建独立笔记**(学习笔记/视频/), 不碰原文件; 原文件从会话日志重建恢复

### 验证
- 单测 5 个(test_r10_*) + 全量 772 passed
- E2E: Agent process_youtube 降级完成(环境 403) + 已有字幕跳过 + 降级不覆盖原文件
- live 同步 + gateway 重启健康

---

## 2026-09-01 Agent 行为引导修复(沙箱读取 + f-string)

> 触发: llava UI 评测任务中 Agent 用 obsidian_knowledge 读沙箱截图(应 read_file), 且写含中文引号的 python f-string 反复语法失败。

### A. obsidian_knowledge 沙箱读取引导
- schema description 开头加: 本工具只读 Obsidian vault 知识文件; 沙箱内文件(data/ 等)用 read_file, 不要用本工具

### B. f-string 嵌套引号引导
- agent_system.md 加: 写 python 脚本避免 f-string 嵌套引号(unterminated string literal); 优先拼接/.format, 含中文引号时尤甚

### 附带修复
- R10 youtube degrade 测试会真跑 yt-dlp(120s 网络超时) → mock subprocess.run 返回失败, 全量回归提速稳定

### 验证
- 单测 2 个(test_r11_*) + 全量 774 passed
- E2E: Agent 读沙箱截图用 read_file(不再 obsidian_knowledge)
- live 同步 + gateway 重启健康

---

## 2026-09-03 本地模型测试任务失控修复(515K tokens / sleep 轮询)

> 触发: qwen2.5vl 图片测试任务消耗 515882 tokens 触发预算。Agent 用 nohup 后台 + sleep 25/28 轮询等模型返回。

### 根因
- execute_command 超时 30s < 本地模型推理(约 2min) → timeout 300 同步被外层截断 → Agent 被迫 nohup 后台
- 每次 sleep 轮询 = 一轮 LLM 调用(约 2 万 tokens) → Q1/Q2/Q3 + llava 复测轮询 15-20 次 ≈ 30-40 万 tokens

### 修复
1. tool_timeout_ms 30s → 180s(config + execute_command 默认值) — 本地模型推理可同步等待
2. agent_system.md 加本地模型调用引导: 同步 curl --max-time 280, 禁止 nohup+sleep 轮询, 多问合并一次 prompt

### 验证
- 单测 2 个(test_r12_*) + 全量 776 passed
- live 同步 + gateway 重启健康

---

## 2026-09-03 qwen2.5vl 测试任务假完成防护(侦察=完成)

> 触发: qwen2.5vl Computer Use 测试任务只做侦察(read 报告 + curl api/tags)后输出过渡语「现在确认服务可用性...做准备」→ 被判 completed → goal done 补满 240 → goal complete → 任务中断, 未实际调模型。

### 根因
- reason=completed 时 _write_turn_end 无条件 complete_goal + done 补满 total → 过渡语(45字符)被当最终交付
- Agent 侦察阶段的过渡内容被 bridge_loop break 分支判为 completed(有内容无 tool_calls)

### 修复
- _write_turn_end 假完成防护: report 短(<120字符)且含过渡词(准备/将要做/接下来/确认可用/先读/再跑等)
  → done 只加本轮工具数(不补满 total) + 不置 goal complete(保持 active 可续跑)
- 修复 guard 变量 bug: 误用未定义 _turn_report → report 参数

### 验证
- 单测 1 个(test_r13_transitional_report_not_complete) + 全量 777 passed
- live 同步 + gateway 重启健康

---

## 2026-09-03 bash data/tmp 脚本审批豁免

> 触发: qwen2.5vl 测试任务中 `bash data/tmp/qwen_merged.sh`(curl 调本地模型写 data/tmp)被判 write 反复触发审批, 用户确认后 Failed to fetch。

### 根因
- _classify_command bash 分支: 非 -c(执行脚本)一律 return write → data/tmp 调试脚本也审批
- 与 python3 <script.py> data/tmp 豁免不一致(python 已豁免, bash 未豁免)

### 修复
- _classify_command bash/sh 分支: 执行 data/tmp/ 下的脚本 → read(与 python3 一致); 非 tmp 脚本仍 write

### 验证
- 单测 1 个(test_r14_bash_tmp_script_exempt) + 全量 778 passed
- bash data/tmp/qwen_merged.sh 放行; bash scripts/deploy.sh 仍审批
- live 同步 + gateway 重启健康

---

## 2026-09-03 execute_command 超时 180s→320s(qwen2.5vl 慢模型)

> 触发: qwen2.5vl Computer Use 测试任务拿到回答但 512K 超预算截断在写报告前。

### 根因
- 引导 Agent 用 timeout 300 同步等待, 但 execute_command 外层 180s 超时先杀 → timeout 300 永远跑不完 → Agent 多次重试(每次一轮 LLM ≈20-40K token)烧到 512K
- qwen2.5vl 7B 实测 3.41 tok/s(RTX 2060): 550 token 需 162s, 三问合并 >200s, 超出 180s

### 修复
- tool_timeout_ms 180s → 320s(config + execute_command 默认值), 使 timeout 300 内层真正完成
- agent_system.md 引导同步(--max-time 300, 超时 320s)

### 验证
- R12 测试更新 320s + 全量 778 passed
- live md5 一致 + gateway 重启健康

---

## 2026-09-03 R15 报告写入任务中断根治: 系统回声假完成 + write_note 通用 vault 通道

> 触发: 「把 Qwen2.5-VL 评估报告写入 Obsidian」任务(turn 22333-22435)反复中断 —
> Agent 读取全部测试数据 + 多次重写 summarize 脚本后, 最终把系统「交付」阶段提示复读两遍
> (report = 2×"[系统] 当前阶段：交付。请用 write_file...")当最终报告 → reason=completed
> → goal 补满 240 → 任务结束, 报告从未写入 Obsidian。

### 根因(取证自 session log + Reviews/8393597675_2 复盘)
1. **系统回声被当完成**: R13 过渡语守卫只拦 <120 字符含过渡词的 report; 本次 report ≈260 字符
   且是 [系统] 阶段提示原文复读(无过渡词) → 绕过守卫 → complete_goal。属 R13 同类洞的新变体。
2. **obsidian_knowledge 无通用落盘通道**: 只有 write_draft(草稿箱/平台稿, 必须 platform)
   与 process_media/process_youtube(学习笔记专用)。Agent 调 write_draft(platform=None)
   → 报「未知平台: None」→ 技术评估类报告无处可写(vault 外 data/reports 又需审批)。
3. **Agent 回复多次被截断**(「你的上一条回复被截断了」) + 工具 stdout 截断 2000 字符
   → summarize 内容看不全 → 反复重写脚本 → 上下文耗尽(386K tokens)后降级复读系统提示。

### 修复
1. **R15-A 系统回声假完成守卫**(agent_gateway_enhanced.py _write_turn_end):
   report 含「[系统]」/「当前阶段」且剔除系统行后剩余 <60 字符 → _is_sys_echo=True,
   折叠进 _is_transitional: done 只加本轮工具数 + 不置 complete(goal 保持 active 可续跑)。
2. **R15-B obsidian_knowledge 新增 write_note 通用 vault 笔记通道**:
   - precision_inject.write_vault_note(title, content, tags, folder): 写 {vault}/{folder}/{title}.md,
     folder 空=vault 根, 可传 收件箱/学习笔记/ 等相对目录; 文件名净化 + 路径穿越防护 + 重名 -2/-3;
   - tool_router obsidian_knowledge 分发 _act=="write_note"(title/content 必填校验);
   - gateway_helpers schema: action enum + 描述区分 write_draft(平台稿, platform 必填)/write_note(技术/评估/复盘);
   - agent_system.md 新增「Obsidian vault 知识交付」章节引导 write_note + 禁止复读 [系统] 提示当交付。
3. 交付本文档: 完整报告已复原并直接写入 vault 根目录(Qwen2.5-VL作为ComputerUse眼睛的实测评估（对比llava）.md)。

### 验证
- R15 单测 4 个(系统回声源码守卫/行为级不 complete/实质报告仍 complete/write_note 通道接线)
- R12-R15 定向 7 passed + goal/turn/guard 组 85 passed
- 全量回归 782 passed(778 基线 + 4)
- live 同步 + gateway 重启健康

---

## 2026-09-04 R15.1 三层补强: 长文截断 / 原样存档污染 / 无落盘校验

> 触发: 上线后新任务(复盘稿残缺版排查, turn 22673-22741)发现三层历史 bug —
> Reviews/2026-09-04-8527542585_1.md 内嵌报告被截断残缺(§1 事实表在"| 产品 |"处断裂)、
> 可复用经验区混入工具输出碎片、避坑清单尾部被日志污染; write_note 自带 frontmatter+H1
> 又遇 content 自带 frontmatter → 双 frontmatter/双标题。

### 三层核对结论(R15 覆盖度)
1. **长文截断**: 部分覆盖 → R15 write_note 单次落盘实测 ~5KB 无截断; 补 append=true 分块续写;
   复盘稿/避坑清单硬切片([:3000]/[:500])会断在表格行中 → 改段落边界截断(_cap_par)。
2. **原样存档污染**: 未覆盖 → write_vault_note/write_task_review/append_pitfall 均原样落盘;
   补 _clean_vault_text 统一清洗(去 [系统] 行/截断残留标记/连续重复段, 剥自带 frontmatter 与重复 H1),
   清洗后为空(仅系统回声)拒绝写入。
3. **无落盘校验**: 未覆盖 → write_note 成功返回 verified{bytes,行数,head 预览} 作写后抽验;
   agent_system 引导写后核对 verified, 复盘稿只写摘要+[[双链]]。

### 改动点
- core/gateway/precision_inject.py: _clean_vault_text + _cap_par 助手; write_vault_note(清洗+拒绝+append);
  write_task_review(清洗报告/挖掘内容 + 段落截断); append_pitfall(清洗+拒绝)
- core/gateway/tool_router.py: write_note 传 append + 返回 verified
- core/lib/gateway_helpers.py: schema 加 append; 描述补清洗/分块/校验说明
- config/prompts/agent_system.md: 交付纪律(content 不带 frontmatter/# 标题; 长文 append 续写; verified 即抽验; 复盘稿不内嵌长文)
- tests/unit/test_precision_inject.py: +4 个 R15.1 测试(清洗行为/落盘+append/段落截断/接线)

### 验证
- R12-R15.1 定向 11 passed + goal/turn/guard 组 85 passed
- 全量回归 786 passed(782 基线 + 4)
- live 同步 + gateway 重启健康

---

## 2026-09-04/05 Computer Use Agent P1–P5 实施（a11y 枚举 + 语义选择 + DOM 执行 + 学习循环 + SOP）

> 触发: POC 证明「a11y 枚举 25 元素 + LLM 选序号 = 100%(14/14)」「VLM 独立产坐标 ±8~164px 不可靠」
> → 用户批准正式设计(docs/reports/computer_use_agent_design_20260904.md)后按 P1-P5 实施。
> 设计文档/验证报告: computer_use_agent_design_20260904.md / computer_use_p3_verify_20260904.md
> (P2/P4 验证含真实百度 E2E 与首条 CU-SOP)。

### P1 基础库 core/tools/a11y_dom.py（纯函数, 11 单测）
- role_of / stable_label(标签优先级 + 占位内容化检测) / build_selector / items_text / validate_selection(role 校验表) / dedupe_key
- 实测修正: contenteditable div → role textbox(百度新版输入); 新闻式占位(普京称…/周健任…)不得当标签 → 静态指令前缀白名单 + 非短文本默认内容

### P2 工具接线 browser_hybrid（enumerate/click/fill/type/press/select_option/hover/observe/close）
- core/tools/browser_hybrid_impl.py: 页面池按 page_id 保留(TTL 10min/上限4), SSRF 内网拦截, fill 执行时 DOM 扫描兜底(百度 A/B 换层 textarea↔div[contenteditable] 实证), 截图强制沙箱
- schema+插件+注册+优先级3; 集成测试真开百度 25 元素 + fill 回读一致 + click 提交 wd 正确
- 全量回归 812 passed

### P3 语义选择（模板 + role 校验双检 + vision 回退）实测 100%
- semantic_select.py: SELECT_SYSTEM 固化; select_index/double_check(本地 qwen2.5:7b 打乱清单独立再选); overlay 编号截图 + ask_vision_choice
- 实测修正①: **/api/generate 忽略 system** → 改 /api/chat(7B 无约束多话/返0)
- 实测修正②: 输入框降级名(多行文本输入框)与意图词不匹配 → SYSTEM 提示 + 引擎「输入意图命中非可编辑且唯一可编辑 → 覆盖」确定性规则
- 实测修正③: **vision 编号回退不可靠(qwen2.5vl 全页 25 标注 2/2 错读, 加图例仍 14≠1)** → 冲突默认 ask, vision 仅参考, 留待更强模型复测
- 实测: 10 意图×2 模型 = qwen2.5:7b 9/9、qwen2.5vl 10/10、双检 8/8 全对(≥95% 达标)
- browser_hybrid act 支持 double_check=true+intent(一致才执行) + fallback=vision 仲裁

### P4 学习循环 + SOP 生成器（cu_learning 工具）
- core/tools/cu_learning_impl.py: start(显式 completion/fail_if)/log_step(plans jsonl + 停止规则: 同一意图>2 → 连续≥3 → 累计>3)/complete(证据门禁防假完成)/count/sop/build_sop(§5 格式: frontmatter+前置+步骤[意图/锚点 role+label+sel/动作/验证]+失败已知)/classify_failure(选择错/执行错/风控/选择器失效/超时/歧义)/telemetry(P5)
- 实测: 真实流程「百度→点开新闻」经学习循环成功≥2 次 → 自动生成首条 CU-SOP 并归档 vault ComputerUseSOPs/baidu-open-news-cu-sop.md(成功 3 次累计)
- 防假完成实证: 无导航点击(URL 未变)被证据门禁拦截 5 次; 修复: click 后接管新标签页 + 链接 href 同页导航兜底(headless target=_blank 实证)

### P5 试点 + 遥测
- 试点: SOP 命中复用第 3 轮照做成功(news.baidu.com); 遥测聚合 plans → data/computer_use/telemetry.json + telemetry_20260905.md(13 运行/3 成功/10 中断-早期探索未 abort, 成功率 23% 为含探索的真实口径, 平均 52s)
- 治理记录(本文档) + live 同步清单

### 经验沉淀(避坑清单已同步, 见 append_pitfall)
- 长文/浏览器任务交付一律走工具落盘+证据, 禁复读系统提示(与 R13/R15 同源)
- headless target=_blank 需新页接管/href 兜底; 百度 A/B 输入控件换层需执行时 DOM 扫描
- 小 VLM 全页编号标注不可靠; 文本 7B 语义选择足够(100%), vision 仅兜底参考

### 全量回归
- P1-P5 各阶段全绿: 812 → 820 → 821(含 telemetry 测试); live 同步 + gateway 重启健康待用户执行
