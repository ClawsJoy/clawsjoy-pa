# V9 工作区浏览器验证报告（2026-08-15）

验证方式：Playwright headless Chromium 打开 workbench.html，预置 localStorage（user_id=web_1783219071801, session_id=1783388196051），输入框输入任务后点击执行，观察前端终端/文件树 + 后端 tool_flow/文件落盘。

## 一、验证结论

| 验证项 | 结果 |
|---|---|
| 从零写入新文件 vfy_web2.py | 通过，18s 完成，5 项 checklist 全过 |
| 文件落盘 | core/lib/vfy_web2.py 含 greet() 返回 Hello Web2 |
| 工具执行 | read_file → write_file → execute_command(py_compile+import+assert) → git 提交 |
| tool_flow 记录 | 7 条 |
| 前端反馈 | 终端逐条显示、文件树更新、任务完成 |
| 假完成拦截 | 空工作区假宣告被 VerificationChain 正确拦截 |

## 二、浏览器验证暴露的问题（已修复）

### #96 _seen KeyError → 前端误报服务不可用
现象：任务实际完成但前端显示 (_seen)。根因：execute_command/sandbox_write 用 setdefault(session_id, {}) 初始化 tracker 缺 _seen/write_count 键，防假完成判定访问 _trk[_seen] 抛 KeyError。修复：commit 6a37984。

### #97 insert_agent_action TypeError (capability_chain)
现象：日志 [AGENT_ACTION] 采集失败 capability_chain unexpected keyword。根因：record_step 传参但签名缺失。修复：commit dc34439。

### #98 write_file 父目录缺失 ENOENT
现象：agent 报告首次 write_file 路径异常报错，切换 heredoc 成功。根因：完整写入前未 mkdir 父目录。修复：commit f9af01b。

### #99 write 系列路由 404
现象：前端 write_file 调 /v9/sandbox/write 三次全 404。根因：f419eb5 重构把 register_write_routes(app) 错误移进 v9_sandbox_read 函数体 return 之后（永不执行）。修复：commit 6a46323。

### #100 write_file 传 Path 给 _sandbox_git_post_write → endswith AttributeError
现象：write_file 完整写入报 'PosixPath' object has no attribute 'endswith'，agent 每次被迫绕 heredoc。根因：write_file.py 完整写入分支传 target(Path) 给 _sandbox_git_post_write（内部 filepath.endswith），且 base/filepath 拼接双重。修复：commit f67e9cc 改传相对路径。

## 三、行为规范 / OS 问题观察（浏览器视角）

### O1. 前端双重执行架构风险（未触发，待评估）
后端 v9_agent_chat 桥接循环（8 轮）已执行工具；前端 agentSend 拿到返回消息若仍带 tool_calls 会再执行一遍。正常路径无重复；风险场景为桥接 8 轮跑满仍有 tool_calls 时。

### O2. 空工作区探测行为
首任务空工作区 agent 先探测可能假宣告，被 VerificationChain 拦截后第二次才写入；前端只见服务不可用（被 #96 掩盖）。

### O3. 会话依赖 localStorage 预置
浏览器新会话无预置会新建随机 session 看不到既有工作区；对老板观察既有 session 不友好。

### O4. 错误信息语义
后端异常 str(e) 直接透传前端（如 '_seen'），建议网关层转友好错误码 + 详情分离。

## 四、待办
- 重启网关加载 #98（sandbox 无法启动 live：chromadb 只读）
- 评估 O1 双重执行
- 评估 O3 workbench session 切换 UI
- O4 统一异常格式
