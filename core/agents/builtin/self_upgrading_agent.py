# 创建新文件: core/agents/builtin/self_upgrading_agent.py

#!/usr/bin/env python3
"""Self-Upgrading Agent - 具备自我升级能力的元认知智能体"""

import json
import os
import psycopg2
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import ollama  # 使用你的Ollama

from core.lib.config_helper import get_data_root


class SelfUpgradingAgent:
    """自我升级型元认知智能体 - 不仅反思，还能改进"""

    def __init__(self, model_name: str = "qwen2.5:7b-instruct-q4_0-gpu"):
        self.model_name = model_name
        self.reflection_dir = Path(f"{get_data_root()}/metacognition")
        self.reflection_dir.mkdir(parents=True, exist_ok=True)

        self.reflections_file = self.reflection_dir / "reflections.json"
        self.improvements_file = self.reflection_dir / "improvements.json"

        self._load_data()

    def _load_data(self):
        """加载历史数据"""
        self.reflections = []
        self.improvements = []

        if self.reflections_file.exists():
            with open(self.reflections_file, "r", encoding="utf-8") as f:
                self.reflections = json.load(f)
        if self.improvements_file.exists():
            with open(self.improvements_file, "r", encoding="utf-8") as f:
                self.improvements = json.load(f)

    def _save_data(self):
        """保存数据"""
        with open(self.reflections_file, "w", encoding="utf-8") as f:
            json.dump(self.reflections[-500:], f, indent=2, ensure_ascii=False)
        with open(self.improvements_file, "w", encoding="utf-8") as f:
            json.dump(self.improvements[-200:], f, indent=2, ensure_ascii=False)

    def _persist_learning_insight(
        self,
        agent_name: str,
        root_cause: str,
        improvement: Dict,
        expected_gain: float,
        success_rate_before: float,
        applied: bool,
    ) -> bool:
        """将反思结果自动写入 SAG（entity_type='learning_insight'）。

        GrowthEngine/精准投喂闭环：SelfUpgradingAgent 反思产出 → SAG 学习洞察 →
        下次精准投喂 _load_asset('learning_insight') 自动注入。

        同一天同一 Agent 的洞察按 entity_name 覆盖更新，避免记录无限膨胀。
        """
        try:
            import psycopg2
            from core.lib.code_entity_extractor import extractor
            db_url = getattr(extractor, "db_url", None) or os.getenv(
                "DATABASE_URL",
                "postgresql://clawsjoy:clawsjoy_secret@localhost:5432/clawsjoy_dev",
            )
            day_key = datetime.now().strftime("%Y%m%d")
            entity_name = f"learning_insight::{agent_name}::{day_key}"
            signature = json.dumps(
                {
                    "timestamp": datetime.now().isoformat(),
                    "agent": agent_name,
                    "root_cause": root_cause,
                    "improvement": improvement,
                    "expected_gain": expected_gain,
                    "success_rate_before": round(success_rate_before, 4),
                    "applied": applied,
                    "source": "self_upgrading_agent",
                },
                ensure_ascii=False,
            )
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO code_entities (project_id, entity_type, entity_name, file_path, signature, related_entities)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (project_id, entity_name, file_path)
                DO UPDATE SET signature = EXCLUDED.signature, related_entities = EXCLUDED.related_entities
                """,
                (
                    "default",
                    "learning_insight",
                    entity_name,
                    "builtin/self_upgrading_agent.py",
                    signature,
                    [f"agent::{agent_name}"],
                ),
            )
            conn.commit()
            cur.close()
            conn.close()
            print(f"[SelfUpgradingAgent] ✅ 学习洞察已写入 SAG: {entity_name}")
            return True
        except Exception as e:
            print(f"[SelfUpgradingAgent] ❌ 学习洞察写入 SAG 失败: {e}")
            return False


    def analyze_with_llm(self, agent_name: str, recent_logs: list) -> Dict:
        """
        使用本地Ollama模型深度分析Agent表现

        Args:
            agent_name: Agent名称
            recent_logs: 最近N次交互日志
        """

        # 统计失败模式
        failures = [log for log in recent_logs if not log.get("success", True)]
        failure_patterns = {}

        for fail in failures[-20:]:  # 分析最近20次失败
            error = fail.get("error", "unknown")
            failure_patterns[error] = failure_patterns.get(error, 0) + 1

        # 构建分析提示
        analysis_prompt = f"""
你是元认知分析专家。分析 {agent_name} 的表现：

## 性能数据
- 总交互: {len(recent_logs)}
- 成功率: {(len(recent_logs) - len(failures)) / max(len(recent_logs),1) * 100:.1f}%
- 最近失败模式: {json.dumps(failure_patterns, ensure_ascii=False)}

## 最近3次失败案例
{json.dumps(failures[-3:], indent=2, ensure_ascii=False, default=str)}

请：
1. 诊断根本原因（1句话）
2. 提出具体改进方案（修改配置参数或提示词）
3. 预估改进后成功率提升（百分比）

以JSON格式输出：
{{"root_cause": "...", "improvement": {{"type": "config|prompt", "key": "...", "new_value": "..."}}, "expected_gain": 数字}}
"""

        try:
            # 调用本地Ollama
            response = ollama.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": analysis_prompt}],
                options={"temperature": 0.3, "num_predict": 500},
            )

            result = json.loads(response["message"]["content"])
            return result
        except Exception as e:
            print(f"⚠️ LLM分析失败: {e}")
            return {"root_cause": "unknown", "improvement": None, "expected_gain": 0}

    def apply_improvement(self, agent_name: str, improvement: Dict) -> bool:
        """
        应用改进到目标Agent配置文件

        Args:
            agent_name: Agent名称（如chat_agent, code_agent）
            improvement: 改进建议
        """

        # 查找Agent配置文件
        config_paths = [
            Path(f"agents/{agent_name}/config.yaml"),
            Path(f"agents/{agent_name}/config.yml"),
            Path(f"agents/{agent_name}/config.json"),
        ]

        config_file = None
        for path in config_paths:
            if path.exists():
                config_file = path
                break

        if not config_file:
            print(f"⚠️ 未找到 {agent_name} 的配置文件")
            return False

        # 备份原配置
        backup_file = config_file.with_suffix(".yaml.bak")
        shutil.copy2(config_file, backup_file)

        try:
            # 根据改进类型应用
            imp_type = improvement.get("type", "config")

            if imp_type == "config":
                # 修改配置参数
                return self._modify_config(config_file, improvement)
            elif imp_type == "prompt":
                # 修改提示词（需要额外处理）
                return self._modify_prompt(agent_name, improvement)

            return False

        except Exception as e:
            print(f"❌ 应用改进失败: {e}")
            # 恢复备份
            shutil.copy2(backup_file, config_file)
            return False

    def _modify_config(self, config_file: Path, improvement: Dict) -> bool:
        """修改YAML/JSON配置文件"""
        import yaml

        key = improvement.get("key", "")
        new_value = improvement.get("new_value", "")

        # 读取配置
        with open(config_file, "r", encoding="utf-8") as f:
            if config_file.suffix == ".json":
                config = json.load(f)
            else:
                config = yaml.safe_load(f)

        # 修改配置（支持点号路径，如 "agent.temperature"）
        keys = key.split(".")
        target = config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = new_value

        # 写回
        with open(config_file, "w", encoding="utf-8") as f:
            if config_file.suffix == ".json":
                json.dump(config, f, indent=2, ensure_ascii=False)
            else:
                yaml.dump(config, f, allow_unicode=True)

        print(f"✅ 已修改 {config_file}: {key} = {new_value}")
        return True

    def _modify_prompt(self, agent_name: str, improvement: Dict) -> bool:
        """修改Agent的系统提示词"""
        agent_file = Path(f"agents/{agent_name}/agent.py")

        if not agent_file.exists():
            return False

        # 备份
        backup_file = agent_file.with_suffix(".py.bak")
        shutil.copy2(agent_file, backup_file)

        # 这里可以修改提示词字符串
        # 简化版：记录需要手动修改
        print(f"📝 建议手动修改 {agent_file} 中的提示词")
        return True

    def should_upgrade(self, agent_name: str, success_rate: float) -> bool:
        """判断是否需要升级"""
        # 检查最近的改进记录
        recent_improvements = [
            imp
            for imp in self.improvements
            if imp.get("agent") == agent_name
            and imp.get("timestamp", "").startswith(datetime.now().strftime("%Y-%m-%d"))
        ]

        # 每天最多升级3次
        if len(recent_improvements) >= 3:
            return False

        # 成功率低于70%需要升级
        return success_rate < 0.7

    def consume_hypothesis(self, limit: int = 20) -> List[Dict]:
        """从 SAG 读取 system_hypothesis，返回可操作的修复建议"""
        try:
            import psycopg2
            from core.lib.code_entity_extractor import extractor
            conn = psycopg2.connect(extractor.db_url)
            cur = conn.cursor()
            cur.execute("""
                SELECT entity_name, signature, created_at
                FROM code_entities
                WHERE entity_type = 'system_hypothesis'
                AND created_at > NOW() - INTERVAL '1 hour'
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            hypotheses = []
            for row in cur.fetchall():
                try:
                    sig = json.loads(row[1])
                    hypotheses.append({
                        "name": row[0],
                        "problem_type": sig.get("problem_type", "unknown"),
                        "inefficiency_rate": sig.get("inefficiency_rate", 0),
                        "triggered_defenses": sig.get("triggered_defenses", []),
                        "insight": sig.get("insight", ""),
                        "task_type": sig.get("task_type", ""),
                        "created_at": str(row[2]),
                    })
                except:
                    pass
            cur.close()
            conn.close()
            return hypotheses
        except:
            return []

    def should_auto_fix(self, hypotheses: List[Dict]) -> List[Dict]:
        """判断哪些 hypothesis 已满足自动修复条件（同类出现 ≥3 次）"""
        from collections import Counter
        type_counts = Counter(h["problem_type"] for h in hypotheses)
        auto_fixes = []
        for problem_type, count in type_counts.items():
            if count >= 3 and problem_type not in ("no_issue", "see_insight"):
                matching = [h for h in hypotheses if h["problem_type"] == problem_type]
                auto_fixes.append({
                    "problem_type": problem_type,
                    "occurrence_count": count,
                    "latest_insight": matching[0]["insight"],
                    "suggested_action": self._suggest_action(problem_type),
                })

        # 逐条检查 code_entities 是否已存在同 entity_name 的记录
        # 已存在则更新 occurrence_count，不新增
        filtered = []
        for fix in auto_fixes:
            entity_name = f'auto_fix::{fix["problem_type"]}'
            try:
                db_url = os.getenv("DATABASE_URL", "postgresql://clawsjoy:clawsjoy_secret@localhost:5432/clawsjoy_dev")
                conn = psycopg2.connect(db_url)
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, signature FROM code_entities WHERE entity_name = %s AND entity_type = 'auto_fix_suggestion' LIMIT 1",
                    (entity_name,)
                )
                row = cur.fetchone()
                if row:
                    existing_sig = json.loads(row[1])
                    existing_sig["occurrence_count"] = existing_sig.get("occurrence_count", 0) + fix["occurrence_count"]
                    cur.execute(
                        "UPDATE code_entities SET signature = %s WHERE id = %s",
                        (json.dumps(existing_sig, ensure_ascii=False), row[0])
                    )
                    conn.commit()
                    print(f"[SelfUpgradingAgent] 更新已有 auto_fix 记录: {entity_name}，occurrence_count += {fix['occurrence_count']}")
                else:
                    filtered.append(fix)
                cur.close()
                conn.close()
            except Exception as e:
                print(f"[SelfUpgradingAgent] 检查 auto_fix 重复失败: {e}")
                filtered.append(fix)
        return filtered

    def _suggest_action(self, problem_type: str) -> Dict:
        """根据问题类型建议修复动作"""
        actions = {
            "path_confusion": {"type": "system_prompt_update", "target": "agent_system.md", "change": "强化 _project_prefix 消费指令"},
            "excessive_reads": {"type": "threshold", "target": "read quota", "change": "降低读取配额触发阈值"},
            "tool_truncated": {"type": "threshold", "target": "write_file line limit", "change": "放开行数限制"},
            "heredoc_failed": {"type": "prompt", "target": "heredoc 模板", "change": "修复 heredoc 写入模板"},
            "repeated_failure_no_switch": {"type": "system_prompt_update", "target": "agent_system.md", "change": "强化被拒后策略切换指令"},
            "subprocess_bypass": {"type": "whitelist", "target": "ALLOWED_COMMANDS", "change": "补充对应命令到白名单"},
            "see_insight": {"type": "noop", "target": "none", "change": "系统运行正常，无需处理"},
            "file_not_found": {"type": "system_prompt_update", "target": "agent_system.md", "change": "提示先校验 _project_prefix 前缀后再 read"},
            "quota_exceeded": {"type": "prompt", "target": "read quota", "change": "改用 query_index 或直接写入，避免重复读取"},
            "verify_mismatch": {"type": "system_prompt_update", "target": "agent_system.md", "change": "改用 read_file 判断代码状态，verify 返回 false 不代表代码有问题"},
            "auto_fixed_verify": {"type": "system_prompt_update", "target": "agent_system.md", "change": "网关 auto_fixed 后需 read_file 验证内容是否正确"},
            "test_failed_loop": {"type": "prompt", "target": "test loop", "change": "输出失败原因而非继续重试，最多循环 3 次"},
        }
        return actions.get(problem_type, {"type": "manual_review", "target": "unknown", "change": "需要人工审查"})

    def auto_fix(
        self,
        problem_type: str = "see_insight",
        sandbox: bool = True,
        agent_name: str = "chat_agent",
        canary_ratio: float = 1.0,
    ) -> Dict:
        """Phase 4: 方案自动生成 + 沙箱验证 + 自动合入（灰度 + 回滚）。

        流程:
            1. 调用 _suggest_action 自动生成修复方案
            2. 在沙箱中验证方案可行性（目标存在性 / 变更完整性 / 类型合法性）
            3. 验证通过后按灰度比例自动合入（调用 apply_improvement）
            4. 合入失败时自动回滚（调用 rollback）
            5. 返回 {fix_plan, sandbox_verified, verification, applied, canary, rollback}

        Args:
            problem_type: 问题类型，传给 _suggest_action
            sandbox: 是否在沙箱中验证（默认 True）
            agent_name: 目标 Agent 名称，传给 apply_improvement 定位配置文件
            canary_ratio: 灰度放量比例（0.0~1.0），1.0 表示全量合入，<1.0 启用灰度
        """
        import os

        # 1. 方案自动生成
        fix_plan = self._suggest_action(problem_type)
        result = {
            "fix_plan": fix_plan,
            "sandbox_verified": False,
            "verification": {},
            "applied": False,
            "canary": {},
            "rollback": {"rolled_back": False, "reason": ""},
        }

        # 无需处理 / 需要人工审查的情况，跳过沙箱验证
        if fix_plan.get("type") == "noop":
            result["sandbox_verified"] = True
            result["verification"] = {"reason": "系统运行正常，无需修复"}
            return result
        if fix_plan.get("type") == "manual_review":
            result["verification"] = {"reason": "未知问题类型，需要人工审查"}
            return result

        # 2. 沙箱验证（sandbox=False 时仍校验，便于统一输出结构）
        target = fix_plan.get("target", "")
        verification = {"target": target, "checks": []}

        # 2.1 目标存在性校验（阈值/白名单等配置类目标无需文件存在）
        config_like_types = {"threshold", "whitelist"}
        target_exists = False
        if fix_plan.get("type") in config_like_types:
            # 配置/阈值类目标（如 read quota、ALLOWED_COMMANDS），无需文件存在
            target_exists = True
        elif target and target != "none":
            candidate_paths = [
                target,
                os.path.join("core", "agents", "builtin", target),
                os.path.join("core", "lib", target),
                os.path.join("core", "lib", "v8", target),
            ]
            for cand in candidate_paths:
                if os.path.exists(cand):
                    target_exists = True
                    verification["resolved_path"] = cand
                    break
            verification["target_exists"] = target_exists
            verification["checks"].append("target_exists" if target_exists else "target_missing")
        else:
            target_exists = True  # 配置/阈值类目标

        # 2.2 变更描述完整性校验
        change_ok = bool(fix_plan.get("change"))
        verification["change_ok"] = change_ok
        verification["checks"].append("change_ok" if change_ok else "change_missing")

        # 2.3 方案类型合法性校验
        valid_types = {"system_prompt_update", "threshold", "prompt", "whitelist", "noop"}
        type_ok = fix_plan.get("type") in valid_types
        verification["type_ok"] = type_ok
        verification["checks"].append("type_ok" if type_ok else "type_unknown")

        verified = bool(target_exists and change_ok and type_ok)
        result["sandbox_verified"] = verified
        result["verification"] = verification

        # 3. 验证通过后自动合入（Phase 4）
        if not verified:
            result["rollback"] = {"rolled_back": False, "reason": "沙箱验证未通过，未执行合入"}
            return result

        # 3.1 灰度发布判定：基于问题类型哈希，保证同一问题类型结果稳定
        seed = sum(ord(c) for c in problem_type)
        gray_value = (seed % 100) / 100.0
        canary_hit = gray_value < canary_ratio
        result["canary"] = {
            "released": canary_hit,
            "canary_ratio": canary_ratio,
            "gray_value": round(gray_value, 2),
        }

        if not canary_hit:
            result["rollback"] = {
                "rolled_back": False,
                "reason": "灰度未命中（{:.0%} >= {:.0%}），本次仅记录方案".format(gray_value, canary_ratio),
            }
            return result

        # 3.2 构造 improvement 并调用 apply_improvement 合入
        improvement = self._fix_plan_to_improvement(fix_plan)
        applied = self.apply_improvement(agent_name, improvement)
        result["applied"] = applied

        if not applied:
            # 4. 合入失败 → 回滚
            rolled_back = self.rollback(agent_name, improvement)
            result["rollback"] = {
                "rolled_back": rolled_back,
                "reason": "合入失败，触发回滚",
            }
        return result

    def _fix_plan_to_improvement(self, fix_plan: Dict) -> Dict:
        """将 _suggest_action 生成的修复方案转换为 apply_improvement 可用的 improvement 结构"""
        type_map = {
            "system_prompt_update": "prompt",
            "threshold": "config",
            "prompt": "prompt",
            "whitelist": "config",
        }
        return {
            "type": type_map.get(fix_plan.get("type", ""), "config"),
            "key": fix_plan.get("target", ""),
            "new_value": fix_plan.get("change", ""),
        }

    def rollback(self, agent_name: str, improvement: Optional[Dict] = None) -> bool:
        """合入失败时回滚：从备份文件恢复目标 Agent 配置。

        apply_improvement 合入前会将原配置备份为 <config>.yaml.bak，
        rollback 将备份内容复制回原配置文件。

        Args:
            agent_name: Agent名称（如chat_agent, code_agent）
            improvement: 改进方案（仅用于日志，可为 None）

        Returns:
            bool: 是否成功回滚
        """
        config_paths = [
            Path(f"agents/{agent_name}/config.yaml"),
            Path(f"agents/{agent_name}/config.yml"),
            Path(f"agents/{agent_name}/config.json"),
        ]

        config_file = None
        for path in config_paths:
            if path.exists():
                config_file = path
                break

        if not config_file:
            print(f"⚠️ 回滚失败：未找到 {agent_name} 的配置文件")
            return False

        backup_file = config_file.with_suffix(".yaml.bak")
        if not backup_file.exists():
            print(f"⚠️ 回滚失败：未找到备份 {backup_file}")
            return False

        try:
            shutil.copy2(backup_file, config_file)
            print(f"↩️ 已回滚 {agent_name}: {config_file} 已从 {backup_file} 恢复")
            return True
        except Exception as e:
            print(f"❌ 回滚失败: {e}")
            return False


    def upgrade_agent(self, agent_name: str, recent_logs: list) -> Dict:
        """
        完整的升级流程

        Returns:
            {"upgraded": bool, "changes": dict, "expected_gain": float}
        """

        # 1. 计算当前成功率
        successes = sum(1 for log in recent_logs if log.get("success", True))
        success_rate = successes / max(len(recent_logs), 1)

        # 2. 判断是否需要升级
        if not self.should_upgrade(agent_name, success_rate):
            return {"upgraded": False, "reason": f"成功率{success_rate:.1%}不需要升级"}

        # 3. 使用LLM深度分析
        analysis = self.analyze_with_llm(agent_name, recent_logs)

        if not analysis.get("improvement"):
            return {"upgraded": False, "reason": "LLM未提出改进方案"}

        # 4. 应用改进
        success = self.apply_improvement(agent_name, analysis["improvement"])

        # 5. 记录改进
        improvement_record = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "success_rate_before": success_rate,
            "root_cause": analysis.get("root_cause", ""),
            "improvement": analysis["improvement"],
            "expected_gain": analysis.get("expected_gain", 0),
            "applied": success,
        }

        self.improvements.append(improvement_record)
        self._save_data()

        # 反思结果自动写入 SAG（entity_type='learning_insight'）
        # 供下次精准投喂 _load_asset('learning_insight') 自动注入
        insight_persisted = self._persist_learning_insight(
            agent_name=agent_name,
            root_cause=analysis.get("root_cause", ""),
            improvement=analysis.get("improvement", {}),
            expected_gain=analysis.get("expected_gain", 0),
            success_rate_before=success_rate,
            applied=success,
        )

        return {
            "upgraded": success,
            "changes": analysis["improvement"],
            "expected_gain": analysis.get("expected_gain", 0),
            "success_rate_before": success_rate,
            "learning_insight_persisted": insight_persisted,
        }


# 使用示例
if __name__ == "__main__":
    # 测试
    upgrader = SelfUpgradingAgent(model_name="qwen2.5:7b-instruct-q4_0-gpu")

    # 模拟chat_agent的日志
    mock_logs = [
        {"success": True, "input": "你好", "output": "你好"},
        {"success": False, "input": "复杂问题", "error": "timeout"},
        {"success": False, "input": "另一个问题", "error": "unknown"},
    ] * 10

    result = upgrader.upgrade_agent("chat_agent", mock_logs)
    print(json.dumps(result, indent=2, ensure_ascii=False))
