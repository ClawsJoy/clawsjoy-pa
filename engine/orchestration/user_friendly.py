"""用户友好的任务编排 - 对话式、可中断、可恢复"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, List, Optional


class UserChoice(Enum):
    """用户决策选项"""

    CONTINUE = "continue"
    RETRY = "retry"
    SKIP = "skip"
    ADJUST = "adjust"
    ROLLBACK = "rollback"
    PAUSE = "pause"
    RESUME = "resume"


@dataclass
class UserFriendlyTask:
    """用户友好的任务定义"""

    name: str
    description: str  # 用户可读的描述
    agent: str
    action: str
    params: Dict
    estimated_time: int = 10  # 预估时间（秒）
    can_skip: bool = False
    can_retry: bool = True
    requires_confirmation: bool = False  # 是否需要用户确认

    # 用户交互
    on_start: Optional[str] = None  # 开始时的提示
    on_complete: Optional[str] = None  # 完成时的提示
    on_error: Optional[str] = None  # 错误时的提示
    confirm_message: Optional[str] = None  # 确认信息


class UserFriendlyOrchestrator:
    """用户友好的编排器"""

    def __init__(self, user_callback: Callable):
        """
        user_callback: 用户交互回调函数
                     返回 (choice, data)
        """
        self.user_callback = user_callback
        self.current_plan = None
        self.checkpoints = {}

    def create_video_plan(self, topic: str) -> List[UserFriendlyTask]:
        """创建视频制作计划（用户可理解）"""
        return [
            UserFriendlyTask(
                name="understand",
                description=f"理解需求：制作关于「{topic}」的视频",
                agent="chat_agent",
                action="understand",
                params={"topic": topic},
                estimated_time=5,
                requires_confirmation=False,
                on_start="🤔 让我理解一下你的需求...",
            ),
            UserFriendlyTask(
                name="collect",
                description="📦 收集素材（图片、视频片段）",
                agent="video_agent",
                action="search",
                params={"keyword": topic},
                estimated_time=30,
                can_skip=False,
                requires_confirmation=False,
                on_start="🔍 正在搜索相关素材...",
                on_complete="✅ 素材收集完成，共找到 15 个可用素材",
                on_error="⚠️ 素材收集失败，是否重试或更换关键词？",
            ),
            UserFriendlyTask(
                name="script",
                description="✍️ 生成视频脚本",
                agent="writer_agent",
                action="write",
                params={"topic": topic},
                estimated_time=20,
                requires_confirmation=False,
                on_start="📝 正在撰写脚本...",
                on_complete="✅ 脚本生成完成，请审阅",
            ),
            UserFriendlyTask(
                name="voice",
                description="🎤 制作配音",
                agent="audio_agent",
                action="tts",
                params={},
                estimated_time=15,
                can_skip=True,
                requires_confirmation=True,
                confirm_message="是否需要配音？",
                on_start="🔊 正在生成配音...",
                on_complete="✅ 配音完成",
            ),
            UserFriendlyTask(
                name="edit",
                description="✂️ 剪辑视频",
                agent="video_agent",
                action="edit",
                params={},
                estimated_time=60,
                requires_confirmation=False,
                on_start="🎬 正在剪辑视频，请稍候...",
                on_complete="✅ 视频剪辑完成",
            ),
            UserFriendlyTask(
                name="subtitle",
                description="📝 添加字幕",
                agent="video_agent",
                action="subtitle",
                params={},
                estimated_time=10,
                can_skip=True,
                requires_confirmation=True,
                confirm_message="是否需要添加字幕？",
                on_start="📝 正在生成字幕...",
                on_complete="✅ 字幕已添加",
            ),
        ]

    def execute_with_feedback(self, tasks: List[UserFriendlyTask]) -> Dict:
        """执行任务并实时反馈"""
        results = []

        for i, task in enumerate(tasks):
            # 发送开始消息
            if task.on_start:
                self._notify(task.on_start)

            # 需要确认
            if task.requires_confirmation:
                choice = self._ask_user(
                    task.confirm_message or f"是否执行「{task.description}」？"
                )
                if choice == UserChoice.SKIP:
                    self._notify(f"⏭️ 已跳过: {task.name}")
                    continue
                elif choice == UserChoice.ROLLBACK:
                    self._rollback(results)
                    return {"success": False, "reason": "用户取消"}

            # 执行任务
            try:
                result = self._execute_task(task)
                results.append({"task": task.name, "success": True, "result": result})

                # 保存检查点
                self._save_checkpoint(i, results)

                # 完成通知
                if task.on_complete:
                    self._notify(task.on_complete)

            except Exception as e:
                # 错误处理
                error_msg = task.on_error or f"❌ 任务失败: {task.name}"
                self._notify(error_msg)

                # 询问用户如何处理
                choice = self._ask_user(
                    f"任务「{task.description}」失败了，是否重试？",
                    options=["重试", "跳过", "回滚", "暂停"],
                )

                if choice == UserChoice.RETRY:
                    # 重试当前任务
                    continue
                elif choice == UserChoice.SKIP:
                    self._notify(f"⏭️ 已跳过: {task.name}")
                    continue
                elif choice == UserChoice.ROLLBACK:
                    self._rollback(results)
                    return {"success": False, "reason": "用户回滚"}
                elif choice == UserChoice.PAUSE:
                    self._pause()
                    return {"success": False, "reason": "用户暂停"}

            # 进度显示
            self._show_progress(i + 1, len(tasks))

        return {"success": True, "results": results}

    def _execute_task(self, task: UserFriendlyTask):
        """执行具体任务（需对接实际 Agent）"""
        # TODO: 对接实际 Agent
        print(f"  执行中: {task.action}...")
        return {"status": "ok"}

    def _notify(self, message: str):
        """通知用户"""
        print(message)

    def _ask_user(self, message: str, options: List[str] = None) -> UserChoice:
        """询问用户"""
        if options:
            print(f"\n{message}")
            print(f"选项: {', '.join(options)}")
        else:
            print(f"\n{message} (y/n)")

        # 这里应该调用实际的用户输入
        # 简化版返回默认
        return UserChoice.CONTINUE

    def _show_progress(self, current: int, total: int):
        """显示进度"""
        percent = int(current / total * 100)
        bar = "█" * (percent // 5) + "░" * (20 - percent // 5)
        print(f"\n进度: [{bar}] {percent}% ({current}/{total})")

    def _save_checkpoint(self, index: int, results: List):
        """保存检查点"""
        self.checkpoints["last_index"] = index
        self.checkpoints["results"] = results
        self.checkpoints["timestamp"] = datetime.now().isoformat()

    def _rollback(self, results: List):
        """回滚"""
        self._notify("🔄 正在回滚...")
        # 反向执行回滚操作
        for task_result in reversed(results):
            self._notify(f"  撤销: {task_result['task']}")

    def _pause(self):
        """暂停"""
        self._notify("⏸️ 任务已暂停，输入「继续」恢复执行")


# 使用示例
if __name__ == "__main__":
    orch = UserFriendlyOrchestrator(user_callback=None)
    tasks = orch.create_video_plan("AI技术趋势")

    print("=" * 50)
    print("📋 任务计划")
    print("=" * 50)
    for i, task in enumerate(tasks, 1):
        print(f"{i}. {task.description} ({task.estimated_time}秒)")

    print("\n开始执行...\n")
    result = orch.execute_with_feedback(tasks)
    print(f"\n结果: {result}")
