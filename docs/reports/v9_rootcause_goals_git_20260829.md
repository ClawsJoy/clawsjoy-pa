# V9 核心问题根因报告（2026-08-29，未改代码）

---

## 问题 1：88 个 active goal 堆积（用户报 45，实测 88）

### 根因：total=160 的完成判定永远达不到

**数据实证**（列出目录 goal）：
```
objective: 列出当前目录的文件
status: active   注意: 任务已完成但永不全
progress: {done: 11, total: 160, pct: 7}
history: done 0 到 11 [turn... tools11]   11 个工具后正常结束
```

**机制**：
1. 无 plan 任务创建 goal 时：total = max_total_tools(32) × goal_max_turns(5) = 160（L5330-5335）
2. 完成判定（L2639-2641）：reason==completed AND done >= total(160) 才 complete_goal
3. 简单任务（列出目录）实际 11 个工具完成：11 < 160 永不 complete

**两条路径收敛不一致**：
| 路径 | 完成判定 | 结果 |
|---|---|---|
| 流式 v9_agent_chat 到 bridge_loop | done >= total(160) | 简单任务达不到, active 堆积 |
| 同步路径(L3983) | 完成即 complete_goal | 正常收敛 |

**时间分布**：08-19 到 08-29 跨 10 天（26 个列出目录 + 6 个三处改动 + 6 个推广 + 4 个简报 + 4 个列出/tmp）

**结论**：设计缺陷 — total 是工具预算上限误当完成标准。简单任务总工具数远小于 160 永远 active。

**修复建议**（不改代码）:
- 完成判定改为：reason==completed 且无待执行工具 则 complete（不依赖 done>=total）
- 或：无 plan 任务 total 设为动态（如 min(实际工具数+1, 160)）
- 或：失败/中断路径（reason=error/paused/budget_limit）goal 置 failed 或 archived
- 存量清理：批量把 done>=1 且无 plan 的 active goal 置 complete

---

## 问题 2：GIT commit 失败 ×3（13:18-13:19）

### 根因：submodule 映射损坏（clawsjoy-ai-extension）

**数据实证**：
```
$ git ls-files -s clawsjoy-ai-extension
160000 601ea64...  clawsjoy-ai-extension   gitlink(submodule 指针)
$ cat .gitmodules
(无)                                        映射缺失!
$ git submodule status
fatal: no submodule mapping found in .gitmodules for path 'clawsjoy-ai-extension'
```

**机制**：
1. clawsjoy-ai-extension 在 git 里是 gitlink（历史提交把它当 submodule 管理）
2. .gitmodules 和 .git/modules/ 都不存在（迁移/复制时丢失）
3. 该路径现在有真实文件: git status 显示 m（submodule 内容变更）
4. _sandbox_git_post_exec（execute_command 后）git add -A + git commit: 无 submodule 映射导致 commit 报 Changes not staged 返回非 0: [GIT] commit 失败: （stderr 空，错误在 stdout）

**项目历史影响**：
- gitlink 指向固定 commit（601ea64），目录内真实文件从未被主仓库跟踪
- 若 gitlink 目标 repo 丢失，文件无法从 git 恢复（但磁盘上当前存在）
- 3 次失败在 13:18-13:19（execute_command 后自动提交）— 非致命（文件已写磁盘），但自动提交静默失败

**修复建议**（不改代码）:
- 恢复 .gitmodules: git submodule add <url> clawsjoy-ai-extension（需原 repo URL）
- 或降级为普通目录: git rm --cached clawsjoy-ai-extension + git add（把目录纳入主仓库跟踪）— 推荐，本地扩展目录非独立 repo
- sandbox_git 增强: commit 失败时打印 stdout（当前只打 stderr）— 诊断性改进

---

## 结论

| 问题 | 类型 | 严重度 | 影响 |
|---|---|---|---|
| goal 堆积 | 设计缺陷（total 误用）| 高 | 88 个 active goal 永久堆积, 内存+状态污染 |
| GIT commit 失败 | 配置损坏（submodule 映射缺失）| 中 | 自动提交静默失败, 文件未纳入 git 历史 |---

# 修复实施验证（2026-08-29 同日完成）

## 修复 1：goal 完成判定（已完成 + 存量清理）

**代码修复**（agent_gateway_enhanced.py L2637-2651，_write_turn_end）：
- reason==completed 且 goal 为 active/paused → 无条件 complete_goal（不再依赖 done>=total）
- reason in (error, paused, budget_limit, max_tokens) 且 active → update_goal_status failed（不再永久堆积）
- 标记日志: [GOAL_FIX] completed 置 complete / {reason} 置 failed
- 已同步 live（/home/flybo/clawsjoy_v5/agent_gateway_enhanced.py，diff 仅此 18 行，语法 OK）
**语义修正**（同日 2nd pass，回归测试暴露边界问题）：
- 初版把 max_tokens/paused 也置 failed → 前端自动续跑依赖 goal_active(L730) 被杀 → 多轮任务断裂
- 修正后：max_tokens/paused 保持原状态(可续跑); 仅 error/budget_limit → failed; completed 含 failed 翻转
- 测试: test_goal_multiturn 8 passed; test_turn_end_associates_goal/attaches_goal 通过


**存量清理**（跨 session 全部路径）：
- 第一次：workspace 嵌套 goals 484 个 → failed
- 第二次：workspace os.walk 44 个 → failed（部分被 except:pass 吞掉，未真正落盘）
- 第三次（定位）：live 目录 /home/flybo/clawsjoy_v5/data/projects/ 下 44 个跨 session active（user-mt0q7ws8-*、ext-integration、zhihu-test、bili_calib_* 等）→ 全部 failed + archive_note
- **验证：REMAINING active: 0**（全量扫描 live + workspace）

> 关键教训：之前两次清理的 cwd 在 workspace，os.walk('data/projects') 只扫到 workspace 嵌套路径；
> 真正的 44 个在 live 目录（sandbox 只读挂载），写入被 Errno 30 拒绝且被 except:pass 静默吞掉。

## 修复 2：submodule 降级（已完成 + 验证）

**workspace 仓库**（session_1783388196051/clawsjoy_dev，即报错仓库）：
- git rm -r --cached clawsjoy-ai-extension（移除 gitlink 160000）
- rm -rf clawsjoy-ai-extension/.git（移除嵌套仓库，否则 git add 仍视为 embedded repo）
- git add clawsjoy-ai-extension（47 个文件纳入跟踪，与 live 一致）
- commit e2b93a2；验证：git ls-files -s 无 160000 条目

**sandbox_git.py 修复**（L69/L141/L147）：
- [GIT] add 失败 / commit 失败 日志改为同时打印 stdout + stderr
- 原因：git commit 失败（Changes not staged + untracked content）错误全部在 stdout，旧代码只打 stderr → 日志恒空
- 已同步 live + 语法 OK + workspace commit a092afc

**根因复现**（/tmp 独立仓库模拟）：gitlink + untracked content + 无 .gitmodules
- git add -A rc=0（静默）
- git commit rc=1，stdout 含 "Changes not staged... modified: sub (untracked content)"，stderr 空
- → 确认旧日志恒空的原因，确认修复有效

**遗留说明**：live 主仓库仍有 SadTalker gitlink（160000 cd4c0465，2.6GB 模型权重目录，.gitmodules 缺失）。
**未降级**——它是外部模型仓库，降级会把权重提交进 git（不建议）；如需要可补 .gitmodules 恢复 submodule 管理。
