"""
ClawsJoy Robotics Agent - 延申版集成入口
符合 wisdom_factory 实例化接口
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging

from bridge.ros2_bridge import ROS2Bridge
from planner.planner import TaskPlanner
from world_model.world_model import WorldModel

logger = logging.getLogger(__name__)


class RoboticsAgentV4:
    """机器人认知引擎 - 符合 ClawsJoy Agent 接口"""

    def __init__(self, user_id="default", mock_mode=True, **kwargs):
        self.user_id = user_id
        self.mock_mode = mock_mode
        self.world_model = WorldModel()
        self.bridge = ROS2Bridge(mock_mode=mock_mode)
        self.planner = TaskPlanner(world_model=self.world_model, bridge=self.bridge)

        # 从硬件同步初始状态
        if mock_mode and hasattr(self.bridge, "hardware"):
            hw_objects = self.bridge.hardware.get_known_objects()
            self.world_model.sync_from_hardware(hw_objects)

        logger.info(f"🤖 Robotics Agent 已启动 (用户:{user_id}, 模式:{'模拟' if mock_mode else '真实'})")
        logger.info(f"   物体: {len(self.world_model.objects)} | 位置: {len(self.world_model.known_locations)}")

    def process(self, user_input: str, context=None) -> dict:
        """统一接口，与 cortex 兼容"""
        result = self.planner.plan(user_input)

        if result["success"]:
            return {
                "success": True,
                "response": f"✅ 完成任务，共执行 {result['steps']} 个动作",
                "steps": result["steps"],
                "details": result["results"],
            }
        else:
            return {
                "success": False,
                "response": f"❌ 执行失败于: {result.get('failed_at', '未知步骤')}",
                "error": result.get("error", ""),
            }

    def get_world_summary(self) -> dict:
        return self.world_model.summary()

    def shutdown(self):
        self.bridge.shutdown()
        logger.info("🤖 Robotics Agent 已关闭")


# 独立运行
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = RoboticsAgentV4(mock_mode=True)

    for task in ["拿水杯", "帮我拿遥控器", "巡逻"]:
        result = agent.process(task)
        status = "✅" if result["success"] else "❌"
        print(f"  {status} {task}: {result['response']}")

    agent.shutdown()
