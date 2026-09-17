#!/usr/bin/env python3
"""
TaskOrchestrator v9.1 — 包工头：任务全生命周期管理

协议：
- 钩子 _on_task_state_change：只做通知 + 触发审查，不做执行调度
- plan / start_next / review_task：显式调用 execute_task
- 返工：review 不通过 → pending → running → execute_task（循环直到通过）
"""

import json
import os
import re
from datetime import datetime
from core.lib.code_entity_extractor import CodeEntityExtractor
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.lib.llm_client import llm_client
from core.lib.v8.roster_engine import roster_engine
from core.lib.v8.task_engine import task_engine
from core.lib.v8.agent_discussion import AgentDiscussionEngine
from core.lib.notify import notify
import yaml
from core.lib.os_event_logger import write_os_event

logger = logging.getLogger(__name__)

MODEL_MAIN = "qwen2.5:7b-instruct-q4_0-gpu"

SKILL_TO_POSITION = {
    "代码开发": "程序员", "写代码": "程序员", "编程": "程序员",
    "bug修复": "程序员", "部署": "程序员",
    "数据分析": "分析师", "分析": "分析师", "竞品分析": "分析师",
    "市场调研": "分析师", "搜索": "分析师",
    "内容写作": "作家", "写作": "作家", "写脚本": "作家",
    "写文案": "作家", "撰写": "作家", "创作": "作家",
    "翻译": "翻译员", "多语言": "翻译员",
    "图片分析": "设计师", "设计": "设计师", "画图": "设计师",
    "音频制作": "作家", "音频": "作家", "音效": "作家",
    "视频制作": "视频编辑", "视频剪辑": "视频编辑",
    "文件管理": "文件管理", "文件读写": "文件管理",
    "任务规划": "决策审查", "规划": "决策审查", "审查": "决策审查",
    "财务规划": "分析师", "预算": "分析师",
    "评估": "决策审查",
    "图像生成": "设计师", "导演模式": "设计师", "拍摄计划": "设计师",
    "工作流执行": "程序员",
}

AGENT_TO_POSITION = {
    "writer_agent": "作家", "analysis_agent": "分析师",
    "code_agent": "程序员", "vision_agent": "设计师",
    "video_agent": "视频编辑", "translate_agent": "翻译员",
    "file_agent": "文件管理", "decision_agent": "决策审查",
    "chat_agent": "作家",
}

POSITION_TO_AGENT = {
    "程序员": "code_agent", "分析师": "analysis_agent",
    "作家": "writer_agent", "设计师": "vision_agent",
    "视频编辑": "video_agent", "翻译员": "translate_agent",
    "文件管理": "file_agent", "决策审查": "decision_agent",
}

ORCHESTRATIONS_FILE = Path("data/v8/orchestrations.json")


class TaskOrchestrator:
    """包工头 — plan / execute / review / start_next"""

    def __init__(self):
        self._orchestrations: Dict[str, dict] = {}
        self.knowledge: dict = {}
        self._load_knowledge()
        self._load_orchestrations()
        self._extractor = CodeEntityExtractor()
        task_engine.on_state_change(self._on_task_state_change)
        self._audit_rules = self._load_audit_rules()

    def _load_audit_rules(self) -> dict:
        """加载审计规则，缺失时使用默认值"""
        defaults = {
            "discussion": {
                "max_rounds": 20,
                "timeout_minutes": 30,
                "duplicate_detection": True,
            }
        }
        try:
            rules_path = Path("config/v8/audit_rules.yaml")
            if rules_path.exists():
                with open(rules_path) as f:
                    rules = yaml.safe_load(f) or {}
                return rules
        except Exception as e:
            logger.warning(f"审计规则加载失败: {e}")
        return defaults

    # ===================================================================
    #  知识 & 持久化
    # ====================================================================

    def _load_knowledge(self):
        self.knowledge["agents"] = self._summarize_agents()
        self.knowledge["positions"] = self._summarize_positions()

    def _summarize_agents(self) -> dict:
        summary = {}
        try:
            from core.agents.wisdom.wisdom_factory import wisdom_factory
            for name, caps in wisdom_factory.CAPABILITIES.items():
                summary[name] = {"skills": caps}
        except Exception as e:
            logger.warning(f"[TaskOrchestrator] 汇总 agents 能力失败: {e}")
        return summary

    def _summarize_positions(self) -> dict:
        positions = {}
        try:
            import yaml
            pos_dir = Path("config/v8/positions")
            if pos_dir.exists():
                for f in pos_dir.glob("*.yaml"):
                    with open(f) as fp:
                        pos = yaml.safe_load(fp)
                        positions[f.stem] = pos
        except Exception as e:
            logger.warning(f"[TaskOrchestrator] 加载 positions 失败: {e}")
        return positions

    def _load_orchestrations(self):
        if ORCHESTRATIONS_FILE.exists():
            try:
                self._orchestrations = json.loads(ORCHESTRATIONS_FILE.read_text())
            except Exception as e:
                logger.warning(f"[TaskOrchestrator] 加载 orchestrations 失败: {e}")

    def _save_orchestrations(self):
        ORCHESTRATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        ORCHESTRATIONS_FILE.write_text(json.dumps(self._orchestrations, ensure_ascii=False, indent=2))

    def _refresh_workers(self, server_id="default"):
        workers = {}
        for m in roster_engine.list_active(server_id):
            budget = roster_engine.check_budget(server_id, m["name"])
            workers[m["name"]] = {
                "position": m.get("position", ""),
                "status": m.get("status", "active"),
                "budget_remaining": budget.get("remaining", 0),
                "task_count": m.get("task_count", 0),
            }
        self.knowledge["workers"] = workers

    # ====================================================================
    #  状态钩子（只做通知 + 触发审查，不做执行调度）
    # ====================================================================

    def _on_task_state_change(self, task_id, old_state, new_state, task_data):
        executor = task_data.get("assigned_to", "")
        title = task_data.get("title", "")

        # #31 V9 长线任务：调度（重试/取下一个）由 on_v9_done/on_v9_fail 驱动，hooks 仅通知，避免双重重试/状态机打架
        if task_data.get("_v9_mode"):
            try:
                if new_state == "done":
                    notify(executor, f"✅「{title}」V9 执行完成")
                elif new_state == "failed":
                    notify("老板", f"「{title}」V9 执行失败，将自动重试或跳过")
            except Exception:
                pass
            return

        if new_state == "running":
            notify(executor, f"开始执行「{title}」")

        elif new_state == "done":
            notify(executor, f"「{title}」已完成")
            self.review_task(task_id, task_data)

        elif new_state == "reviewed":
            output = task_data.get("output", "")
            if output:
                notify("老板", f"✅「{title}」已完成\n{output[:1500]}")
            else:
                notify("老板", f"✅「{title}」审查通过")

        elif new_state == "failed":
            notify("老板", f"「{title}」执行失败")
            # 自动重试 1 次；仍失败 → 继续下一个任务，避免任务链卡死
            retry_count = task_data.get("_retry_count", 0)
            if retry_count < 1:
                task_data["_retry_count"] = retry_count + 1
                logger.warning(f"任务 {task_id} 执行失败，自动重试第 {retry_count + 1} 次")
                self.execute_task(task_data)
                return
            self.start_next(task_data)

    # ====================================================================
    #  Plan
    # ====================================================================

    def plan(self, user_input: str, user_id: str,
             channel_id: str = "", server_id: str = "default") -> dict:
        self._refresh_workers(server_id)

        project_dir = Path(f"data/projects/{user_id}")
        has_brief = False
        if project_dir.exists():
            has_brief = any(project_dir.rglob("BRIEF.md"))
        if not has_brief:
            template_dir = Path("config/templates/project")
            if template_dir.exists():
                import shutil
                shutil.copytree(template_dir, project_dir, dirs_exist_ok=True)
                brief_file = project_dir / "BRIEF.md"
                if brief_file.exists():
                    content = brief_file.read_text()
                    content = content.replace("{项目名称}", user_input[:30])
                    content = content.replace("{老板的原始需求}", user_input)
                    brief_file.write_text(content)

        subtasks = self._decompose(user_input)
        if not subtasks:
            return {"success": False, "response": "无法拆解需求，请提供更具体的描述。"}

        active_agents = roster_engine.list_active(server_id)
        created_tasks = []
        for sub in subtasks:
            agent = self._find_worker(sub.get("required_skill", ""), active_agents)
            if not agent:
                continue
            task = task_engine.create(
                server_id=server_id,
                title=sub["title"],
                assigned_to=agent["name"],
                assigned_position=agent.get("position", ""),
                created_by=user_id,
                priority="high" if len(created_tasks) == 0 else "normal",
            )
            task["_skill"] = sub.get("required_skill", "")
            task["_agent_name"] = agent["name"]
            task["_step"] = len(created_tasks) + 1
            task["_channel_id"] = channel_id
            task["output_file"] = sub.get("output_file") or self._generate_output_file(sub["title"], len(created_tasks))
            created_tasks.append(task)

        if not created_tasks:
            return {"success": False, "response": "当前无可用工人执行此任务，请先聘用对应岗位。"}

        # P0-C: 持久化任务附加字段（create() 已落盘，内存修改需显式写回，否则交付物校验失效）
        try:
            _data_p0c = task_engine._load(server_id)
            for _t in created_tasks:
                _tid_p0c = _t["id"]
                if _tid_p0c in _data_p0c["tasks"]:
                    for _k_p0c in ("_skill", "_agent_name", "_step", "_channel_id", "output_file"):
                        if _k_p0c in _t:
                            _data_p0c["tasks"][_tid_p0c][_k_p0c] = _t[_k_p0c]
            task_engine._save(server_id, _data_p0c)
        except Exception:
            pass

        self._orchestrations[user_id] = {
            "input": user_input,
            "task_ids": [t["id"] for t in created_tasks],
            "total": len(created_tasks),
            "created_at": datetime.now().isoformat(),
        }
        self._save_orchestrations()

        card = self._build_card(created_tasks, user_input)

        # 显式启动第一个
        first_task = created_tasks[0]
        task_engine.transition(server_id, first_task["id"], "running", "自动开始")
        self.execute_task(first_task)

        agent_name = first_task.get("_agent_name", "待分配")
        next_hint = ""
        if len(created_tasks) > 1:
            next_hint = f"\n\n📌 下一步：**{created_tasks[1]['title']}**（完成后自动开始）"

        # === SAG: plan 实体入库 ===
        plan_entity_name = f"plan::{user_input}::{int(datetime.now().timestamp())}"
        complexity = "简单" if len(created_tasks) <= 3 else ("中等" if len(created_tasks) <= 6 else "复杂")
        try:
            self._extractor.upsert_entity({
                "entity_type": "plan",
                "entity_name": plan_entity_name,
                "signature": json.dumps({
                    "complexity": complexity,
                    "steps_count": len(created_tasks),
                    "estimated_calls": len(created_tasks)
                }, ensure_ascii=False),
                "related_entities": [t["title"] for t in created_tasks],
                "file_path": ""
            }, project_id=user_id)
        except Exception:
            pass

        # 自动注册子任务为 SAG task 实体
        try:
            for _t in created_tasks:
                self._extractor.upsert_entity({
                    "entity_type": "task",
                    "entity_name": _t["title"],
                    "signature": json.dumps({"assigned_to": _t.get("_agent_name", "")}, ensure_ascii=False),
                    "related_entities": [plan_entity_name],
                    "file_path": _t.get("output_file", "")
                }, project_id=user_id)
        except Exception:
            pass

        return {
            "success": True,
            "response": card + f"\n\n▶️ 第1步「{first_task['title']}」已启动 → @{agent_name}{next_hint}",
            "method": "planned",
            "intent": "plan",
            "confidence": 0.90,
            "agents_used": [t.get("_agent_name", "") for t in created_tasks],
            "tasks": created_tasks,
            "tokens": 0,
            "model": "orchestrator",
        }

    # ====================================================================
    #  Execute
    # ====================================================================

    # ====================================================================
    #  交付物校验助手
    # ====================================================================

    DELIVERABLE_KEYWORDS = ("创建", "写", "实现", "生成", "修改", "修复", "编写", "产出", "新建")

    def _resolve_deliverable_paths(self, task_data) -> List[Path]:
        """从 output_file / 标题提取交付物路径列表（相对 data/projects/{created_by}）。"""
        created_by = task_data.get("created_by", "")
        title = task_data.get("title", "")
        output_file = task_data.get("output_file", "")

        candidates: List[str] = []
        if output_file:
            candidates.append(output_file)
        # 从标题中提取文件名/路径（含常见扩展名）
        for m in re.findall(
            r"[\w\-./\\]+\.(?:py|md|txt|json|yaml|yml|toml|ini|sh|js|ts|html|css|csv|sql|pdf|docx?|xlsx?|png|jpg|jpeg|svg)",
            title,
        ):
            if m not in candidates:
                candidates.append(m)

        paths: List[Path] = []
        for cand in candidates:
            p = Path(cand)
            if p.is_absolute():
                paths.append(p)
            elif created_by:
                paths.append(Path(f"data/projects/{created_by}") / p)
            else:
                paths.append(p)
        return paths

    def _deliverable_ok(self, task_data) -> bool:
        """标题含 创建/写/实现/生成/修改/修复 等词时，校验交付物真实存在。"""
        title = task_data.get("title", "")
        if not any(kw in title for kw in self.DELIVERABLE_KEYWORDS):
            return True
        paths = self._resolve_deliverable_paths(task_data)
        if not paths:
            # 无可校验路径 → 不阻塞
            return True
        # P0-A: 仅当标题含显式文件路径（非生成的 output_file）时严格校验文件真实存在；
        # 纯文本/生成类任务（标题无路径）允许文本作为交付物，避免误伤
        _title_has_path = bool(re.search(
            r"[\w\-./\\]+\.(?:py|md|txt|json|yaml|yml|toml|ini|sh|js|ts|html|css|csv|sql)", title))
        if not _title_has_path:
            return True
        return any(p.exists() for p in paths)

    def execute_task(self, task_data, server_id="default"):
        title = task_data.get("title", "")
        worker = task_data.get("assigned_to", "")
        position = task_data.get("assigned_position", "")
        created_by = task_data.get("created_by", "")

        if not worker:
            task_engine.transition(server_id, task_data["id"], "failed", "无执行者")
            return {"response": "", "success": False}

        # 花名册覆盖：有 api_key 走适配器
        member = roster_engine.get(server_id, worker)
        if member and member.get("api_key"):
            try:
                from core.lib.v8.adapters.factory import get_adapter
                adapter = get_adapter(member.get("model", ""), api_key=member["api_key"])
                if adapter:
                    result = adapter.execute(f"任务：{title}")
                    if result.get("success"):
                        task_data["output"] = result["content"][:2000]
                        if not self._deliverable_ok(task_data):
                            task_engine.transition(server_id, task_data["id"], "failed", "交付物缺失")
                            return {"response": "", "success": False}
                        task_engine.transition(server_id, task_data["id"], "done", "执行完成")
                        self._extractor.update_task_progress(
                            task_name=task_data.get("title", ""),
                            session_id=server_id,
                            step_number=1,
                            step_description="适配器执行",
                            tool_name="adapter",
                            file_path=task_data.get("output_file", ""),
                            status="completed"
                        )
                        return {"response": result["content"][:2000], "success": True}
            except Exception as e:
                logger.warning(f"适配器执行失败: {e}")

        agent_type = POSITION_TO_AGENT.get(position, "chat_agent")

        original_input = ""
        for uid, state in self._orchestrations.items():
            if task_data["id"] in state.get("task_ids", []):
                original_input = state.get("input", "")
                break

        rules = ""
        try:
            rules_path = Path("config/RULES.md")
            if rules_path.exists():
                rules = rules_path.read_text()
        except Exception:
            pass

        brief_content = ""
        try:
            user_project_dir = Path(f"data/projects/{created_by}")
            if user_project_dir.exists():
                for brief_file in user_project_dir.rglob("BRIEF.md"):
                    brief_content += brief_file.read_text() + "\n"
                    spec_dir = brief_file.parent / "specs"
                    if spec_dir.exists():
                        for spec_file in spec_dir.glob("*.md"):
                            brief_content += f"\n---\n{spec_file.read_text()}\n"
                    break
        except Exception:
            pass

        # 在 prompt 拼接之前注入前序文件
        previous_files = ""
        try:
            user_project_dir = Path(f"data/projects/{created_by}")
            if user_project_dir.exists():
                for brief_file in user_project_dir.rglob("BRIEF.md"):
                    project_dir = brief_file.parent
                    all_tasks = task_engine.list(server_id)
                    for t in all_tasks:
                        if t.get("created_by") == created_by and t.get("output_file"):
                            prev_path = project_dir / t["output_file"]
                            if prev_path.exists():
                                previous_files += f"\n【前序任务：{t['title']}】\n{prev_path.read_text()[:1000]}\n"
                    break
        except Exception:
            pass

        prompt = f"""【你的身份】
你是 ClawsJoy 的 {position}。

【规则】
直接产出，不要反问，不要建议过程。不确定的标注"待确认"。

【项目背景】
ClawsJoy 是一个本地 AI 劳动力管理平台。一人公司老板在 Discord 频道里聘 AI 员工、分配任务、自动协作。核心功能：AI 劳动力管理、Discord 频道协作、自动记账。

{previous_files}

【你的任务】
{title}

【验收标准】
{brief_content}

直接产出最终交付物。这是独立文件，不要重复前序已产出的内容。使用 Markdown 表格。不要复述规则和背景。""" 
        
        result = {}
        try:
            from core.agents.wisdom.wisdom_factory import wisdom_factory
            agent = wisdom_factory.get_agent(agent_type, f"worker_{worker}")
            result = agent.process(user_input=prompt, context={
                "skip_intent": True,
                "task_id": task_data["id"],
                "created_by": created_by,
                "server_id": server_id,
                "channel_id": task_data.get("_channel_id", ""),
            })
            # agent.process() 可能返回生成器，迭代取最后一个值
            if hasattr(result, '__next__'):
                try:
                    gen_result = None
                    for gen_result in result:
                        pass
                    result = gen_result if gen_result is not None else {}
                except Exception as gen_e:
                    logger.warning(f"生成器迭代失败: {gen_e}")
                    result = {}
        except Exception as e:
            logger.warning(f"执行失败: {e}")

        # 检查 response 值是否是生成器，收集完整字符串
        if isinstance(result, dict):
            resp = result.get("response")
            if resp is not None and hasattr(resp, '__next__'):
                result["response"] = ''.join(list(resp))

        if result.get("success") and result.get("response"):
            _resp_text = str(result["response"] or "").strip()
            # P0-A 假完成防护①：反问/空泛输出视为无效产出（Agent 未遵守"直接产出，不要反问"）
            _invalid_pat = ("请提供", "请等待", "需要更多信息", "请确认", "请说明", "请补充",
                            "请告诉我", "请给出", "无法直接", "需要你提供", "请上传", "请分享")
            if len(_resp_text) < 20 or any(_p in _resp_text for _p in _invalid_pat):
                task_engine.transition(server_id, task_data["id"], "failed",
                                       f"产出无效（Agent 反问/空泛输出）：{_resp_text[:60]}")
                return {"response": "", "success": False}

            # P0-A 假完成防护②：交付物校验前置（先校验后写盘，避免文本写盘使校验恒通过）
            if not self._deliverable_ok(task_data):
                task_engine.transition(server_id, task_data["id"], "failed", "交付物缺失")
                return {"response": "", "success": False}

            task_data["output"] = _resp_text[:2000]

            output_file = task_data.get("output_file", "")
            if output_file and created_by:
                try:
                    user_project_dir = Path(f"data/projects/{created_by}")
                    if user_project_dir.exists():
                        for brief_file in user_project_dir.rglob("BRIEF.md"):
                            out_path = brief_file.parent / output_file
                            out_path.write_text(_resp_text)
                            break
                except Exception:
                    pass

            data = task_engine._load(server_id)
            if task_data["id"] in data["tasks"]:
                data["tasks"][task_data["id"]]["output"] = _resp_text[:2000]
            task_engine._save(server_id, data)
            task_engine.transition(server_id, task_data["id"], "done", "执行完成")
            return {"response": _resp_text, "success": True}

        task_engine.transition(server_id, task_data["id"], "failed", "执行失败")
        self._extractor.update_task_progress(
            task_name=task_data.get("title", ""),
            session_id=server_id,
            step_number=1,
            step_description="任务执行",
            tool_name="wisdom",
            file_path=task_data.get("output_file", ""),
            status="failed",
            error_message="执行失败"
        )
        return {"response": "", "success": False}


    # ====================================================================
    #  Review
    # ====================================================================
    def review_task(self, task_id, task_data, server_id="default"):
        title = task_data.get("title", "")
        created_by = task_data.get("created_by", "")
        worker = task_data.get("assigned_to", "")
        output = task_data.get("output", "")

        if not output:
            self.start_next(task_data)
            return

        spec = ""
        try:
            spec_dir = Path(f"data/projects/{created_by}")
            if spec_dir.exists():
                for spec_file in spec_dir.rglob("*.md"):
                    spec += spec_file.read_text() + "\n"
        except Exception:
            pass

        retry_count = task_data.get("_retry_count", 0)

        prompt = f"""你是 ClawsJoy 的审查员。对照验收标准，审查以下任务产出。

【验收标准】
{spec}

【任务产出】
{output[:1500]}

请逐项检查，只输出：
通过项：
- ...
修改项：
- ...

如果全部通过，只输出"通过"。不要反问。"""


        import time

        def _has_modify_items(text):
            """判定审查是否通过：'修改项'章节为空 → 无修改项 → 通过"""
            if not text or not text.strip():
                return False
            lines = text.strip().splitlines()
            in_modify = False
            items = []
            for line in lines:
                s = line.strip()
                if not in_modify:
                    if "修改项" in s:
                        in_modify = True
                    continue
                # 遇到下一个章节标题则结束收集
                if "通过项" in s or s.startswith(("【", "#", "验收标准", "总结")):
                    break
                if not s:
                    continue
                items.append(s)
            for it in items:
                clean = it.lstrip("-*+ .").strip()
                if clean and clean not in ("无", "无修改项", "没有", "无问题", "无异常", "无异议", "None", "none", "无需修改"):
                    return True
            return False

        try:
            # LLM 返回空时重试 1 次（P0-B：120s×3 可阻塞队列 360s，降为 30s×2 并保证续跑）
            review = ""
            for attempt in range(2):
                try:
                    review = llm_client.generate(prompt, task_type="review", timeout=30)
                except Exception as e:
                    logger.warning(f"审查生成异常: {e}")
                    review = ""
                if review and review.strip():
                    break
                if attempt < 2:
                    print(f"[ORCH] review 为空，2 秒后重试第 {attempt + 1} 次")
                    time.sleep(2)

            # 重试后仍为空：标记 pending_review 等待人工复核，但队列继续（P0-B 不阻塞后续任务）
            if not review or not review.strip():
                print(f"[ORCH] review 重试后仍为空，标记 pending_review: {title}")
                task_engine.transition(server_id, task_id, "pending_review", "审查结果为空，等待人工复核")
                notify("老板", f"⚠️「{title}」审查结果为空，已标记 pending_review，等待人工复核")
                self.start_next(task_data)
                return

            review_dir = Path(f"data/projects/{created_by}/reviews")
            review_dir.mkdir(parents=True, exist_ok=True)
            review_file = review_dir / f"{task_id}_review.md"

            # 判定改为：'修改项'为空 → 审查通过（不再依赖 startswith("通过")）
            if not _has_modify_items(review):
                task_engine.transition(server_id, task_id, "reviewed", "审查通过")
                self._extractor.update_task_progress(
                    task_name=task_data.get("title", ""),
                    session_id=server_id,
                    step_number=1,
                    step_description="审查通过",
                    tool_name="review",
                    file_path="",
                    status="completed"
                )
                # === SAG: 更新 plan 状态为 completed ===
                self._extractor.upsert_entity({
                    "entity_type": "plan",
                    "entity_name": f"plan::{task_data.get('title', '')}",
                    "signature": json.dumps({"status": "completed"}),
                    "related_entities": [],
                    "file_path": ""
                }, project_id=task_data.get("created_by", ""))
                review_file.write_text(f"✅ 审查通过\n\n{review}")
                self.start_next(task_data)
            elif retry_count >= 2:
                notify("老板", f"❌「{title}」返工{retry_count}次未通过")
                with open(review_file, "a") as f:
                    f.write(f"\n---\n❌ 返工{retry_count+1}次，标记失败\n{review}\n")
                task_engine.transition(server_id, task_id, "failed", "审查多次不通过")
                self._extractor.update_task_progress(
                    task_name=task_data.get("title", ""),
                    session_id=server_id,
                    step_number=1,
                    step_description="审查不通过",
                    tool_name="review",
                    file_path="",
                    status="failed",
                    error_message="审查多次不通过"
                )
                # === SAG: 更新 plan 状态为 failed ===
                self._extractor.upsert_entity({
                    "entity_type": "plan",
                    "entity_name": f"plan::{task_data.get('title', '')}",
                    "signature": json.dumps({"status": "failed"}),
                    "related_entities": [],
                    "file_path": ""
                }, project_id=task_data.get("created_by", ""))
            else:
                notify(worker, f"🔄「{title}」返工第{retry_count+1}次")
                with open(review_file, "a") as f:
                    f.write(f"\n---\n🔄 返工第{retry_count+1}次\n{review}\n")
                task_data["_retry_count"] = retry_count + 1
                print(f"[ORCH] 返工 {worker} {title} 第{retry_count+1}次")
                task_engine.transition(server_id, task_id, "pending", "审查不通过")
                task_engine.transition(server_id, task_id, "running", "返工重试")
                updated_task = task_engine.get(server_id, task_id)
                self.execute_task(updated_task)
        except Exception as e:
            logger.warning(f"审查失败: {e}")
            self.start_next(task_data)


    # ====================================================================
    #  #31 长线任务循环（V9 队列驱动）
    # ====================================================================

    def get_current_queue_task(self, user_id, session_id, current_plan=None) -> Optional[dict]:
        """#31 定位长线任务队列当前任务：running 优先，否则首个 pending。无队列返回 None。"""
        orch = self._orchestrations.get(user_id)
        if not orch:
            return None
        for _tid in orch.get("task_ids", []):
            _t = task_engine.get("default", _tid)
            if _t and _t["status"] == "running":
                return _t
        for _tid in orch.get("task_ids", []):
            _t = task_engine.get("default", _tid)
            if _t and _t["status"] == "pending":
                return _t
        return None

    def run_v9_queue_task(self, task, user_id, session_id, current_plan=None, sub_task_id=None, server_id="default"):
        """#31 V9 队列任务入口：标记 _v9_mode、确保 running、启动 V9 异步执行（带 done/fail 回调链式取下一个）"""
        _task_id = task["id"]
        if task["status"] != "running":
            task_engine.transition(server_id, _task_id, "running", "V9 自动开始")
        # 持久化 _v9_mode / _v9_session（供 hooks 判断与断点续跑）
        try:
            _data31 = task_engine._load(server_id)
            _data31["tasks"][_task_id]["_v9_mode"] = True
            _data31["tasks"][_task_id]["_v9_session"] = session_id
            task_engine._save(server_id, _data31)
        except Exception:
            pass
        from core.gateway.execute_agent_task import _execute_agent_task
        _plan = {
            "title": task.get("title", ""),
            "output_file": task.get("output_file", ""),
            "assigned_to": task.get("assigned_to", ""),
            "user_id": user_id,
            "session_id": session_id,
            "current_plan": current_plan or {},
        }
        import threading as _th31
        _th31.Thread(
            target=_execute_agent_task,
            args=(user_id, session_id, [
                {"role": "system", "content": f"执行任务：{task.get('title', '')}。输出写入：{task.get('output_file', '')}。计划：{json.dumps(_plan, ensure_ascii=False)}"}
            ], os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"), _task_id, sub_task_id),
            kwargs={
                "on_done": self.on_v9_done,
                "on_fail": self.on_v9_fail,  # P3: 直接传绑定方法(带 dict 注解), 结构化失败回调
            },
            daemon=True,
        ).start()
        return {"status": "executing", "task_id": _task_id, "queue": True}

    def on_v9_done(self, task_id, user_id, session_id, output=""):
        """#31 V9 完成回调：done + 回写 output + 自动取下一个（链式）"""
        server_id = "default"
        task = task_engine.get(server_id, task_id)
        if not task:
            return
        task["output"] = str(output or task.get("output", ""))[:2000]
        try:
            _data31 = task_engine._load(server_id)
            _data31["tasks"][task_id]["output"] = task["output"]
            task_engine._save(server_id, _data31)
        except Exception:
            pass
        task_engine.transition(server_id, task_id, "done", "V9 执行完成")
        self._next_v9(task, user_id, server_id)

    def on_v9_fail(self, task_id, user_id, session_id, reason: dict = None):
        """#31 V9 失败回调（P3 结构化）：transition failed，按 code 决策
        - NETWORK: 自动重试 1 次（网络抖动可恢复）
        - TIMEOUT: 终止（不重试，继续下一个——重试只会再次超时）
        - 其他(LLM_API/TOOL_EXEC/TOOL_ARGS/UNKNOWN): 原逻辑重试 1 次
        兼容旧文本调用: 非 dict 时按无 code 处理（保持原重试 1 次行为）。
        """
        server_id = "default"
        task = task_engine.get(server_id, task_id)
        if not task:
            return
        _code = reason.get("code", "") if isinstance(reason, dict) else ""
        _msg = reason.get("message", "") if isinstance(reason, dict) else str(reason or "")
        task_engine.transition(server_id, task_id, "failed", str(_msg or "V9 执行失败")[:200])
        # P3: TIMEOUT 终止（不重试）
        if _code == "TIMEOUT":
            logger.warning(f"任务 {task_id} V9 超时终止，不重试")
            self._next_v9(task, user_id, server_id)
            return
        _retry = task.get("_retry_count", 0)
        if _retry < 1:
            try:
                _data31 = task_engine._load(server_id)
                _data31["tasks"][task_id]["_retry_count"] = _retry + 1
                task_engine._save(server_id, _data31)
            except Exception:
                pass
            logger.warning(f"任务 {task_id} V9 执行失败（code={_code or 'n/a'}），自动重试第 {_retry + 1} 次")
            self.run_v9_queue_task(task_engine.get(server_id, task_id), user_id, session_id)
            return
        self._next_v9(task, user_id, server_id)

    def _next_v9(self, task, user_id, server_id="default"):
        """#31 取同批次下一个 pending 任务，有则 V9 链式执行，无则结束"""
        orch = self._orchestrations.get(user_id)
        if not orch:
            return
        for _tid in orch.get("task_ids", []):
            _t = task_engine.get(server_id, _tid)
            if _t and _t["status"] == "pending":
                self.run_v9_queue_task(_t, user_id, _t.get("_v9_session", ""))
                return
        try:
            notify("老板", "🎉 长线任务队列已全部完成！")
        except Exception:
            pass

    # ====================================================================
    #  Start Next
    # ====================================================================

    def start_next(self, task_data, server_id="default"):
        all_tasks = task_engine.list(server_id)
        created_by = task_data.get("created_by", "")

        next_tasks = [
            t for t in all_tasks
            if t.get("created_by") == created_by
            and t["status"] == "pending"
            and t.get("assigned_to")
        ]

        if next_tasks:
            next_tasks.sort(key=lambda t: t.get("created_at", ""))
            next_t = next_tasks[0]
            task_engine.transition(server_id, next_t["id"], "running", "自动开始")
            self.execute_task(next_t)
            return

        orphan = [t for t in all_tasks
                  if t.get("created_by") == created_by
                  and t["status"] == "pending"
                  and not t.get("assigned_to")]
        if orphan:
            names = "、".join([t["title"] for t in orphan])
            notify("老板", f"⚠️ 以下任务无可用工人：{names}")

        notify("老板", "🎉 所有可执行任务已完成！")

    # ====================================================================
    #  拆解
    # ====================================================================

    def _decompose(self, user_input: str) -> List[dict]:
        agent_summary = json.dumps(
            {name: caps.get("skills", []) for name, caps in self.knowledge.get("agents", {}).items()},
            ensure_ascii=False
        )
        active_positions = []
        try:
            for m in roster_engine.list_active("default"):
                active_positions.append(m.get("position", ""))
        except Exception:
            pass
        position_hint = f"当前可用工人岗位：{', '.join(active_positions)}。只拆这些岗位能做的步骤。" if active_positions else ""

        # ================================================================
        # 改 1：_decompose prompt — 每个 task 产出独立文件
        # ================================================================

        prompt = f"""将以下需求拆解为 2-4 个子任务。每个子任务产出一个独立文件，后续任务依赖前序文件。

可用 Agent 能力：
{agent_summary}

{position_hint}

需求：{user_input}

规则：
- 每个子任务产出一个独立文件，文件名根据任务内容用英文命名（如 storyboard.md、visual_style.md、video_script.md、audio_plan.md）
- 后续任务基于前序文件展开，不重复前序内容
- 每个 task 产出物必须不同，不要拆出两个相似 task
- 不要把同一工种的工作拆成多个 task
- 视觉/设计类用"图像生成"或"设计"，音频类用"音频制作"，不全部用"内容写作"
- 不要拆出审查、审核、验收步骤
- 标题用"动词+对象"，不含"你们""帮我"
- required_skill 从可用技能中选择：内容写作, 视频制作, 视频剪辑, 图像生成, 翻译, 设计, 音频制作, 数据分析

输出严格 JSON 数组：
[{{"title": "撰写分镜脚本", "required_skill": "内容写作", "output_file": "storyboard.md"}}, ...]"""


        try:
            resp = llm_client.generate(
                prompt, model=MODEL_MAIN, max_tokens=800,
                temperature=0.2, task_type="task_decompose", timeout=30
            )
            # llm_client.generate() 可能返回生成器，迭代取最后一个值
            if hasattr(resp, '__next__'):
                try:
                    gen_resp = None
                    for gen_resp in resp:
                        pass
                    resp = gen_resp if gen_resp is not None else ""
                except Exception as gen_e:
                    logger.warning(f"生成器迭代失败: {gen_e}")
                    resp = ""
            resp = resp.strip()
            if "```" in resp:
                match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', resp, re.DOTALL)
                if match:
                    resp = match.group(1)
            if "[" in resp and "]" in resp:
                start = resp.index("[")
                end = resp.rindex("]") + 1
                parsed = json.loads(resp[start:end])
                if isinstance(parsed, list) and len(parsed) > 0:
                    return parsed
        except Exception as e:
            logger.warning(f"LLM 拆解失败: {e}")

        return self._rule_decompose(user_input)

    def _rule_decompose(self, text: str) -> List[dict]:
        parts = re.split(r'[，,；;然后接着再]+', text)
        parts = [p.strip() for p in parts if len(p.strip()) > 3]
        if not parts:
            return [{"title": text[:50], "required_skill": self._guess_skill(text)}]
        return [{"title": p[:50], "required_skill": self._guess_skill(p)} for p in parts[:4]]

    def _guess_skill(self, text: str) -> str:
        for skill in SKILL_TO_POSITION:
            if any(w in text for w in skill):
                return skill
        return "内容写作"

    def _find_worker(self, skill: str, active_agents: List[dict]) -> Optional[dict]:
        target = SKILL_TO_POSITION.get(skill, "")
        if target:
            for a in active_agents:
                if a.get("position") == target:
                    return a
        target = AGENT_TO_POSITION.get(skill, "")
        if target:
            for a in active_agents:
                if a.get("position") == target:
                    return a
        for a in active_agents:
            if a.get("position", "") in skill or skill in a.get("position", ""):
                return a

        # 降级：找不到工人 → 分配给作家
        for a in active_agents:
            if a.get("position") == "作家":
                return a
        return None

    # ====================================================================
    #  Discord
    # ====================================================================

    def discuss_plan(self, user_message: str, current_plan: dict, user_id: str = "老板", server_id: str = "default") -> dict:
        """多轮计划讨论：快速路径 + 兜底 + 审计检查"""
        # 快速确认路径
        if any(kw in user_message for kw in ["确认", "开始执行", "执行计划", "按此计划", "ok", "好的", "可以", "行"]):
            return {
                "plan_status": "confirmed",
                "message": "计划已确认，开始执行。",
                "current_plan": current_plan,
            }

        # === 审计检查 ===
        discussion_rules = self._audit_rules.get("discussion", {})
        max_rounds = discussion_rules.get("max_rounds", 20)
        timeout_minutes = discussion_rules.get("timeout_minutes", 30)
        duplicate_detection = discussion_rules.get("duplicate_detection", True)

        discussion = current_plan.get("_discussion", [])

        # === Token 预算检查 ===
        token_budget = self._audit_rules.get("token_budget", {})
        _per_session = token_budget.get("per_session", 50000)
        _per_day = token_budget.get("per_day", 500000)
        try:
            _billing_file = Path(f"data/v8/billing_{server_id}.jsonl")
            _today_str = datetime.now().strftime("%Y-%m-%d")
            _session_tokens = 0
            _day_tokens = 0
            if _billing_file.exists():
                with open(_billing_file) as _bf:
                    for _line in _bf:
                        try:
                            _entry = json.loads(_line)
                            _ts = _entry.get("timestamp", "")
                            if _ts.startswith(_today_str) and "ollama" not in (_entry.get("model", "") or "").lower():
                                _summary = (_entry.get("summary", "") or "").lower()
                                _task_type = (_entry.get("task_type", "") or "").lower()
                                if "discuss" not in _summary and "discuss" not in _task_type:
                                    continue
                                _day_tokens += _entry.get("tokens", 0)
                                # 简单取最近一条记录的 session 近似值
                        except Exception:
                            pass
            # per_session 用当前讨论轮次 * 预估单轮 token
            _session_tokens = (len(discussion) + 1) * 2000
            if _per_day > 0 and _day_tokens >= _per_day:
                write_os_event(
                    event_type="intercept",
                    operation="publish",
                    command="discuss_plan",
                    reason=f"全局 Token 日预算超限({_day_tokens}>={_per_day})",
                    detail={"plan": current_plan.get("title", ""), "day_tokens": _day_tokens, "per_day": _per_day},
                    user_id=user_id,
                    server_id=server_id,
                )
                current_plan["_discussion"] = discussion + [{"role": "user", "content": user_message}]
                return {
                    "plan_status": "confirmed",
                    "message": f"今日 Token 预算已超限({_day_tokens}/{_per_day})，自动确认计划。",
                    "current_plan": current_plan,
                }
            if _session_tokens >= _per_session:
                write_os_event(
                    event_type="intercept",
                    operation="publish",
                    command="discuss_plan",
                    reason=f"会话 Token 预算超限({_session_tokens}>={_per_session})",
                    detail={"plan": current_plan.get("title", ""), "session_tokens": _session_tokens, "per_session": _per_session},
                    user_id=user_id,
                    server_id=server_id,
                )
                current_plan["_discussion"] = discussion + [{"role": "user", "content": user_message}]
                return {
                    "plan_status": "confirmed",
                    "message": f"会话 Token 预算已超限({_session_tokens}/{_per_session})，自动确认计划。",
                    "current_plan": current_plan,
                }
        except Exception as _e:
            logger.warning(f"Token 预算检查失败: {_e}")
        # === /Token 预算检查 ===

        # 1. 轮次上限检查
        if len(discussion) >= max_rounds:
            write_os_event(
                event_type="intercept",
                operation="publish",
                command="discuss_plan",
                reason=f"讨论轮次超限({len(discussion)}>={max_rounds})",
                detail={"plan": current_plan.get("title", ""), "rounds": len(discussion), "max_rounds": max_rounds},
                user_id=user_id,
                server_id=server_id,
            )
            current_plan["_discussion"] = discussion + [{"role": "user", "content": user_message}]
            return {
                "plan_status": "confirmed",
                "message": f"讨论已达上限({max_rounds}轮)，自动确认计划。最新反馈已记录。",
                "current_plan": current_plan,
            }

        # 2. 超时检测
        if len(discussion) > 0:
            last_msg = discussion[-1]
            if "timestamp" in last_msg:
                try:
                    last_time = datetime.fromisoformat(last_msg["timestamp"])
                    elapsed = (datetime.now() - last_time).total_seconds() / 60
                    if elapsed > timeout_minutes:
                        write_os_event(
                            event_type="intercept",
                            operation="publish",
                            command="discuss_plan",
                            reason=f"讨论超时({elapsed:.1f}min>{timeout_minutes}min)",
                            detail={"plan": current_plan.get("title", ""), "elapsed_minutes": round(elapsed, 1), "timeout_minutes": timeout_minutes},
                            user_id=user_id,
                            server_id=server_id,
                        )
                        current_plan["_discussion"] = discussion + [{"role": "user", "content": user_message}]
                        return {
                            "plan_status": "confirmed",
                            "message": f"讨论已超时({elapsed:.1f}分钟)，自动归档。最新反馈已记录。",
                            "current_plan": current_plan,
                        }
                except Exception:
                    pass

        # 3. 重复检测
        if duplicate_detection and len(discussion) > 0:
            last_user_msg = discussion[-1].get("content", "").strip()
            if last_user_msg == user_message.strip():
                write_os_event(
                    event_type="intercept",
                    operation="publish",
                    command="discuss_plan",
                    reason="重复消息检测",
                    detail={"plan": current_plan.get("title", ""), "duplicate_content": user_message[:100]},
                    user_id=user_id,
                    server_id=server_id,
                )
                return {
                    "plan_status": "discussing",
                    "message": "检测到重复消息，请勿重复发送相同内容。",
                    "current_plan": current_plan,
                }

        current_plan["_discussion"] = discussion + [{"role": "user", "content": user_message}]
        return {
            "plan_status": "discussing",
            "message": "收到您的反馈。",
            "current_plan": current_plan,
        }

    def agent_discuss_plan(self, focus, agents, user_id="老板", server_id="default", max_rounds=8):
        """多 Agent 讨论计划：调用 AgentDiscussionEngine.discuss()，返回讨论结果"""
        engine = AgentDiscussionEngine()
        result = engine.discuss(
            focus=focus,
            agents=agents,
            max_rounds=max_rounds,
            user_id=user_id,
        )
        return {
            "consensus": result.get("consensus", False),
            "decision": result.get("decision", ""),
            "rounds": result.get("rounds", 0),
            "history": result.get("history", []),
        }

    def build_discussion_prompt(self, user_message: str, current_plan: dict, user_id: str = "老板", server_id: str = "default", agent_name: str = "编排Agent"):
        """构造讨论 prompt + 选择模型/端点"""
        import os
        model_name = os.getenv("ORCHESTRATOR_MODEL", "deepseek-reasoner")
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        endpoint = None
        # 查花名册
        try:
            from core.lib.v8.roster_engine import roster_engine
            member = roster_engine.get(server_id, agent_name)
        except Exception:
            member = None
        # 根据花名册 position 动态生成 System Prompt
        _position = member.get("position", "员工") if member else "员工"
        _prompts = {
            "编排Agent": "你是 ClawsJoy 的任务编排 Agent，负责分析需求、拆解步骤、制定计划。",
            "程序员": "你是 ClawsJoy 的程序员，负责代码开发、技术方案设计。",
            "设计师": "你是 ClawsJoy 的设计师，负责视觉设计、创意方案。",
            "作家": "你是 ClawsJoy 的作家，负责内容创作、文案撰写。",
            "分析师": "你是 ClawsJoy 的分析师，负责数据分析、竞品研究。",
            "翻译员": "你是 ClawsJoy 的翻译员，负责多语言翻译。",
            "元认知Agent": "你是 ClawsJoy 的元认知分析 Agent，负责分析团队效率、系统问题。",
        }
        _role_prompt = _prompts.get(_position, f"你是 ClawsJoy 的 {_position}，负责完成老板分配的任务。")
        # === SAG: 查询历史 hypothesis 生成警告 ===
        history_warnings_list = []
        try:
            from core.lib.code_entity_extractor import extractor
            if hasattr(extractor, 'query_entities'):
                hypotheses = extractor.query_entities(entity_type="system_hypothesis", limit=5)
                for h in hypotheses:
                    if h.get("inefficiency_rate", 0) > 0.3:
                        history_warnings_list.append(f"⚠ {h.get('problem_type', '')}: {h.get('insight', '')}")
        except Exception:
            pass
        system_prompt = f"""{_role_prompt}

当前计划：
{json.dumps(current_plan.get("plan", []), ensure_ascii=False, indent=2)}

你的职责：
1. 理解用户的反馈
2. 如果用户选定了技术方案，更新计划中对应的步骤
3. 如果用户质疑推荐，用技术细节解释理由，但不固执——用户偏好优先
4. 输出 JSON：{{"response": "...", "plan_updated": false, "plan_status": "discussing"}}
用户确认时 plan_status 改为 "confirmed"。"""

        if member:
            model_name = member.get("model", model_name)
            api_key = member.get("api_key", api_key)

        if "ollama" in model_name.lower() or "qwen" in model_name.lower():
            endpoint = "http://127.0.0.1:11434/api/chat"
        else:
            endpoint = "https://api.deepseek.com/chat/completions"

        return {
            "model": model_name,
            "api_key": api_key,
            "endpoint": endpoint,
            "system_prompt": system_prompt,
            "current_plan": current_plan,
            "history_warnings": history_warnings_list,
        }

    def _build_card(self, tasks: List[dict], original_input: str) -> str:
        emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        lines = [f"📋 **任务已创建** — 共 {len(tasks)} 步\n"]
        for i, t in enumerate(tasks):
            e = emoji[i] if i < len(emoji) else "▶️"
            lines.append(f"{e} **{t['title']}** → @{t.get('_agent_name', '待分配')}")
        lines.append(f"\n💬 *{original_input[:120]}{'...' if len(original_input) > 120 else ''}*")
        return "\n".join(lines)

    def _generate_output_file(self, title: str, step: int) -> str:
        short = re.sub(r'[^a-zA-Z\u4e00-\u9fa5]', '', title)[:8]
        return f"step{step:02d}_{short}.md"


orchestrator = TaskOrchestrator()
