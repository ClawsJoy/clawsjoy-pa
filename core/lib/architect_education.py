#!/usr/bin/env python3
"""Architect Education - Architect Education 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""把我的架构思维教给 LLM"""

import json
from datetime import datetime
from pathlib import Path

import requests


class ArchitectEducation:
    """架构师教育体系 - 把我的思考方法教给 LLM"""

    def __init__(self):
        self.ollama_url = "config_loader.get_ollama_url()"
        self.model = unified_config.get_llm_config().get(
            "fast_model",
            unified_config.get_llm_config().get(
                "fast_model",
                unified_config.get("llm.fast_model", get_llm_model(fast=True)),
            ),
        )
        self.lessons = []

    # ========== 课程1：系统化思维 ==========
    def teach_system_thinking(self, problem: str) -> str:
        """教 LLM 系统化思考"""
        prompt = f"""你是 ClawsJoy 系统的架构师。请用系统化思维分析问题。

问题：{problem}

你的思考框架：
1. 这个问题的边界是什么？（输入、输出、约束）
2. 涉及哪些组件？（列出所有相关组件）
3. 组件之间如何交互？（数据流、控制流）
4. 可能出问题的地方在哪里？（风险点）
5. 如何验证解决方案正确？

请按此框架输出分析。"""

        return self._call_llm(prompt)

    # ========== 课程2：分层思维 ==========
    def teach_layer_thinking(self, requirement: str) -> str:
        """教 LLM 分层设计"""
        prompt = f"""你是 ClawsJoy 架构师。请用分层思维设计解决方案。

需求：{requirement}

分析框架：
1. 用户层：用户如何交互？
2. 应用层：需要哪些功能模块？
3. 服务层：需要哪些服务？
4. 数据层：需要存储什么？
5. 基础设施层：需要什么支撑？

请逐层分析并输出设计方案。"""

        return self._call_llm(prompt)

    # ========== 课程3：权衡思维 ==========
    def teach_tradeoff_thinking(self, options: str, constraints: str) -> str:
        """教 LLM 做权衡决策"""
        prompt = f"""你是 ClawsJoy 架构师。请在约束下做出最优决策。

可选方案：{options}
约束条件：{constraints}

分析框架：
1. 各方案的优缺点是什么？
2. 哪些约束是硬性的？
3. 哪些可以妥协？
4. 推荐方案是什么？
5. 为什么推荐这个？

请输出决策分析。"""

        return self._call_llm(prompt)

    # ========== 课程4：演进思维 ==========
    def teach_evolution_thinking(self, current: str, target: str) -> str:
        """教 LLM 如何规划演进路线"""
        prompt = f"""你是 ClawsJoy 架构师。请规划演进路径。

当前状态：{current}
目标状态：{target}

分析框架：
1. 差距在哪里？（当前缺什么？）
2. 依赖关系是什么？（先做什么才能做后什么？）
3. 分几个阶段？每阶段做什么？
4. 每阶段如何验证成功？
5. 风险预案是什么？

请输出演进路线图。"""

        return self._call_llm(prompt)

    # ========== 课程5：故障思维 ==========
    def teach_fault_thinking(self, symptom: str) -> str:
        """教 LLM 如何排查问题"""
        prompt = f"""你是 ClawsJoy 架构师。请排查系统问题。

症状：{symptom}

排查框架：
1. 现象确认：具体表现是什么？
2. 可能原因：列出所有可能的原因
3. 排除法：用二分法缩小范围
4. 根因：最可能的原因
5. 修复方案：临时 + 长期
6. 预防措施：如何避免再次发生

请输出排查分析。"""

        return self._call_llm(prompt)

    # ========== 综合训练：真实问题 ==========
    def train_on_real_problems(self):
        """用 ClawsJoy 真实问题训练"""

        problems = [
            {"type": "system", "question": "ClawsJoy 如何实现多用户数据隔离？"},
            {"type": "performance", "question": "Agent 通信延迟高，如何优化？"},
            {"type": "security", "question": "如何保护用户隐私数据不被泄露？"},
            {"type": "scalability", "question": "如何设计系统支持 10000 并发用户？"},
        ]

        results = []
        for p in problems:
            print(f"\n📚 训练: {p['question']}")

            if p["type"] == "system":
                answer = self.teach_system_thinking(p["question"])
            elif p["type"] == "performance":
                answer = self.teach_fault_thinking(p["question"])
            else:
                answer = self.teach_layer_thinking(p["question"])

            results.append(
                {
                    "question": p["question"],
                    "answer": answer[:500],
                    "timestamp": datetime.now().isoformat(),
                }
            )

            print(f"✅ 完成\n{answer[:200]}...")

        # 保存训练结果
        with open(f"{get_data_root()}/architect_training.json", "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        return results

    def _call_llm(self, prompt: str) -> str:
        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 1000},
                },
                timeout=get_timeout("llm"),
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
        except Exception as e:
            print(f"调用失败: {e}")
        return ""


if __name__ == "__main__":
    print("=" * 60)
    print("架构师教育体系 - 把我的思维教给 LLM")
    print("=" * 60)

    educator = ArchitectEducation()

    # 开始训练
    results = educator.train_on_real_problems()

    print("\n" + "=" * 60)
    print(f"训练完成！共 {len(results)} 个案例")
    print("结果保存在 data/architect_training.json")
