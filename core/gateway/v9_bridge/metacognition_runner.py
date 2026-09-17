# -*- coding: utf-8 -*-
"""元认知审查 runner（S1，从 _v9_bridge_loop 归位，2026-09-12）。

复用 Metacognition + GLM 做任务复盘，SelfUpgradingAgent 消费 hypothesis 生成 auto_fix_suggestion。

契约：
- run_metacognition_review(*, messages, user_id, session_id) -> dict
  纯函数（除 meta.reflect/evolve + extractor.upsert_entity 的落库副作用）。
  返回 state dict（当前调用方丢弃——历史行为：元认知结论未被持久化，见体检）。
"""

import json
import os
from datetime import datetime


def _extract_intent(content: str) -> dict:
    """从 Agent 输出中提取任务意图"""
    plan_keywords = ["阶段", "步骤", "先做", "开发路线", "推荐", "建议"]
    if not any(kw in content for kw in plan_keywords):
        return None

    import re

    files = list(set(re.findall(r"`?([\w-]+/[\w-]+\.py)`?", content)))

    return {
        "source": "agent_plan",
        "files": files,
        "summary": content[:500],
        "extracted_at": datetime.now().isoformat(),
    }


def run_metacognition_review(*, messages, user_id, session_id):
    """元认知审查：Metacognition 复盘 + SelfUpgradingAgent 消费 + 意图提取。"""
    state = {}
    try:
        glm_key = os.getenv("GLM_API_KEY", "")
        if glm_key and len(messages) > 1:
            from core.lib.metacognition import Metacognition

            meta = Metacognition(f"agent_{user_id}")

            last_user = ""
            for m in reversed(messages):
                if m["role"] == "user":
                    last_user = m.get("content", "")[:200]
                    break

            behavior_log = []
            for m in messages[-15:]:
                if m["role"] == "tool":
                    behavior_log.append(m.get("content", "")[:100])
                elif m["role"] == "assistant" and m.get("content"):
                    behavior_log.append(f"Agent: {m['content'][:80]}")

            reflection = meta.reflect(
                user_input=last_user,
                response=f"Agent完成 {len(messages)} 轮对话",
            )

            # SelfUpgradingAgent 消费 system_hypothesis
            try:
                from core.agents.builtin.self_upgrading_agent import SelfUpgradingAgent

                upgrader = SelfUpgradingAgent()
                hypotheses = upgrader.consume_hypothesis(limit=20)
                auto_fixes = upgrader.should_auto_fix(hypotheses)
                if auto_fixes:
                    state["auto_fixes"] = auto_fixes
                    print(f"[V9] SelfUpgradingAgent 发现 {len(auto_fixes)} 个可自动修复的问题")
                    for _fix in auto_fixes:
                        try:
                            from core.lib.code_entity_extractor import extractor

                            extractor.upsert_entity(
                                {
                                    "entity_type": "auto_fix_suggestion",
                                    "entity_name": f'auto_fix::{_fix["problem_type"]}',
                                    "signature": json.dumps(_fix, ensure_ascii=False),
                                    "related_entities": [
                                        _fix["problem_type"],
                                        _fix.get("suggested_action", {}).get("target", "unknown"),
                                    ],
                                    "file_path": "",
                                }
                            )
                        except Exception:
                            pass
            except Exception as _e_up:
                print(f"[V9] SelfUpgradingAgent 消费失败: {_e_up}")

            if len(meta.reflections) >= 10:
                evolution = meta.evolve()
                if evolution.get("suggestions"):
                    state["optimization_tips"] = "; ".join(evolution["suggestions"])
            if reflection.get("task_pattern"):
                state["last_task_pattern"] = reflection["task_pattern"]

            # ★ 新增：意图提取
            last_assistant_msg = ""
            for m in reversed(messages):
                if m["role"] == "assistant" and m.get("content"):
                    last_assistant_msg = m["content"]
                    break

            intent = _extract_intent(last_assistant_msg)
            if intent:
                state["intent_model"] = intent

            state["last_review"] = datetime.now().isoformat()
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"[V9] 元认知审查失败: {e}")
        from core.lib.os_event_logger import write_os_event

        write_os_event(
            event_type="intercept",
            operation="execute",
            os_action="blocked",
            reason="metacognition_failed",
            command="Metacognition.reflect",
            detail={"error": "silent pass"},
            session_id=locals().get("session_id", ""),
            task_id=locals().get("task_id", ""),
        )
    return state
