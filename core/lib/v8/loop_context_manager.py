#!/usr/bin/env python3
"""LoopContextManager v1.0 — 四层上下文编排注入

架构：
  Layer 1 (核心层 · 恒定):   任务级 system prompt，随任务固定不变
  Layer 2 (摘要层 · 递进):   recap_checkpoint()，按 step 递进注入历史摘要
  Layer 3 (检索层 · 按需):   _load_asset_step_aware()，基于 os_precision_feeds.yaml
                              按任务关键词和岗位匹配精准投喂
  Layer 4 (过滤网 · 控制):   inject_related_context()，SAG 关联上下文检索，
                              通过 max_items / max_chars 做过滤控制

用法:
    ctx_mgr = LoopContextManager()
    context = ctx_mgr.inject_all(
        task_name="修改用户登录模块",
        step_number=3,
        user_id="user_abc",
        session_id="session_xyz",
    )
"""

# ============================================================
# [P0-2] 四层注入调用链收敛 — 当前状态声明（2026-08 架构决策）
# ------------------------------------------------------------
# 本文件是「四层上下文编排注入」的完整实现，但当前属于死代码，
# 主流程未接入本文件的四层注入主链路，保留作架构参考。
#
# 1) 实际调用点（仅 2 处，均未走四层注入主链路）：
#    - core/lib/v8/loop_context_manager.py（V8 侧副本）
#      <- agent_gateway_enhanced.py L6067-6068
#         仅调用 _inject_tool_declarations() 注入工具声明段；
#         四层注入核心（inject_all / recap_checkpoint /
#         _load_asset_step_aware / inject_related_context）未被调用。
#    - clawsjoy_v10/engine/context/loop_context_manager.py（V10 侧副本）
#      <- clawsjoy_v10/run.py L37
#         仅 import 触发模块加载副作用（# noqa: E402,F401），
#         未调用任何方法。
#
# 2) 与主流程的关系（双轨并存）：
#    主流程 agent_gateway_enhanced.py 内部散落独立的
#    recap（步骤摘要 / steps_summary）与 precision（精准投喂 /
#    os_precision_feeds.yaml / 工具声明段）实现，与本文件互不调用。
#    本文件是历史完整实现，暂不接入主流程调用链（改动太大），
#    禁止据此误判「主流程已接入四层注入」。
#
# 3) 维护约定：
#    - 修改注入逻辑时，优先改主流程（agent_gateway_enhanced.py）
#      中已生效的 recap/precision 实现；
#    - 本文件与 core/lib/v8/loop_context_manager.py 内容完全一致
#      （md5 相同），修改需两侧同步。
# ============================================================

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml

logger = logging.getLogger(__name__)

# ============================================================
# 路径常量
# ============================================================
CONFIG_DIR = Path("core/config")
PROMPTS_DIR = CONFIG_DIR / "prompts"
POSITIONS_DIR = CONFIG_DIR / "v8/positions"
V8_DATA_DIR = Path("data/v8")
CAPABILITIES_YAML = Path("config/os_capabilities.yaml")

# ============================================================
# 岗位 → 能力映射（#153 花名册能力差异化）
# 与 roster_default.json 中每个 Agent 的能力描述段保持一致，
# 精准投喂注入时按 position 匹配对应能力描述。
# ============================================================
POSITION_CAPABILITY_MAP = {
    "程序员": ["read_file", "write_file", "list_dir", "search_files", "execute_command", "query_index"],
    "设计师": ["read_file", "list_dir", "search_files", "execute_command"],
    "分析师": ["read_file", "list_dir", "search_files", "query_index"],
    "作家": ["read_file", "write_file", "list_dir", "execute_command"],
    "视频编辑": ["read_file", "list_dir", "execute_command"],
    "翻译员": ["read_file", "write_file", "query_index"],
    "文件管理": ["read_file", "write_file", "list_dir", "search_files"],
    "决策审查": ["read_file", "search_files", "query_index"],
    "编排Agent": ["read_file", "list_dir", "query_index"],
    "元认知Agent": ["read_file", "query_index", "execute_command"],
}

# ============================================================
# 默认 System Prompt（兜底）
# ============================================================
DEFAULT_SYSTEM_PROMPT = """你是 ClawsJoy 的 AI 助手。

你拥有以下能力：
1. 读写文件
2. 执行命令
3. 搜索代码
4. 查询知识库

请根据任务上下文和用户指令完成工作。"""


class LoopContextManager:
    """四层上下文编排注入 — 单例"""

    _instance = None

    # ---------- 缓存 ----------
    _feeds_config: Optional[dict] = None
    _position_prompts: Dict[str, str] = {}
    _system_prompt_cache: Optional[str] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    # ================================================================
    # 公开接口
    # ================================================================

    def inject_all(
        self,
        task_name: str,
        step_number: int,
        user_id: str,
        session_id: str,
    ) -> Dict[str, Any]:
        """四层上下文编排注入，返回组装好的完整上下文。

        参数:
            task_name:   任务名称 / 用户指令摘要
            step_number: 当前步骤编号（从 1 开始）
            user_id:     用户 ID
            session_id:  会话 ID

        返回:
            {
                "system_prompt": str,       # Layer 1
                "recap": str,               # Layer 2
                "precision_feed": str,      # Layer 3
                "sag_context": str,         # Layer 4
                "assembled": str,           # 四层拼接后的完整上下文
                "meta": {
                    "layers": 4,
                    "step": step_number,
                    "task": task_name,
                    "timestamp": "...",
                }
            }

        容错策略:
            每层独立 try/except：单层失败只跳过该层（置为空字符串并记录日志），
            其余层继续执行；最终始终返回完整 dict，绝不返回 None。
        """
        # --- Layer 1: 任务级 system prompt（核心层 · 恒定） ---
        try:
            system_prompt = self._build_system_prompt(task_name)
        except Exception as e:
            logger.error(f"[LoopContextManager] Layer1 system_prompt 构建失败: {e}")
            system_prompt = ""

        # --- Layer 2: recap 递进注入（摘要层 · 递进） ---
        try:
            recap = self.recap_checkpoint(step_number, session_id)
        except Exception as e:
            logger.error(f"[LoopContextManager] Layer2 recap 注入失败: {e}")
            recap = ""

        # --- Layer 3: 精准投喂（检索层 · 按需） ---
        try:
            precision_feed = self._load_asset_step_aware(task_name, step_number, user_id)
        except Exception as e:
            logger.error(f"[LoopContextManager] Layer3 precision_feed 注入失败: {e}")
            precision_feed = ""

        # --- Layer 4: SAG 关联上下文（过滤网 · 控制） ---
        try:
            sag_context = self.inject_related_context(task_name, session_id)
        except Exception as e:
            logger.error(f"[LoopContextManager] Layer4 sag_context 注入失败: {e}")
            sag_context = ""

        # --- 组装完整上下文 ---
        try:
            assembled = self._assemble_context(
                system_prompt=system_prompt,
                recap=recap,
                precision_feed=precision_feed,
                sag_context=sag_context,
                task_name=task_name,
                step_number=step_number,
            )
        except Exception as e:
            logger.error(f"[LoopContextManager] 上下文组装失败: {e}")
            assembled = ""

        return {
            "system_prompt": system_prompt,
            "recap": recap,
            "precision_feed": precision_feed,
            "sag_context": sag_context,
            "assembled": assembled,
            "meta": {
                "layers": 4,
                "step": step_number,
                "task": task_name,
                "timestamp": datetime.now().isoformat(),
            },
        }

    # ================================================================
    # Layer 1: 任务级 System Prompt
    # ================================================================

    def _build_system_prompt(self, task_name: str) -> str:
        """构建任务级 system prompt。

        策略：
        1. 读取 core/config/prompts/agent_system.md 作为基础 System Prompt
        2. 按 task_name 关键词匹配岗位，加载岗位级 prompt 增强
        3. 组装成任务级 system prompt
        """
        # ---- 1. 基础 System Prompt ----
        base_prompt = self._load_base_system_prompt()

        # ---- 2. 岗位级增强 ----
        position = self._infer_position(task_name)
        position_prompt = self._load_position_prompt(position)

        # ---- 3. 组装 ----
        parts = [base_prompt]
        if position_prompt:
            parts.append(f"\n## 岗位指令（{position}）\n{position_prompt}")
        parts.append(
            f"\n## 当前任务\n任务名称: {task_name}\n"
            f"请根据上述指令和以下上下文完成任务。"
        )

        return "\n\n---\n\n".join(parts)

    # ================================================================
    # Layer 2: Recap Checkpoint（摘要层 · 递进）
    # ================================================================

    def recap_checkpoint(self, step_number: int, session_id: str) -> str:
        """注入复述摘要。

        从 data/v8/recap_{session_id}.jsonl 读取历史 step 的 recap 条目，
        按 step_number 筛选出 <= 当前 step 的条目，
        按时间顺序拼接成「递进摘要」。

        如果文件不存在或为空，返回空字符串。
        """
        recap_file = V8_DATA_DIR / f"recap_{session_id}.jsonl"
        if not recap_file.exists():
            logger.debug("recap_checkpoint: 无 recap 文件 %s", recap_file)
            return ""

        entries = []
        try:
            with open(recap_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    # 只取 <= 当前 step 的条目
                    if entry.get("step", 999) <= step_number:
                        entries.append(entry)
        except OSError as e:
            logger.warning("recap_checkpoint: 读取失败 %s", e)
            return ""

        if not entries:
            return ""

        # 按 step 排序
        entries.sort(key=lambda e: e.get("step", 0))

        lines = ["## 任务历史摘要（递进）"]
        for e in entries:
            step = e.get("step", "?")
            summary = e.get("summary", e.get("content", ""))
            lines.append(f"- Step {step}: {summary[:300]}")

        return "\n".join(lines)

    # ================================================================
    # Layer 3: 精准投喂（检索层 · 按需）
    # ================================================================

    def _load_position_capabilities(self, position: str) -> str:
        """按岗位从 os_capabilities.yaml 加载能力描述段（#153 花名册能力差异化）。

        从 os_capabilities.yaml 读取 capability 列表，按 position 匹配
        POSITION_CAPABILITY_MAP，渲染为与 roster_default.json 中能力描述段
        一致的文本；岗位无映射或读取失败时返回空字符串。
        """
        if not position:
            return ""
        cap_ids = POSITION_CAPABILITY_MAP.get(position)
        if not cap_ids:
            return ""
        try:
            if not CAPABILITIES_YAML.exists():
                logger.warning("os_capabilities.yaml 不存在: %s", CAPABILITIES_YAML)
                return ""
            with open(CAPABILITIES_YAML, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except (OSError, yaml.YAMLError) as e:
            logger.warning("读取 os_capabilities.yaml 失败: %s", e)
            return ""

        caps_by_id = {str(c.get("id", "")).strip(): c for c in data.get("capabilities", [])}
        lines = [f"【能力描述】作为 ClawsJoy 的{position}，你拥有以下能力："]
        for cid in cap_ids:
            cap = caps_by_id.get(cid)
            desc = str(cap.get("description", "")).strip() if cap else ""
            lines.append(f"    - {cid}: {desc}")
        return "\n".join(lines)

    def _load_asset_step_aware(
        self,
        task_name: str,
        step_number: int,
        user_id: str,
    ) -> str:
        """精准投喂 — 按任务关键词和用户岗位匹配 os_precision_feeds.yaml。

        工作流程：
        1. 加载 os_precision_feeds.yaml
        2. 遍历 feeds，匹配 task_name 关键词和用户岗位
        3. 按 feed.inject.source 加载对应资产
        4. 按 max_chars / max_items 做截断控制
        5. 组合成投喂文本返回

        返回:
            投喂文本，无匹配时返回空字符串。
        """
        feeds = self._load_feeds_config()
        if not feeds:
            return ""

        # 推断用户岗位
        position = self._infer_position(task_name)

        matched_feeds = []
        for feed in feeds:
            feed_id = feed.get("id", "")
            keywords = feed.get("keywords", [])
            agent_positions = feed.get("agent_positions", [])

            # 关键词匹配
            kw_match = any(kw in task_name for kw in keywords)
            # 岗位匹配
            pos_match = position in agent_positions if agent_positions else True

            if kw_match and pos_match:
                matched_feeds.append(feed)

        if not matched_feeds:
            logger.debug(
                "_load_asset_step_aware: 无匹配 feed (task=%s, position=%s)",
                task_name,
                position,
            )
            return ""

        # 加载匹配的资产
        parts = []
        # #153 花名册能力差异化：注入当前岗位的能力描述段
        position_cap_text = self._load_position_capabilities(position)
        if position_cap_text:
            parts.append(f"【岗位能力（{position}）】\n{position_cap_text}")
        for feed in matched_feeds:
            feed_id = feed.get("id", "unknown")
            inject_configs = feed.get("inject", [])
            for inject_cfg in inject_configs:
                source = inject_cfg.get("source", "")
                max_chars = inject_cfg.get("max_chars", 2000)
                max_items = inject_cfg.get("max_items", None)
                asset_text = self._load_asset_source(
                    source=source,
                    max_chars=max_chars,
                    max_items=max_items,
                )
                if asset_text:
                    parts.append(f"【精准投喂: {feed_id}/{source}】\n{asset_text}")

        return "\n\n".join(parts) if parts else ""

    # ================================================================
    # Layer 3b: 精准投喂（独立注入 · 单层）
    # ================================================================

    def inject_precision_only(
        self,
        task_name: str,
        step_number: int,
        user_id: str,
        session_id: str,
        position: Optional[str] = None,
        match_mode: str = "or",
        prefix: str = "[系统注入] 基于任务类型自动投喂：",
    ) -> str:
        # 精准投喂 — 仅注入 Layer 3（精准投喂），不做四层拼接。
        # 与 _load_asset_step_aware 的差异：
        #   1. position 可显式传入（roster 真实岗位），缺省回退 _infer_position(task_name)；
        #   2. match_mode="or" 时关键词或岗位任一命中即注入（保持异步路径行为），
        #      而非 _load_asset_step_aware 的关键词 AND 岗位匹配；
        #   3. 资产加载复用 precision_feed._load_asset，保持 source 兼容，
        #      空源跳过、同源去重，并复用模块级缓存（hypothesis / learning_insight）；
        #   4. 输出保留 prefix（默认 "[系统注入] 基于任务类型自动投喂："）。
        #
        # 参数:
        #   task_name:   任务名称 / 用户指令摘要
        #   step_number: 当前步骤编号（从 1 开始）
        #   user_id:     用户 ID
        #   session_id:  会话 ID
        #   position:    roster 真实岗位；为 None 时回退 _infer_position(task_name)
        #   match_mode:  "or"（默认）关键词或岗位任一命中即注入；
        #                "and" 时需关键词与岗位同时命中
        #   prefix:      输出前缀，保留原注入前缀格式
        # 返回:
        #   投喂文本，无匹配 feed 或资产为空时返回空字符串。

        # 复用 precision_feed._load_asset（保持 source 兼容、空源去重、缓存）
        try:
            from core.lib import precision_feed
        except Exception as e:
            logger.warning("[LoopContextManager] inject_precision_only 导入 precision_feed 失败: %s", e)
            return ""

        feeds = self._load_feeds_config()
        if not feeds:
            return ""

        # position 显式传入（roster 真实岗位）优先，缺省回退任务推断
        if not position:
            position = self._infer_position(task_name)

        matched_feeds = []
        for feed in feeds:
            feed_id = feed.get("id", "")
            keywords = feed.get("keywords", []) or []
            agent_positions = feed.get("agent_positions", []) or []

            # 关键词匹配
            kw_match = any(kw in task_name for kw in keywords)
            # 岗位匹配
            pos_match = position in agent_positions if agent_positions else True

            if match_mode == "or":
                hit = kw_match or pos_match
            else:  # "and"
                hit = kw_match and pos_match

            if hit:
                matched_feeds.append(feed)

        if not matched_feeds:
            logger.debug(
                "inject_precision_only: 无匹配 feed (task=%s, position=%s, match_mode=%s)",
                task_name,
                position,
                match_mode,
            )
            return ""

        # 加载匹配的资产（precision_feed._load_asset：source 兼容、空源去重、缓存）
        parts = []
        seen_sources = set()
        for feed in matched_feeds:
            feed_id = feed.get("id", "unknown")
            inject_configs = feed.get("inject", []) or []
            for inject_cfg in inject_configs:
                source = (inject_cfg.get("source", "") or "").strip()
                if not source:
                    continue  # 空源跳过
                if source in seen_sources:
                    continue  # 同源去重：只注入一次
                seen_sources.add(source)
                max_chars = inject_cfg.get("max_chars", 2000)
                max_items = inject_cfg.get("max_items", None)
                params = {"max_chars": max_chars}
                if max_items:
                    params["max_items"] = max_items
                asset_text = precision_feed._load_asset(
                    source=source,
                    params=params,
                    user_id=user_id,
                    session_id=session_id,
                    step_number=step_number,
                )
                if asset_text:
                    parts.append(f"【精准投喂: {feed_id}/{source}】\n{asset_text}")

        if not parts:
            return ""

        return f"{prefix}\n" + "\n\n".join(parts)

    # ================================================================
    # Layer 4: SAG 关联上下文（过滤网 · 控制）
    # ================================================================

    def inject_related_context(self, task_name: str, session_id: str) -> str:
        """注入 SAG 关联上下文。

        从 data/v8/sag_{session_id}.jsonl 读取 SAG 历史条目，
        按 task_name 关键词匹配，用 max_items / max_chars 做过滤控制。

        返回:
            关联上下文字符串，无匹配时返回空字符串。
        """
        sag_file = V8_DATA_DIR / f"sag_{session_id}.jsonl"
        if not sag_file.exists():
            logger.debug("inject_related_context: 无 SAG 文件 %s", sag_file)
            return ""

        # 从 task_name 提取关键词用于匹配
        keywords = self._extract_keywords(task_name)

        entries = []
        try:
            with open(sag_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    # 用关键词匹配 SAG 条目
                    entry_text = json.dumps(entry, ensure_ascii=False)
                    if any(kw in entry_text for kw in keywords):
                        entries.append(entry)
        except OSError as e:
            logger.warning("inject_related_context: 读取失败 %s", e)
            return ""

        if not entries:
            return ""

        # 过滤控制：最多 5 条，每条最多 500 字符
        max_items = 5
        max_chars_per_item = 500

        entries = entries[:max_items]
        lines = ["## SAG 关联上下文"]
        for i, entry in enumerate(entries, 1):
            # 格式化条目，截断长内容
            text = json.dumps(entry, ensure_ascii=False, indent=None)
            if len(text) > max_chars_per_item:
                text = text[:max_chars_per_item] + "...(截断)"
            lines.append(f"- [{i}] {text}")

        return "\n".join(lines)

    # ================================================================
    # 内部工具方法
    # ================================================================

    def _assemble_context(
        self,
        system_prompt: str,
        recap: str,
        precision_feed: str,
        sag_context: str,
        task_name: str,
        step_number: int,
    ) -> str:
        """将四层上下文拼接为完整的 prompt 文本。"""
        parts = [system_prompt]

        if precision_feed:
            parts.append(precision_feed)

        if sag_context:
            parts.append(sag_context)

        if recap:
            parts.append(recap)

        footer = (
            f"\n\n## 步骤信息\n"
            f"- 任务: {task_name}\n"
            f"- 步骤: {step_number}"
        )
        parts.append(footer)

        return "\n\n---\n\n".join(parts)

    # ---------- 基础 System Prompt 加载 ----------

    def _load_base_system_prompt(self) -> str:
        """加载基础 System Prompt（#150：启动时注入最新工具声明段）。"""
        if self._system_prompt_cache:
            return self._system_prompt_cache

        prompt_path = PROMPTS_DIR / "agent_system.md"
        if prompt_path.exists():
            try:
                text = prompt_path.read_text(encoding="utf-8")
                # #150: 每次 Agent 启动从 os_capabilities.yaml 注入最新工具声明
                self._system_prompt_cache = self._inject_tool_declarations(text)
                return self._system_prompt_cache
            except OSError as e:
                logger.warning("读取 agent_system.md 失败: %s", e)

        # 兜底
        return DEFAULT_SYSTEM_PROMPT

    def _render_tool_declarations(self) -> str:
        """从 os_capabilities.yaml 渲染结构化工具声明段（#150）。

        每次 Agent 启动读取最新工具列表，渲染为独立段追加，与现有能力声明不冲突。
        """
        try:
            if not CAPABILITIES_YAML.exists():
                logger.warning("os_capabilities.yaml 不存在: %s", CAPABILITIES_YAML)
                return ""
            with open(CAPABILITIES_YAML, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except (OSError, yaml.YAMLError) as e:
            logger.warning("读取 os_capabilities.yaml 失败: %s", e)
            return ""

        caps = data.get("capabilities", [])
        if not caps:
            return ""

        lines = [
            "## 工具声明（自动注入段）",
            "",
            "> 本段由 `os_capabilities.yaml` 在 Agent 启动时自动生成，作为独立段追加，与现有能力声明互不冲突。",
            "> 新增工具只需在 `os_capabilities.yaml` 增加一条记录，Agent 重启后自动注入。",
            "",
            "| 工具名 | 功能描述 | 参数 | 版本 |",
            "| --- | --- | --- | --- |",
        ]
        for cap in caps:
            cid = str(cap.get("id", "")).strip()
            desc = str(cap.get("description", "")).strip() or "-"
            ctype = str(cap.get("type", "")).strip()
            params = cap.get("parameters") or cap.get("constraints") or []
            if isinstance(params, list):
                params_text = "; ".join(str(p) for p in params)
            elif isinstance(params, str):
                params_text = params
            else:
                params_text = ""
            params_text = (params_text or "-").replace("|", "\\|").replace("\n", " ")
            desc = desc.replace("|", "\\|")
            since = str(cap.get("since", "")).strip() or "-"
            lines.append(f"| `{cid}` | {desc} | {params_text} | {since} |")
            if ctype:
                lines.append(f"  - type: `{ctype}`")
        return "\n".join(lines)

    def _inject_tool_declarations(self, text: str) -> str:
        """将工具声明段注入基础 System Prompt（#150）。

        在 <!-- TOOL_DECLARATIONS_START/END --> 标记之间替换生成内容；
        若标记缺失则追加到文件末尾，保证与现有能力声明互不冲突。
        """
        rendered = self._render_tool_declarations()
        if not rendered:
            return text
        start_marker = "<!-- TOOL_DECLARATIONS_START -->"
        end_marker = "<!-- TOOL_DECLARATIONS_END -->"
        if start_marker in text and end_marker in text:
            head, _ = text.split(start_marker, 1)
            _, tail = text.split(end_marker, 1)
            return f"{head}{start_marker}\n{rendered}\n{end_marker}{tail}"
        return f"{text.rstrip()}\n\n---\n\n{start_marker}\n{rendered}\n{end_marker}\n"

    def _load_position_prompt(self, position: str) -> str:
        """加载岗位级 prompt 增强。"""
        if position in self._position_prompts:
            return self._position_prompts[position]

        # 岗位名 → 文件名映射
        position_file_map = {
            "程序员": "programmer.yaml",
            "分析师": "analyst.yaml",
            "作家": "writer.yaml",
            "设计师": "designer.yaml",
            "视频编辑": "video_editor.yaml",
            "翻译员": "translator.yaml",
            "文件管理": "file_manager.yaml",
            "决策审查": "reviewer.yaml",
            "元认知Agent": "metacognition.yaml",
            "编排Agent": "orchestrator.yaml",
        }

        filename = position_file_map.get(position)
        if not filename:
            self._position_prompts[position] = ""
            return ""

        filepath = POSITIONS_DIR / filename
        if not filepath.exists():
            self._position_prompts[position] = ""
            return ""

        try:
            with open(filepath, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            # 尝试提取 review_prompt 或 description
            prompt = (
                data.get("review_prompt")
                or data.get("description")
                or ""
            )
            if isinstance(prompt, str):
                self._position_prompts[position] = prompt.strip()
                return self._position_prompts[position]
        except Exception as e:
            logger.warning("加载岗位 prompt %s 失败: %s", filename, e)

        self._position_prompts[position] = ""
        return ""

    # ---------- 岗位推断 ----------

    def _infer_position(self, task_name: str) -> str:
        """根据任务名推断岗位。"""
        # 从 os_precision_feeds.yaml 提取 keyword→position 映射
        # 或使用 task_orchestrator.py 的 SKILL_TO_POSITION 逻辑
        skill_keywords = {
            "代码": "程序员",
            "开发": "程序员",
            "编程": "程序员",
            "bug": "程序员",
            "修复": "程序员",
            "部署": "程序员",
            "重构": "程序员",
            "创建": "程序员",
            "实现": "程序员",
            "修改": "程序员",
            "写代码": "程序员",
            "分析": "分析师",
            "数据分析": "分析师",
            "调研": "分析师",
            "搜索": "分析师",
            "竞品": "分析师",
            "市场": "分析师",
            "财务": "分析师",
            "预算": "分析师",
            "内容": "作家",
            "写作": "作家",
            "脚本": "作家",
            "文案": "作家",
            "撰写": "作家",
            "创作": "作家",
            "翻译": "翻译员",
            "多语言": "翻译员",
            "图片": "设计师",
            "设计": "设计师",
            "画图": "设计师",
            "图像": "设计师",
            "音频": "作家",
            "音效": "作家",
            "视频": "视频编辑",
            "剪辑": "视频编辑",
            "文件": "文件管理",
            "任务规划": "决策审查",
            "规划": "决策审查",
            "审查": "决策审查",
            "评估": "决策审查",
            "盘点": "分析师",
            "报错": "程序员",
            "失败": "程序员",
            "排查": "程序员",
            "账单": "决策审查",
            "费用": "决策审查",
            "token": "决策审查",
        }

        for keyword, position in skill_keywords.items():
            if keyword in task_name:
                return position
        return "程序员"  # 默认

    # ---------- Feed 配置加载 ----------

    def _load_feeds_config(self) -> list:
        """加载 os_precision_feeds.yaml。"""
        if self._feeds_config is not None:
            return self._feeds_config

        feed_path = CONFIG_DIR / "os_precision_feeds.yaml"
        if not feed_path.exists():
            logger.warning("os_precision_feeds.yaml 不存在")
            self._feeds_config = []
            return []

        try:
            with open(feed_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            self._feeds_config = data.get("feeds", [])
            return self._feeds_config
        except Exception as e:
            logger.warning("加载 os_precision_feeds.yaml 失败: %s", e)
            self._feeds_config = []
            return []

    # ---------- 资产源加载 ----------

    def _load_asset_source(
        self,
        source: str,
        max_chars: int = 2000,
        max_items: Optional[int] = None,
    ) -> str:
        """按 source 名称加载对应资产。

        支持的 source:
          - os_capabilities:     core/config/os_capabilities.yaml
          - system_hypothesis:   data/v8/hypothesis.jsonl
          - world_model:         data/v8/world_model.json
          - dependency_graph:    data/v8/dependency_graph.json
          - os_events:           data/v8/events.jsonl
          - billing_summary:     core/config/v8/audit_rules.yaml（结合 ledger）
          - current_plan_discussion: data/v8/discussion_{session_id}.jsonl
        """
        source_handlers = {
            "os_capabilities": self._load_os_capabilities,
            "system_hypothesis": self._load_system_hypothesis,
            "world_model": self._load_world_model,
            "dependency_graph": self._load_dependency_graph,
            "os_events": self._load_os_events,
            "billing_summary": self._load_billing_summary,
            "current_plan_discussion": self._load_plan_discussion,
            "sag_dependency_chain": lambda max_chars=2000, max_items=None: "",
        }

        handler = source_handlers.get(source)
        if handler is None:
            logger.warning("未知资产源: %s", source)
            return ""

        try:
            text = handler(max_chars=max_chars, max_items=max_items)
            return text
        except Exception as e:
            logger.warning("加载资产源 %s 失败: %s", source, e)
            return ""

    def _load_os_capabilities(self, max_chars: int = 2000, **kwargs) -> str:
        """加载 OS 能力配置。"""
        path = CONFIG_DIR / "os_capabilities.yaml"
        if not path.exists():
            return ""
        try:
            text = path.read_text(encoding="utf-8")
            return text[:max_chars]
        except OSError:
            return ""

    def _load_system_hypothesis(self, max_chars: int = 2000, max_items: int = 5, **kwargs) -> str:
        """加载系统假设。"""
        path = V8_DATA_DIR / "hypothesis.jsonl"
        if not path.exists():
            return ""
        return self._read_jsonl_truncated(path, max_items=max_items or 5, max_chars=max_chars)

    def _load_world_model(self, max_chars: int = 3000, **kwargs) -> str:
        """加载 world model。"""
        path = V8_DATA_DIR / "world_model.json"
        if not path.exists():
            return ""
        try:
            text = path.read_text(encoding="utf-8")
            if len(text) > max_chars:
                # 尝试保留结构，截断内容
                data = json.loads(text)
                return json.dumps(data, ensure_ascii=False, indent=2)[:max_chars]
            return text
        except (OSError, json.JSONDecodeError):
            return ""

    def _load_dependency_graph(self, max_chars: int = 2000, **kwargs) -> str:
        """加载依赖图。"""
        path = V8_DATA_DIR / "dependency_graph.json"
        if not path.exists():
            return ""
        try:
            text = path.read_text(encoding="utf-8")
            return text[:max_chars]
        except OSError:
            return ""

    def _load_os_events(self, max_chars: int = 2000, max_items: int = 20, **kwargs) -> str:
        """加载 OS 事件。"""
        path = V8_DATA_DIR / "events.jsonl"
        if not path.exists():
            return ""
        return self._read_jsonl_truncated(path, max_items=max_items or 20, max_chars=max_chars)

    def _load_billing_summary(self, max_chars: int = 1500, **kwargs) -> str:
        """加载账单摘要。"""
        path = V8_DATA_DIR / "billing_summary.json"
        if not path.exists():
            return ""
        try:
            text = path.read_text(encoding="utf-8")
            return text[:max_chars]
        except OSError:
            return ""

    def _load_plan_discussion(self, max_chars: int = 2000, **kwargs) -> str:
        """加载当前计划讨论。"""
        # 需要 session_id，从当前上下文中无法获取，返回空
        # 实际调用时由上层传入
        return ""

    # ---------- 工具方法 ----------

    def _read_jsonl_truncated(
        self,
        path: Path,
        max_items: int = 5,
        max_chars: int = 2000,
    ) -> str:
        """读取 jsonl 文件，按 max_items 和 max_chars 截断。"""
        lines = []
        try:
            with open(path, encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if i >= max_items:
                        break
                    line = line.strip()
                    if line:
                        lines.append(line)
        except OSError as e:
            logger.warning("读取 %s 失败: %s", path, e)
            return ""

        if not lines:
            return ""

        text = "\n".join(lines)
        if len(text) > max_chars:
            text = text[:max_chars] + "...(截断)"
        return text

    @staticmethod
    def _extract_keywords(text: str) -> list:
        """从文本中提取关键词用于匹配。

        策略（与 consensus_engine.py 一致）：
        - 英文场景：取长度 >= 2 的词
        - 中文场景：取字符 bigram
        """
        words = text.split()
        if len(words) > 1:
            return list({w for w in words if len(w) >= 2})

        chars = text.strip()
        if len(chars) <= 1:
            return []
        return list({chars[i:i + 2] for i in range(len(chars) - 1)})


# ============================================================
# 单例导出
# ============================================================

loop_context_manager = LoopContextManager()
