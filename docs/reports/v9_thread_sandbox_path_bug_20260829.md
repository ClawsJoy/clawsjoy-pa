---

# 线程沙箱文件路径 bug 检查报告（2026-08-29）

## 现象
- 线程(子任务)里的文件会保存到线程外 / V9 Agent 访问不到跨线程文件 / 之前清理发现 128 个分叉文件

## 路径解析链
1. V9 沙箱根: _get_sandbox_base(uid, sid) = data/projects/{uid}/{sid}/clawsjoy_dev（相对路径, 依赖 cwd）
2. 工具执行: _execute_sandbox_tool(tool, args, uid, sid, sandbox_base=None) → base = sandbox_base or _get_sandbox_base()
3. 子任务: subtask_executor._run → sandbox_base=.../clawsjoy_dev/subtasks/{tid}/ 传入 _execute_agent_task
4. execute_agent_task L1431 正确传 sandbox_base=_sb_task3（async 路径 OK）
5. 路径归一化: _resolve_path(base, path) → _normalize_path(..., base_override=base) 剥离 clawsjoy_dev/ 前缀后拼回 base

## 发现的 Bug（已修复）
### Bug 1: subtasks/{tid} 双重嵌套（文件写错位置但仍在线程内）
- LLM 在子任务里写路径常带 subtasks/{tid}（从 system prompt 得知目录存在）
- 旧逻辑只剥 clawsjoy_dev/ 前缀 → subtasks/{tid} 保留 → 拼回 sub_base → subtasks/{tid}/subtasks/{tid}/xxx
- 实测: data/projects/{uid}/{sid}/clawsjoy_dev/subtasks/taskA/subtasks/taskA/result.md

### Bug 2: 主沙箱绝对路径被重定向进子任务（跨线程文件读不到）
- 子任务里写 data/projects/{uid}/{sid}/clawsjoy_dev/shared.md → 被归一化进子任务目录
- 跨线程(主线程↔子任务)无法共享文件

## 修复（path_utils.py）
- 新增 _subtask_offset(base): 识别 base 的 subtasks/{tid} 偏移段
- _normalize_path + _resolve_path 双向对齐: 路径含 subtasks/{tid} → 剥该段拼回 base（防双重嵌套）
- 显式指向主沙箱的绝对路径(不含当前 subtask 段) → 保持指向主沙箱（跨线程读写可用）
- 精确段匹配: subtasks/taskA/ 或 endswith, 防 taskAB 误命中 taskA

## 验证
- 新增 test_file_isolation_fix.py 7 项（相对路径/带subtasks绝对路径/主沙箱/临时目录/主沙箱不受影响/相似名不误判）
- 全量回归 652 passed（原 641 + 11）
- 已同步 live + 网关重启
- 清理残留: 4 个双重嵌套分叉文件(subtest 测试遗留)移到正确位置, 0 分叉文件残留

## 跨线程访问现状
- 修复后: 子任务内相对路径 → 子任务沙箱; 显式主沙箱绝对路径 → 主沙箱（可读写共享文件）
- 隔离仍保留: 子任务默认写自己的 subtasks/{tid}/ 目录, 不污染主线程

,---,,# 审核修复（2nd pass）,,## 问题: _resolve_path 与 _normalize_path 的 subtask 对齐条件不一致,,**现象**: 指向其他子任务(如 taskAB)的路径, 落点取决于写法:,- abs 写法(走 _normalize_path) → clawsjoy_dev/subtasks/taskAB/x.md (正确),- clawsjoy_dev/ 或裸 subtasks/ 写法(走 _resolve_path L93) → subtasks/taskA/subtasks/taskAB/x.md (双重嵌套),,**根因**: _resolve_path L93 分支只处理"命中当前 _off_sub"的情况;,subtasks/ 开头但指向其他子任务时错误拼回 base(双重嵌套), 而 _normalize_path 判定为主沙箱。,,**修复**: _resolve_path L93 分支加一致性分支 —,路径以 subtasks/ 开头但非当前 _off_sub → 解析到主沙箱(与 _normalize_path 行为对齐);,主沙箱根从 base 推导(去掉 /subtasks/{tid} 段, 因 _resolve_path 无 uid/sid 参数)。,,**验证**: 三种写法(taskAB abs/clawsjoy_dev/bare)落点一致; taskA 仍对齐 sub_base;,主沙箱绝对路径/主沙箱base/tmp 均不回归; 新增测试 test_subtask_other_sibling_consistent;,全量回归 653 passed; 已同步 live + 网关重启。,
