#!/usr/bin/env python3
"""长线任务循环端到端测试
1. 启动一个简单的长线任务（mock orchestrator，3 步任务）
2. 观察七态状态机的完整流转
3. 检查 steps_summary 表是否有 checkpoint 写入
"""
import json
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


# 防止 LLM 依赖：mock orchestrator
class MockOrchestrator:
    """最小 orchestrator：plan 返回固定 3 步任务，execute_task 直接置 output"""

    def __init__(self):
        self.goal = "写一篇 1000 字说明文"
        self.executed = []

    def plan(self, user_input, user_id, server_id="default"):
        return {
            "name": user_input,
            "tasks": [
                {"title": "撰写引言", "required_skill": "内容写作", "output_file": "intro.md", "status": "pending"},
                {"title": "撰写正文", "required_skill": "内容写作", "output_file": "body.md", "status": "pending"},
                {"title": "撰写结论", "required_skill": "内容写作", "output_file": "conclusion.md", "status": "pending"},
            ],
        }

    def execute_task(self, task_data):
        task_data["status"] = "success"
        task_data["output"] = f"已完成：{task_data['title']}"
        self.executed.append(task_data["title"])


def main():
    from core.lib.v8.long_loop_state_machine import ALL_STATES, LongLoopStateMachine

    orch = MockOrchestrator()
    sm = LongLoopStateMachine(
        task_id="e2e_test_001",
        session_id="session_e2e",
        user_id="tester",
        orchestrator=orch,
    )

    # 记录状态流转（patch _transition）
    transitions = []
    orig_transition = sm._transition

    def traced_transition(target):
        source = sm._state
        orig_transition(target)
        transitions.append(f"{source}→{target}")

    sm._transition = traced_transition

    print("=" * 60)
    print("STEP 1: 启动长线任务")
    report = sm.run("写一篇 1000 字说明文", "tester")

    print("\n" + "=" * 60)
    print("STEP 2: 七态状态机完整流转")
    print("初始状态:", "idle")
    print("状态转移序列:")
    for t in transitions:
        print("  ", t)
    print("最终状态:", sm.state)
    print("step_number:", sm.step_number, "| exec_step:", sm._exec_step)
    print("checkpoints(内存):", len(sm.checkpoints))
    print("steps_summary(内存):", len(sm.steps_summary))

    print("\n" + "=" * 60)
    print("STEP 3: 检查 steps_summary 表是否有 checkpoint 写入")
    import psycopg2

    from core.lib.code_entity_extractor import extractor

    conn = psycopg2.connect(extractor.db_url)
    cur = conn.cursor()
    cur.execute(
        "SELECT task_name, step_number, summary_json FROM steps_summary "
        "WHERE task_name LIKE '%%e2e%%' OR task_name LIKE '%%long_loop%%' "
        "ORDER BY id DESC LIMIT 20"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    print(f"steps_summary 表查询到 {len(rows)} 条相关记录:")
    for r in rows:
        print("  ", r[0], "| step:", r[1], "|", str(r[2])[:100])

    # 判定
    if rows:
        print("\n✅ checkpoint 已写入 steps_summary 表")
    else:
        print("\n❌ steps_summary 表无 checkpoint 写入（仅内存，未落库）")

    # 输出最终报告关键信息
    print("\n" + "=" * 60)
    print("最终报告:")
    print(
        json.dumps(
            {k: report.get(k) for k in ("task_name", "total_steps", "succeeded", "failed")},
            ensure_ascii=False,
            indent=2,
        )
    )

    # 清理测试任务记录（避免污染）
    conn = psycopg2.connect(extractor.db_url)
    cur = conn.cursor()
    cur.execute("DELETE FROM steps_summary WHERE task_name LIKE '%%e2e_test%%'")
    conn.commit()
    cur.close()
    conn.close()
    print("\n[cleanup] 已清理 e2e 测试产生的 steps_summary 记录")


if __name__ == "__main__":
    main()
