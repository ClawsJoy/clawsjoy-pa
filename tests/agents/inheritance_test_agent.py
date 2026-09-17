"""传承测试 Agent - 验证经验是否能被实际使用"""

from typing import Dict, Optional

from core.agents.base.base_agent import BaseAgent


class InheritanceTestAgent(BaseAgent):
    """传承测试 Agent"""

    name = "inheritance_test_agent"
    description = "用于测试传承系统的 Agent"
    type = "test"

    def on_init(self):
        self.log("传承测试 Agent 初始化完成")

    def process(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        """处理用户输入 - 使用传承的经验"""
        self._update_stats()

        # 尝试从传承系统中获取最佳经验
        best_exp = self.get_best_experience()

        if best_exp:
            # 使用经验生成响应
            exp_type = best_exp.type
            exp_content = best_exp.content

            if exp_type == "pattern":
                response = f"根据学习到的模式: {exp_content.get('keyword', '未知')}"
            elif exp_type == "rule":
                response = f"根据规则: {exp_content.get('condition', '未知')} -> {exp_content.get('action', '执行')}"
            elif exp_type == "strategy":
                response = f"根据策略: {exp_content.get('rule', '优先处理')}"
            else:
                response = f"使用经验: {exp_type}"

            # 记录使用结果（成功）
            self.reinforce_experience(best_exp.id, success=True)

            return {
                "success": True,
                "response": response,
                "user_id": self.user_id,
                "experience_used": best_exp.id,
                "experience_type": best_exp.type,
                "experience_confidence": best_exp.confidence,
            }
        else:
            return {
                "success": True,
                "response": "暂无可用经验，请先学习",
                "user_id": self.user_id,
            }
