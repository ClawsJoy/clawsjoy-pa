#!/usr/bin/env python3
"""Metacognition - Metacognition 模块

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
"""元认知模块 - Agent 自我反思与进化"""

import json
import os
import threading
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class Metacognition:
    """元认知 - Agent 的自我意识"""

    VERSION = "1.0.0"

    def __init__(self, agent_id: str = "default"):
        self.agent_id = agent_id
        self.meta_dir = Path(f"{get_data_root()}/agents/{agent_id}/metacognition")
        self.meta_dir.mkdir(parents=True, exist_ok=True)
        self._save_lock = threading.Lock()

        self.reflections_file = self.meta_dir / "reflections.json"
        self.evolutions_file = self.meta_dir / "evolutions.json"
        self._load()

    def _load(self):
        # 加载反思记录(JSON 损坏容错, 2026-09-07)
        self.reflections = self._load_json_tolerant(self.reflections_file, "reflections")
        # 加载进化记录(JSON 损坏容错)
        self.evolutions = self._load_json_tolerant(self.evolutions_file, "evolutions")

    @staticmethod
    def _load_json_tolerant(path, kind):
        """JSON 容错加载: 解析失败/结构异常 → 备份 + 重建空列表, 不抛异常。

        2026-09-07: reflections.json 9.7MB 中途损坏(写中断/磁盘满), json.load 抛
        JSONDecodeError → os_monitor 线程每次启动即崩溃 → 反复重试告警刷屏。
        损坏文件原样备份为 {name}.bak-{timestamp}(copy2, 不覆盖既有 .bak,
        审计可恢复), 内存置空列表让调用线程正常继续; 下次 _save 会用干净数据
        重建文件。
        """
        if not Path(str(path)).exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            raise ValueError(f"{kind}.json 顶层应为 list, 实际为 {type(data).__name__}")
        except Exception as exc:
            try:
                import shutil

                bak_path = str(path) + ".bak-" + str(int(time.time()))
                shutil.copy2(path, bak_path)
                print(
                    f"[METACOG] {kind}.json 损坏({type(exc).__name__}: {str(exc)[:80]}), "
                    f"已备份到 {os.path.basename(bak_path)}, 重建空列表继续运行"
                )
            except Exception as bak_exc:
                print(f"[METACOG] {kind}.json 损坏且备份失败: {bak_exc}")
            return []

    def _save(self):
        with self._save_lock:
            with open(self.reflections_file, "w", encoding="utf-8") as f:
                json.dump(self.reflections[-500:], f, indent=2, ensure_ascii=False)
            with open(self.evolutions_file, "w", encoding="utf-8") as f:
                json.dump(self.evolutions, f, indent=2, ensure_ascii=False)

    def reflect(
        self,
        user_input: str,
        response: str,
        user_feedback: Optional[str] = None,
        os_events: Optional[List[Dict]] = None,
    ) -> Dict:
        """反思一次交互"""
        # 自评回答质量
        quality_score = self._assess_quality(response)
        was_helpful = self._was_helpful(response, user_feedback)

        reflection = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input[:200],
            "response": response[:200],
            "quality_score": quality_score,
            "was_helpful": was_helpful,
            "feedback": user_feedback,
            "insight": self._generate_insight(response, quality_score, was_helpful),
        }

        # 追加 os_events 到 evidence 字段
        if os_events:
            reflection["evidence"] = list(os_events)

            # event_type 分组计数
            type_counts = {}
            for evt in os_events:
                evt_type = evt.get("event_type", "unknown")
                type_counts[evt_type] = type_counts.get(evt_type, 0) + 1

            reflection["task_pattern"] = {
                "os_events_summary": type_counts,
            }

            # 调用 GLM 深度分析
            glm_result = self._glm_assess(os_events)
            if glm_result:
                try:
                    glm_parsed = json.loads(glm_result)
                    reflection["glm_analysis"] = glm_parsed
                    # 覆盖 insight 为 GLM 的分析结果
                    if glm_parsed.get("description"):
                        reflection["insight"] = glm_parsed["description"]
                except Exception:
                    reflection["glm_raw"] = glm_result

            # 同类 event_type + reason 高频模式检测，写入 code_entities
            from collections import Counter

            pattern_counts = Counter((e.get("event_type"), e.get("reason")) for e in os_events)
            for (evt_type, reason), count in pattern_counts.items():
                if count >= 3:
                    from core.lib.code_entity_extractor import extractor

                    extractor.upsert_entity(
                        entity={
                            "entity_type": "system_hypothesis",
                            "entity_name": f"{evt_type}_{reason}",
                            "file_path": "data/v8/events_default.jsonl",
                            "signature": f"{evt_type}_{reason}:出现{count}次",
                            "related_entities": [f"os_event:{evt_type}"],
                        }
                    )
                # 消费 error_context 记录，生成负面 hypothesis
        try:
            cur.execute(
                "SELECT entity_name, signature FROM code_entities WHERE entity_type='error_context' ORDER BY created_at DESC LIMIT 20"
            )
            error_rows = cur.fetchall()
            error_patterns = {}
            for row in error_rows:
                try:
                    sig = json.loads(row[1]) if row[1] else {}
                except Exception:
                    sig = {}
                error_type = str(sig.get("error", ""))[:50]
                if error_type:
                    error_patterns[error_type] = error_patterns.get(error_type, 0) + 1
            for error_type, count in error_patterns.items():
                if count >= 2:
                    extractor.upsert_entity(
                        entity={
                            "entity_type": "system_hypothesis",
                            "entity_name": f"error_pattern_{error_type[:30]}",
                            "file_path": "memory/metacognition/",
                            "signature": json.dumps(
                                {
                                    "type": "negative",
                                    "pattern": error_type,
                                    "count": count,
                                    "insight": f"错误模式「{error_type}」出现{count}次，建议自动修正策略",
                                },
                                ensure_ascii=False,
                            ),
                        }
                    )
        except Exception:
            pass
        self.reflections.append(reflection)
        self._save()
        return reflection

    def _assess_quality(self, response: str) -> float:
        """评估回答质量 (0-1)"""
        score = 0.5

        # 长度适中
        if 20 < len(response) < 500:
            score += 0.2

        # 有具体内容
        if any(k in response for k in ["Agent", "技能", "系统", "功能"]):
            score += 0.2

        # 不是模板回复
        if "我不知道" not in response and "无法回答" not in response:
            score += 0.1

        return min(1.0, score)

    def _was_helpful(self, response: str, feedback: Optional[str]) -> bool:
        """判断是否有帮助"""
        if feedback:
            return "好" in feedback or "谢谢" in feedback or "正确" in feedback
        return len(response) > 30 and "?" not in response

    def _generate_insight(self, response: str, score: float, helpful: bool) -> str:
        """生成洞察"""
        if score < 0.4:
            return "回答质量偏低，需要更详细的回复"
        elif score < 0.7:
            return "回答基本可用，但可以更精准"
        else:
            return "回答质量良好，继续保持"

    def _glm_assess(self, os_events: List[Dict]) -> str:
        """调用 GLM5.2 深度分析 OS 事件"""
        api_key = os.getenv("GLM_API_KEY", "")
        if not api_key:
            return ""

        try:
            import requests
            import yaml

            # 加载 meta_cognition_system.yaml prompt
            prompt_config = yaml.safe_load(open("config/prompts/meta_cognition_system.yaml", encoding="utf-8"))
            system_prompt = prompt_config.get("meta_cognition_prompt", "")

            # 构造输入：os_events 摘要 + 分析规则
            events_summary = json.dumps(os_events[-50:], ensure_ascii=False, indent=2)
            user_prompt = f"""请分析以下 OS 事件数据： {events_summary}  基于以上数据，按你的分析规则产出 JSON 格式的问题报告。"""

            resp = requests.post(
                "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                json={
                    "model": "glm-4-flash",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1000,
                },
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30,
            )

            if resp.status_code == 200:
                result = resp.json()
                content = result["choices"][0]["message"]["content"]
                # 提取 JSON
                if "{" in content and "}" in content:
                    start = content.index("{")
                    end = content.rindex("}") + 1
                    return content[start:end]
                return content
            return ""
        except Exception:
            return ""

    def evolve(self) -> Dict:
        """自我进化 - 从反思中学习"""
        if len(self.reflections) < 10:
            return {"status": "need_more_data", "message": "需要更多交互才能进化"}

        # 计算统计
        recent = self.reflections[-50:]
        avg_score = sum(r["quality_score"] for r in recent) / len(recent)
        helpful_rate = sum(1 for r in recent if r["was_helpful"]) / len(recent)

        # 生成进化建议
        suggestions = []
        if avg_score < 0.5:
            suggestions.append("需要提高回答质量，增加信息量")
        if helpful_rate < 0.6:
            suggestions.append("需要更好地理解用户意图")

        evolution = {
            "timestamp": datetime.now().isoformat(),
            "total_reflections": len(self.reflections),
            "avg_quality_score": round(avg_score, 2),
            "helpful_rate": round(helpful_rate, 2),
            "suggestions": suggestions,
            "version_increment": 0.01 if avg_score > 0.7 else 0,
        }

        self.evolutions.append(evolution)
        self._save()
        return evolution

    def get_stats(self) -> Dict:
        """获取元认知统计"""
        if not self.reflections:
            return {"total": 0}

        recent = self.reflections[-50:]
        return {
            "total_reflections": len(self.reflections),
            "total_evolutions": len(self.evolutions),
            "avg_quality_recent": round(sum(r["quality_score"] for r in recent) / len(recent), 2),
            "helpful_rate": round(sum(1 for r in recent if r["was_helpful"]) / len(recent), 2),
        }


if __name__ == "__main__":
    meta = Metacognition("test_agent")

    # 模拟反思
    meta.reflect("ClawsJoy 有什么功能？", "ClawsJoy 有10个Agent和20+技能", "很好")
    meta.reflect("你好", "你好", "太简短了")

    print("元认知统计:", meta.get_stats())
    print("进化建议:", meta.evolve())
