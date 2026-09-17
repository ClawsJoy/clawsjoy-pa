# V9 断点1 排查报告 — PROJECT_TREE 为空(len=0)

- 日期: 2026-08-19
- 范围: 断点1 路径认知 — bridge_loop 启动时注入项目结构树(PROJECT_TREE len=0)

---

## 一、根因

`core/lib/sandbox_tools.py::_generate_project_tree()` 扫描的根目录是 **会话沙箱**:

```python
_base = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev")
```

而该目录是**每会话新建的空工作目录**(只含 goals/、data/v8/、.agent_state.json 等会话产物),
**不含项目源码**(BRIEF.md、core/、config/、data/ 都在网关工作区 = 项目根)。

→ 新会话首轮扫描 `_paths` 为空 → `if not _paths: return ""` → **PROJECT_TREE len=0**,
Agent 完全不知道项目结构, 基准测试 T1/T3 因"文件不存在"失败。

**证据**:
- 网关日志: `[PROJECT_TREE] len=111/119/0/107` — 新会话(len=0), 老会话(沙箱已有产物)非 0
- 沙箱内容: `data/projects/bench/base_T1/clawsjoy_dev/` = goals/ + data/v8/ + .agent_state.json (无 core/config/BRIEF.md)
- 项目根: 网关 CWD = `_PROJECT_ROOT` = `os.path.dirname(agent_gateway_enhanced.py)` (含 BRIEF.md/core/config)

## 二、修复

`_generate_project_tree` 改为扫描**项目根**(本模块 core/lib/ → 上三级, 与网关 _PROJECT_ROOT 同源):

1. **根目录**: 会话沙箱 → 项目根 `Path(__file__).resolve().parent.parent.parent`
2. **顶层登记**: `iterdir()` 先登记全部顶层目录/文件(摘要模式完整性, 不依赖 rglob 顺序), 目录单独收集
3. **有界扫描**: rglob 上限 800 路径; `data/` 只登记顶层名(防 data/projects 海量 session 文件膨胀)
4. **摘要模式**: >50 文件 → "顶层目录 + 顶层入口文件 + 项目规模"(注入体积 ≤ ~600 字符); 跳过逐文件
   meta(行数/函数)计算 — 旧实现会对每个 .py 全量读文件(大项目每次请求全量扫描, 慢)

修复后输出示例:
```
clawsjoy_dev/
 顶层目录: agents, config, core, data, docs, tests, tools, web, ...
 顶层入口文件: agent_gateway_enhanced.py, ...
项目规模: 801 文件, 354 Python 文件, 1 个 Agent
```

## 三、验证

| 项 | 结果 |
|---|---|
| 树非空 | len 0 → **415**, 含 core/config/data ✓ |
| 生成耗时 | 0.13s(旧实现大项目会全量读 .py, 数秒级) ✓ |
| 实机注入 | `[PROJECT_TREE] len=415`(网关重启后每次请求) ✓ |
| 回归测试 | 新增 tests/unit/test_project_tree.py(非空+核心目录+有界+快速), 12 相关测试通过 |

## 四、残余缺口(独立于树注入)

树注入后 Agent **知道** core/config/data 在哪, 但 **read_file/list_dir 仍把相对路径解析到会话沙箱**
(空目录) → "文件不存在"。即: 认知已通, **访问未通**。

- T1: read_file('clawsjoy_dev/BRIEF.md') → 沙箱内无 → 探索后 max_tokens
- T3: read_file('core/gateway/session_log.py') → 沙箱内无 → 探索后 max_tokens

**下一步建议**: 沙箱路径映射(read/list/search 对项目路径回退到项目根, 或沙箱根与项目根关联)。
这是断点1的"另一半", 也直接影响断点3边界验证的完成度 — 建议与断点2一起实施。
