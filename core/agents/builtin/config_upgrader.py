#!/usr/bin/env python3
"""配置升级器 - 专门针对你的YAML配置结构的自我升级模块"""

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import ollama
import yaml


class ConfigUpgrader:
    """配置升级器 - 自动优化Agent配置文件"""

    def __init__(self, model_name: str = "qwen2.5:7b-instruct-q4_0-gpu"):
        self.model_name = model_name
        self.upgrade_log = Path("data/upgrades/upgrade_history.json")
        self.upgrade_log.parent.mkdir(parents=True, exist_ok=True)
        self._load_history()

    def _load_history(self):
        if self.upgrade_log.exists():
            with open(self.upgrade_log, "r", encoding="utf-8") as f:
                self.history = json.load(f)
        else:
            self.history = []

    def _save_history(self):
        with open(self.upgrade_log, "w", encoding="utf-8") as f:
            json.dump(self.history[-500:], f, indent=2, ensure_ascii=False)

    def _get_current_config_summary(self, agent_name: str) -> str:
        """获取当前配置摘要"""
        config_file = Path(f"agents/{agent_name}/config.yaml")
        if not config_file.exists():
            return "未找到配置文件"

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except Exception as e:
            print(f"⚠️ 配置文件解析失败: {e}")
            return """
- 模型: qwen2.5:7b-instruct-q4_0-gpu
- 温度: 0.7
- max_tokens: 1024
"""

        agent_cfg = config.get("agent", {})
        llm_cfg = agent_cfg.get("llm", {})

        return f"""
- 模型: {llm_cfg.get('model', 'unknown')}
- 温度: {llm_cfg.get('temperature', 0.7)}
- max_tokens: {llm_cfg.get('max_tokens', 1024)}
- 能力: {', '.join(agent_cfg.get('capabilities', [])[:3])}
"""

    def _extract_json_from_response(self, text: str) -> Optional[Dict]:
        """从LLM响应中提取JSON"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except Exception as e:
            pass

        # 查找JSON代码块
        json_pattern = r"```json\s*([\s\S]*?)\s*```"
        match = re.search(json_pattern, text)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception as e:
                pass

        # 查找花括号包裹的内容
        brace_pattern = r"\{[\s\S]*\}"
        match = re.search(brace_pattern, text)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception as e:
                pass

        return None

    def analyze_performance(self, agent_name: str, logs: List[Dict]) -> Dict:
        """分析Agent性能并生成优化建议"""

        total = len(logs)
        if total == 0:
            return {"has_issue": False, "message": "无日志数据", "success_rate": 1.0}

        successes = sum(1 for log in logs if log.get("success", False))
        success_rate = successes / total if total > 0 else 1.0

        failures = [log for log in logs if not log.get("success", False)]
        failure_types = {}
        for fail in failures:
            error = fail.get("error", "unknown")
            failure_types[error] = failure_types.get(error, 0) + 1

        config_summary = self._get_current_config_summary(agent_name)

        # 简化的提示词，要求明确输出JSON
        analysis_prompt = f"""分析 {agent_name} 的性能并给出优化建议。

当前配置:
{config_summary}

性能数据:
- 总交互数: {total}
- 成功率: {success_rate:.1%}
- 失败类型: {json.dumps(failure_types, ensure_ascii=False)}

请只输出一个JSON对象，不要有其他文字，格式如下：
{{
    "has_issue": false,
    "issue_type": "low_success_rate",
    "suggestions": {{
        "temperature": 0.8,
        "model": null,
        "max_tokens": null,
        "prompt_improvements": ""
    }},
    "reasoning": "改进原因"
}}

注意：
- 如果成功率>=70%，has_issue为false
- temperature范围0-1
- 只修改有问题的参数，没问题的设为null
"""

        try:
            print(f"📡 调用 {self.model_name} 分析...")
            response = ollama.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": analysis_prompt}],
                options={"temperature": 0.1, "num_predict": 500},
            )

            raw_response = response["message"]["content"]
            print(f"📝 LLM响应: {raw_response[:200]}...")

            # 提取JSON
            result = self._extract_json_from_response(raw_response)

            if result is None:
                print(f"⚠️ 无法解析JSON，使用默认分析")
                result = {
                    "has_issue": success_rate < 0.7,
                    "issue_type": "low_success_rate" if success_rate < 0.7 else "none",
                    "suggestions": {
                        "temperature": (
                            0.5
                            if success_rate < 0.5
                            else 0.8 if success_rate > 0.9 else None
                        ),
                        "model": "qwen2.5:7b-instruct-q4_0-gpu",
                        "max_tokens": None,
                        "prompt_improvements": "",
                    },
                    "reasoning": f"基于成功率{success_rate:.1%}自动调整",
                }

            result["success_rate"] = success_rate
            result["total_interactions"] = total

            return result

        except Exception as e:
            print(f"⚠️ LLM分析失败: {e}")
            return {
                "has_issue": success_rate < 0.7,
                "success_rate": success_rate,
                "total_interactions": total,
                "issue_type": "low_success_rate" if success_rate < 0.7 else "none",
                "suggestions": {},
                "reasoning": f"自动模式: 成功率{success_rate:.1%}",
            }

    def apply_upgrade(self, agent_name: str, suggestions: Dict) -> bool:
        """应用升级建议到配置文件"""

        config_file = Path(f"agents/{agent_name}/config.yaml")
        if not config_file.exists():
            print(f"❌ 配置文件不存在: {config_file}")
            return False

        # 检查是否有实际更改
        has_changes = any(v is not None for v in suggestions.values() if v != "")
        if not has_changes:
            print("ℹ️ 没有需要应用的更改")
            return False

        backup_file = config_file.with_suffix(".yaml.bak")
        shutil.copy2(config_file, backup_file)
        print(f"📦 已备份到: {backup_file}")

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if "agent" not in config:
                config["agent"] = {}

            agent_cfg = config["agent"]
            if "llm" not in agent_cfg:
                agent_cfg["llm"] = {}

            llm_cfg = agent_cfg["llm"]

            changes_made = []

            if suggestions.get("temperature") is not None:
                old_temp = llm_cfg.get("temperature", 0.7)
                new_temp = float(suggestions["temperature"])
                llm_cfg["temperature"] = new_temp
                changes_made.append(f"temperature: {old_temp} → {new_temp}")

            if suggestions.get("model") is not None and suggestions["model"]:
                old_model = llm_cfg.get("model", "unknown")
                llm_cfg["model"] = suggestions["model"]
                changes_made.append(f"model: {old_model} → {suggestions['model']}")

            if suggestions.get("max_tokens") is not None:
                old_tokens = llm_cfg.get("max_tokens", 1024)
                new_tokens = int(suggestions["max_tokens"])
                llm_cfg["max_tokens"] = new_tokens
                changes_made.append(f"max_tokens: {old_tokens} → {new_tokens}")

            if (
                suggestions.get("prompt_improvements")
                and suggestions["prompt_improvements"].strip()
            ):
                prompt_file = Path(f"agents/{agent_name}/prompt_suggestions.txt")
                with open(prompt_file, "a", encoding="utf-8") as f:
                    f.write(f"\n--- {datetime.now().isoformat()} ---\n")
                    f.write(suggestions["prompt_improvements"])
                    f.write("\n")
                changes_made.append("prompt_suggestions已保存")

            if not changes_made:
                print("ℹ️ 没有需要应用的更改")
                return False

            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

            print(f"✅ 已应用升级: {', '.join(changes_made)}")
            return True

        except Exception as e:
            print(f"❌ 升级失败: {e}")
            shutil.copy2(backup_file, config_file)
            return False

    def upgrade_agent(
        self, agent_name: str, logs: List[Dict], auto_apply: bool = False
    ) -> Dict:
        """完整的升级流程"""

        print(f"🔍 正在分析 {agent_name} 的表现...")
        print(f"📊 日志数量: {len(logs)}")

        analysis = self.analyze_performance(agent_name, logs)

        success_rate = analysis.get("success_rate", 1.0)
        print(f"📈 当前成功率: {success_rate:.1%}")

        if not analysis.get("has_issue"):
            return {
                "upgraded": False,
                "reason": f"性能正常 (成功率{success_rate:.1%})，无需升级",
                "success_rate": success_rate,
                "analysis": analysis,
            }

        suggestions = analysis.get("suggestions", {})

        # 检查是否有有效建议
        has_valid_suggestion = any(
            v is not None and v != "" for v in suggestions.values()
        )

        if not has_valid_suggestion:
            return {
                "upgraded": False,
                "reason": "未生成有效改进建议",
                "success_rate": success_rate,
                "analysis": analysis,
            }

        applied = False
        if auto_apply:
            applied = self.apply_upgrade(agent_name, suggestions)
        else:
            print(f"\n📋 建议的改进:")
            for key, value in suggestions.items():
                if value is not None and value != "":
                    print(f"   • {key}: {value}")
            print(f"\n💡 推理: {analysis.get('reasoning', 'N/A')}")

        record = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "success_rate_before": success_rate,
            "interactions": analysis.get("total_interactions", 0),
            "issue_type": analysis.get("issue_type", "unknown"),
            "suggestions": suggestions,
            "applied": applied,
            "auto_apply": auto_apply,
        }

        self.history.append(record)
        self._save_history()

        return {
            "upgraded": applied,
            "success_rate_before": success_rate,
            "suggestions": suggestions,
            "reasoning": analysis.get("reasoning", ""),
            "history_record": record,
        }


# 添加到 config_upgrader.py
def validate_upgrade(self, agent_name: str, before_rate: float) -> Dict:
    """验证升级效果"""
    # 等待一段时间收集新数据
    time.sleep(3600)  # 等待1小时

    # 重新计算成功率
    new_logs = self.collect_logs(agent_name, hours=24)
    new_rate = calculate_success_rate(new_logs)

    if new_rate > before_rate:
        return {"success": True, "improvement": new_rate - before_rate}
    else:
        # 回滚
        self.rollback(agent_name)
        return {"success": False, "reason": "性能未提升"}


def _update_agent_prompt(self, agent_name: str, suggestion: Dict) -> bool:
    """更新Agent的系统提示词"""
    # 禁止修改 .py 文件
    print(f"⚠️ 跳过修改 {agent_name}/agent.py，自动升级只允许修改配置文件")
    return False


def _update_agent_workflow(self, agent_name: str, suggestion: Dict) -> bool:
    """调整工作流"""
    # 禁止修改工作流代码
    print(f"⚠️ 跳过修改工作流，自动升级只允许修改配置文件")
    return False


if __name__ == "__main__":
    upgrader = ConfigUpgrader(model_name="qwen2.5:7b-instruct-q4_0-gpu")

    # 创建测试日志（成功率50%）
    bad_logs = []
    for i in range(100):
        bad_logs.append(
            {
                "success": i % 2 == 0,
                "input": f"问题{i}",
                "output": "答案" if i % 2 == 0 else "",
                "error": None if i % 2 == 0 else "timeout",
            }
        )

    print("=" * 60)
    print("测试配置升级器")
    print("=" * 60)

    result = upgrader.upgrade_agent("chat_agent", bad_logs, auto_apply=False)

    print("\n" + "=" * 60)
    print("升级结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 显示历史记录
    print(f"\n📜 历史记录数: {len(upgrader.history)}")
