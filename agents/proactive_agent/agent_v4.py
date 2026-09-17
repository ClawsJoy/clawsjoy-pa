#!/usr/bin/env python3
"""ProactiveAgent v4.2 - 精简稳定版（主动服务）"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import re
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

from core.agents.business.business_agent import BusinessAgent


class ProactiveAgentV4(BusinessAgent):
    """主动服务 Agent - 精简稳定版"""

    name = "proactive_agent_v4"
    description = "主动服务助手"
    version = "5.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self._reminders = []
        print(f"💡 ProactiveAgent v{self.version} 启动")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.85)

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        t = user_input.lower()

        if any(kw in t for kw in ["提醒", "闹钟"]):
            return self._set_reminder(user_input)

        if any(kw in t for kw in ["查看提醒", "我的提醒"]):
            return self._list_reminders()

        # 基于实际结果生成下一步建议
        if context and context.get("result_summary"):
            prompt = f"用户刚做了：{user_input}\n系统回复摘要：{context['result_summary']}\n\n根据以上信息，生成1-2条下一步行动建议。不要重复系统已经给出的信息。直接给出简短建议。"
            result = self._call_llm(prompt)
            if result and len(result) > 150:
                result = result[:150]
            if result and result.strip():
                return self._resp("💡 " + result.strip())

        # 降级：关键词匹配
        suggestions = []
        if "写" in t or "创作" in t:
            suggestions.append("需要我帮你续写小说吗？")
        if "漫剧" in t or "视频" in t:
            suggestions.append("需要导出素材到视频工具吗？")
        if "名字" in t or "我是" in t:
            suggestions.append("需要我记住你的偏好吗？")
        if not suggestions:
            suggestions.append("输入「提醒我」设置提醒")
            suggestions.append("输入「记住」保存信息")
        return self._resp("💡 " + " | ".join(suggestions[:3]))


    # ================================================================
    #  设置提醒
    # ================================================================

    def _set_reminder(self, user_input: str) -> Dict:
        # 解析时间
        time_match = re.search(r'(\d+)\s*(分钟|小时|秒)', user_input)
        if time_match:
            value, unit = int(time_match.group(1)), time_match.group(2)
            if "分钟" in unit:
                delta = timedelta(minutes=value)
            elif "小时" in unit:
                delta = timedelta(hours=value)
            else:
                delta = timedelta(minutes=5)
            remind_time = datetime.now() + delta
        else:
            remind_time = datetime.now() + timedelta(minutes=5)
        
        # 解析内容
        content = re.sub(r'(提醒我|设置提醒|闹钟)\s*\d+\s*(分钟|小时|秒)?', '', user_input).strip()
        if not content:
            content = "提醒事项"
        
        self._reminders.append({
            "id": len(self._reminders) + 1,
            "content": content,
            "time": remind_time.isoformat(),
            "status": "pending"
        })
        
        return self._resp(f"⏰ 提醒已设置\n\n📝 {content}\n⏰ {remind_time.strftime('%H:%M:%S')}")

    # ================================================================
    #  查看提醒
    # ================================================================

    def _list_reminders(self) -> Dict:
        pending = [r for r in self._reminders if r.get("status") == "pending"]
        if not pending:
            return self._resp("📭 暂无待提醒事项")
        
        lines = ["⏰ 我的提醒："]
        for r in pending:
            t = datetime.fromisoformat(r["time"]).strftime("%H:%M")
            lines.append(f"  {r['id']}. {r['content']} @ {t}")
        return self._resp("\n".join(lines))

    # ================================================================
    #  辅助
    # ================================================================

    def _resp(self, content: str, **kwargs) -> Dict:
        return {"success": True, "response": content, "output_content": content, **kwargs}


if __name__ == "__main__":
    agent = ProactiveAgentV4("test")
    print(agent.process("提醒我 5分钟后 喝水")["response"])       
