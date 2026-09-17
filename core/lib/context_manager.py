#!/usr/bin/env python3
"""上下文管理器 - 滑动窗口+摘要+实体缓存"""

import json
from typing import Dict, List, Optional


class ContextManager:
    """上下文管理器：滑动窗口8轮 + 摘要压缩 + 实体缓存"""
    
    MAX_WINDOW = 8           # 保留最近8轮完整对话
    MAX_ENTITIES = 20        # 最多缓存20个实体
    SUMMARY_TRIGGER = 12     # 超过12轮触发摘要
    FATIGUE_THRESHOLD = 20          # 连续 N 步无实质进展触发疲劳警告
    FATIGUE_SUMMARY_REPEAT_THRESHOLD = 0.7  # 摘要重复率阈值
    
    def __init__(self):
        self._window: List[Dict] = []      # 滑动窗口
        self._entities: Dict[str, str] = {}  # 实体缓存 {名字: john, 邮箱: xx@xx, ...}
        self._world_model: dict = {}
        self._summary: dict = {
            "task_goal": "",
            "completed": [],
            "in_progress": "",
            "failed_attempts": [],
            "key_findings": [],
            "file_status": {}
        }  # 结构化早期对话摘要
        self._total_turns = 0
        self._seen_keys: set = set()  # known_patterns 去重集合
        # #83 疲劳度检测状态
        self._fatigue_no_progress_steps = 0
        self._fatigue_summary_snapshot = ""
        self._fatigue_warned_steps = False
        self._fatigue_warned_summary = False
    
    # ========== 滑动窗口 ==========
    
    def add_turn(self, user: str, assistant: str, action: str, extracted: Dict, world_model: dict = None, last_task_pattern: dict = None, intent_model: dict = None):
        """添加一轮对话"""
        self._total_turns += 1
        self._window.append({
            "user": user[:200], "assistant": assistant[:200],
            "action": action, "extracted": extracted,
            "world_model": world_model,
            "last_task_pattern": last_task_pattern,
            "intent_model": intent_model,  # 新增
        })
        if world_model:
            self._world_model = world_model
        if last_task_pattern:
            pattern = last_task_pattern
            # 守卫 1：拦截无效修正（correction 缺少 original 不记录）
            if pattern.get('type') == 'correction' and not pattern.get('original'):
                return
            # 守卫 2：去重（相同 type/original/resolved 只记录一次）
            _key = (pattern.get('type'), str(pattern.get('original')), str(pattern.get('resolved')))
            if _key in self._seen_keys:
                return
            self._seen_keys.add(_key)
            self._last_task_pattern = pattern
        if intent_model:
            self._intent_model = intent_model  # 新增
        # 保持窗口大小
        if len(self._window) > self.MAX_WINDOW:
            removed = self._window.pop(0)
            # 被移除的轮次加入摘要
            self._summary = self._summarize_old(removed, self._summary)
        
        # 触发完整摘要
        if self._total_turns > self.SUMMARY_TRIGGER and self._total_turns % 5 == 0:
            self._compact()
    
    def _summarize_old(self, removed: Dict, current_summary: dict) -> dict:
        """将被移除的轮次按字段分类存储进摘要。代码块和用户指令不压缩。"""
        user_msg = removed.get("user", "")
        assistant_msg = removed.get("assistant", "")
        
        # 资产保护：包含代码块或用户具体指令的消息不压缩
        if "```" in user_msg or "```" in assistant_msg:
            return current_summary
        if any(kw in user_msg for kw in ["写入以下", "替换为", "用 write_file", "完整代码"]):
            return current_summary
        
        action = removed.get("action", "")
        ext = removed.get("extracted", {})
        user_msg = user_msg[:200]

        # 按 action 类型分类存储
        if action in ("task_goal", "create_file", "fix", "rebuild", "rewrite"):
            current_summary["task_goal"] = user_msg[:200]
        if action in ("write_file", "edit_file", "execute_command") and ext.get("success"):
            step = ext.get("desc", action)
            if not self._is_jaccard_dup(step, current_summary["completed"]):
                current_summary["completed"].append(step)
                if len(current_summary["completed"]) > 10:
                    current_summary["completed"] = current_summary["completed"][-10:]
        if action in ("write_file", "execute_command") and not ext.get("success"):
            fail = ext.get("error", action)
            if not self._is_jaccard_dup(fail, current_summary["failed_attempts"]):
                current_summary["failed_attempts"].append(fail)
                if len(current_summary["failed_attempts"]) > 5:
                    current_summary["failed_attempts"] = current_summary["failed_attempts"][-5:]
        elif action == "finding" or ext.get("finding"):
            finding = ext.get("finding", user_msg[:100])
            if not self._is_jaccard_dup(finding, current_summary["key_findings"]):
                current_summary["key_findings"].append(finding)
                if len(current_summary["key_findings"]) > 10:
                    current_summary["key_findings"] = current_summary["key_findings"][-10:]
        elif action == "file_status" or ext.get("file"):
            fname = ext.get("file", "")
            fstat = ext.get("status", "modified")
            current_summary["file_status"][fname] = fstat
        # 保留最新的 world_model
        _wm = removed.get("world_model")
        if _wm:
            current_summary["world_model"] = _wm
        # 更新项目结构快照（压缩时顺手更新）
        import os as _os2
        _proj_root = _os2.path.join("clawsjoy_dev")  # 默认项目根目录
        _struct = {}
        for _dir in ["services", "ui", "models", "utils"]:
            _path = _os2.path.join(_proj_root, _dir)
            if _os2.path.exists(_path):
                _struct[_dir] = sorted([f for f in _os2.listdir(_path) if f.endswith(".py") and f != "__pycache__"])
        if _os2.path.exists(_os2.path.join(_proj_root, "config.py")):
            _struct["config"] = "config.py"
        if _os2.path.exists(_os2.path.join(_proj_root, "app.py")):
            _struct["entry"] = "app.py"
        current_summary["project_structure"] = _struct
        if action and "in_progress" in action:
            current_summary["in_progress"] = user_msg[:200]

        return current_summary
    
    def _compact(self):
        """压缩早期窗口为摘要"""
        if len(self._window) <= 4:
            return
        # 保留最近4轮，更早的压缩
        to_compress = self._window[:-4]
        self._window = self._window[-4:]
        for item in to_compress:
            self._summary = self._summarize_old(item, self._summary)
    
    # ========== 去重辅助 ==========

    def _extract_keywords(self, text: str) -> set:
        """提取文本关键词集合（分词 + 去停用词）"""
        import re as _re
        tokens = _re.findall(r'[a-zA-Z\u4e00-\u9fff]+', text.lower())
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                      'has', 'have', 'had', 'do', 'does', 'did', 'will', 'would',
                      'can', 'could', 'shall', 'should', 'may', 'might', 'must',
                      'to', 'of', 'in', 'on', 'at', 'by', 'for', 'with', 'from',
                      'and', 'or', 'but', 'not', 'no', 'so', 'if', 'as', 'it',
                      'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she',
                      'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your',
                      'his', 'its', 'our', 'their', '\u7684', '\u4e86', '\u662f',
                      '\u5728', '\u548c', '\u6709', '\u4e0d', '\u5c31', '\u6211',
                      '\u4f60', '\u4ed6', '\u5979', '\u5b83', '\u4eec', '\u8fd9',
                      '\u90a3', '\u4e2a', '\u4e0a', '\u4e0b', '\u6765', '\u53bb',
                      '\u5230', '\u8bf4', '\u8981', '\u4f1a', '\u4e5f', '\u90fd',
                      '\u800c', '\u4e0e', '\u53ca', '\u4f46', '\u6216'}
        return {t for t in tokens if len(t) > 1 and t not in stop_words}

    def _keyword_overlap(self, text1: str, text2: str) -> float:
        """计算两段文本的关键词重叠率（Jaccard）"""
        kw1 = self._extract_keywords(text1)
        kw2 = self._extract_keywords(text2)
        if not kw1 or not kw2:
            return 0.0
        intersection = kw1 & kw2
        union = kw1 | kw2
        return len(intersection) / len(union)

    def _is_jaccard_dup(self, text: str, items: List[str], threshold: float = 0.7) -> bool:
        """Jaccard 近似去重：与 items 中任一文本的关键词重叠率 > threshold 视为重复"""
        for existing in items:
            if self._keyword_overlap(text, existing) > threshold:
                return True
        return False

    def compress_and_store(self) -> dict:
        """压缩并持久化当前窗口为摘要，返回完整摘要快照

        去重逻辑：
        1. 错误重试去重：同一 (tool_name, file_path, error_type) 只保留第一次错误 + 最后一次成功
        2. 内容相似去重：相邻消息的关键词重叠率 > 70% 视为重复，只保留第一条
        """
        if not self._window:
            return dict(self._summary)

        # ——— 阶段1：错误重试去重 ———
        seen: dict = {}
        dedup_idx: set = set()

        for i, item in enumerate(self._window):
            ext = item.get("extracted", {})
            tool_name = ext.get("tool_name", item.get("action", ""))
            file_path = ext.get("file_path", "")
            error_msg = ext.get("error", "")
            error_type = error_msg[:40] if error_msg else ""
            success = ext.get("success", False)

            if error_type:
                key = (tool_name, file_path, error_type)
            else:
                key = (tool_name, file_path)

            if key not in seen:
                seen[key] = {"first_error": i if not success else None,
                             "last_success": i if success else None}
            else:
                record = seen[key]
                if not success:
                    dedup_idx.add(i)  # 重复错误，删除
                else:
                    if record["last_success"] is not None:
                        dedup_idx.add(record["last_success"])  # 删除前一次成功
                    record["last_success"] = i

        window1 = [item for idx, item in enumerate(self._window) if idx not in dedup_idx]

        # ——— 阶段2：内容相似去重（相邻消息） ———
        content_dedup: set = set()
        for i in range(1, len(window1)):
            prev = window1[i - 1]
            curr = window1[i]
            prev_text = f"{prev.get('user', '')} {prev.get('assistant', '')}"
            curr_text = f"{curr.get('user', '')} {curr.get('assistant', '')}"
            overlap = self._keyword_overlap(prev_text, curr_text)
            if overlap > 0.70:
                content_dedup.add(i)

        self._window = [item for idx, item in enumerate(window1) if idx not in content_dedup]

        # ——— 阶段2.5：窗口与摘要重叠率检测 ———
        # 高重叠（>0.7）说明窗口内容已被摘要覆盖，跳过压缩避免冗余
        _win_text = " ".join(
            f"{item.get('user', '')} {item.get('assistant', '')}"
            for item in self._window
        )
        _sum_text = " ".join(
            str(v) for v in (
                [self._summary.get("task_goal", "")]
                + self._summary.get("completed", [])
                + [self._summary.get("in_progress", "")]
                + self._summary.get("failed_attempts", [])
                + self._summary.get("key_findings", [])
            ) if v
        )
        summary_overlap = self._keyword_overlap(_win_text, _sum_text)
        if summary_overlap <= 0.7:
            # 原有逻辑：压缩到摘要
            for item in self._window:
                self._summary = self._summarize_old(item, self._summary)
        self._window = self._window[-2:] if self._window else []
        return dict(self._summary)

    def _density(self) -> dict:
        """上下文密度统计：token 总量、去重率、摘要占比"""
        import re as _re
        _win_text = " ".join(
            f"{item.get('user', '')} {item.get('assistant', '')}"
            for item in self._window
        )
        _sum_text = " ".join(
            str(v) for v in (
                [self._summary.get("task_goal", "")]
                + self._summary.get("completed", [])
                + [self._summary.get("in_progress", "")]
                + self._summary.get("failed_attempts", [])
                + self._summary.get("key_findings", [])
            ) if v
        )
        def _tok(t: str) -> int:
            return len(_re.findall(r"[a-zA-Z]+|[一-鿿]", t))
        window_tokens = _tok(_win_text)
        summary_tokens = _tok(_sum_text)
        total_tokens = window_tokens + summary_tokens
        _all = _re.findall(r"[a-zA-Z]+|[一-鿿]", _win_text + " " + _sum_text)
        dedup_rate = (1.0 - len(set(_all)) / len(_all)) if _all else 0.0
        return {
            "token_total": total_tokens,
            "window_tokens": window_tokens,
            "summary_tokens": summary_tokens,
            "dedup_rate": round(dedup_rate, 4),
            "summary_ratio": round(summary_tokens / total_tokens, 4) if total_tokens else 0.0,
        }
    
    # ========== 疲劳度检测（#83） ==========
    
    def _summary_text(self) -> str:
        """从 _summary 提取摘要文本（复用 _density 的文本拼接逻辑）"""
        return " ".join(
            str(v) for v in (
                [self._summary.get("task_goal", "")]
                + self._summary.get("completed", [])
                + [self._summary.get("in_progress", "")]
                + self._summary.get("failed_attempts", [])
                + self._summary.get("key_findings", [])
            ) if v
        )
    
    def check_fatigue(self, progress: Optional[float] = None) -> Optional[str]:
        """疲劳度检查（#83）：每次步进调用一次。
        
        - progress 为 None 时自动判断：当前摘要与上步快照的 Jaccard 关键词重复率
          > FATIGUE_SUMMARY_REPEAT_THRESHOLD 视为"无实质进展"步。
        - 连续 >= FATIGUE_THRESHOLD 步无进展 -> 疲劳警告。
        - 单步摘要重复率 > 阈值 -> 步骤趋同警告。
        - 两个警告条件各自只触发一次，避免重复注入。
        """
        curr_summary = self._summary_text()
        if progress is not None:
            # 显式进展：重置无进展计数
            self._fatigue_no_progress_steps = 0
        elif self._fatigue_summary_snapshot:
            overlap = self._keyword_overlap(self._fatigue_summary_snapshot, curr_summary)
            if overlap > self.FATIGUE_SUMMARY_REPEAT_THRESHOLD:
                self._fatigue_no_progress_steps += 1
            else:
                self._fatigue_no_progress_steps = 0
            # 步骤趋同告警（单条件只触发一次）
            if overlap > self.FATIGUE_SUMMARY_REPEAT_THRESHOLD and not self._fatigue_warned_summary:
                self._fatigue_warned_summary = True
                return (
                    f"[疲劳] 步骤趋同告警：摘要重复率 {overlap:.2f} 超过阈值 "
                    f"{self.FATIGUE_SUMMARY_REPEAT_THRESHOLD}，任务可能陷入循环，建议切换策略。"
                )
        self._fatigue_summary_snapshot = curr_summary
    
        if self._fatigue_no_progress_steps >= self.FATIGUE_THRESHOLD and not self._fatigue_warned_steps:
            self._fatigue_warned_steps = True
            return (
                f"[疲劳] 疲劳度告警：连续 {self._fatigue_no_progress_steps} 步无实质进展"
                f"（阈值 {self.FATIGUE_THRESHOLD}），建议暂停反思或拆分任务。"
            )
        return None
    
    def fatigue_status(self) -> dict:
        """返回当前疲劳度状态"""
        return {
            "no_progress_steps": self._fatigue_no_progress_steps,
            "fatigue_threshold": self.FATIGUE_THRESHOLD,
            "summary_repeat_threshold": self.FATIGUE_SUMMARY_REPEAT_THRESHOLD,
            "warned_steps": self._fatigue_warned_steps,
            "warned_summary": self._fatigue_warned_summary,
            "summary_snapshot_len": len(self._fatigue_summary_snapshot),
        }
    
    # ========== 实体缓存 ==========
    
    def update_project_structure(self, struct: dict):
        """更新项目结构记忆(写工具执行后自动刷新; Agent 注入上下文可见)"""
        self._summary["project_structure"] = struct
        return struct

    def update_entity(self, key: str, value: str):
        """更新实体缓存"""
        if key and value and len(value) < 100:
            self._entities[key] = value
            if len(self._entities) > self.MAX_ENTITIES:
                # 移除最旧的
                self._entities.pop(next(iter(self._entities)))
    
    def get_entity(self, key: str) -> Optional[str]:
        """获取实体"""
        return self._entities.get(key)
    
    def get_all_entities(self) -> Dict[str, str]:
        return dict(self._entities)
    
    # ========== 上下文注入 ==========
    
    def inject(self) -> str:
        """生成注入prompt的上下文片段"""
        parts = []
        
        # 1. 摘要（早期对话）
        if self._summary:
            parts.append(f"【早期对话】{self._summary}")
        
        # 2. 最近对话
        if self._window:
            lines = []
            for item in self._window[-4:]:  # 只取最近4轮
                ext = item.get("extracted", {})
                if ext:
                    lines.append(f"用户: {item['user'][:80]} → {item['action']}({json.dumps(ext, ensure_ascii=False)[:60]})")
                else:
                    lines.append(f"用户: {item['user'][:80]} → {item['action']}")
            parts.append("【最近对话】\n" + "\n".join(lines))
        
        # 3. 实体
        if self._entities:
            entities_str = ", ".join(f"{k}={v}" for k, v in list(self._entities.items())[:10])
            parts.append(f"【已知信息】{entities_str}")
        
        if not self._summary.get("task_goal") and not self._summary.get("completed"):
            return ""

        # 结构化输出，方便 Agent 快速恢复状态
        import json as _json
        structured = {
            **self._summary,
            "recent_turns": [
                {"user": item["user"][:80], "action": item["action"]}
                for item in self._window[-4:]
            ],
            "entities": dict(list(self._entities.items())[:10]),
            "total_turns": self._total_turns,
            "world_model": {k: v for k, v in getattr(self, '_world_model', {}).items() if v.get("status") != "path_mismatch"} if getattr(self, '_world_model', None) else None,
            "world_model_updated": getattr(self, '_world_model', {}).get("last_updated", "未知") if getattr(self, '_world_model', None) else None,
            "last_task_pattern": getattr(self, '_last_task_pattern', None),
            "intent_model": getattr(self, '_intent_model', None),  # 新增
            "_density": self._density(),
        }
        return _json.dumps(structured, ensure_ascii=False)
    def clear(self):
        self._window.clear()
        self._entities.clear()
        self._summary = {
            "task_goal": "",
            "completed": [],
            "in_progress": "",
            "failed_attempts": [],
            "key_findings": [],
            "file_status": {}
        }
        self._total_turns = 0

    
    def resolve_reference(self, text: str) -> str:
        """指代消解：用实体缓存替换指代词"""
        if any(w in text for w in ["那个", "这个", "刚才", "它"]):
            # 从最近的实体中找
            for key, value in reversed(list(self._entities.items())):
                if len(value) > 2 and key not in ["名字", "姓名"]:
                    text = text.replace("那个", value).replace("这个", value)
                    break
        return text
    
    def clear(self):
        self._window.clear()
        self._entities.clear()
        self._summary = {
            "task_goal": "",
            "completed": [],
            "in_progress": "",
            "failed_attempts": [],
            "key_findings": [],
            "file_status": {}
        }
        self._total_turns = 0


# 全局实例（按用户）
_managers: Dict[str, ContextManager] = {}

def get_context(user_id: str = "default") -> ContextManager:
    if user_id not in _managers:
        _managers[user_id] = ContextManager()
    return _managers[user_id]
