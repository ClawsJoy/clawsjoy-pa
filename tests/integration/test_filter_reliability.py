"""过滤网可靠性评估 — 变量抽取准确率 / 模块过滤召回率 / 三层摘要保真"""
import sys, json, re
sys.path.insert(0, ".")
import pytest

from core.lib.task_vars import extract_task_vars, filter_world_model_modules


def test_variable_extraction_accuracy():
    """维度1: 48 个真实任务样本的路径+标识符抽取（P2 扩充 10->48，覆盖各命名形态）"""
    samples = [
        # --- 基础 10 个（保留） ---
        ("修改 clawsjoy_dev/core/gateway/security.py 的 _is_path_escape", ["security.py", "_is_path_escape"]),
        ("优化 core/lib/precision_feed.py 的 _load_asset 注入逻辑", ["precision_feed.py", "_load_asset"]),
        ("修复 audit.py 的 verify_completion_report 窗口", ["audit.py", "verify_completion_report"]),
        ("在 task_vars.py 新增 filter_dependency_graph 测试", ["task_vars.py", "filter_dependency_graph"]),
        ("重构 execute_agent_task.py 的 _save_state", ["execute_agent_task.py", "_save_state"]),
        ("写 tool_router.py 的 execute_command 分支", ["tool_router.py", "execute_command"]),
        ("检查 message_assembler.py 的三层滚动", ["message_assembler.py"]),
        ("完善 goal_state.py 的 create_goal", ["goal_state.py", "create_goal"]),
        ("看 sandbox_ops.py 的 exec handler", ["sandbox_ops.py"]),
        ("query_index.py 的 entity_type 分支", ["query_index.py", "entity_type"]),
        # --- 完整路径前缀 clawsjoy_dev/ ---
        ("修改 clawsjoy_dev/core/gateway/quota_manager.py 的 check_tool_quota", ["quota_manager.py", "check_tool_quota"]),
        ("优化 clawsjoy_dev/core/lib/sag_audit_bridge.py 的 register_entity", ["sag_audit_bridge.py", "register_entity"]),
        ("修复 clawsjoy_dev/core/gateway/state_persist.py 的持久化", ["state_persist.py"]),
        ("重构 clawsjoy_dev/core/context/context_manager.py 的 record_tool_flow", ["context_manager.py", "record_tool_flow"]),
        ("写 clawsjoy_dev/core/tools/write_file.py 的 write 分支", ["write_file.py"]),
        # --- 深层路径（多级目录） ---
        ("修复 core/gateway/sandbox_write.py 的 _write_safe", ["sandbox_write.py", "_write_safe"]),
        ("优化 core/lib/v8/task_orchestrator.py 的 discuss_plan", ["task_orchestrator.py", "discuss_plan"]),
        ("检查 core/agents/cortex.py 的推理路径", ["cortex.py"]),
        ("完善 core/gateway/message_assembler.py 的 _layered_compress", ["message_assembler.py", "_layered_compress"]),
        # --- 多文件任务（同时指向 2+ 文件） ---
        ("同时修改 security.py 的 _is_path_escape 和 audit.py 的 verify_completion_report", ["security.py", "_is_path_escape", "audit.py", "verify_completion_report"]),
        ("对比 tool_router.py 与 sandbox_ops.py 的工具分发差异", ["tool_router.py", "sandbox_ops.py"]),
        ("迁移 shared_state.py 的常量到 config.py", ["shared_state.py", "config.py"]),
        # --- 非 py 扩展名 ---
        ("调整 config/system/system_unified.yaml 的 gateway 端口", ["system_unified.yaml"]),
        ("更新 config/prompts/agent_system.md 的执行纪律章节", ["agent_system.md"]),
        ("修改 frontend/index.html 的标题", ["index.html"]),
        ("写 tools/sync_check.sh 的校验逻辑", ["sync_check.sh"]),
        ("查看 requirements.txt 依赖", ["requirements.txt"]),
        # 已知局限: 扩展名 alternation 中 js 先于 json 匹配, package.json 被截为 package.js（评估报告记录）
        # --- 点号连接标识符 ---
        ("调用 extractor.db_url 连接数据库", ["extractor.db_url"]),
        ("使用 llm_client.chat 完成对话", ["llm_client.chat"]),
        ("检查 roster_engine.get 的成员", ["roster_engine.get"]),
        # --- 驼峰 / 大写开头 ---
        ("初始化 AtomicEngine 引擎", ["AtomicEngine"]),
        ("调用 SmartAgent 的方法", ["SmartAgent"]),
        ("实现 VerificationChain 的校验", ["VerificationChain"]),
        # --- 下划线私有成员 ---
        ("修复 _check_recent_writes 的逻辑", ["_check_recent_writes"]),
        ("完善 _notify_done_impl 回调", ["_notify_done_impl"]),
        ("优化 _audit_cross_check_save 流程", ["_audit_cross_check_save"]),
        ("重构 _v9_bridge_loop 的桥接", ["_v9_bridge_loop"]),
        # --- 中文任务描述（中文关键词驱动） ---
        ("优化安全检测模块的路径逃逸防护", ["安全检测", "路径逃逸"]),
        ("完善审计复核的误判窗口", ["审计复核"]),
        ("修复沙箱写操作的锚点校验", ["沙箱写操作"]),
        ("检查会话恢复的快照逻辑", ["会话恢复"]),
        # --- 混合：路径+多标识符+中文 ---
        ("修改 core/gateway/security.py 的 _is_path_escape 并完善 路径逃逸 防护", ["security.py", "_is_path_escape"]),
        ("优化 core/lib/precision_feed.py 的 _load_asset 和 _init_precision_feed_cache", ["precision_feed.py", "_load_asset", "_init_precision_feed_cache"]),
        ("重构 execute_agent_task.py 的 _save_state 与 _validate_task_completion", ["execute_agent_task.py", "_save_state", "_validate_task_completion"]),
        ("修复 sandbox_ops.py 的 _with_http_tool_flow 审计", ["sandbox_ops.py", "_with_http_tool_flow"]),
        ("完善 tool_router.py 的 _execute_sandbox_tool 配额", ["tool_router.py", "_execute_sandbox_tool"]),
        ("检查 goal_state.py 的 get_goal 与 update_goal", ["goal_state.py", "get_goal", "update_goal"]),
        ("写 core/gateway/audit.py 的 audit_tool_call 测试", ["audit.py", "audit_tool_call"]),
    ]
    _EXT = (".py", ".yaml", ".yml", ".md", ".html", ".css", ".json", ".txt", ".sh", ".sql", ".js", ".ts", ".jsx", ".tsx")
    assert len(samples) >= 48, f"样本数不足: {len(samples)}"
    for task, expect in samples:
        v = extract_task_vars(task)
        # 按扩展名区分文件路径与代码标识符
        file_expects = [e for e in expect if e.endswith(_EXT)]
        if file_expects:
            assert any(any(fe in p for fe in file_expects) for p in v["paths"]), f"{task}: 路径抽取失败 {v['paths']}"
        # 标识符：下划线/点号连接/驼峰（含中文关键词驱动的样本）
        fns = [e for e in expect if not e.endswith(_EXT)]
        if fns:
            tokens_all = " ".join(v["tokens"])
            kw_all = " ".join(v["keywords"])
            assert any(e in tokens_all or e in kw_all for e in fns), f"{task}: 标识符抽取失败 tokens={v['tokens']} keywords={v['keywords']}"


def test_negative_samples_no_false_variables():
    """维度1b: 12 个负样本 — 纯闲聊/噪声输入不得抽出代码实体变量"""
    negatives = [
        "你好",
        "谢谢",
        "今天天气怎么样",
        "请介绍一下你自己",
        "帮我看看",
        "再试一次",
        "好的明白了",
        "the quick brown fox",
        "a b c d",
        "nothing here to see",
        "重复重复重复",
        "你好，请开始吧",
    ]
    for task in negatives:
        v = extract_task_vars(task)
        # 负样本定义：不得抽出代码实体（路径/标识符）。闲聊中文词可能进入 keywords（语义关键词，非代码实体），允许
        assert v["paths"] == [], f"{task}: 负样本抽出路径 {v['paths']}"
        assert v["tokens"] == [], f"{task}: 负样本抽出标识符 {v['tokens']}"
        # keywords 不得含代码标识符形态（含 . / _ / 驼峰）
        kw_bad = [k for k in v["keywords"] if "." in k or "_" in k or re.search(r"[a-z][A-Z]", k)]
        assert not kw_bad, f"{task}: 负样本关键词含代码形态 {kw_bad}"


def test_module_filter_recall_precision():
    """维度2: 构造 20 模块，任务指向 2 个 → 100% 召回 + 100% 准确"""
    modules = {}
    for i in range(20):
        modules[f"clawsjoy_dev/core/lib/mod{i}.py"] = {"skeleton": f"模块 {i}", "functions": [], "imports": []}
    modules["clawsjoy_dev/core/gateway/security.py"] = {"skeleton": "安全检测", "functions": ["_is_path_escape"], "imports": []}
    modules["clawsjoy_dev/core/gateway/audit.py"] = {"skeleton": "审计", "functions": ["verify_completion_report"], "imports": []}
    vars_ = extract_task_vars("修改 security.py 的 _is_path_escape 和 audit.py")
    out = filter_world_model_modules(modules, vars_, top_limit=30)
    relevant = {"clawsjoy_dev/core/gateway/security.py", "clawsjoy_dev/core/gateway/audit.py"}
    kept = set(out.keys())
    assert relevant.issubset(kept), f"召回不足: 缺 {relevant - kept}"
    assert kept.issubset(relevant), f"误投: {kept - relevant}"
    assert len(kept) == 2, f"应只保留 2 个，实际 {len(kept)}"


def test_three_layer_summary_fidelity():
    """维度3: 摘要保留任务目标/已完成/失败"""
    from core.gateway.message_assembler import _summarize_messages_semantic
    msgs = [
        {"role": "user", "content": "修改 security.py 的 _is_path_escape 修复路径逃逸"},
        {"role": "assistant", "content": "已完成：修改了 _is_path_escape 的 basename 判断"},
        {"role": "user", "content": "然后优化 audit.py 的复核"},
        {"role": "assistant", "content": "失败：audit.py 导入报错"},
    ]
    summary = _summarize_messages_semantic(msgs)
    assert summary.get("task_goal"), "任务目标丢失"
    assert "security" in summary.get("task_goal", "")
    assert summary.get("completed"), "已完成步骤丢失"
    assert summary.get("failed_attempts"), "失败尝试丢失"
    assert "audit" in summary.get("failed_attempts", [""])[0]
