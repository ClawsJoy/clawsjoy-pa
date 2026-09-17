#!/usr/bin/env python3
"""AgentDiscussionEngine v8.0 — Agent 讨论引擎：并行调用多模型，收集结果，调用共识引擎，管理讨论状态"""

import copy
import json
import re
import logging
import threading
from typing import Dict, List, Optional
from queue import Queue, Empty

from core.lib.precision_feed import _load_asset, _precision_feed_cache
from core.lib.v8.consensus_engine import ConsensusEngine
from core.lib.llm_client import llm_client
from core.lib.v8.roster_engine import RosterEngine
from core.gateway.chat_stream import _skeletonize_sys_prompt

logger = logging.getLogger(__name__)

# #68-70 讨论引擎上下文注入完整性：
# - 花名册身份 / 精准投喂（os_capabilities/system_hypothesis）/ 降噪 / 审计 均已注入（_call_agent）
# - 骨架化 _skeletonize_sys_prompt 从 chat_stream 统一导入（与 chat_stream else 分支一致）
# - _denoise_sys_prompt 在 chat_stream 中是 chat_stream_handler 的嵌套函数（无法模块级导入），
#   此处保持复现实现，逻辑与 chat_stream 版一致。
def _denoise_sys_prompt(sys_prompt: str) -> str:
    """降噪把关：过滤 EXPIRED/SKIPPED 任务引用和 _ 开头的脚本文件名引用"""
    if not sys_prompt:
        return sys_prompt
    lines = sys_prompt.split('\n')
    filtered = []
    for line in lines:
        if re.search(r'(?:\[|\s)(EXPIRED|SKIPPED)(?:\]|\s|$)', line):
            continue
        if re.search(r'(?:^|[\s/:])_\w+\.py', line):
            continue
        filtered.append(line)
    _denoised = '\n'.join(filtered)
    if len(_denoised) != len(sys_prompt):
        logger.info(f"[DENOISE] filtered {len(sys_prompt) - len(_denoised)} chars of noise from _sys_prompt")
    return _denoised


def audit_agent_output(user_message: str, agent_reply: str) -> list:
    """Phase 1 实时审计层：Agent 输出拦截
    规则A：无关脚本检测
    规则B：超范围文件修改检测
    """
    warnings = []
    # 规则A：检测 Agent 回复中是否包含 _*.py 脚本名
    _scripts = re.findall(r'(?<![a-zA-Z])_\w+\.py', agent_reply)
    if _scripts:
        for _s in sorted(set(_scripts)):
            warnings.append(f"[审计] \u26a0\ufe0f 检测到执行了无关脚本：{_s}")
    # 规则B：如果用户指令指定了修改范围，检查实际修改的文件
    _scope = re.search(r'只(?:改|修改|允许)(?:\s+)(\S+\.\w+)', user_message)
    if _scope:
        _allowed = _scope.group(1)
        _found = re.findall(
            r'(?:修改|写入|创建|write_file|编辑)(?:\s*(?:文件|了))?\s*[`\"\']?([\w./-]+\.\w+)[`\"\']?',
            agent_reply,
        )
        _extra = [f for f in _found if f != _allowed and _allowed not in f]
        if _extra:
            warnings.append(f"[审计] \u26a0\ufe0f 修改了指令外的文件：" + ", ".join(sorted(set(_extra))))
    if warnings:
        logger.info(f"[AUDIT] {'; '.join(warnings)}")
    return warnings


class AgentDiscussionEngine:
    """Agent 讨论引擎（单例）：并行调用多模型，收集结果，调用共识引擎，管理讨论状态。

    流程：
    1. 每轮并行调用所有 Agent 的模型
    2. 调用 ConsensusEngine.evaluate() 判断共识
    3. 达成共识 → 返回结果
    4. 未达成 → 把其他人的观点注入下一轮 prompt，继续
    5. 超过 max_rounds → 多数决强制结束

    使用示例:
        engine = AgentDiscussionEngine()
        result = engine.discuss(
            focus="用户登录模块应该用 JWT 还是 Session？",
            agents=[
                {"name": "小程", "model": "deepseek-v4-flash"},
                {"name": "小审", "model": "qwen2.5:7b-instruct-q4_0-gpu"},
            ]
        )
        print(result["decision"])
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._consensus_engine = ConsensusEngine()
        self._roster_engine = RosterEngine()

    # ========== 公开接口 ==========

    def discuss(
        self,
        focus: str,
        agents: Optional[List[Dict[str, str]]] = None,
        max_rounds: int = 8,
        system_prompt: str = "",
        user_id: str = "guest",
        session_id: str = "",
    ) -> dict:
        """多 Agent 讨论，直到达成共识或达到最大轮次。

        参数:
            focus: 讨论主题
            agents: Agent 配置列表
                [{"name": "小程", "model": "deepseek-v4-flash"},
                 {"name": "小审", "model": "qwen2.5:7b-instruct-q4_0-gpu"}]
            max_rounds: 最大讨论轮次（默认 8），死循环防护
            system_prompt: 可选的系统提示词
            user_id: 用户 ID（用于精准投喂）
            session_id: 会话 ID（用于精准投喂）

        返回:
            {
                "consensus": True/False,   # 是否达成共识
                "decision": "最终决策",    # 最终决策文本
                "rounds": 实际轮次,        # 实际进行的轮数
                "history": [每轮的讨论记录] # 完整讨论历史
            }
        """
        # ── 参数校验 ──
        if focus is None:
            yield {"type": "done", "consensus": False, "decision": "", "rounds": 0, "history": []}
            return
        if agents is None:
            # 从花名册读取 can_discuss=true 的成员
            agents = [
                {"name": m["name"], "model": m["model"]}
                for m in self._roster_engine.list("default")
                if m.get("can_discuss", False)
            ]
        if not agents:
            yield {"type": "done", "consensus": False, "decision": "", "rounds": 0, "history": []}
            return

        max_rounds = max(1, min(max_rounds, 50))  # 硬上限 50

        # ── 初始化 Agent 状态 ──
        agent_states = []
        for a in agents:
            agent_states.append({
                "name": a["name"],
                "model": a["model"],
                "last_output": "",
                "silent_rounds": 0,     # 连续无响应轮次
                "error_count": 0,       # 连续出错次数（熔断用）
                "is_fused": False,      # 是否已熔断
            })

        # ── 讨论历史 ──
        history = []

        # ── 构造初始 prompt ──
        base_prompt = f"【讨论主题】\n{focus}\n\n请针对以上主题给出你的分析和建议。"

        # ── 精准投喂：从 agent_gateway_enhanced 加载匹配的数据资产 ──
        _inject_parts = []
        try:
            _feeds_config = _precision_feed_cache
            _agent_pos = ""
            try:
                _member = self._roster_engine.get("default", "")
                if _member:
                    _agent_pos = _member.get("position", "")
            except Exception:
                pass
            for _feed in _feeds_config.get("feeds", []):
                if _feed.get("status") != "active":
                    continue
                _kw_match = any(kw in focus for kw in _feed.get("keywords", []))
                _pos_match = _agent_pos and _agent_pos in _feed.get("agent_positions", [])
                if _kw_match or _pos_match:
                    for _inj in _feed.get("inject", []):
                        _source = _inj["source"]
                        _data = _load_asset(_source, _inj.get("params", {}), user_id, session_id)
                        if _data:
                            _inject_parts.append(_data[:_inj.get("max_chars", 2000)])
        except Exception:
            pass
        _precision_feeds_text = ""
        if _inject_parts:
            _precision_feeds_text = "\n".join(_inject_parts)

        # ── 多轮讨论 ──
        for round_idx in range(1, max_rounds + 1):
            round_result = {
                "round": round_idx,
                "responses": [],
                "viewpoints": {},
            }

            # 收集本轮有效 Agent（跳过熔断的）
            active_agents = [s for s in agent_states if not s["is_fused"]]

            if not active_agents:
                # 所有 Agent 都已熔断 → 强制结束
                break

            # ── 并行调用所有活跃 Agent ──
            threads = []
            results_lock = threading.Lock()
            round_outputs: Dict[str, str] = {}

            def _call_agent(state: dict):
                """线程内调用单个 Agent 的模型"""
                if state["is_fused"]:
                    return

                # 构造带他人观点的 prompt
                prompt = self._build_prompt(
                    base_prompt=base_prompt,
                    focus=focus,
                    agent_name=state["name"],
                    last_output=state["last_output"],
                    other_viewpoints=round_result["viewpoints"],
                    round_num=round_idx,
                )

                try:
                    # 从花名册获取 Agent 身份
                    _member = self._roster_engine.get("default", state["name"])
                    _roster_prompt = _member.get("system_prompt", "") if _member else ""
                    _agent_api_key = _member.get("api_key", "") if _member else ""

                    _sys_prompt = _roster_prompt or self._default_system_prompt(state["name"])
                    if _precision_feeds_text:
                        # "## " 分段：与 chat_stream 的 "## 系统假设" 风格一致，供 _skeletonize_sys_prompt 按优先级截断
                        _sys_prompt = f"{_sys_prompt}\n\n## 系统注入\n基于任务类型自动投喂：\n\n{_precision_feeds_text}"
                    _sys_prompt = _denoise_sys_prompt(_sys_prompt)
                    # #68-70 骨架化：超长 prompt 按优先级截断（与 chat_stream else 分支一致）
                    _sys_prompt = _skeletonize_sys_prompt(_sys_prompt)
                    content = ""
                    for token in llm_client.generate_stream(
                        prompt=prompt,
                        model=state["model"],
                        task_type="chat",
                        system_prompt=_sys_prompt,
                        api_key=_agent_api_key,
                    ):
                        if isinstance(token, bytes):
                            token = token.decode('utf-8')
                        try:
                            if isinstance(token, str) and token.startswith('data: '):
                                token = token[6:]
                            data_token = json.loads(token)
                            if "response" in data_token:
                                token = data_token["response"]
                            elif "choices" in data_token:
                                delta = data_token["choices"][0].get("delta", {})
                                token = delta.get("content") or delta.get("reasoning_content") or ""
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass
                        content += token
                        token_queue.put((state["name"], token))
                    token_queue.put((state["name"], None))
                    response = {"success": True, "content": content, "tokens": 0, "model": state["model"]}
                    response = {"success": True, "content": content, "tokens": 0, "model": state["model"]}

                    with results_lock:
                        if response.get("success"):
                            content = response["content"].strip()
                            if content:
                                state["last_output"] = content
                                state["silent_rounds"] = 0
                                state["error_count"] = 0
                                round_outputs[state["name"]] = content
                                round_result["viewpoints"][state["name"]] = content
                                # 审计输出：每轮 Agent 回复后调用
                                _warnings = audit_agent_output(focus, content)
                                if _warnings:
                                    logger.warning(f"[DISCUSS_AUDIT] {'; '.join(_warnings)}")
                            else:
                                state["silent_rounds"] += 1
                        else:
                            state["error_count"] += 1
                            state["silent_rounds"] += 1

                except Exception:
                    with results_lock:
                        state["error_count"] += 1
                        state["silent_rounds"] += 1

            # 启动所有线程
            token_queue = Queue()
            for state in active_agents:
                t = threading.Thread(target=_call_agent, args=(state,))
                threads.append(t)
                t.start()

            # 轮询 Queue 实时 yield token
            remaining = len(threads)
            while remaining > 0:
                try:
                    agent_name, token_or_none = token_queue.get(timeout=0.1)
                    if token_or_none is None:
                        remaining -= 1
                    else:
                        yield {"type": "token", "round": round_idx, "agent": agent_name, "token": token_or_none}
                except Empty:
                    pass

            # ── 熔断检查 ──
            for state in agent_states:
                if state["error_count"] >= 3 and not state["is_fused"]:
                    state["is_fused"] = True

            # ── 跳过检查：连续 2 轮无响应 → 标记熔断 ──
            for state in agent_states:
                if state["silent_rounds"] >= 2 and not state["is_fused"]:
                    state["is_fused"] = True
            # yield 每个 Agent 的输出
            for name, content in round_outputs.items():
                yield {"type": "agent_output", "round": round_idx, "agent": name, "content": content}
            # ── 记录本轮讨论 ──
            round_record = {
                "round": round_idx,
                "responses": dict(round_outputs),
                "silent": [s["name"] for s in agent_states if s["is_fused"] and s["name"] not in round_outputs],
            }
            history.append(round_record)

            # 没有有效输出 → 结束
            if not round_outputs:
                continue

            # ── 调用共识引擎 ──
            consensus_result = self._consensus_engine.evaluate(round_outputs)

            if consensus_result["consensus"]:
                # 达成共识
                yield {
                    "type": "done",
                    "consensus": True,
                    "decision": consensus_result["decision"],
                    "rounds": round_idx,
                    "history": history,
                }
                return
            # 如果是最后一轮，用多数决强制结束
            if round_idx == max_rounds:
                decision = self._majority_vote(
                    round_outputs,
                    consensus_result.get("decision", ""),
                )
                yield {
                    "type": "done",
                    "consensus": True,
                    "decision": decision,
                    "rounds": round_idx,
                    "history": history,
                }
                return
            # ── 未达成共识，准备下一轮 ──
            # 将本轮观点注入 base_prompt 供下一轮使用
            # round_result["viewpoints"] 已在 _call_agent 中填充，下一轮会传给 _build_prompt

        # ── 异常退出（全部熔断等）──
        yield {
            "type": "done",
            "consensus": False,
            "decision": self._fallback_decision(history),
            "rounds": len(history),
            "history": history,
        }
        return
    # ========== 内部方法 ==========

    def _build_prompt(
        self,
        base_prompt: str,
        focus: str,
        agent_name: str,
        last_output: str,
        other_viewpoints: Dict[str, str],
        round_num: int,
    ) -> str:
        """构建带他人观点的 prompt。"""
        parts = [f"【第 {round_num} 轮讨论】"]
        parts.append(base_prompt)

        if other_viewpoints:
            parts.append("\n【其他 Agent 的观点】")
            for name, viewpoint in other_viewpoints.items():
                if name != agent_name and viewpoint:
                    parts.append(f"  {name}: {viewpoint[:500]}")

        if last_output:
            parts.append(f"\n【你上一轮的观点】\n{last_output[:500]}")

        parts.append(f"\n请以 {agent_name} 的身份，结合以上信息，给出你的分析和建议。")

        return "\n".join(parts)

    def _default_system_prompt(self, agent_name: str) -> str:
        """默认系统提示词。"""
        return (
            f"你是 {agent_name}，一个专业的 AI 讨论伙伴。\n"
            "你需要参与团队讨论，给出有深度、有逻辑的分析。\n"
            "请保持客观理性，可以赞同或反驳他人观点，但要有理有据。"
        )

    def _majority_vote(self, outputs: Dict[str, str], consensus_decision: str) -> str:
        """多数决：取共识引擎的决策，或投票最多的观点。"""
        if consensus_decision:
            return consensus_decision
        # 简单返回第一个有效输出
        for _, content in outputs.items():
            if content:
                return content
        return ""

    def _fallback_decision(self, history: list) -> str:
        """异常退出的兜底决策。"""
        if not history:
            return ""
        # 取最后一轮第一个有效响应
        last_round = history[-1]
        responses = last_round.get("responses", {})
        for _, content in responses.items():
            if content:
                return content
        return ""

    # ========== 状态查询 ==========

    def get_status(self) -> dict:
        """获取当前引擎状态（调试用）。"""
        return {
            "engine": "AgentDiscussionEngine",
            "singleton": True,
            "status": "ready",
        }
