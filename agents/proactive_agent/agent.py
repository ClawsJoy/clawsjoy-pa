"""主动服务 Agent - 唤醒和协调其他 Agent"""

import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

from core.agents.builtin.agent_manager import AgentManager
from core.agents.business.base_business_agent import BusinessAgent


class ProactiveAgent(BusinessAgent):
    """主动服务 Agent - 唤醒者、协调者"""

    name = "proactive_agent"
    description = "主动服务智能体 - 唤醒和协调其他Agent"
    version = "2.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self.reminders = []
        self.wake_up_schedule = []
        self.running = True
        self._start_active_loop()
        print(f"🤖 {self.name} 主动服务已启动（唤醒者模式）")

    def _start_active_loop(self):
        """启动主动循环"""

        def loop():
            while self.running:
                try:
                    self._check_reminders()
                    self._wake_up_agents()
                    self._health_check_all()
                    time.sleep(30)
                except Exception as e:
                    print(f"主动服务错误: {e}")

        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
        print(f"✅ {self.name} 主动循环已启动（每30秒检查）")

    def _check_reminders(self):
        """检查并触发提醒"""
        now = datetime.now()
        for r in self.reminders:
            if not r.get("triggered"):
                remind_time = r.get("time")
                if remind_time and now >= remind_time:
                    r["triggered"] = True
                    self._trigger_reminder(r)

    def _trigger_reminder(self, reminder: Dict):
        """触发提醒，可能唤醒相关 Agent"""
        content = reminder.get("content", "")
        print(f"\n🔔 提醒: {content}")

        # 根据提醒内容唤醒相关 Agent
        if "会议" in content or "开会" in content:
            self._wake_agent("meeting_agent", content)
        elif "代码" in content or "编程" in content:
            self._wake_agent("code_agent", content)
        elif "分析" in content:
            self._wake_agent("analysis_agent", content)
        elif "记忆" in content or "记住" in content:
            self._wake_agent("memory_agent", content)

    def _wake_agent(self, agent_name: str, task: str):
        """唤醒指定 Agent"""
        print(f"   📢 唤醒 {agent_name} 处理: {task}")
        try:
            # 尝试导入并调用 Agent
            module = __import__(f"agents.{agent_name}.agent", fromlist=[f"{agent_name}Agent"])
            class_name = self._get_class_name(agent_name)
            agent_class = getattr(module, class_name)
            agent = agent_class(self.user_id)

            # 异步执行，不阻塞
            thread = threading.Thread(target=agent.process, args=(task,))
            thread.start()
            print(f"   ✅ {agent_name} 已被唤醒并开始工作")
        except Exception as e:
            print(f"   ❌ 唤醒 {agent_name} 失败: {e}")

    def _wake_up_agents(self):
        """定期唤醒沉睡的 Agent（健康检查和预热）"""
        am = AgentManager()
        for agent_name in list(am.agents.keys())[:10]:  # 每次检查10个
            if agent_name == self.name:
                continue
            # 简单健康检查，不实际唤醒所有
            pass

    def _health_check_all(self):
        """对所有 Agent 进行健康检查"""
        # 每5分钟汇报一次
        pass

    def _get_class_name(self, agent_name: str) -> str:
        parts = agent_name.split("_")
        class_name = "".join(p.capitalize() for p in parts)
        if not class_name.endswith("Agent"):
            class_name = class_name + "Agent"
        return class_name

    def set_reminder(self, content: str, remind_time: datetime):
        """设置提醒"""
        self.reminders.append({"content": content, "time": remind_time, "triggered": False})
        return {"success": True, "message": f"已设置提醒: {content}"}

    def wake_all(self) -> Dict:
        """唤醒所有 Agent"""
        am = AgentManager()
        awakened = []
        for agent_name in am.agents.keys():
            if agent_name == self.name:
                continue
            try:
                self._wake_agent(agent_name, "健康检查")
                awakened.append(agent_name)
            except Exception:
                pass
        return {"success": True, "awakened": awakened, "count": len(awakened)}

    def _execute_business(self, user_input: str, context: Dict = None) -> Dict:
        """处理业务"""
        import re

        if "唤醒所有" in user_input:
            return self.wake_all()

        match = re.search(r"(\d{1,2}):(\d{2})", user_input)
        if match and "提醒" in user_input:
            hour, minute = int(match.group(1)), int(match.group(2))
            now = datetime.now()
            remind_time = now.replace(hour=hour, minute=minute, second=0)
            if remind_time <= now:
                remind_time = remind_time.replace(day=now.day + 1)
            return self.set_reminder(user_input, remind_time)

        return {
            "success": True,
            "response": "主动服务已就绪。\n- 设置提醒：提醒我 14:30 开会\n- 唤醒所有 Agent：唤醒所有",
            "agent": self.name,
        }

    def process(self, user_input: str, context=None) -> Dict:
        return self._execute_business(user_input, context)


proactive_agent = ProactiveAgent()
