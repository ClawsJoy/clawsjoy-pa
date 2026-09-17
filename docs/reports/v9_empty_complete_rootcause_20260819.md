# V9 直接完成无输出 根因报告

- 日期: 2026-08-19
- 方式: 只读排查 + 实机复现(沙箱网关 stream 请求)
- 证据源: 复现 run(sess_rc3, 13 工具) + 代码路径逐段核对 + 前端渲染分支分析

---

## 一、结论速览

| 现象 | 根因 | 严重度 |
|---|---|---|
| 检查项目状态 → 0/16 → ✅ 任务完成, 无工具调用, 无输出内容 | bridge_loop 首轮 LLM 返回空消息(无 content 无 tool_calls) → 正常 break(_bridge_exhausted=False) → done payload message={} 空对象 → 前端 msg.content 空不渲染 + msg.tool_calls 空 → 打 ✅ 任务完成 | 高 |
| 收敛指令(P1-1)误触发? | 否 — P1-1 只在 8 轮耗尽时触发(本次复现 rc3 确认正常), 且收敛指令不进 session_log 不污染后续请求 | 排除 |
| 前端收到 done 直接 break 没显示 message? | 部分 — 若 message 为空对象则确实无内容可显示; 若 message 有 content 则正常显示 | 部分成立 |

---

## 二、根因链(逐条对照)

### 排查1: bridge_loop 是否执行工具循环?
- **取决于 LLM 首轮返回**。若首轮返回 tool_calls(如 rc3 复现: 13 工具), 则正常执行 8 轮。
- 若首轮返回 **空 content + 空 tool_calls**(API 异常/上下文不足/模型判断无需工具), 则:
  - L1952 `if not _btool_calls:` → L1953 `_bridge_exhausted = False` → break(正常结束)
  - **for-else 不触发**(break 跳过 else), `_round_exhausted` 保持 False(正确)
  - done payload: `_loop_data2` 找最后一条 assistant 且 content 非空 → 若全空 → **None**
  - `data.choices[0].message = {}` 空对象

### 排查2: _round_exhausted 是否首轮被置位?
- **否**。for-else 仅在循环完整跑完 8 轮(无任何 break)时触发。首轮 break 会跳过 else。
- 实测验证: `_sim([1]*8)=True`, `_sim([1,1,0])=False`(中途 break 不触发)。

### 排查3: 最终 message 有内容但前端没渲染?
- **分两种情况**
  - message 有 content: 前端 L1541 `if (msg.content) agentLog('🤖 '+content)` 正常渲染。
  - message 为空对象 `{}`(首轮空回复): L1541 跳过, L1571 `!msg.tool_calls` → 打 ✅ 任务完成 → break。**无输出内容**。

### 排查4: ✅ 任务完成 出现在哪一层?
- **前端 agentLog(L1578/L2100)**, 不是后端。后端只在 `_resp_content` 含 '✅ 任务完成' 时做假完成拦截(L2097), 但首轮空回复不走该路径。

---

## 三、实机复现验证

### 复现 A: 正常耗尽(rc3, 13 工具)
```
events: 11 (start + 9 progress + done)
done: exh=True, tc=0, content='...已达轮次上限，请基于现有信息输出评...'
session_log: 13 tool_call, 7 assistant 轮次
```
- 结论: P1-1 收敛指令在此场景**正确工作**, 不是误触发。

### 复现 B: 首轮空回复(理论路径, 代码级确认)
```
LLM 返回 {'content':'', 'tool_calls':[]}
→ L1952 not _btool_calls → break, _bridge_exhausted=False
→ _loop_data2=None (无 assistant content)
→ done payload: data.choices[0].message = {}
→ 前端: msg.content 空(不渲染) + msg.tool_calls 空 → '✅ 任务完成' + break
→ 用户看到: 0/16 → ✅ 任务完成, 无输出
```

---

## 四、为什么之前能完成(hello.txt)现在不能?

| 场景 | 首轮 LLM 行为 | 结果 |
|---|---|---|
| hello.txt 受控任务 | 明确写文件指令 → 首轮就 tool_calls | 正常执行 |
| 检查项目状态(自由任务) | 开放任务 → 模型可能首轮给空回复/或预加载上下文不足 | 0/16 直接完成 |

开放任务首轮空回复概率更高: 无明确指令时模型倾向'无需工具/直接回答', 但回答内容又为空(推理型模型 thinking 模式 content 可能延迟或为空)。

---

## 五、修复方案建议

### P0: 首轮空回复 → 重试而非直接完成
bridge_loop 在 `not _btool_calls` 且 `not _bmsg.get('content')`(首轮空回复)时, 不直接 break:
- 追加一次重试: 注入 '[系统] 请基于任务给出具体分析或工具调用' 后 continue。
- 或: 返回 `_final_resp = {success:True, status:'need_more', message:'模型未产出内容, 请重试'}` 供前端提示。

### P1: done payload 空 message 防护
- `_loop_data2` 为 None 时, 用最后一条 user 消息或显式提示填充, 避免前端拿到空对象直接判完成。

### P2: 前端 msg 为空时不给 ✅ 任务完成
- `if (!msg.tool_calls && !msg.content) { agentLog('⚠️ 模型无输出, 请重试'); continue; }` 而非直接判完成。

---

## 六、排除项(用户怀疑但非根因)

| 怀疑 | 结论 |
|---|---|
| P1-1 收敛指令误触发 | 排除 — for-else 仅 8 轮耗尽触发, rc3 实测正常 |
| P0-1 _bridge_exhausted=True 误设 | 排除 — 首轮空回复路径设 False(正确), 仅超限/耗尽设 True |
| 收敛指令污染后续请求 | 排除 — 收敛指令不进 session_log(只改内存 messages), derive_messages 无污染 |
| 前端 break 没显示 | 部分 — 空 message 时确实无内容可显示, 是症状而非根因 |

核心根因: **首轮 LLM 空回复(无 content 无 tool_calls)被当作正常完成, 前端对空 message 直接判 ✅ 任务完成**。
