"""ExecutorAgent - 执行层"""

from typing import Dict, Optional

from core.agents.business.base_business_agent import BusinessAgent


class ExecutorAgent(BusinessAgent):
    name = "executor_agent"
    description = "任务执行器"
    version = "2.1.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        print(f"⚙️ ExecutorAgent v{self.version} 已上线")

    def _execute_business(self, user_input: str, context: Dict = None) -> Dict:
        """执行任务 - 调用大脑调度器(do_anything 已删除 bff9ce70, 功能不可用)"""
        # 审计记录: 记录不可用原因(避免 return 后死代码)
        _unavailable = {"success": False, "response": "executor_agent: do_anything 已删除，此功能不可用"}
        self.audit(
            action="execute_task",
            details={"input": user_input, "output": _unavailable},
            result=False,
        )
        return _unavailable

    def handle(self, user_input: str, context: dict = None) -> dict:
        """统一入口"""
        return self._execute_business(user_input, context)
