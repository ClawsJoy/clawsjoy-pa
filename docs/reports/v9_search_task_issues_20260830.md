# 深挖任务第三轮卡死分析（2026-08-30）

> 任务: "深挖 Claude 训练原文"
> 现象: Agent 用 web_search 但结果质量差 → 反复 browse/fetch 失败(内网误判/连接重置)
>       → 第 4 轮目标丢失("任务目标只有一句 hi") → 用户取消。
> 前两轮修复(F1 tmp免审批 / F2 漂移检测 / web_search 工具 / 递归key / tmp相似度)已生效:
>   日志中 data/tmp 写不再审批/不再相似度拒, web_search 可用, 无 decode 脚本死胡同。

---

## 本轮新暴露的问题

### W1【高】web_search 结果质量差 → Agent 反复试错浪费预算
- Bing RSS 对中文新闻 query 索引差: 实测"Claude 训练 AI 研究员"返回日文汽车网站
- Agent 日志自述 "Bing 质量太差（已知问题）"
- 后果: Agent 拿垃圾结果 browse/fetch → 连接失败(Connection reset/SSL EOF) → 3 轮预算耗尽
- 根因: web_search 只支持单 query, 无"站点限定/更精确/重试"能力; 中文新闻索引弱

### W2【中】browse_web/fetch_web "localhost/内网地址不允许访问" 误判
- 日志: browse_web 被拦 4 次, fetch_web 被拦 2 次, 都是 "localhost/内网地址"
- 根因: _is_private_host 对**解析失败返回 True(保守拒绝)**(L1307-1308) —
  若 Agent 传入的 URL hostname 为空/相对/畸形, 或目标站 DNS 临时失败 → 误判内网
- 叠加: web_search 返回的某些 URL 可能带 tracking 参数解析异常

### W3【高】目标丢失 — goal_context_injection 只注入 active goal
- 日志第 4 轮: Agent 说"任务目标只有一句 hi", 读 .agent_state.json/BRIEF.md 找目标
- 根因: goal_context_injection(L227) 要求 status=active; 深挖任务经用户多次取消/继续,
  goal 状态可能被 _write_turn_end 置 failed/complete, 或用户"hi"消息触发 create_goal 归档旧目标
- 后果: Agent 完全丢失任务上下文, 退化为通用聊天

---

## 根本性解决方案

### F-W1: web_search 增强
- 支持 site: 限定(自动加 site:新浪/量子位 等新闻站)
- query 质量提示: 返回结果为空/全不相关时, 提示用更精确标题短语
- 多源 fallback: Bing RSS 失败 → 尝试 Bing HTML(带重定向解码) 或 直接 fetch 新闻站搜索 API

### F-W2: _is_private_host 不因解析失败误判
- 解析失败不再返回 True(内网), 而是返回 False + 让上层用 HTTP 层 SSRF 兜底
- 或: browse_web/fetch_web 在 _is_private_host 前先验证 URL 合法性(hostname 非空/无异常字符)

### F-W3: goal 上下文增强
- goal_context_injection 不限于 active: 最近一个 goal(不论状态) 也注入 "最近目标(可能已中断)"
- 或: 用户消息含"继续"时, 恢复最近非 complete 的 goal objective

---

## 实施范围(本轮)
W3(目标丢失, 最严重) + W2(内网误判) 优先; W1(搜索质量) 需要换搜索源, 单独评估。
