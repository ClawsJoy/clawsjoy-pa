# -*- coding: utf-8 -*-
"""守卫顺序注册表 — 精确复现现状执行顺序(见 p1_guard_pluginization_plan.md §3.2)。

注册表是守卫挂载的唯一定义: 顺序 = 列表顺序(order 字段同步)。
P1 S1 只建骨架(占位守卫), S2+ 逐个实现并接线。

顺序设计(现状 bridge/exec/tool_router 内联逻辑的合并序):
  pre-execute(可拒绝, 短路):
    10  quota          G9  配额(最先 — 资源保护)
    20  mode           G10 模式
    30  forced_tool    G11 强制工具校验
    40  forbidden      G12+G13 §4.1/§4.2/§4.3 禁则
    50  escape         G2+G3 锚点B 路径/命令越权
    60  plan           G4  计划确认(状态机透传) — 先于写审批(复现 bridge_loop 原顺序 G2→锚点A)
    70  approval       G1  锚点A 写审批(状态机透传)
    80  recursion      G7  递归暂停(状态机透传)
    85  web_fetch      G13 网络抓取同 URL 递归(≤3, 防反复抓同一页面)
  post-execute(观察, 不短路):
    100 reminder       G6  重复工具提醒
    110 audit          G15 审计+tool_flow
    120 failure_pause  G14 连续失败计数

注: 子任务 scope 挂载时 exclude approval/plan(审批差异由作用域表达)。
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from core.gateway.guards.base import EVENT_POST_EXECUTE, EVENT_PRE_EXECUTE, ToolGuard
from core.os.plugin import V9Plugin

# ===== 守卫类占位(S1 骨架 — 均继承 ToolGuard, check 返回 None=放行) =====
# S2+ 逐个实现真实逻辑; 占位阶段挂载零副作用, 不接任何现有守卫。


class QuotaGuard(ToolGuard):
    """G9 配额检查 — 与 tool_router._execute_sandbox_tool 内联逻辑逐字一致。

    payload 需含: tool/args/user_id/session_id
    原逻辑(§#236): session 未初始化配额 → init_quota; check_tool_quota 超限 → 拒绝。
    """

    name = "quota_guard"
    event = EVENT_PRE_EXECUTE

    def check(self, payload):
        tool = payload.get("tool", "")
        session_id = payload.get("session_id", "")
        if not tool or not session_id:
            return None
        import core.gateway.quota_manager as _qm
        from core.gateway.quota_manager import check_tool_quota, init_quota

        if session_id not in _qm._quota_table:
            init_quota(session_id)
        _allowed, _rem, _sug = check_tool_quota(tool, session_id)
        if not _allowed:
            return ToolGuard.deny(_sug, status="quota_exhausted", error={"error": _sug, "quota_exhausted": True})
        return None


class ModeGuard(ToolGuard):
    """G10 模式检查 — 与 tool_router 内联逻辑逐字一致。

    payload 需含: tool/session_id/messages
    原逻辑(P1-1): minimal 模式禁用 list_dir/search_files/query_index。
    """

    name = "mode_guard"
    event = EVENT_PRE_EXECUTE

    def check(self, payload):
        tool = payload.get("tool", "")
        session_id = payload.get("session_id", "")
        messages = payload.get("messages") or []
        if tool not in ("list_dir", "search_files", "query_index"):
            return None
        from core.gateway.quota_manager import get_mode, get_mode_tools

        # 取真实用户任务(跳过 [系统] 注入上下文, 防快照/steer 误分类模式)
        from core.lib.gateway_helpers import last_user_task_msg

        _task_hint = last_user_task_msg(messages)
        _mode = get_mode(session_id, _task_hint)
        _mode_tools = get_mode_tools(session_id, _task_hint)
        if tool not in _mode_tools:
            # 2026-08-30: 主消息直接列可用工具(Agent 只看主消息, 不看 hint → 反复重试被拒工具浪费预算)
            _mode_list = "、".join(_mode_tools)
            _main_msg = f"当前模式不支持该工具 {tool}({_mode} 模式)，可用工具: {_mode_list}。请改用其中的工具，不要重复尝试被拒工具。"
            return ToolGuard.deny(
                _main_msg,
                status="mode_limited",
                mode=_mode,
                hint=f"当前任务处于 {_mode} 模式，仅开放: {_mode_list}",
                error={"error": _main_msg, "mode": _mode, "hint": f"当前任务处于 {_mode} 模式，仅开放: {_mode_list}"},
            )
        return None


class ForcedToolGuard(ToolGuard):
    """G11 强制工具校验 — 与 tool_router 内联逻辑逐字一致。

    payload 需含: tool/messages
    2026-08-30 根本修复: 读工具**永不禁用**。
    原逻辑"用户消息含修改词 + 调读工具 → 拒绝"是反模式 —
    1) "完善/总结/复盘"等文档词被误判为代码修改(日志: "总结不完善点"→ list_dir/read_file 全被拒)
    2) Agent 读文件是必要前置, 强制"直接写"只会让它用 execute_command awk/cat 绕行(预算 5 倍消耗)
    写保护已有: 写文件走 write_file 审批卡 / execute_command 写命令审批, 无需禁读。
    """

    name = "forced_tool_guard"
    event = EVENT_PRE_EXECUTE

    def check(self, payload):
        # 读工具永远放行 — 见类 docstring(2026-08-30 根本修复)
        return None


class ForbiddenGuard(ToolGuard):
    """G12+G13 禁则硬约束 — §4.1/§4.2/§4.3 合并(与 tool_router/write_file 内联逐字一致)。

    payload 需含: tool/args/messages
      §4.1 execute_command: 禁止 _*.py 临时/测试脚本(_tmp_/_gate_/_vfy/vfy_/_fix)
      §4.3 execute_command: 禁止 open(path,'w') 直写(需含 clawsjoy_dev/)
      §4.2 write_file:     禁止写共享配置文件(filter_net/.agent_state/dependency_graph/
                           retrieval_cache/skill_registry_v2)
    """

    name = "forbidden_guard"
    event = EVENT_PRE_EXECUTE

    _CONFIG_FILES = (
        "filter_net.json",
        ".agent_state.json",
        "dependency_graph.json",
        "retrieval_cache.json",
        "skill_registry_v2.json",
        "permission.json",
    )

    def check(self, payload):
        tool = payload.get("tool", "")
        args = payload.get("args") or {}
        if tool == "execute_command":
            import re as _re_forbid

            _cmd_t = str(args.get("command", "")) or ""
            # 修复: 只拦"执行临时脚本"(python/bash/node + 临时名 + 脚本后缀), 读/引用临时文件不拦
            _tmp_run = _re_forbid.search(
                r"(?:^|[\s;&|])(?:python3?|bash|sh|node)\s+[^\s;&|]*(?:_tmp_|_gate_|_vfy|vfy_|_fix)[^\s;&|]*\.(?:py|js|sh)\b",
                _cmd_t,
            )
            if _tmp_run:
                return ToolGuard.deny(
                    "禁止执行含「临时/测试脚本名」的脚本（_*.py 禁则，见 agent_manual §4.1）。请检查是否误用了测试文件。",
                    status="forbidden",
                    error={
                        "error": "禁止执行含「临时/测试脚本名」的脚本（_*.py 禁则，见 agent_manual §4.1）。请检查是否误用了测试文件。",
                        "forbidden": True,
                    },
                )
            if _re_forbid.search(r"open\([^)]*['\"]w['\"]", _cmd_t) and "clawsjoy_dev/" in _cmd_t:
                return ToolGuard.deny(
                    "禁止用 open(path,'w') 直接写沙箱文件（agent_manual §4.3）。所有写操作必须走 write_file（锚点A 确认）。",
                    status="forbidden",
                    error={
                        "error": "禁止用 open(path,'w') 直接写沙箱文件（agent_manual §4.3）。所有写操作必须走 write_file（锚点A 确认）。",
                        "forbidden": True,
                    },
                )
            return None
        if tool == "write_file":
            _w_path = str(args.get("path", "") or "")
            _w_base = _w_path.split("/")[-1]
            if _w_base in self._CONFIG_FILES:
                return ToolGuard.deny(
                    f"禁止 write_file 直接写共享配置文件 {_w_base}（agent_manual §4.2）。这些文件由系统管理，需改配置请走系统接口或说明理由请求人工处理。",
                    status="forbidden",
                    error={
                        "error": f"禁止 write_file 直接写共享配置文件 {_w_base}（agent_manual §4.2）。这些文件由系统管理，需改配置请走系统接口或说明理由请求人工处理。",
                        "forbidden": True,
                    },
                )
        return None


class EscapeGuard(ToolGuard):
    """G2+G3 锚点B 越权拦截 — 与 bridge_loop 内联逻辑逐字一致。

    payload 需含: tool/args/session_id/sandbox_base
      G2 路径越权: write_file/write_large/edit_file 的 path 逃逸沙箱(_is_path_escape)
      G3 高危命令: execute_command 触发 _SYS_ESCAPE_PATTERNS(_detect_sys_escape)
    返回 status="escalation_blocked", blocked 结构供调用方透传前端。
    """

    name = "escape_guard"
    event = EVENT_PRE_EXECUTE

    _WRITE_TOOLS = ("write_file",)  # 2026-08-24: 对齐 _TOOL_REGISTRY(edit_file/write_large 未注册, 拦截后确认执行必失败)

    def check(self, payload):
        tool = payload.get("tool", "")
        args = payload.get("args") or {}
        sandbox_base = payload.get("sandbox_base")
        # G2: 路径越权(写类工具)
        if tool in self._WRITE_TOOLS:
            _path = str(args.get("path", "") or "")
            if sandbox_base is not None:
                from core.gateway.security import _is_path_escape

                _esc = _is_path_escape(str(sandbox_base), _path)
            else:
                _esc = False
            if _esc:
                return ToolGuard.deny(
                    "路径越权，已被拦截",
                    status="escalation_blocked",
                    blocked={"tool": tool, "path": _path, "reason": "路径越权"},
                    error={"error": "路径越权，已被拦截", "escalated": True},
                    escalated=True,
                )
        # G3: 高危命令(execute_command)
        if tool == "execute_command":
            from core.gateway.security import _detect_sys_escape

            _cmd = str(args.get("command", "") or "")
            _esc_cmd = _detect_sys_escape(_cmd)
            if _esc_cmd:
                return ToolGuard.deny(
                    f"高危命令被拦截: {_esc_cmd[1]}",
                    status="escalation_blocked",
                    blocked={"tool": tool, "command": _cmd[:200], "reason": _esc_cmd[1]},
                    error={"error": f"高危命令被拦截: {_esc_cmd[1]}", "escalated": True},
                    escalated=True,
                )
        # 断点2: 读工具路径越权 — 只读白名单(沙箱/会话目录/项目根)外(如 /etc/passwd) → 立即拦截
        if tool in ("read_file", "list_dir", "search_files"):
            from core.gateway.security import _is_read_path_escape

            _rpath = str(args.get("path", "") or ".")
            # Q1(2026-09-05): data/vault 镜像不存在 → 直接引导 obsidian_knowledge(不触发审批, 不浪费轮次)
            _vault_mirror = _rpath.startswith(("data/vault", "vault/")) or "/data/vault/" in _rpath
            if _vault_mirror:
                return ToolGuard.deny(
                    "data/vault 不存在：Obsidian 第二大脑没有沙箱镜像，只能经 obsidian_knowledge 访问。"
                    "请用 obsidian_knowledge（action=read/search/update_sop/append_pitfall/write_note，见工具说明）读知识库，"
                    "不要用 read_file 读 data/vault。",
                    blocked={"tool": tool, "path": _rpath, "reason": "vault 镜像不存在"},
                    error={"error": "Obsidian vault 无沙箱镜像(data/vault 不存在)，请用 obsidian_knowledge 工具访问"},
                )
            if sandbox_base is not None and _is_read_path_escape(sandbox_base, _rpath):
                # 2026-08-30: Obsidian vault 路径(/mnt/d/...) → 引导用 obsidian_knowledge(read)
                # (Agent 反复用 read_file 读 vault 被拦, 却不知正确工具 → 浪费多轮)
                _is_vault = "Obsidian/ClawsJoy" in _rpath or _rpath.startswith("/mnt/d/Obsidian")
                _hint_vault = (
                    "Obsidian 知识库在沙箱外，read_file 无法读取。"
                    "请用 obsidian_knowledge 工具(action=read, sop_key=平台发布工作流/番茄推广SOP/视频制作SOP/避坑清单)读取。"
                )
                _msg = (
                    _hint_vault
                    if _is_vault
                    else "路径越权，已被拦截。该路径在只读白名单外，请换沙箱内或项目根路径（clawsjoy_dev/ 或 core/、config/、data/ 相对路径）。"
                )
                return ToolGuard.deny(
                    _msg,
                    status="escalation_blocked",
                    blocked={"tool": tool, "path": _rpath, "reason": "路径越权(只读白名单外)", "vault_hint": _is_vault},
                    error={"error": _msg, "escalated": True},
                    escalated=True,
                )
        return None


class ApprovalGuard(ToolGuard):
    """G1 锚点A 写审批 — 检测写操作是否已确认(与 bridge_loop 逻辑逐字一致)。

    payload 需含: tool/args/session_id/tool_call_id/approved
      - approved=True 且 id 匹配 → 放行(已确认)
      - 否则 → deny status="write_pending", 携带 pending_write 建议结构
    状态写入(_pending_writes/_persist_pending_writes)由**调用方**处理(收到 write_pending 后写状态)。
    子任务 scope 不挂此守卫(免审批)。
    """

    name = "approval_guard"
    event = EVENT_PRE_EXECUTE

    # 2026-08-30 根本修复: execute_command 的写操作(含 python -c open()/heredoc 写/重定向)
    # 之前不在审批范围 → Agent 用 python -c open() 绕过 write_file 审批直接写文件(日志多次出现)
    # → 工具即边界(harness): 所有写沙箱文件的路径统一走审批, 无绕过
    _WRITE_TOOLS = ("write_file", "execute_command")

    _SOP_MIRRORS = (
        "docs/reports/platform_publish_workflow.md",
        "docs/reports/fanqie_promotion_sop.md",
        "docs/reports/bilibili_video_script.md",
    )

    # 三档 WriteTier(2026-09-11, 借 Codex exec_policy Decision): allow/prompt/forbidden
    # 落地老板四级数据分级: 脱敏(沙箱内 data/*)→allow 自动; 原始(沙箱外绝对路径)→prompt 授权; 隐私(敏感标记)→forbidden 禁止
    _ALLOW_PREFIXES = (
        "data/tmp/",
        "data/reports/",
        "data/screenshots/",
        "data/videos/",
        "data/audio/",
        "data/vision/",
        "data/computer_use/",
    )
    _FORBIDDEN_MARKS = (
        ".env",
        "id_rsa",
        "id_ed25519",
        ".pem",
        ".key",
        "password",
        "secret",
        "token",
        "apikey",
        "密钥",
        "密码",
        "身份证",
        "银行卡",
        "工资表",
        "工资单",
        "客户报价",
    )

    def _write_tier(self, args):
        """按写入目标判三档: allow(自动)/prompt(授权)/forbidden(禁止)。"""
        target = str(args.get("path", "") or args.get("command", "") or "")
        tl = target.lower()
        for m in self._FORBIDDEN_MARKS:
            if m in tl:
                return "forbidden"
        for pre in self._ALLOW_PREFIXES:
            if pre in tl:
                return "allow"
        # 沙箱外绝对路径 → prompt(原始数据需授权)
        if (
            tl.startswith("/mnt/")
            or tl.startswith("/home/")
            or tl.startswith("/etc/")
            or tl.startswith("/usr/")
            or tl.startswith("/root/")
            or tl.startswith("/tmp/")
        ):
            return "prompt"
        # heuristics 兜底: 未知 → prompt(安全侧, 不静默放行)
        return "prompt"

    def _is_exec_write(self, args):
        """execute_command 是否写操作: 用 _classify_command(含 python -c open() 检测)。"""
        try:
            from core.gateway.sandbox_util import _classify_command

            _cmd = str(args.get("command", "") or "")
            return _classify_command(_cmd) == "write"
        except Exception:
            # 兜底: 含重定向/heredoc 写标记
            _c = str(args.get("command", "") or "")
            return any(m in _c for m in (">", ">>", "tee ", "open(", "write_text", "os.remove"))

    def _writes_sop_mirror(self, args):
        """D4 漏洞修复(2026-08-30): execute_command 的 sed -i / python open() 写 SOP 镜像文件
        (Agent 曾用 sed -i 绕过 write_file 镜像保护直改 SOP) → 拒绝并引导 update_sop。"""
        _cmd = str(args.get("command", "") or "")
        for _mir in self._SOP_MIRRORS:
            if _mir in _cmd and any(
                m in _cmd for m in ("sed -i", "sed -i'", "open(", "write_text", ">>", "> ", "tee ", "mv ", "cp ")
            ):
                return True
        return False

    def check(self, payload):
        tool = payload.get("tool", "")
        if tool not in self._WRITE_TOOLS:
            return None
        session_id = payload.get("session_id", "")
        tc_id = payload.get("tool_call_id", "")
        approved = payload.get("approved") or {}
        args = payload.get("args") or {}
        # execute_command: 仅写命令触发审批(读命令/探测不拦)
        if tool == "execute_command":
            # D4 漏洞修复: sed -i/python open() 直写 SOP 镜像 → 直接拒绝(非审批, 无绕过路径)
            if self._writes_sop_mirror(args):
                return ToolGuard.deny(
                    "SOP 沙箱镜像是只读的(vault 唯一真源)。请用 obsidian_knowledge(action=update_sop) 更新 SOP，"
                    "修改会自动同步到镜像。不要用 sed -i/python open() 直接改 SOP 文件。",
                    status="forbidden",
                    error={"error": "SOP 镜像只读, 请用 obsidian_knowledge(update_sop) 更新"},
                    escalated=True,
                )
            if not self._is_exec_write(args):
                return None
        # 三档 WriteTier(2026-09-11): allow 自动放行 / forbidden 禁止 / prompt 走下方审批卡
        _tier = self._write_tier(args)
        if _tier == "allow":
            return None  # 脱敏内部数据(沙箱 data/*)自动放行
        if _tier == "forbidden":
            return ToolGuard.deny(
                "隐私/敏感内容禁止写入(命中敏感标记: 密钥/密码/身份证/银行卡/客户报价等)。请脱敏后再写。",
                status="forbidden",
                error={"error": "隐私/敏感内容禁止写入", "forbidden": True},
            )
        # S3(2026-09-05) 空参单点逻辑(与桥接共用 shared_state.empty_arg_error; 其它执行路径的后备)
        # 2026-08-31 修复: write_file 缺 path → 直接拒绝(不进审批)
        if tool in ("write_file", "write_large", "edit_file"):
            from core.gateway.shared_state import empty_arg_error as _ea_ss

            _ea_msg = _ea_ss(tool, args)
            if _ea_msg:
                return ToolGuard.deny(_ea_msg, status="forbidden", error={"error": _ea_msg, "forbidden": True})
        _pending_ok = bool(approved) and approved.get("id") == tc_id and bool(approved.get("approved"))
        if _pending_ok:
            return None  # 已确认, 放行执行
        # 死循环修复: 同 session 同文件首次批准后, 后续 write_file 该文件免审
        # (Agent 分片/重试时每次生成新 tool_call_id, 若只按 id 放行则反复弹审批)
        _path = str(args.get("path", "") or "")
        if tool == "execute_command":
            # execute_command 用 command 做批准指纹(路径不易提取, 用命令前缀)
            _cmd_fp = str(args.get("command", "") or "")[:120]
            try:
                from core.gateway.shared_state import is_file_approved

                if _cmd_fp and is_file_approved(session_id, "cmd:" + _cmd_fp):
                    return None
            except Exception:
                pass
        if _path:
            try:
                from core.gateway.shared_state import is_file_approved

                if is_file_approved(session_id, _path):
                    return None  # 该文件本 session 已批准, 免审放行
            except Exception:
                pass
        # 未确认 → 返回 write_pending(调用方写状态 + 前端卡片)
        # 完整内容保留(full_content, 2026-08-29 修复): 确认后执行若 messages 反查不到原始
        # tool_call(跨轮/恢复), fallback 用 full_content 而非 500 字符截断的 content_preview —
        # 否则覆盖大文件时新内容被截断 → 相似度 0% 误拒绝(BUG: 确认写入失败)
        _pending_write = {
            "id": tc_id,
            "tool": tool,
            "path": str(args.get("path", "")),
            "content_preview": str(args.get("content", ""))[:500],
            "content": str(args.get("content", "") or ""),  # 完整内容(确认后执行用)
            "command": str(args.get("command", ""))[:200],
            "reason": str(args.get("reason", "") or "")[:200],  # R3(2026-08-30): 写理由(给老板审批看)
            "ts": time.time(),
            "approved": False,
        }
        # R3(2026-08-30): reason 缺失引导 — 不硬拒(兼容旧 Agent 无 reason), 但卡片/注入提醒补理由
        _reason_note = ""
        if tool == "write_file" and not str(args.get("reason", "") or "").strip():
            _reason_note = "（未提供 reason，请提醒 Agent 说明写该文件的理由）"
        # 批91：出口类命令在卡片上写清「要往哪发」—— 批89 点名的副作用对策
        _exfil_note = ""
        try:
            from core.gateway.sandbox_util import exfil_note as _en

            _exfil_note = _en(str(args.get("command", "") or ""))
        except Exception:
            _exfil_note = ""
        _card_msg = "等待老板确认写入"
        if _exfil_note:
            _card_msg = _exfil_note + "。等待老板确认"
        # 批153 · 授权记忆（grants）：老板点过「一直允许」的**同场景**免问放行（体检项 61：留痕）。
        # 安全边界：**出口类不参与授权**（exfil_note 命中「发到外部」时照样问）——门1 不动。
        try:
            _is_exfil_out = "发到外部" in str(_exfil_note or "")
            from core.pa.grants import is_granted, log_grant_use, scene_of

            _scene = scene_of(tool, args)
            if _scene and not _is_exfil_out and is_granted(_scene):
                log_grant_use(_scene, tool, args)
                return None
        except Exception as _ge:
            print("[GRANT_FAIL] %s" % _ge)
        return ToolGuard.deny(
            _card_msg + _reason_note,
            status="write_pending",
            pending_write=_pending_write,
            pending_id=tc_id,
            error={"error": "等待老板确认写入" + _reason_note, "pending": True, "pending_id": tc_id},
        )


class PlanGuard(ToolGuard):
    """G4 计划确认 — 检测多文件/多意图任务(与 bridge_loop 逻辑逐字一致)。

    payload 需含: tool/args/session_id/assistant_content/tool_calls_plan(同批写工具列表)
      - 同批 ≥2 个不同文件 或 ≥3 个修改意图 → deny status="plan_pending"
      - 已 approved → 放行
    状态写入(_plan_pending)由调用方处理。
    子任务 scope 不挂此守卫。
    """

    name = "plan_guard"
    event = EVENT_PRE_EXECUTE

    _WRITE_TOOLS = ("write_file",)  # 2026-08-24: 对齐 _TOOL_REGISTRY(edit_file/write_large 未注册, 拦截后确认执行必失败)

    def check(self, payload):
        tool = payload.get("tool", "")
        if tool not in self._WRITE_TOOLS:
            return None
        session_id = payload.get("session_id", "")
        approved = payload.get("approved") or {}
        if approved and approved.get("approved"):
            return None
        # 同批工具调用(前端 plan_pending 需要): 收集所有写工具的 path/意图
        plan_calls = payload.get("tool_calls_plan") or []
        _plan_files = []
        _plan_intents = 0
        import json as _json

        for _pc in plan_calls:
            _fn_p = _pc.get("function", {}).get("name", "")
            if _fn_p not in self._WRITE_TOOLS:
                continue
            _plan_intents += 1
            try:
                _pth_p = _json.loads(_pc["function"]["arguments"]).get("path", "")
            except Exception:
                _pth_p = ""
            if _pth_p and _pth_p not in _plan_files:
                _plan_files.append(_pth_p)
        if len(_plan_files) >= 2 or _plan_intents >= 3:
            return ToolGuard.deny(
                "检测到多文件/多意图任务，等待老板确认计划",
                status="plan_pending",
                plan_pending_info={
                    "ts": time.time(),
                    "approved": False,
                    "plan": str(payload.get("assistant_content", ""))[:1500],
                    "files": _plan_files,
                    "intents": _plan_intents,
                },
                error={"error": "检测到多文件/多意图任务，等待老板确认计划", "plan_pending": True},
            )
        return None


class RecursionGuard(ToolGuard):
    """G7 递归检测 — 检测同一 (tool, path) 连续重复(与 execute_agent_task 逻辑逐字一致)。

    payload 需含: tool/args/task_id
      - check_recursion 返回 pause → deny status="paused"
      - warn → 放行但带 warn 提示(payload["guard_results"]["warn"])
    断点写入(_pause_recursion)由调用方处理(收到 paused 后)。
    """

    name = "recursion_guard"
    event = EVENT_PRE_EXECUTE

    def check(self, payload):
        tool = payload.get("tool", "")
        args = payload.get("args") or {}
        task_id = payload.get("task_id") or payload.get("session_id")
        if not task_id:
            return None
        from core.gateway.execute_agent_task import check_recursion
        from core.gateway.path_utils import _extract_tool_path

        _rec_path = _extract_tool_path(args, tool)
        _rec_status, _rec_msg = check_recursion(task_id, tool, _rec_path)
        if _rec_status == "pause":
            return ToolGuard.deny(
                _rec_msg,
                status="paused",
                recursion_reason=_rec_msg,
                recursion_path=_rec_path,
                error={"error": _rec_msg, "paused": True},
            )
        if _rec_status == "warn":
            payload.setdefault("guard_results", {})["recursion_warn"] = _rec_msg
        return None


class ReminderGuard(ToolGuard):
    """G6 重复工具提醒 — 包装 repeat_tool_reminder.observe(观察, 永不否决)。

    payload 需含: tool/args/agent_id
    原逻辑(execute_agent_task L1208-1212): observe 命中阈值 → 提醒文本。
    观察守卫挂 post-execute, 调用方用 emit 触发; 提醒文本经 payload["reminder"] 回传,
    由调用方注入 messages(不在此处注入, 保持守卫无副作用)。
    """

    name = "reminder_guard"
    event = EVENT_POST_EXECUTE

    def check(self, payload):
        tool = payload.get("tool", "")
        args = payload.get("args") or {}
        agent_id = payload.get("agent_id") or payload.get("task_id") or payload.get("session_id")
        if not tool or agent_id is None:
            return None
        from core.gateway.repeat_tool_reminder import observe

        _msg = observe(agent_id, tool, args)
        if _msg:
            # 观察守卫: emit 共享 payload, 直接写入(payload["reminder"] 由调用方注入 messages)
            payload.setdefault("guard_results", {})["reminder"] = _msg
        return None


class AuditGuard(ToolGuard):
    """G15 审计+tool_flow — 包装 _with_tool_flow 的记录逻辑(观察)。

    payload 需含: tool/args/user_id/session_id/result/elapsed_ms
    原逻辑(_with_tool_flow): record_tool_flow + audit_tool_call(成功/失败/异常都记)。
    守卫纯记录, 不修改 result; 异常内部吞掉(与原装饰器一致)。
    """

    name = "audit_guard"
    event = EVENT_POST_EXECUTE

    def check(self, payload):
        tool = payload.get("tool", "")
        args = payload.get("args") or {}
        user_id = payload.get("user_id", "")
        session_id = payload.get("session_id", "")
        result = payload.get("result") or {}
        elapsed_ms = payload.get("elapsed_ms", 0)
        from core.context.context_manager import record_tool_flow
        from core.gateway.audit import audit_tool_call

        _summary = result.get("success", False) and "success" or result.get("error", "failed")[:100]
        try:
            record_tool_flow(tool, args, f"{_summary} ({elapsed_ms}ms)", user_id, session_id)
        except Exception:
            pass
        try:
            audit_tool_call(tool, args, result, user_id, session_id, elapsed_ms=elapsed_ms)
        except Exception:
            pass
        return None


class FailurePauseGuard(ToolGuard):
    """G14 连续失败暂停 — 计数观察; 达 8 次返回暂停提醒(动作留调用方)。

    payload 需含: tool/result/session_id/messages
    原逻辑(_check_consecutive_failure): success 重置; >=5 注入提示; >=8 返回 paused。
    守卫只计数+返回状态, 不直接改 messages/_paused_breakpoints(调用方按 payload 处理)。
    """

    name = "failure_pause_guard"
    event = EVENT_POST_EXECUTE

    def check(self, payload):
        tool = payload.get("tool", "")
        result = payload.get("result") or {}
        session_id = payload.get("session_id", "")
        if not session_id:
            return None
        import time as _t

        from core.gateway.shared_state import _consecutive_failures, _paused_breakpoints

        if result.get("success"):
            _consecutive_failures.pop(session_id, None)
            return None
        _consecutive_failures[session_id] = _consecutive_failures.get(session_id, 0) + 1
        _n = _consecutive_failures[session_id]
        if _n >= 8:
            _paused_breakpoints[session_id] = {
                "tool": tool,
                "count": _n,
                "at": _t.time(),
                "reason": "连续失败8次，任务已暂停",
                "last_error": str(result.get("error", ""))[:200],
            }
            payload.setdefault("guard_results", {}).update(
                {
                    "paused": True,
                    "paused_breakpoint": _paused_breakpoints[session_id],
                    "error": "连续失败8次，任务已暂停。请老板介入或换任务。",
                }
            )
            # 跨 session 记忆: 连续失败沉淀 known_issues(用户级, 后续会话注入提示)
            try:
                from core.gateway.memory import remember_issue as _mem_issue

                _mem_issue(payload.get("user_id"), f"连续失败{tool}: {str(result.get('error', ''))[:160]}")
            except Exception:
                pass
            return None
        if _n >= 3:
            # P4 steer 全量迁移: ≥3 失败提示由 tool_router 走 add_steer 通道(同阈值同文案),
            # guard 不再写 inject_message(避免与 steer 双份注入)。guard 仅保留 paused(≥8)。
            pass
        return None


class WebFetchGuard(ToolGuard):
    """G13 网络抓取递归检测 — 同一 URL 累计抓取 ≤3 次(防 Agent 反复抓同一页面)。

    payload 需含: tool/args/session_id
      - 同一 URL 累计 >3 → deny status="paused"(与 check_recursion 断点语义一致)
      - 第 2/3 次 → 仅 warn(经 payload["guard_results"]["web_fetch_warn"], 放行)
    """

    name = "web_fetch_guard"
    event = EVENT_PRE_EXECUTE

    _NET_TOOLS = ("fetch_web", "browse_web", "playwright_browser")

    def check(self, payload):
        tool = payload.get("tool", "")
        if tool not in self._NET_TOOLS:
            return None
        args = payload.get("args") or {}
        url = str(args.get("url") or "").strip()
        task_id = payload.get("task_id") or payload.get("session_id")
        if not task_id:
            return None
        import time as _t

        from core.gateway.execute_agent_task import _recursion_tracker

        # 递归 key = URL(不同 URL 各自计数); URL 缺失时 fallback 到工具名
        _pattern = url if url else "<no-url>:" + tool
        _key = "webfetch:" + task_id
        entry = _recursion_tracker.setdefault(
            _key, {"pattern": None, "count": 0, "first_seen": None, "breakpoint": None}
        )
        if entry["pattern"] == _pattern:
            entry["count"] += 1
        else:
            entry["pattern"] = _pattern
            entry["count"] = 1
            entry["first_seen"] = _t.time()
        _n = entry["count"]
        if _n > 3:
            # 跨 session 记忆: 同 URL 重复抓取沉淀 known_issues(防后续会话重蹈覆辙)
            try:
                from core.gateway.memory import remember_issue as _mem_issue

                _mem_issue(payload.get("user_id"), f"同一URL重复抓取已拦截({url[:60] or tool})，请换源或搜索")
            except Exception:
                pass
            return ToolGuard.deny(
                f"对同一 URL {url[:80] or tool} 的抓取已达 {_n} 次(上限 3)。请改用 web_search 或更换信息源，避免重复抓取。",
                status="paused",
                web_fetch_reason="same-url-repeat",
                error={"error": f"同一 URL 抓取超限({_n}/3)，请换源或搜索", "paused": True},
            )
        if _n >= 2:
            payload.setdefault("guard_results", {})["web_fetch_warn"] = f"第 {_n} 次抓取同一 URL {url[:60] or tool}，如无进展请换源"
        return None


# ===== 注册表 =====
# name -> (order, class)
GUARD_ORDER: List[Dict[str, Any]] = [
    {"name": "quota_guard", "order": 10, "cls": QuotaGuard},
    {"name": "mode_guard", "order": 20, "cls": ModeGuard},
    {"name": "forced_tool_guard", "order": 30, "cls": ForcedToolGuard},
    {"name": "forbidden_guard", "order": 40, "cls": ForbiddenGuard},
    {"name": "escape_guard", "order": 50, "cls": EscapeGuard},
    {"name": "plan_guard", "order": 60, "cls": PlanGuard},  # 计划确认先于写审批(复现 bridge_loop 原顺序 G2→锚点A)
    {"name": "approval_guard", "order": 70, "cls": ApprovalGuard},
    {"name": "recursion_guard", "order": 80, "cls": RecursionGuard},
    {"name": "web_fetch_guard", "order": 85, "cls": WebFetchGuard},
    {"name": "reminder_guard", "order": 100, "cls": ReminderGuard},
    {"name": "audit_guard", "order": 110, "cls": AuditGuard},
    {"name": "failure_pause_guard", "order": 120, "cls": FailurePauseGuard},
]

_GUARD_BY_NAME = {g["name"]: g for g in GUARD_ORDER}


def get_guard_classes() -> Dict[str, type]:
    """name -> class 映射(供外部按名实例化)。"""
    return {name: g["cls"] for name, g in _GUARD_BY_NAME.items()}


def guard_names() -> List[str]:
    """按顺序返回全部守卫名。"""
    return [g["name"] for g in GUARD_ORDER]


def mount_guards(
    ctx: Any, scope: Optional[str] = None, include: Optional[List[str]] = None, exclude: Optional[List[str]] = None
) -> List[ToolGuard]:
    """按注册表挂载守卫到 ctx(或 scope)。

    include/exclude 过滤(子任务 scope 用 exclude=["approval_guard", "plan_guard"])。
    返回已挂载实例列表(供测试断言/后续 unmount)。
    """
    _ex = set(exclude or [])
    _inc = set(include) if include is not None else None
    mounted = []
    for g in GUARD_ORDER:
        name = g["name"]
        if name in _ex:
            continue
        if _inc is not None and name not in _inc:
            continue
        guard = g["cls"]()
        guard.order = g["order"]
        ctx.mount(guard, scope=scope)
        mounted.append(guard)
    return mounted


def unmount_guards(ctx: Any, guards: List[ToolGuard]) -> int:
    """卸载守卫列表(测试回滚用)。"""
    n = 0
    for guard in guards:
        if ctx.unmount(guard):
            n += 1
    return n
