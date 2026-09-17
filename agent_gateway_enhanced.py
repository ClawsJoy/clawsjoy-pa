#!/usr/bin/env python3
"""ClawsJoy Gateway v6.0 - 精简路由层

设计原则:
- 只做路由、鉴权、限流、日志
- 所有业务逻辑委托给 AgentCortex / lib
- 单一入口: /v5/execute
"""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from core.gateway.archive import _archive_asset, _archive_user_message  # v9_agent_chat 归档依赖
from core.gateway.execute_agent_task import _execute_agent_task, _update_world_model
from core.gateway.message_assembler import _compress_messages
from core.gateway.registry import _init_registries
from core.gateway.sandbox_git import MAX_CONTEXT_TOKENS
from core.gateway.shared_state import *
from core.gateway.shared_state import (  # 状态解耦：删双份后统一归位 shared_state
    _EXECUTION_POLICY_CACHE,
    ALLOWED_COMMANDS,
    _query_cache,
    _retry_cache,
    _session_failed,
)
from core.gateway.state_persist import (
    _load_retrieval_cache,
    _persist_retrieval_cache,
    _persist_state,
    _safe_serialize_state,
)
from core.gateway.write_gate import *
from core.lib.gateway_helpers import _get_sandbox_base
from core.lib.tool_executor import tool_executor

_PROJECT_ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.abspath(__file__)))

# H2 防线修复: H1 提取遗留的漏变量定义（防线抓到）
# _file_retry_state: 大文件重试计数（函数内 get/set, 原无定义 → NameError 被吞）
_file_retry_state = {}
# _task_config: 任务配置默认值（原在 execute_agent_task 模块级, 此处从该模块复用）
from core.gateway.execute_agent_task import _task_config  # noqa: E402

with open(os.path.join(_PROJECT_ROOT, "config/system_config.yaml"), "r") as _f:
    _sys_cfg = yaml.safe_load(_f).get("system", {})
_env_path = _sys_cfg.get("env_file_path", "config/.env")
if not os.path.isabs(_env_path):
    _env_path = os.path.join(_PROJECT_ROOT, _env_path)
load_dotenv(_env_path, override=True)

# 如果 .env 文件没有配置代理，清除 shell 残留的代理
_env_has_proxy = False
with open(_env_path) as _f:
    for _line in _f:
        if _line.startswith("HTTP_PROXY=") or _line.startswith("HTTPS_PROXY="):
            _env_has_proxy = True
            break
if not _env_has_proxy:
    for _k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
        os.environ.pop(_k, None)

import os as _os_check

_DEEPSEEK_KEY_LOADED = _os_check.environ.get("DEEPSEEK_API_KEY", "NOT_FOUND")

import concurrent.futures
import json
import logging
import logging.handlers
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

# ===== 会话级写入追踪器（#166 防假完成：以实际写入记录为准，替代消息扫描）=====
# ===== 会话级 Git 状态追踪器：给 Agent 感知写后提交状态 =====
# ===== #192 失败通道：老板通知函数（追加写入 data/v8/notifications.json，格式与 core/lib/v8/notifications.py 对齐）=====
from core.gateway.sandbox_util import notify_boss

# v9_sandbox_search 文件列表缓存（模块级）
# v9_sandbox_search 空结果熔断（#192）：{session_id: count}，连续 3 次空结果熔断
# 熔断计数归属任务跟踪：{session_id: last_task_id}，task_id 变化时重置计数

# v9 沙箱执行环境白名单：subprocess 仅注入白名单变量，阻断代理/敏感环境变量泄露（#185）
_SANDBOX_ENV = {
    k: v
    for k, v in os.environ.items()
    if k
    in {
        "PATH",
        "HOME",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "PYTHONIOENCODING",
        "PYTHONPATH",
        "TMPDIR",
        "TEMP",
        "TMP",
        "PWD",
        "VIRTUAL_ENV",
        "SYSTEMROOT",
        "USER",
        "LOGNAME",
    }
}
# 统一 heredoc 标记列表（模块级单一定义）：三处使用点共享，取并集（#192）
_HEREDOC_MARKERS = [
    "<< 'PYEOF'",
    '<< "PYEOF"',
    "<< 'EOF'",
    '<< "EOF"',
    "<< 'REGISTER_EOF'",
    "<< 'ENDOFFILE'",
    "<< 'HEREDOC_END'",
    "<<-",
    "<< ",
]

from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS

from core.gateway.shared_state import _guard_log
from core.lib.precision_feed import _init_precision_feed_cache, _load_asset, _precision_feed_cache
from core.lib.sandbox_tools import _generate_project_tree

# ========== 命令分类器 ==========
_READ_CMDS = {
    "cat",
    "head",
    "tail",
    "ls",
    "find",
    "grep",
    "wc",
    "sort",
    "diff",
    "cut",
    "tr",
    "file",
    "stat",
    "which",
    "echo",
    "printf",
    "awk",
    "sed",
    "du",
    "df",
    "free",
    "ps",
    "top",
    "htop",
    "uptime",
    "uname",
    "whoami",
    "id",
    "env",
    "printenv",
    "pwd",
    "date",
    "cal",
    "true",
    "false",
    "test",
    "[",
    "expr",
    "basename",
    "dirname",
    "realpath",
    "readlink",
    "xargs",
    "tee",
}
_WRITE_CMDS = {
    "cp",
    "mv",
    "rm",
    "mkdir",
    "rmdir",
    "touch",
    "chmod",
    "chown",
    "ln",
    "dd",
    "mount",
    "umount",
    "mkfs",
    "tar",
    "zip",
    "unzip",
    "gzip",
    "gunzip",
    "rsync",
    "scp",
    "ssh",
    "systemctl",
    "service",
    "kill",
    "killall",
    "pkill",
    "reboot",
    "shutdown",
    "init",
    "poweroff",
    "halt",
}

import threading as _threading

from core.gateway.os_monitor import _os_event_monitor

_thread = _threading.Thread(target=_os_event_monitor, daemon=True)
_thread.start()
from core.agents.cortex import agent_cortex
from core.lib.auth_middleware import require_auth
from core.lib.error_handler import register_error_handlers
from core.lib.gateway_helpers import (
    _add_project_prefix,
    _auto_correct_path,
    _get_agent_tools,
    _unified_preprocess,
    cleanup_task_context,
)
from core.lib.llm_client import llm_client
from core.lib.performance_middleware import get_perf_stats
from core.lib.rate_limiter import rate_limit, rate_limiter
from core.lib.response_cache import response_cache
from core.lib.safety_guard import set_safe_recursion_limit
from core.lib.unified_config import unified_config
from core.routes.skill_routes import skill_bp

# ========== 蓝图 ==========
# from api.v5 import agents, butler, health  # api/ 目录不存在，已禁用
from web.api.video_studio_api import video_studio_bp
from web.routes import web_bp

set_safe_recursion_limit()

# ========== 日志 ==========
# #80 日志文件化 + 轮转：10MB × 5 备份，保留 stdout 输出
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.handlers.RotatingFileHandler(
            "logs/gateway.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        ),
        logging.StreamHandler(),
    ],
)
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.propagate = False
# ========== Flask ==========
app = Flask(__name__)
# #106 C3：roster 路由注册移到 639 行统一区（此处重复注册已删除）
register_error_handlers(app)
CORS(app)
# GPT-6 阶段0 止血 P0-3/P0-4(2026-09-08): 安全中间件 — 沙箱路由限环回 + 外部强制认证(过渡)
try:
    from core.lib.security_middleware import register_security_middleware

    register_security_middleware(app)
except Exception as _sec_e:
    print(f"[SEC_MW] 安全中间件注册失败(不影响启动): {_sec_e}")

# app.register_blueprint(agents.api_bp, url_prefix="/api/v5")  # api.v5 已禁用
# app.register_blueprint(health.api_bp, url_prefix="/api/v5")  # api.v5 已禁用
# app.register_blueprint(butler.api_bp, url_prefix="/api/v5")  # api.v5 已禁用
from core.routes.system_routes import system_bp

app.register_blueprint(video_studio_bp)
app.register_blueprint(system_bp)
app.register_blueprint(skill_bp)
from core.routes.agent_routes import agent_bp

app.register_blueprint(agent_bp)
app.register_blueprint(web_bp)

# ========== Prometheus（可选） ==========
try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

    request_count = Counter("clawsjoy_requests_total", "Total requests", ["method", "endpoint", "status"])
    request_duration = Histogram("clawsjoy_request_duration_seconds", "Request duration", ["method", "endpoint"])
except ImportError:
    CONTENT_TYPE_LATEST = "text/plain"

    def generate_latest():
        return ""

    request_count = request_duration = None

# ========== Swagger ==========
from flasgger import Swagger

swagger = Swagger(
    app,
    config={
        "headers": [],
        "specs": [{"endpoint": "apispec", "route": "/apispec.json"}],
        "swagger_ui": True,
        "specs_route": "/apidocs/",
    },
)

# ====================================================================
#  核心路由（唯一入口）
# ====================================================================

# ====================================================================
#  基础路由
# ====================================================================


# ====================================================================
#  会话
# ====================================================================

from core.lib.auth_api import AuthManager
from core.lib.session_manager import session_manager

# ====================================================================
#  记忆（委托给 memory_agent）
# ====================================================================


# ====================================================================
#  统计与监控
# ====================================================================


# ====================================================================
#  用户认证
# ====================================================================


auth_manager = AuthManager()


# ====================================================================
#  文件与项目
# ====================================================================


# ====================================================================
#  流式输出（SSE）
# ====================================================================

from core.gateway.context_validator import audit_agent_output
from core.gateway.quota_manager import _check_discuss_token_budget

#  静态文件（P1 已拆到 routes/static.py）
from routes.static import bp as _static_bp

# ====================================================================
#  反馈
# ====================================================================


app.register_blueprint(_static_bp)
from routes.sandbox import bp as _sandbox_bp

app.register_blueprint(_sandbox_bp)
from routes.v5 import bp as _v5_bp

app.register_blueprint(_v5_bp)
from routes.v5_api import bp as _v5_api_bp

app.register_blueprint(_v5_api_bp)


# ========== v8 API：AI劳动力管理 ==========
from core.lib.v8.roster_engine import roster_engine
from core.lib.v8.routes.roster import register_roster_routes

register_roster_routes(app)
from core.lib.v8.routes.billing import register_billing_routes

register_billing_routes(app)
from core.lib.v8.routes.task import register_task_routes

# ========== v8 Task API ==========
from core.lib.v8.task_engine import task_engine

register_task_routes(app)


# ========== v8 Notifications API ==========
from core.lib.v8.notifications import list_notifications, mark_all_read, mark_read, unread_count
from core.lib.v8.routes.v8_misc import register_misc_routes

register_misc_routes(app)

# ====================================================================
#  V9 沙箱 & Agent API
# ====================================================================

from core.context.context_manager import _get_skeleton_by_path, _is_repeat_read_attempt, _is_repeat_read_attempt_v2
from core.gateway.context_validator import (
    _check_recent_writes,
    _classify_task_type,
    _get_task_done_when,
    _is_plan_message,
    _is_readonly_task,
    _planning_output_valid,
    _should_inject_hint,
)
from core.gateway.message_assembler import (
    _calc_token_budget,
    _finalize_messages,
    _hard_truncate_messages,
    _inject_sys_content,
    _tg_estimate,
    _truncate_oversized_messages,
    _validate_messages,
)
from core.gateway.path_utils import (
    _extract_tool_path,
    _format_path_for_agent,
    _normalize_path,
    _resolve_main_repo,
    _resolve_path,
)
from core.gateway.sag_feedback import (
    _build_code_edges,
    _record_path_pattern,
    _update_sag_edge_learning,
    _update_sag_feedback,
)
from core.gateway.sandbox_git import (
    _auto_merge_to_main,
    _git_status,
    _has_git_diff,
    _sandbox_git_post_exec,
    _sandbox_git_post_write,
    _sandbox_git_pre_write,
    _track_git_commit,
)

# #99 修复：write 系列路由注册被错误移进 v9_sandbox_read 函数体内（return 之后永不执行）
# → /v9/sandbox/write 等 4 个路由 404，前端 write_file 全部失败
from core.gateway.sandbox_write import register_write_routes
from core.lib.util import _get_skeletons_by_type

register_write_routes(app)

# 状态解耦：检索/失败/读缓存/连续计数/产物 → 统一由 core.gateway.shared_state 提供（删双份，见 _load_retrieval_cache / state_persist）

# ===== #192 检索缓存持久化：data/v8/retrieval_cache.json =====
_RETRIEVAL_CACHE_FILE = "data/v8/retrieval_cache.json"


from routes.browser import bp as _browser_bp

app.register_blueprint(_browser_bp)
from routes.session import bp as _session_bp

app.register_blueprint(_session_bp)
from routes.audit import bp as _audit_bp

app.register_blueprint(_audit_bp)
from routes.balance import bp as _balance_bp

app.register_blueprint(_balance_bp)
from routes.misc import bp as _misc_bp

app.register_blueprint(_misc_bp)
from routes.files import bp as _files_bp

app.register_blueprint(_files_bp)
from routes.memory import bp as _memory_bp

app.register_blueprint(_memory_bp)
from routes.stats import bp as _stats_bp

app.register_blueprint(_stats_bp)
from routes.task import bp as _task_bp

app.register_blueprint(_task_bp)
from routes.metrics import bp as _metrics_bp

app.register_blueprint(_metrics_bp)
from routes.auth import bp as _auth_bp

app.register_blueprint(_auth_bp)

from core.gateway.message_assembler import _estimate_tokens
from core.gateway.shared_state import _load_v9_execution_policy

_policy = _load_v9_execution_policy()
from core.context.context_manager import _inject_user_history
from core.gateway.approval import (
    _handle_plan_approval,
    _handle_write_approval,
    _resume_bridge_after_approval,
    _v9_handle_approvals,
)
from core.gateway.audit import _record_approval, _record_escalation
from core.gateway.context_validator import _v9_detect_ask

# ===== #104 锚点B：越权拦截（一律拒绝，无审批放行）=====
# 高危系统命令：硬禁止，不提供任何放行
# #106 C2：越权检测移入独立 security 模块（消除 sandbox_ops->agent_gateway 循环依赖）
from core.gateway.security import _SYS_ESCAPE_PATTERNS, _detect_sys_escape, _is_path_escape
from core.gateway.tool_router import _filter_tools_by_mode, _truncate_tool_result_content
from core.gateway.turn_protocol import _write_turn_end
from core.gateway.v9_bridge.context_utils import (
    _v9_ctx_summary,
    _v9_inject_context,
    _v9_is_resume_utterance,
    _v9_keep_old_task,
    _v9_looks_like_new_task,
    _v9_mark_agent_plan,
    _v9_round_checkpoint,
)
from core.gateway.v9_bridge.response_helpers import _build_tool_steps_summary, _goal_info_for_response
from core.gateway.write_gate import _v9_restore_pending_writes


def _v9_bridge_loop(
    messages,
    tools,
    user_id,
    session_id,
    adapter,
    _thinking2=False,
    model=None,
    plan_status=None,
    current_plan=None,
    data=None,
    on_round=None,
):
    """H1 全量提取: 桥接循环(LLM调用+工具执行+门控拦截)。返回 (messages, tool_steps, bridge_exhausted, final_resp, tokens)。final_resp=None=正常结束。

    任务2 流式: on_round(round_no, tool_steps_snapshot, thinking) 每轮与初始回调（供 SSE 实时进度事件）。
    """
    # H1 审核补充: model/plan_status/current_plan 参数化 + _exec_tool_94 函数内 import(原主函数局部)
    from core.gateway.billing import _record_cost_round
    from core.gateway.tool_router import _execute_sandbox_tool as _exec_tool_94
    from core.gateway.v9_bridge.llm_call import call_bridge_llm
    from core.gateway.v9_bridge.loop import _init_bridge_state, _token_water_guard
    from core.gateway.v9_bridge.response_builder import build_bridge_response
    from core.gateway.v9_bridge.response_guard import (
        _budget_limit_guard,
        _normalize_bridge_response,
        _run_response_guard,
    )
    from core.gateway.v9_bridge.round_start import rebuild_context
    from core.gateway.v9_bridge.tool_runner import _commit_results, _run_approval_gate, _run_exec_phase, _run_pre_phase

    _st = _init_bridge_state(
        messages=messages,
        tools=tools,
        user_id=user_id,
        session_id=session_id,
        model=model,
        _thinking2=_thinking2,
        on_round=on_round,
    )
    messages = _st["messages"]
    tokens = _st["tokens"]
    data_resp = _st["data_resp"]
    _is_7b_fallback = _st["_is_7b_fallback"]
    _tool_steps = _st["_tool_steps"]
    _bridge_exhausted = _st["_bridge_exhausted"]
    _task_start_ts = _st["_task_start_ts"]
    _max_total_tools = _st["_max_total_tools"]
    _max_bridge_rounds = _st["_max_bridge_rounds"]
    _water_tok = _st["_water_tok"]
    _no_think = _st["_no_think"]
    _turn_id = _st["_turn_id"]
    _cap_block = _st["_cap_block"]
    # ===== B 块(2026-09-13) 续跑上下文 choke point =====
    # 事故: 预算耗尽轮在下方 _budget_limit_guard 早退(见 479-481) → 跳过
    # persist_session_learning_state(619) 与 build_bridge_response(621) 这两个
    # **唯一**的 .agent_state.json last_task 写入点 → 老板回「继续」时无上下文 → no_context。
    # 放在这里 = 轮循环之前的唯一必经点: 之后任何退出路径(预算耗尽/取消/工具上限/异常/
    # 正常结束)都已经先落盘过 last_task 与 BRIEF.md。
    try:
        from core.gateway.resume_context import ensure_resumable_context as _ensure_rc

        _rc_diag = _ensure_rc(user_id=user_id, session_id=session_id, messages=messages)
        if _rc_diag.get("written") or _rc_diag.get("brief_written"):
            print(
                f"[RESUME_CTX] 已落盘可续跑上下文: src={_rc_diag.get('source')} "
                f"task={str(_rc_diag.get('task'))[:60]!r} brief={_rc_diag.get('brief_written')}"
            )
    except Exception as _rc_e:
        print(f"[RESUME_CTX] 落盘失败(不阻断主流程): {_rc_e}")
    if _cap_block:
        _cap_msg = str(_cap_block.get("error", "当前模式不支持该任务"))
        print(f"[CAPABILITY] 提前拦截: {_cap_msg}")
        return (messages, [], _bridge_exhausted, _cap_block, 0, None, None)
    _guard_paused = False  # P0-2: 守卫暂停标记(连续失败≥8), 终止外层循环
    _cancelled = False  # #1 协作取消标记(POST /v9/cancel 置位, 下轮检查点退出)
    _round_exhausted = False  # P1-1: range(8) 自然耗尽标记(非工具数超限/非守卫暂停)
    _empty_reply_count = 0  # P0: 首轮空回复(无 content 无 tool_calls)重试计数, 最多2次
    _ea_seen = {}  # (2026-09-05) 空参引导计数: (tool, session) -> 连续空参次数
    _bridge_runtime = {}  # S6-D3: 7B/explore/dup/drift/buv/envb/dig/domfail 运行时状态
    _token_water_hit = False  # R1: token 水位触发标记(正常收尾, 非中断)
    _budget_warned80 = False  # L5: 80% 预算预警已发标记(每任务一次)

    def _ts_progress():
        return {
            "done": len(_tool_steps),
            "total": _max_total_tools,
            "step_index": len(_tool_steps),
            "total_steps": _max_total_tools,
        }

    # 批167 · P0-0（执行可靠性门）：**round 级打点必须带 run_id**。
    # 实测根据：并发请求交错时，用「行窗口」切分归因会把 A 请求的 LLM_RETURN 划给 B 请求
    # ⇒ 造出「round 0 看起来卡死」的假象（历史 44 例里 **23 例**的窗口内根本没有本请求的 LLM_START；
    #   其中被判「真挂」的那 1 例，其 LLM_START 就落在窗口之外）。带 run_id 后可机械归因，不靠窗口。
    # 批170 修正：run_id **必须与 SessionLog 落盘同源**（canonical turn 游标）。
    # 批167 用的是 gateway 自己的 epoch 型 _turn_id ⇒ 打点是 ⟪session:1789432222⟫，
    # 而落盘是 ⟪session:1⟫ ⇒ run_chain 取到 0 条事件（P0-1「每步 run_id 证据」不成立）。
    # 这里每次打印时**现取**（而不是循环前算一次），避免 turn_start 尚未落盘时取到 :0。
    def _p0_rid():
        try:
            from core.gateway.run_id import canonical_run_id as _p0_cr

            return _p0_cr(session_id)
        except Exception as _p0_rid_e:
            return "?(打点异常: %s)" % _p0_rid_e

    print("[ROUND] 循环开始 max_rounds=%s run_id=%s" % (_max_bridge_rounds, _p0_rid()), flush=True)
    for _bridge_round in range(_max_bridge_rounds):
        print("[ROUND] round %d 开始 run_id=%s" % (_bridge_round, _p0_rid()), flush=True)
        messages = rebuild_context(
            messages=messages,
            tools=tools,
            user_id=user_id,
            session_id=session_id,
            model=model,
            is_7b_fallback=_is_7b_fallback,
        )
        # #1 协作取消: 每轮 LLM 调用前检查(不硬杀, 标记后下轮退出)
        from core.gateway.shared_state import is_cancel_requested

        if is_cancel_requested(session_id):
            print(f"[CANCEL] 协作取消请求, 退出 session={session_id}")
            _cancelled = True
            _bridge_exhausted = True
            break
        # #2 运行时上下文投影: 策略快照变化才追加(持久 user 消息, 轮起始位安全)
        try:
            from core.gateway.context_projection import project_runtime_context, render_policy_snapshot

            _snap_ctx = render_policy_snapshot(
                user_id,
                session_id,
                {
                    "write_pending": bool(_pending_writes.get(session_id)),
                    "plan_pending": bool(_plan_pending.get(session_id)),
                },
            )
            _ctx_txt = project_runtime_context(session_id, _snap_ctx)
            if _ctx_txt:
                print(f"[CTX_PROJECT] 注入运行时快照({len(_ctx_txt)}字)")
                # 基准修复: role=system(非 user) — 守卫/任务分类/验证链只扫描 user 消息,
                # 快照含"修改/写入"等词曾误判全部读任务为修改任务 → 读工具全被拒
                messages.append({"role": "system", "content": _ctx_txt})
                try:
                    from core.gateway.session_log import log_event as _log_ctx

                    _log_ctx(
                        session_id, "user_message", {"role": "system", "content": _ctx_txt, "source": "runtime_context"}
                    )
                except Exception:
                    pass
        except Exception:
            pass
        # Turn 协议 Step2: step_start(每轮 LLM 调用前)
        try:
            from core.gateway.session_log import log_event as _log_step

            _step_id = _bridge_round + 1
            from core.gateway.turn_protocol import write_step_start as _ws_start

            _ws_start(session_id, _turn_id, _step_id, round_no=_bridge_round)
        except Exception:
            pass
        # P0 费用保护: max_tokens 动态(普通 4000, thinking 8000)
        _mt_out = 8000 if _thinking2 else 4000
        print("[ROUND] round %d 进入 LLM 调用前 run_id=%s" % (_bridge_round, _p0_rid()), flush=True)
        # 批153 · P0-1 打点：LLM_START / LLM_RETURN **带 run_id**（不用手工放标记即可归因）。
        # 判据：同一 run_id 下 START 有、RETURN 无 ⇒ 断在 LLM 调用；两者都有但无后续 [ROUND] ⇒ 断在循环推进。
        # 批170 修正：这里原来用 gateway 自己的 epoch 型 _turn_id 拼 run_id（⟪session:1789432554⟫），
        # 与 round 级打点、SessionLog 落盘的 canonical run_id（⟪session:1⟫）**不同源**
        # ⇒ run_chain 按打点 run_id 取到 0 条事件。统一改为 canonical（同一出口 _p0_rid()）。
        try:
            _p01_rid = _p0_rid()
            print(
                "[LLM_START] run_id=%s round=%d model=%s mt_out=%s"
                % (_p01_rid, _bridge_round, getattr(adapter, "model", "?"), _mt_out),
                flush=True,
            )
        except Exception as _p01e:
            _p01_rid = ""
            print("[LLM_START] run_id=? round=%d (打点异常: %s)" % (_bridge_round, _p01e), flush=True)
        import time as _p01_t

        _p01_t0 = _p01_t.time()
        resp, _is_7b_fallback = call_bridge_llm(
            messages=messages,
            tools=tools,
            user_id=user_id,
            session_id=session_id,
            adapter=adapter,
            mt_out=_mt_out,
            thinking2=_thinking2,
            no_think=_no_think,
            bridge_round=_bridge_round,
            is_7b_fallback=_is_7b_fallback,
            daily_cost_exceeded=globals().get("_v9_daily_cost_exceeded"),
            last_7b_result=globals().get("_7b_last_result", ""),
            data=data,
        )
        print(
            "[ROUND] round %d LLM 返回 success=%s err=%s run_id=%s"
            % (_bridge_round, resp.get("success"), str(resp.get("error"))[:120], _p0_rid()),
            flush=True,
        )
        # 批153 · P0-1 打点（配 LLM_START）：返回侧带 run_id + 耗时 + 成功/错误
        try:
            print(
                "[LLM_RETURN] run_id=%s round=%d ok=%s elapsed=%.2fs err=%s"
                % (
                    _p01_rid,
                    _bridge_round,
                    bool(resp.get("success")),
                    _p01_t.time() - _p01_t0,
                    str(resp.get("error") or "")[:120],
                ),
                flush=True,
            )
        except Exception:
            print("[LLM_RETURN] run_id=? round=%d ok=%s" % (_bridge_round, bool(resp.get("success"))), flush=True)
        # PROBE_20260914_004(批108): 判「LLM 返回了内容但 tool_calls 为空」是否成立
        _llm_tcs_n = -1
        _llm_content = ""
        try:
            _llm_msg = (((resp.get("data") or {}).get("choices") or [{}])[0] or {}).get("message") or {}
            _llm_tcs_n = len(_llm_msg.get("tool_calls") or [])
            _llm_content = str(_llm_msg.get("content") or "")
        except Exception as _pr_e:
            print("[ROUND] round %d LLM 返回 tool_calls 解析失败: %s" % (_bridge_round, str(_pr_e)[:80]), flush=True)
        print(
            "[ROUND] round %d LLM 返回 tool_calls=%d content_len=%d content_head=%s"
            % (_bridge_round, _llm_tcs_n, len(_llm_content), _llm_content[:120]),
            flush=True,
        )
        if not resp.get("success"):
            _write_turn_end(
                session_id, _turn_id, tokens, "error", str(resp.get("error", "API错误"))[:200], len(_tool_steps)
            )
            return (
                messages,
                _tool_steps,
                _bridge_exhausted,
                {
                    "success": False,
                    "error": resp.get("error", "API错误"),
                    "reason": "error",
                    "reason_detail": str(resp.get("error", "API错误"))[:200],
                },
                tokens,
                None,
                None,
            )
        print("[ROUND] round %d tool_calls=%d 为空则收尾 / 非空则进入工具阶段" % (_bridge_round, _llm_tcs_n), flush=True)
        data_resp = resp["data"]
        tokens += resp.get("tokens", 0)
        # #18 P0: 每轮 usage 明细日志(治费用不明) — input/output/reasoning/cache
        try:
            _ud = resp.get("usage_detail") or {}
            print(
                f"[TOKEN_LOG] round={_bridge_round} model={getattr(adapter, 'model', '?')} "
                f"input={_ud.get('input',0)} output={_ud.get('output',0)} "
                f"reasoning={_ud.get('reasoning',0)} cache={_ud.get('cache',0)} "
                f"total={_ud.get('total', resp.get('tokens',0))} 累计={tokens}"
            )
        except Exception:
            pass
        _bl = _budget_limit_guard(
            tokens=tokens,
            messages=messages,
            adapter=adapter,
            user_id=user_id,
            session_id=session_id,
            tool_steps=_tool_steps,
            turn_id=_turn_id,
            bridge_exhausted=_bridge_exhausted,
            progress_fn=_ts_progress,
            goal_info_fn=_goal_info_for_response,
            write_turn_end_fn=_write_turn_end,
        )
        if _bl is not None:
            return _bl
        _bmsg, _btool_calls = _normalize_bridge_response(data_resp=data_resp, session_id=session_id)
        _resp = _run_response_guard(
            messages=messages,
            data_resp=data_resp,
            bmsg=_bmsg,
            btool_calls=_btool_calls,
            session_id=session_id,
            bridge_round=_bridge_round,
            turn_id=_turn_id,
            tokens=tokens,
            tool_steps=_tool_steps,
            bridge_exhausted=_bridge_exhausted,
            empty_reply_count=_empty_reply_count,
            no_think=_no_think,
            detect_ask_fn=_v9_detect_ask,
            is_plan_message_fn=_is_plan_message,
            ctx_summary_fn=_v9_ctx_summary,
            write_turn_end_fn=_write_turn_end,
            ts_progress_fn=_ts_progress,
            goal_info_fn=_goal_info_for_response,
            plan_pending=_plan_pending,
            user_id=user_id,
        )
        if _resp["final_resp"] is not None:
            # 批175（假失败根因的另一半）：本循环的返回契约是 **7 元组**，
            # 此前这里直接 `return _resp["final_resp"]`（返回载荷 dict）⇒ make_stream_response 解包
            # `_m2, _ts2, _bex2, _fr2, _tk2, _r2, _rd2 = _bo` 抛
            # ValueError: too many values to unpack (expected 7)（实测 run_id=pa175_ask_probe2:1）。
            # 两处（守卫返回契约 + 本行）必须同时正确，ask/plan_pending 才能正常收尾。
            return (messages, _tool_steps, _bridge_exhausted, _resp["final_resp"], tokens, None, None)
        _empty_reply_count = _resp["empty_reply_count"]
        _no_think = _resp["no_think"]
        if _resp["empty_retry"]:
            continue
        # 2026-09-13 完成核验未过 → 回灌失败原因续跑（与 empty_retry 同构）
        if _resp.get("verification_retry"):
            continue
        if _resp["normal_complete"]:
            _bridge_exhausted = False  # #103 O1：正常结束（未跑满）
            break
        _pre_items, _pre_terminal, _pre_wp_list = _run_pre_phase(
            btool_calls=_btool_calls,
            bmsg=_bmsg,
            messages=messages,
            session_id=session_id,
            user_id=user_id,
            bridge_round=_bridge_round,
            ea_seen=_ea_seen,
        )
        _exec_results, _exec_cancelled = _run_exec_phase(
            pre_items=_pre_items, session_id=session_id, user_id=user_id, exec_tool_fn=_exec_tool_94
        )
        if _exec_cancelled:
            _cancelled = True
            _bridge_exhausted = True
            break
        _commit = _commit_results(
            pre_items=_pre_items,
            exec_results=_exec_results,
            messages=messages,
            bmsg=_bmsg,
            session_id=session_id,
            user_id=user_id,
            bridge_round=_bridge_round,
            turn_id=_turn_id,
            tokens=tokens,
            tool_steps=_tool_steps,
            bridge_exhausted=_bridge_exhausted,
            is_7b_fallback=_is_7b_fallback,
            runtime=_bridge_runtime,
            write_turn_end_fn=_write_turn_end,
            truncate_fn=_truncate_tool_result_content,
        )
        _bridge_exhausted = _commit["bridge_exhausted"]
        globals()["_7b_last_result"] = _bridge_runtime.get("_7b_last_result", "")
        globals()["_7b_fail_streak"] = _bridge_runtime.get("_7b_fail_streak", 0)
        if _commit["sevenb_fail"]:
            return (
                messages,
                _tool_steps,
                _bridge_exhausted,
                {"success": False, "error": "7B 降级模型连续失败，已停止", "reason": "error"},
                tokens,
                None,
                None,
            )
        _approval = _run_approval_gate(
            pre_terminal=_pre_terminal,
            pre_wp_list=_pre_wp_list,
            guard_paused=_guard_paused,
            messages=messages,
            bmsg=_bmsg,
            data_resp=data_resp,
            session_id=session_id,
            user_id=user_id,
            bridge_round=_bridge_round,
            turn_id=_turn_id,
            tokens=tokens,
            tool_steps=_tool_steps,
            bridge_exhausted=_bridge_exhausted,
            progress_fn=_ts_progress,
            goal_info_fn=_goal_info_for_response,
            write_turn_end_fn=_write_turn_end,
            pending_cleanup_fn=_pending_cleanup,
            record_escalation_fn=_record_escalation,
        )
        if _approval is not None:
            return _approval
        # #1 协作取消: 每轮工具执行后检查(取消在下一轮生效)
        if is_cancel_requested(session_id):
            print(f"[CANCEL] 每轮工具后取消检查, 退出 session={session_id}")
            _cancelled = True
            _bridge_exhausted = True
            break
        # P0-2: 守卫暂停 → 终止外层循环
        if _guard_paused:
            break
        # #21 总工具数硬上限: 累计超限 → 注入收敛提示 + 强制结束循环
        if len(_tool_steps) >= _max_total_tools:
            _bmsg["content"] = (_bmsg.get("content") or "") + (
                f"\n\n[系统] 工具调用总数已达上限 {_max_total_tools}，强制结束本轮。请收敛操作，优先确认已完成的关键写入。" if _bmsg.get("content") else ""
            )
            print(f"[TOOL_BUDGET] 总工具数 {len(_tool_steps)} 达上限 {_max_total_tools}, 强制结束循环")
            # #8 审计告警: 执行预算超限 → 通知老板
            try:
                from core.gateway.sandbox_util import notify_boss

                notify_boss(
                    event_type="budget_limit",
                    message=f"V9 工具预算超限({len(_tool_steps)}/{_max_total_tools})",
                    detail=f"session={session_id} turn_id={_turn_id} 已强制结束循环",
                    level="warn",
                )
            except Exception:
                pass
            _bridge_exhausted = True  # P0-1: 超限即耗尽, 前端按 bridge_exhausted break(不再 continue 重发)
            break
        messages = _validate_messages(messages)
        # 任务2 流式: 每轮循环结束回调（实时进度事件）
        if on_round is not None:
            try:
                on_round(_bridge_round, list(_tool_steps), str(_bmsg.get("content", ""))[:300])
            except Exception:
                pass
        # Turn 协议 Step2: step_end(每轮工具执行后)
        try:
            from core.gateway.session_log import log_event as _log_step_e
            from core.gateway.turn_protocol import write_step_end as _ws_end

            _ws_end(session_id, _turn_id, _bridge_round + 1)
        except Exception:
            pass
        # R1 token 水位检查 → loop.py _token_water_guard（S6-E 归位）
        _twg = _token_water_guard(tokens=tokens, water_tok=_water_tok, budget_warned80=_budget_warned80, bmsg=_bmsg)
        _budget_warned80 = _twg["budget_warned80"]
        if _twg["token_water_hit"]:
            _token_water_hit = True
            _bridge_exhausted = False  # 正常收尾(非耗尽/非中断)
            break
    else:
        # R1(2026-08-30): 轮次护栏耗尽(防失控上限, 默认 100 轮) — 注入收敛指令, 让 LLM 基于现有信息汇报
        _bridge_exhausted = True
        _round_exhausted = True
    # #1 协作取消: 置 fallback data_resp(后续 msg/防截断/元认知等段都访问 data_resp, 防 None 崩溃)
    if _cancelled and not data_resp:
        data_resp = {
            "choices": [{"message": {"content": "[系统] 任务已取消（协作取消）。", "role": "assistant"}, "finish_reason": "stop"}]
        }
        _bmsg = data_resp["choices"][0].get("message", {})
    # 防虚假完成拦截（S5 归位 completion_guard.run_completion_guard）
    from core.gateway.completion_guard import run_completion_guard

    messages = run_completion_guard(messages=messages, data_resp=data_resp, session_id=session_id, cancelled=_cancelled)
    # 输出防截断：检测 finish_reason == "length" 并重试(#1 协作取消: data_resp 可能为 None)
    if data_resp and data_resp.get("choices", [{}])[0].get("finish_reason") == "length":
        _first_content = data_resp["choices"][0]["message"]["content"]
        messages.append({"role": "assistant", "content": data_resp["choices"][0]["message"].get("content", "")})
        messages.append({"role": "system", "content": "你的上一条回复被截断了，请从中断处直接继续输出，不要重复已输出的内容。"})
        # [TOKEN_GUARD] V9 API 调用前 Token 硬截断（复用 core/lib/llm_client.py _tg_estimate 逻辑）
        _tg_before = _tg_estimate(messages, tools)
        if _tg_before > _calc_token_budget(model, tools) * 0.9:
            _tg_sys = [m for m in messages if m.get("role") == "system"][:2]
            _tg_tail = messages[-4:]
            _tg_summary = {"role": "system", "content": "【上下文摘要】中间消息已被强制截断，保留前 2 条 system 与最近 4 条消息。"}
            messages = _tg_sys + [_tg_summary] + _tg_tail
            if _tg_estimate(messages, tools) > _calc_token_budget(model, tools):
                for _m in messages:
                    if _m.get("role") == "system" and len(str(_m.get("content", "") or "")) > 5000:
                        _m["content"] = str(_m["content"])[:5000]
            _guard_log(
                "TOKEN_GUARD", f"[TOKEN_GUARD] 强制截断：{_tg_before} → {_tg_estimate(messages, tools)}", "token_guard.log"
            )
        # 唯一出口: 截断后必须过配对+结构修复(此前漏网 → 孤立 tool/缺 type → DeepSeek 400)
        messages = _finalize_messages(messages)
        # 降本修复: retry 路径同样压缩
        try:
            # 修(2026-09-13): 此处曾一并 import _tg_estimate/_calc_token_budget —— 函数内 import 会把这两个
            # 名字变成 _v9_bridge_loop 的**局部名**，导致上方 line 572 的 TOKEN_GUARD 分支抛
            # UnboundLocalError（只在 finish_reason=="length" 即长输出被截断时触发，短任务永不触发）。
            # 两者在模块级 line 284 已 import，这里不再重复导入。
            from core.gateway.message_assembler import _compress_messages

            if _tg_estimate(messages, tools) > _calc_token_budget(model, tools) * 0.8:
                messages = _compress_messages(messages, user_id, session_id, keep=8)
                messages = _finalize_messages(messages)
        except Exception:
            pass
        resp_retry = adapter.execute_with_tools(
            messages=messages,
            tools=tools,
            user_id=user_id,
            temperature=0.7,
            max_tokens=_mt_out,
            thinking=(_thinking2 and not _no_think),
        )
        if resp_retry.get("success"):
            data_resp["choices"][0]["message"]["content"] = (
                _first_content + resp_retry["data"]["choices"][0]["message"]["content"]
            )
            tokens += resp_retry.get("tokens", 0)
    _today_cost, _today_cost_day, _daily_cost_exceeded = _record_cost_round(
        tokens=tokens,
        model=model,
        user_id=user_id,
        today_cost=globals().get("_v9_today_cost", 0.0),
        today_cost_day=globals().get("_v9_today_cost_day", ""),
        daily_cost_exceeded=globals().get("_v9_daily_cost_exceeded", False),
    )
    globals()["_v9_today_cost"] = _today_cost
    globals()["_v9_today_cost_day"] = _today_cost_day
    globals()["_v9_daily_cost_exceeded"] = _daily_cost_exceeded

    # ===== 元认知审查（复用 Metacognition + GLM）=====
    from core.gateway.v9_bridge.metacognition_runner import run_metacognition_review

    meta_state = run_metacognition_review(messages=messages, user_id=user_id, session_id=session_id)
    # ===== 元认知审查结束 =====

    # ===== 学习能力：持久化会话状态 =====
    from core.gateway.memory import persist_session_learning_state

    state = persist_session_learning_state(
        messages=messages,
        user_id=user_id,
        session_id=session_id,
        tokens=tokens,
        _task_start_ts=_task_start_ts,
        meta_state=meta_state,
    )
    # ===== 学习能力结束 =====
    return build_bridge_response(
        messages=messages,
        data_resp=data_resp,
        session_id=session_id,
        user_id=user_id,
        tokens=tokens,
        tool_steps=_tool_steps,
        bridge_exhausted=_bridge_exhausted,
        round_exhausted=_round_exhausted,
        guard_paused=_guard_paused,
        cancelled=_cancelled,
        empty_reply_count=_empty_reply_count,
        bmsg=_bmsg,
        turn_id=_turn_id,
        current_plan=current_plan,
        plan_status=plan_status,
        data=data,
        file_retry_state=_file_retry_state,
        policy=_policy,
        build_tool_steps_summary_fn=_build_tool_steps_summary,
        goal_info_fn=_goal_info_for_response,
        write_turn_end_fn=_write_turn_end,
        ts_progress_fn=_ts_progress,
    )


# P3-B: /v9/agent/chat 已迁 routes/v9_chat.py（编排下沉 entry.py + 注入式注册）
from routes.v9_chat import register as _register_v9_chat

_register_v9_chat(
    app,
    bridge_loop_fn=_v9_bridge_loop,
    allowed_commands=ALLOWED_COMMANDS,
    max_context_tokens=MAX_CONTEXT_TOKENS,
    deepseek_key_loaded=_DEEPSEEK_KEY_LOADED,
    resolve_session_id_fn=_resolve_v9_session_id,
)


# ====================================================================
#  启动
# ====================================================================


# ========== PA 服务层接线 (2026-09-10, 最小侵入) ==========
# 把 core.pa 的画像/账本/会话/分派 暴露为 /v9/pa/*; 失败不影响主流程。
try:
    from core.pa.gateway_routes import llm_brain as _pa_llm_brain
    from core.pa.gateway_routes import register_pa_routes as _register_pa_routes

    _register_pa_routes(app, brain=_pa_llm_brain())
    print("[PA] /v9/pa/* 路由已挂载 (画像/账本/会话/分派 + LLM 脑)")
except Exception as _e_pa_wire:
    print("[PA] 路由挂载失败(不影响主流程): %s" % _e_pa_wire)

if __name__ == "__main__":
    from core.gateway.boot import run_gateway_startup

    run_gateway_startup(app)
