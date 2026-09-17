"""cu_learning 工具插件 — Computer Use 学习循环 + SOP 生成器(P4)。

包装 core/lib/gateway_helpers._handle_cu_learning; 计划默认落 data/computer_use/plans/
(cwd 相对; 网关任务可传 plan_dir 指向沙箱 data)。SOP 尽力写 vault ComputerUseSOPs/。
"""
from core.tools.base import ToolPlugin
from core.lib.gateway_helpers import _handle_cu_learning, _get_default_tools

CU_LEARNING_SCHEMA = next(
    (t for t in _get_default_tools() if t.get("function", {}).get("name") == "cu_learning"),
    None,
)


class CuLearningPlugin(ToolPlugin):
    name = "cu_learning"
    quota = 20
    schema = CU_LEARNING_SCHEMA

    def execute(self, args: dict, ctx) -> dict:
        return _handle_cu_learning(args or {})
