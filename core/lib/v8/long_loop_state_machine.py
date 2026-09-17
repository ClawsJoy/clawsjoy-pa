#!/usr/bin/env python3
"""LongLoopStateMachine v8.1 — 长循环状态机：七态 + PAUSED 生命周期管理"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import tiktoken
logger = logging.getLogger(__name__)
# ============================================================
# 状态常量（七态 + PAUSED）
# ============================================================
STATE_IDLE = "idle"
STATE_PLANNING = "planning"
STATE_EXECUTING = "executing"
STATE_VERIFYING = "verifying"
STATE_COMPRESSING = "compressing"
STATE_RETRIEVING = "retrieving"
STATE_ERROR = "error"
STATE_DONE = "done"
STATE_PAUSED = "paused"

ALL_STATES = frozenset({
    STATE_IDLE,
    STATE_PLANNING,
    STATE_EXECUTING,
    STATE_VERIFYING,
    STATE_COMPRESSING,
    STATE_RETRIEVING,
    STATE_ERROR,
    STATE_DONE,
    STATE_PAUSED,
})

# ============================================================
# 合法转移表: {源状态: {目标状态: 说明}}
# ============================================================
TRANSITIONS: Dict[str, Dict[str, str]] = {
    STATE_IDLE: {
        STATE_PLANNING: "任务进入规划阶段",
    },
    STATE_PLANNING: {
        STATE_EXECUTING: "规划完成，开始执行",
        STATE_ERROR: "规划阶段出错",
    },
    STATE_EXECUTING: {
        STATE_VERIFYING: "执行完成，进入验证",
        STATE_ERROR: "执行阶段出错",
        STATE_DONE: "执行完成",
    },
    STATE_VERIFYING: {
        STATE_COMPRESSING: "验证通过，进入压缩",
        STATE_ERROR: "验证失败，进入错误",
    },
    STATE_COMPRESSING: {
        STATE_RETRIEVING: "压缩完成，进入检索",
        STATE_ERROR: "压缩阶段出错",
    },
    STATE_RETRIEVING: {
        STATE_EXECUTING: "检索完成，回到执行",
    },
    STATE_ERROR: {
        STATE_EXECUTING: "错误恢复，重新执行",
        STATE_DONE: "错误无法恢复，终止",
    },
    STATE_PAUSED: {},  # PAUSED 的转移由 pause / resume 方法动态处理
    STATE_DONE: {},    # 终态
}


class LongLoopStateMachine:
    """长循环状态机 — 管理长循环任务的全生命周期（七态 + PAUSED）"""

    def __init__(self, task_id: str, session_id: str, user_id: str, orchestrator) -> None:
        self.task_id = task_id
        self.session_id = session_id
        self.user_id = user_id
        self.orchestrator = orchestrator

        self._state: str = STATE_IDLE
        self._previous_state: Optional[str] = None  # 供 pause / resume 使用
        self._step_number: int = 0
        self._exec_step: int = 0  # 独立执行计数器：执行成功 +1，error 重试保持不变
        self._checkpoints: list[dict] = []
        self._created_at: str = datetime.utcnow().isoformat()
        self._updated_at: str = self._created_at
        self.steps_summary: List[str] = []
        self.messages: List[Dict] = []
        self._error_count: int = 0
        # #156 心跳检测：间隔分钟数（从 audit_rules.yaml 读取，默认 30）与上次活动时间
        self._heartbeat_minutes: int = self._load_heartbeat_minutes()
        self._last_activity_at: float = time.time()

    # ----------------------------------------------------------
    # 属性
    # ----------------------------------------------------------
    @property
    def state(self) -> str:
        return self._state

    @property
    def step_number(self) -> int:
        return self._step_number

    @property
    def checkpoints(self) -> list[dict]:
        return list(self._checkpoints)

    # ----------------------------------------------------------
    # 核心转移逻辑
    # ----------------------------------------------------------
    def _transition(self, target: str) -> None:
        """执行状态转移，校验合法性后更新状态。

        Args:
            target: 目标状态

        Raises:
            ValueError: 转移不合法时抛出
        """
        source = self._state

        # PAUSED 状态的转移由 pause / resume 管理，不走常规 TRANSITIONS
        if source == STATE_PAUSED:
            raise ValueError(
                f"非法转移: 状态 {source} 的转移由 pause/resume 方法管理，"
                f"不能直接调用 _transition({target})"
            )

        allowed = TRANSITIONS.get(source, {})
        if target not in allowed:
            raise ValueError(
                f"非法状态转移: {source} -> {target}。"
                f"允许的目标: {list(allowed.keys())}"
            )

        self._previous_state = source
        self._state = target
        self._updated_at = datetime.utcnow().isoformat()
        self._step_number += 1
        logging.info(f"[LONG_LOOP] {self.task_id} {source} → {target}")
    # ----------------------------------------------------------
    # 规划入口
    # ----------------------------------------------------------
    def _enter_planning(self, user_input: str, user_id: str) -> None:
        """进入规划阶段：调用 orchestrator.plan 并存入结果，然后转移到执行状态。

        Args:
            user_input: 用户输入
            user_id: 用户ID
        """
        self._transition(STATE_PLANNING)
        self.plan_data = self.orchestrator.plan(
            user_input, user_id, server_id="default"
        )
        logging.info(f"[DEBUG_PLAN] plan_data keys={list(self.plan_data.keys())}, tasks_count={len(self.plan_data.get('tasks', []))}")
        self._transition(STATE_EXECUTING)
    # ----------------------------------------------------------
    # 执行入口
    # ----------------------------------------------------------
    def _enter_executing(self) -> None:
        """进入执行阶段：从 plan_data 获取当前步骤，注入复述和关联上下文，执行单步。

        流程:
            0. [TOKEN_BUDGET] Token 预算检查 — 防止 V9 上下文硬截断
            1. 从 self.plan_data 获取当前步骤的任务数据
            2. 调用 recap_checkpoint() 注入复述，防止长任务注意力漂移
            3. 调用 inject_related_context() 注入关联上下文
            4. 调用 orchestrator.execute_task() 执行单步
            5. 成功 → _transition(STATE_COMPRESSING)，失败 → _transition(STATE_ERROR)
        """
        # [TOKEN_BUDGET] Token 预算检查 — 防止 V9 上下文硬截断
        _TOKEN_BUDGET_THRESHOLD = 120000
        _before_tokens = 0
        _after_tokens = 0
        _truncated = False

        try:
            _enc = tiktoken.get_encoding("cl100k_base")
            _text_parts = [str(m.get("content", "")) for m in self.messages if m.get("content")]
            _total_text = "\n".join(_text_parts)
            _before_tokens = len(_enc.encode(_total_text))
        except Exception:
            _before_tokens = 0

        if _before_tokens > _TOKEN_BUDGET_THRESHOLD:
            # 丢弃最早步骤的非核心上下文，只保留：
            #   - System Prompt
            #   - 当前步骤 SAG 检索结果（最近 2 条非 system 消息）
            #   - 最近 2 步摘要
            _kept: List[dict] = []

            # 1. 保留 System Prompt
            for msg in self.messages:
                if msg.get("role") == "system":
                    _kept.append(msg)

            # 2. 保留最近 2 条非 system 消息（含当前步骤 SAG 检索结果）
            _non_system = [m for m in self.messages if m.get("role") != "system"]
            _kept.extend(_non_system[-2:] if len(_non_system) >= 2 else _non_system)

            # 3. 重建 messages
            self.messages = _kept

            # 4. 保留最近 2 步摘要
            if len(self.steps_summary) > 2:
                self.steps_summary = self.steps_summary[-2:]

            # 计算截断后 tokens
            try:
                _after_text = "\n".join([str(m.get("content", "")) for m in self.messages if m.get("content")])
                _after_tokens = len(_enc.encode(_after_text))
            except Exception:
                _after_tokens = 0

            _truncated = True

        if _truncated:
            print(f"[TOKEN_BUDGET] 截断前 {_before_tokens} tokens → 截断后 {_after_tokens} tokens")

        # 1. 从 plan_data 获取当前步骤
        tasks: List[dict] = self.plan_data.get("tasks", []) if self.plan_data else []
        if not tasks:
            self._transition(STATE_ERROR)
            return
        # V9 修复: _exec_step 越界（全部任务执行完成）-> 直接进入 DONE，避免死循环
        if self._exec_step >= len(tasks):
            self._transition(STATE_DONE)
            return

        # 独立执行计数器 _exec_step 从 0 开始，不从 _step_number 推导
        step_idx = self._exec_step
        if step_idx < 0 or step_idx >= len(tasks):
            self._transition(STATE_ERROR)
            return

        logging.info(f"[DEBUG_EXEC] _exec_step={self._exec_step}, tasks_count={len(tasks)}, step_idx={step_idx}")
        task_data = tasks[step_idx]
        task_name: str = task_data.get("title", f"step_{self._exec_step}")

        # 2. 每步前调 recap_checkpoint() 注入复述
        from core.lib.gateway_helpers import recap_checkpoint, inject_related_context
        recap_checkpoint(task_name, self._exec_step)

        # 3. 调 inject_related_context() 注入关联上下文
        keywords: List[str] = [task_name]
        skill = task_data.get("_skill", "")
        if skill:
            keywords.extend(skill.split())
        inject_related_context(task_name, keywords)

        # 4. 调 orchestrator.execute_task() 执行单步
        try:
            self.orchestrator.execute_task(task_data)
            # 追加消息到 self.messages，供 _enter_compressing 压缩使用
            self.messages.append({
                "role": "assistant",
                "content": task_data.get("output", f"Executed task: {task_name}"),
                "step": self._exec_step,
                "task": task_name,
            })
            # 执行成功：独立执行计数器 +1（error 重试不经过此处，_exec_step 保持不变）
            self._exec_step += 1
            # 执行完成 → 进入验证阶段（Verifier 模块集中校验）
            self._transition(STATE_VERIFYING)
        except Exception as e:
            # 5. 失败 → _transition(STATE_ERROR)（_exec_step 保持不变，重试时重复执行当前步骤）
            # 记录失败模式（#172）
            self._last_fail_tool = getattr(self, '_last_tool', 'execute')
            self._last_fail_path = getattr(self, '_last_path', '')
            self._last_fail_error = str(e)[:100]
            self._transition(STATE_ERROR)

    # ----------------------------------------------------------

    # ----------------------------------------------------------
    # 验证入口
    # ----------------------------------------------------------
    def _enter_verifying(self) -> None:
        # 进入验证阶段：调用 Verifier 校验步骤产出，并做 AST 语法与文件完整性检查。
        #
        # 流程:
        #   1. 调用 verifier.verify(step_result) 验证当前步骤产出
        #   2. AST 语法检查（防代码崩溃）
        #   3. 文件完整性校验
        #   4. 通过 → _transition(STATE_COMPRESSING)
        #   5. 失败 → 记录失败原因 → _transition(STATE_ERROR)
        import ast as _ast
        import os as _os

        # 0. 收集当前步骤产出与目标
        _step_result = ""
        _step_goal = ""
        if self.messages:
            _step_goal = str(self.messages[0].get("task") or self.messages[0].get("content") or "")
            _step_result = str(self.messages[-1].get("content") or "")
        if not _step_result:
            _step_result = getattr(self, "_last_step_output", "") or ""

        _fail_reasons: List[str] = []

        # 1. 调 verifier.verify() 验证步骤产出
        try:
            from core.lib.v8.verifier import Verifier
            _verify_result = Verifier().verify(
                step_result=_step_result,
                step_goal=_step_goal,
                task_name=self.task_id,
                skill=getattr(self, "_last_skill", ""),
            )
            if not _verify_result.get("passed", False):
                _fail_reasons.append(f"verifier: {_verify_result.get('reason', '验证未通过')}")
            else:
                logger.info("[VERIFY] step=%s 产出验证通过", self._step_number)
        except Exception as _v_err:
            _fail_reasons.append(f"verifier异常: {_v_err}")

        # 2. AST 语法检查（防代码崩溃）
        _code_candidates = [_step_result, getattr(self, "_last_step_output", "")]
        for _cand in _code_candidates:
            if not _cand:
                continue
            if "```python" in _cand or "```py" in _cand:
                import re as _re
                _blocks = _re.findall(r"```(?:python|py)\n(.*?)```", _cand, flags=_re.S)
                _cands = _blocks or [_cand]
            else:
                _cands = [_cand]
            for _blk in _cands:
                try:
                    _ast.parse(_blk)
                except SyntaxError as _syn_err:
                    _fail_reasons.append(f"AST语法错误: {_syn_err}")
                    break

        # 3. 文件完整性校验（提取产出中提到的 .py 文件，确认存在且可编译）
        if _step_result:
            import re as _re
            for _f in _re.findall(r"[\w./\\-]+\.py\b", _step_result)[:10]:
                if _f.startswith(("http://", "https://")):
                    continue
                _clean = _f.strip("\"'()[]")
                if not _os.path.exists(_clean):
                    _fail_reasons.append(f"文件缺失: {_clean}")
                    continue
                try:
                    with open(_clean, "r", encoding="utf-8") as _fh:
                        _ast.parse(_fh.read())
                except Exception as _f_err:
                    _fail_reasons.append(f"文件不可编译: {_clean} ({_f_err})")

        # 4. 判定
        if not _fail_reasons:
            logger.info("[VERIFY] step=%s 全部校验通过，进入压缩", self._step_number)
            self._transition(STATE_COMPRESSING)
        else:
            _reason = " | ".join(_fail_reasons)
            logger.error("[VERIFY] step=%s 验证失败: %s", self._step_number, _reason)
            self._last_verify_fail_reason = _reason
            self._transition(STATE_ERROR)

    def _enter_compressing(self) -> None:
        """进入压缩阶段：压缩上下文，记录摘要，然后转移到检索状态。

        流程:
            1. 调用 _compress_messages() 压缩 self.messages
            2. 从压缩结果中提取摘要
            3. 追加到 self.steps_summary
            4. 成功 → _transition(STATE_RETRIEVING)
        """
        # 1. 压缩 self.messages
        from core.lib.gateway_helpers import _compress_messages
        compressed = _compress_messages(
            self.messages,
            user_id=self.user_id,
            session_id=self.session_id,
            step_number=self._step_number,
        )

        # 3. 提取摘要并写入 steps_summary
        summary = ""
        for msg in compressed:
            if msg.get("role") == "system" and "【历史摘要】" in msg.get("content", ""):
                summary = msg["content"].replace("【历史摘要】", "").strip()
                break
        self.steps_summary.append(
            summary or f"Step {self._step_number}: context compressed ({len(self.messages)} → {len(compressed)} msgs)"
        )

        # 3.5 漂移检测：从 messages 提取原始目标与当前输出
        try:
            from core.lib.v8.drift_detector import DriftDetector
            _goal = ""
            _output = ""
            if self.messages:
                _goal = str(self.messages[0].get("task") or self.messages[0].get("content") or "")
                _output = str(self.messages[-1].get("content") or "")
            if _goal and _output:
                _drift = DriftDetector().detect(goal=_goal, output=_output)
                self.steps_summary.append(
                    f"Step {self._step_number}: drift_score={_drift.get('score', 0.0):.3f} ({_drift.get('level', 'unknown')})"
                )
                logging.info(
                    "[DRIFT] step=%s score=%.3f level=%s coverage=%.3f jaccard=%.3f",
                    self._step_number,
                    _drift.get("score", 0.0),
                    _drift.get("level", "unknown"),
                    _drift.get("keyword_coverage", 0.0),
                    _drift.get("jaccard_similarity", 0.0),
                )
        except Exception:
            pass

        # 4. 收集压缩阶段反馈
        try:
            from core.lib.v8.feedback_collector import FeedbackCollector
            FeedbackCollector().collect(
                task_name=f"step_{self._step_number}",
                session_id=self.session_id,
                feedback_type="used",
                feedback_value=1.0,
                context=f"compress_{len(self.messages)}_to_{len(compressed)}",
            )
        except Exception:
            pass

        # 4.6 checkpoint 落库：steps_summary → PostgreSQL（断点恢复）
        try:
            from core.lib.code_entity_extractor import CodeEntityExtractor
            CodeEntityExtractor().store_step_summary(
                task_name=self.task_id,
                step_number=self._step_number,
                summary_json={
                    "step": self._step_number,
                    "summary": self.steps_summary[-1] if self.steps_summary else "",
                    "messages_before": len(self.messages),
                    "messages_after": len(compressed),
                    "checkpoint_at": datetime.utcnow().isoformat(),
                },
            )
        except Exception as _ckpt_err:
            logger.warning("[CHECKPOINT] store_step_summary 失败: %s", _ckpt_err)

        # 5. 成功 → _transition(STATE_RETRIEVING)
        self._transition(STATE_RETRIEVING)

    # ----------------------------------------------------------
    # 检索入口
    # ----------------------------------------------------------
    def _enter_retrieving(self) -> None:
        """进入检索阶段：调用 inject_related_context() 检索关联上下文，然后转移到执行状态。

        流程:
            1. 调用 inject_related_context() 检索关联上下文
            2. 检索成功 → _transition(STATE_EXECUTING)
            3. 检索失败 → 仍然 _transition(STATE_EXECUTING)（宽容策略）
        """

        # 0. 存档恢复：扫描 steps_summary 中的【存档:...】路径，恢复上下文
        from core.lib.gateway_helpers import restore_context_from_archive, inject_related_context
        for step_entry in self.steps_summary:
            if "【存档:" in str(step_entry):
                import re as _re
                m = _re.search(r'【存档:(.+?)】', str(step_entry))
                if m:
                    arc_path = m.group(1)
                    restored = restore_context_from_archive(arc_path)
                    if restored:
                        print(f"[ARCHIVE_RESTORE] restored {len(restored)} msgs from {arc_path}")

        # 1. 调用 inject_related_context() 检索关联上下文
        task_name = f"step_{self._step_number}"
        keywords = [task_name]
        result = inject_related_context(task_name, keywords)

        # 2. 漂移检测 → 自动纠正：调用 DriftDetector.auto_correct() 注入纠正提示
        from core.lib.v8.drift_detector import DriftDetector
        goal = (
            getattr(self.orchestrator, "goal", None)
            or getattr(self.orchestrator, "task_goal", None)
            or ""
        )
        output = ""
        if self.messages:
            last = self.messages[-1]
            output = last.get("content", "") if isinstance(last, dict) else str(last)
        if goal and output:
            try:
                drift = DriftDetector().auto_correct(goal, output)
                if drift["detected"]:
                    prompt = drift["correction_prompt"]
                    print(f"[DRIFT_CORRECT] {prompt}")
                    # 注入纠正提示到消息上下文，供后续执行步骤参考
                    self.messages.append({"role": "system", "content": prompt})
                    self.steps_summary.append(prompt)
            except Exception as exc:
                logger.warning(f"[DRIFT_CORRECT] auto_correct 调用失败: {exc}")

        # 3. 检索成功 → _transition(STATE_EXECUTING)
        # 4. 检索失败 → 仍然 _transition(STATE_EXECUTING)（宽容策略）
        self._transition(STATE_EXECUTING)

    # ----------------------------------------------------------
    # 暂停 / 恢复
    # ----------------------------------------------------------
    def pause(self) -> None:
        """从 EXECUTING / COMPRESSING / RETRIEVING 进入 PAUSED 状态。"""
        if self._state not in (STATE_EXECUTING, STATE_COMPRESSING, STATE_RETRIEVING):
            raise ValueError(
                f"非法暂停: 当前状态 {self._state}，"
                f"仅允许从 {STATE_EXECUTING}/{STATE_COMPRESSING}/{STATE_RETRIEVING} 暂停"
            )
        self._previous_state = self._state
        self._state = STATE_PAUSED
        self._updated_at = datetime.utcnow().isoformat()

    def resume(self) -> None:
        """从 PAUSED 恢复到暂停前的状态。"""
        if self._state != STATE_PAUSED:
            raise ValueError(
                f"非法恢复: 当前状态 {self._state}，仅 PAUSED 状态可以恢复"
            )
        if self._previous_state is None:
            raise ValueError("无法恢复: 丢失暂停前状态记录")
        self._state = self._previous_state
        self._previous_state = None
        self._updated_at = datetime.utcnow().isoformat()

    # ----------------------------------------------------------
    # 检查点
    # ----------------------------------------------------------
    def _write_checkpoint(self, step_number: int, extra: Optional[Dict[str, Any]] = None) -> dict:
        """记录检查点。

        Args:
            step_number: 当前步骤号
            extra: 可选的额外信息

        Returns:
            检查点数据字典
        """
        checkpoint = {
            "step_number": step_number,
            "state": self._state,
            "timestamp": datetime.utcnow().isoformat(),
            "extra": extra or {},
        }
        self._checkpoints.append(checkpoint)
        return checkpoint

    # ----------------------------------------------------------
    # 序列化
    # ----------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "state": self._state,
            "previous_state": self._previous_state,
            "step_number": self._step_number,
            "checkpoints": self._checkpoints,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
        }

    def to_json(self, **kwargs) -> str:
        return json.dumps(self.to_dict(), **kwargs)

    def __repr__(self) -> str:
        return (
            f"<LongLoopStateMachine task={self.task_id} "
            f"state={self._state} step={self._step_number}>"
        )


    # ----------------------------------------------------------
    # 错误处理
    # ----------------------------------------------------------
    def _enter_error(self) -> None:
        """进入错误状态：累计错误次数，记录失败模式，决定重试/切换方案/放弃。

        流程:
            1. self._error_count += 1
            2. 记录失败模式 (tool_name, file_path, error_type)
            3. 同一组合连续失败 2 次 → 注入换方案提示
            4. 连续 3 次 → 跳过当前步骤
        """
        self._error_count += 1
        # V9 修复: 累计错误 >= 5 次 -> 放弃执行，进入 DONE，避免 error<->executing 死循环
        if self._error_count >= 5:
            logger.warning(f"[LONG_LOOP] 任务 {self.task_id} 累计错误 {self._error_count} 次，放弃执行")
            self._transition(STATE_DONE)
            return
        
        # #172 失败模式识别
        if not hasattr(self, '_fail_patterns'):
            self._fail_patterns = {}
        
        _tool = getattr(self, '_last_fail_tool', 'unknown')
        _path = getattr(self, '_last_fail_path', '')
        _err = getattr(self, '_last_fail_error', '')
        _key = (_tool, _path, _err)
        
        if _key in self._fail_patterns:
            self._fail_patterns[_key] += 1
        else:
            self._fail_patterns[_key] = 1
        
        _count = self._fail_patterns[_key]
        
        if _count >= 3:
            # 连续 3 次同一失败 → 跳过当前步骤
            logger.warning(f"[LONG_LOOP] 步骤 {self._step_number} 连续 {_count} 次失败({_tool} {_path})，跳过")
            self._exec_step += 1
            self._fail_patterns[_key] = 0  # 重置，让下一步可以重试
            self._transition(STATE_EXECUTING)
        elif _count >= 2:
            # 第 2 次失败 → 注入换方案提示
            logger.warning(f"[LONG_LOOP] 步骤 {self._step_number} 第 {_count} 次失败({_tool} {_path})，提示换方案")
            if hasattr(self, 'messages') and self.messages:
                self.messages.append({
                    "role": "system",
                    "content": f"[系统] 前{_count}次使用 {_tool} 操作 {_path} 均失败({_err})，请换一种方式。"
                })
            self._transition(STATE_EXECUTING)
        else:
            self._transition(STATE_EXECUTING)

    def _build_final_report(self) -> dict:
        """收集执行结果，组装最终报告（run() 进入 DONE 后调用）。

        流程:
            1. 从 self.steps_summary 收集所有步骤摘要
            2. 从 self.plan_data 获取原始计划（任务名、总步数）
            3. 组装最终报告：任务名、总步数、成功/失败步骤、每步摘要
            4. 将 step=-1 条目写入 self.steps_summary，同时返回报告供调用方使用
        """
        plan = self.plan_data or {}
        tasks: List[dict] = plan.get("tasks", [])
        total_steps = len(tasks)

        # 1. 任务名：优先取计划中的 name/title/task_name，兜底 task_id
        task_name = (
            plan.get("name")
            or plan.get("title")
            or plan.get("task_name")
            or self.task_id
        )

        # 2. 组装每步摘要，区分成功/失败步骤
        succeeded_steps: List[dict] = []
        failed_steps: List[dict] = []
        steps: List[dict] = []
        for idx, task in enumerate(tasks, start=1):
            status = str(task.get("status", "")).lower()
            if not status:
                status = "success" if task.get("output") else "failed"
            step_entry = {
                "step": idx,
                "title": task.get("title") or task.get("name") or f"step_{idx}",
                "status": status,
                "output": task.get("output", ""),
                "summary": (
                    self.steps_summary[idx - 1]
                    if idx - 1 < len(self.steps_summary)
                    else ""
                ),
            }
            steps.append(step_entry)
            if status in ("success", "done", "completed", "succeeded", "ok"):
                succeeded_steps.append(step_entry)
            else:
                failed_steps.append(step_entry)

        report = {
            "task_name": task_name,
            "task_id": self.task_id,
            "total_steps": total_steps,
            "succeeded": len(succeeded_steps),
            "failed": len(failed_steps),
            "succeeded_steps": succeeded_steps,
            "failed_steps": failed_steps,
            "steps": steps,
            "step_summaries": list(self.steps_summary),
            "state": self._state,
            "generated_at": datetime.utcnow().isoformat(),
        }

        # 3. 写入 steps_summary（step=-1 表示最终报告）
        self.steps_summary.append(
            json.dumps(
                {"step": -1, "type": "final_report", "report": report},
                ensure_ascii=False,
            )
        )
        logging.info(
            "[FINAL_REPORT] task=%s total=%d success=%d failed=%d",
            task_name,
            total_steps,
            len(succeeded_steps),
            len(failed_steps),
        )
        self.final_report = report
        return report

    # ----------------------------------------------------------
    # 心跳检测（#156）
    # ----------------------------------------------------------
    def _load_heartbeat_minutes(self) -> int:
        """从 audit_rules.yaml 读取心跳间隔（分钟），默认 30。

        优先读取 long_loop.heartbeat_minutes，其次 monitoring.heartbeat_minutes、
        顶层 heartbeat_minutes；读取失败或未配置时回退默认值 30。
        """
        default = 30
        try:
            from pathlib import Path
            import yaml
            candidates = [
                Path("config/v8/audit_rules.yaml"),  # cwd 相对路径（与 billing_hook 一致）
                Path(__file__).resolve().parents[3] / "config" / "v8" / "audit_rules.yaml",
            ]
            cfg = None
            for path in candidates:
                if path.exists():
                    with open(path, "r", encoding="utf-8") as f:
                        cfg = yaml.safe_load(f) or {}
                    break
            if not cfg:
                return default
            value = (
                (cfg.get("long_loop") or {}).get("heartbeat_minutes")
                or (cfg.get("monitoring") or {}).get("heartbeat_minutes")
                or cfg.get("heartbeat_minutes")
            )
            return int(value) if value else default
        except Exception:
            return default

    def _heartbeat_expired(self) -> bool:
        """距离上次活动是否已超过 _heartbeat_minutes 分钟。"""
        return (time.time() - self._last_activity_at) > (self._heartbeat_minutes * 60)

    # ----------------------------------------------------------
    # 主循环
    # ----------------------------------------------------------
    def run(self, user_input: str, user_id: str) -> dict:
        """运行长循环状态机主循环。

        流程:
            1. 从 IDLE → _enter_planning；若处于 PAUSED（心跳暂停）则 resume() 从断点继续
            2. while state != DONE: 根据当前状态调用对应 _enter_* 方法
            3. 每步执行前检查心跳：超过 _heartbeat_minutes 无活动 → 保存断点并刷新活动时间，继续执行（不中断）
            4. 异常时 _error_count += 1，进入 ERROR
            5. 进入 DONE 后收集执行结果，生成最终报告并返回
        """
        # 1. 初始化错误计数；PAUSED 状态自动恢复断点，否则 IDLE → _enter_planning
        self._error_count = 0
        if self._state == STATE_PAUSED:
            self.resume()  # 心跳暂停后恢复，从断点继续
        else:
            self._enter_planning(user_input, user_id)
        self._last_activity_at = time.time()

        # 2. while state != DONE: 根据当前状态调用对应 _enter_* 方法
        while self._state != STATE_DONE and self._step_number < 1000:  # V9 修复: 1000 步兜底，防止死循环
            try:
                # 2.1 每步执行前检查心跳：超过 _heartbeat_minutes 无活动 → 保存断点并继续执行（不中断）
                if self._heartbeat_expired():
                    if self._state in (STATE_EXECUTING, STATE_COMPRESSING, STATE_RETRIEVING):
                        self._write_checkpoint(
                            self._step_number,
                            {
                                "reason": "heartbeat_timeout",
                                "heartbeat_minutes": self._heartbeat_minutes,
                                "last_activity_at": self._last_activity_at,
                            },
                        )
                        self._last_activity_at = time.time()
                        logging.info(
                            f"[LONG_LOOP] {self.task_id} 心跳超时"
                            f"({self._heartbeat_minutes}分钟无活动) → 已保存断点 step={self._step_number}，继续执行"
                        )
                if self._state == STATE_PLANNING:
                    pass
                elif self._state == STATE_EXECUTING:
                    self._enter_executing()
                elif self._state == STATE_COMPRESSING:
                    self._enter_compressing()
                elif self._state == STATE_RETRIEVING:
                    self._enter_retrieving()
                elif self._state == STATE_ERROR:
                    self._enter_error()
                elif self._state == STATE_PAUSED:
                    break
                elif self._state == STATE_IDLE:
                    break
                # 2.2 步骤执行完成即视为一次活动，刷新心跳时间
                self._last_activity_at = time.time()
            except Exception:
                self._error_count += 1
                self._state = STATE_ERROR

        # 3. DONE 后收集执行结果，生成最终报告
        self.final_report = self._build_final_report()
        return self.final_report

# ============================================================
# 任务队列 + 检查点恢复
# ============================================================

    @classmethod
    def from_checkpoint(cls, queue_file: str = "data/v8/task_queue.json", orchestrator=None):
        """从任务队列恢复未完成任务。

        读取 queue_file（TaskQueue 持久化的 JSON 数组）：
        - 存在未完成任务（status != "done"）→ 取最后一个，恢复其检查点并继续执行
        - 无未完成任务 → 返回 None

        Returns:
            LongLoopStateMachine | None: 恢复后的状态机实例；无未完成任务时返回 None
        """
        import os
        if not os.path.exists(queue_file):
            return None
        try:
            with open(queue_file, "r", encoding="utf-8") as f:
                tasks = json.load(f)
        except Exception as exc:
            logger.warning(f"[LONG_LOOP] 读取任务队列失败 {queue_file}: {exc}")
            return None
        if not isinstance(tasks, list):
            return None

        unfinished = [t for t in tasks if t.get("status") != "done"]
        if not unfinished:
            return None

        # 取最后一个未完成任务（含其保存的检查点）
        task = unfinished[-1]
        task_id = task.get("task_id") or task.get("id")
        if not task_id:
            return None
        machine = cls(
            task_id=task_id,
            session_id=task.get("session_id", ""),
            user_id=task.get("user_id", ""),
            orchestrator=orchestrator,
        )

        # 恢复检查点：最近一次 checkpoint 的 step_number/state，并回填 checkpoints 列表
        checkpoint = task.get("checkpoint") or {}
        if checkpoint:
            machine._step_number = int(checkpoint.get("step_number", 0))
            saved_state = checkpoint.get("state")
            if saved_state in ALL_STATES:
                machine._state = saved_state
            machine._checkpoints = list(checkpoint.get("checkpoints") or [])

        # 检查点恢复后一律视为 PAUSED，run() 会通过 resume() 从断点继续
        machine._state = STATE_PAUSED
        user_input = task.get("user_input") or ""
        user_id = task.get("user_id") or ""
        try:
            report = machine.run(user_input, user_id)
            # 执行完成 → 标记任务已完成
            task["status"] = "done"
            task["report"] = report
            with open(queue_file, "w", encoding="utf-8") as f:
                json.dump(tasks, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.warning(f"[LONG_LOOP] 任务 {task_id} 恢复执行失败: {exc}")
        return machine


class TaskQueue:
    """长循环任务队列：添加任务并持久化，逐个执行 LongLoopStateMachine。"""

    def __init__(self, queue_file: str = "data/v8/task_queue.json") -> None:
        self.queue_file = queue_file
        self.tasks: List[Dict] = []
        self._load()

    # ----------------------------------------------------------
    # 持久化
    # ----------------------------------------------------------
    def _load(self) -> None:
        import os
        if not os.path.exists(self.queue_file):
            self.tasks = []
            return
        try:
            with open(self.queue_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.tasks = data if isinstance(data, list) else []
        except Exception as exc:
            logger.warning(f"[TASK_QUEUE] 读取队列失败 {self.queue_file}: {exc}")
            self.tasks = []

    def _persist(self) -> None:
        from pathlib import Path
        Path(self.queue_file).parent.mkdir(parents=True, exist_ok=True)
        with open(self.queue_file, "w", encoding="utf-8") as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=2)

    # ----------------------------------------------------------
    # 队列操作
    # ----------------------------------------------------------
    def add_task(self, task: dict) -> dict:
        """添加任务并持久化到 queue_file。

        Args:
            task: 任务字典，至少包含 task_id / user_input / user_id /
                  session_id；可携带 checkpoint（检查点恢复时使用）

        Returns:
            写入后的任务字典（含 status=pending）
        """
        entry = dict(task)
        entry.setdefault("status", "pending")
        entry.setdefault("created_at", datetime.utcnow().isoformat())
        self.tasks.append(entry)
        self._persist()
        return entry

    def run_all(self, orchestrator=None) -> List[dict]:
        """逐个执行 LongLoopStateMachine.run()，完成自动取下一个。

        Args:
            orchestrator: 可选编排器，透传给 LongLoopStateMachine

        Returns:
            执行结果列表（每个任务一条，含 task_id / status / report）
        """
        results: List[dict] = []
        # 逐个取出未完成任务执行，完成后自动取下一个
        while True:
            pending = [t for t in self.tasks if t.get("status") != "done"]
            if not pending:
                break
            task = pending[0]
            task_id = task.get("task_id") or task.get("id")
            if not task_id:
                # 无 task_id 的脏任务：跳过避免死循环
                task["status"] = "done"
                task["error"] = "missing task_id"
                self._persist()
                continue
            machine = LongLoopStateMachine(
                task_id=task_id,
                session_id=task.get("session_id", ""),
                user_id=task.get("user_id", ""),
                orchestrator=orchestrator or task.get("orchestrator"),
            )
            user_input = task.get("user_input") or ""
            user_id = task.get("user_id") or ""
            try:
                report = machine.run(user_input, user_id)
                task["status"] = "done"
                task["report"] = report
                task["checkpoint"] = machine.to_dict()
                results.append({"task_id": task_id, "status": "done", "report": report})
                logger.info(f"[TASK_QUEUE] 任务完成 {task_id}，继续下一个")
            except Exception as exc:
                task["status"] = "error"
                task["error"] = str(exc)
                task["checkpoint"] = machine.to_dict()
                results.append({"task_id": task_id, "status": "error", "error": str(exc)})
                logger.warning(f"[TASK_QUEUE] 任务失败 {task_id}: {exc}")
            self._persist()
        return results
