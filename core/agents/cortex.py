#!/usr/bin/env python3
"""
AgentCortex v4.0 - ClawsJoy 智能皮层
架构：意图识别 → 上下文检索 → Agent执行 → 回复生成
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.lib.growth_engine import get_growth
from core.lib.llm_client import llm_client
from core.lib.memory_bank import get_bank
from core.lib.vector_bank import get_vector_bank

_INTENT_CACHE = {}
# fastText 全局模型（只加载一次）
_ft_model = None
# 批178 · A1 落地（批177 §2.3 的方案）：**失败只尝试一次**。
# 此前代码读 'models/intent_classifier.bin'，而真文件在 'data/intent_classifier.bin'（批177 取证）⇒
# 每次请求都重试一次**必然失败**的加载，且每次都走一遍 stderr 重定向/还原（批176 D2 事故的触发路径）；
# 实测 0.678 ms/次 × 今日 203 次请求。现在：首次失败即置位，本进程内不再重试；
# 原因打一条 **stdout + flush** 日志（批176 留痕纪律：不依赖 stderr，它会被人换成 /dev/null）。
# 批179 · A1 行为面收口：失败事实**进 capability ledger**（不再只是打印）——
# 能力存活率可用 capability_ledger.liveness_report(FT_MODEL_SESSION, capabilities=("intent_classifier",)) 查。
# 为什么用 result=SKIPPED（而不是 FAIL/PASS）：# 批180 起 liveness_report 的算术是「**只把 PASS 算作已执行**」——
# FAIL 会被算进 failed（rate 仍 0），但语义上它表示「跑了但没过」，而这里是「**根本没跑起来**」；
# 「本该跑却没跑」的准确取值就是 SKIPPED（这张表存在的理由）。
# 为什么 session 用固定伪会话：_get_ft_model 是**进程级**加载器、没有 session 上下文，
# 且失败事实本身就是进程级事实（只发一次）；固定伪会话让 E1/E2 的检索是确定性的。
FT_MODEL_SESSION = "__capability_global__"
_ft_model_load_failed = False


def _record_ft_model_unavailable(exc):
    """把「意图分类器不可用」写进 capability ledger（失败不阻断主流程）。"""
    try:
        from core.gateway import capability_ledger as _cl

        return _cl.record(
            "intent_classifier",
            FT_MODEL_SESSION,
            "SKIPPED",
            expected=True,
            detail="意图分类器不可用（%s: %s）；本进程内不再重试；调用方降级到关键词规则" % (type(exc).__name__, exc),
        )
    except Exception as _e_rec:
        print("[FT_MODEL] ledger 上报失败(不阻断): %s" % _e_rec, flush=True)
        return None


def _get_ft_model():
    global _ft_model, _ft_model_load_failed
    if _ft_model is None and not _ft_model_load_failed:
        try:
            import os
            import sys

            import fasttext

            _stderr = sys.stderr
            _devnull = open(os.devnull, "w", encoding="utf-8")
            sys.stderr = _devnull
            # 批176 · D2 修复：重定向必须**成对还原**。此前还原语句在 try 体内，
            # 而 fasttext.load_model('models/intent_classifier.bin') 会抛异常（该模型文件不存在）
            # ⇒ 还原语句被跳过 ⇒ **全局 sys.stderr 永久变 /dev/null**
            # ⇒ [BRIDGE_ERROR]/[SSE_ERROR] 的 traceback 全被丢弃
            # （批101–175 五批「后端日志干干净净、[SSE_ERROR]=0」的真因；批176 L2 实证）。
            # finally 保证正常/异常都还原；同一 finally 里关掉 devnull 句柄（原先每次请求漏一个 fd）。
            try:
                _ft_model = fasttext.load_model("models/intent_classifier.bin")
            finally:
                sys.stderr = _stderr
                try:
                    _devnull.close()
                except Exception:
                    pass
        except Exception as _ft_e:
            # 批178 · A1：置位 + 一次性告警（stdout，含失败原因）——不再每个请求重复跑这条路径。
            _ft_model_load_failed = True
            print("[FT_MODEL] 意图分类器不可用（%s: %s），本进程内不再重试（调用方降级到关键词规则）" % (type(_ft_e).__name__, _ft_e), flush=True)
            # 批179：同一处、同样只发一次 —— 失败事实进 ledger（可被 liveness_report 检索）。
            _record_ft_model_unavailable(_ft_e)
    return _ft_model


from core.lib.context_manager import get_context

logger = logging.getLogger(__name__)

MODEL_MAIN = "qwen2.5:7b-instruct-q4_0-gpu"


@dataclass
class CapabilityProfile:
    action: str
    agent: str
    success_count: int = 0
    total_count: int = 0
    avg_confidence: float = 0.5
    avg_latency_ms: float = 0
    last_used: str = ""

    @property
    def success_rate(self) -> float:
        return self.success_count / max(self.total_count, 1)

    def update(self, success: bool, confidence: float, latency_ms: float):
        self.total_count += 1
        if success:
            self.success_count += 1
        n = self.total_count
        self.avg_confidence = (self.avg_confidence * (n - 1) + confidence) / n
        self.avg_latency_ms = (self.avg_latency_ms * (n - 1) + latency_ms) / n
        self.last_used = datetime.now().isoformat()


@dataclass
class RetrievalResult:
    field: str
    content: str
    source: str
    score: float = 0.0


class SystemRetriever:
    def __init__(self):
        self.retrieval_log: List[Dict] = []
        self._bank_cache: Dict[str, Any] = {}

    def _get_bank(self, uid):
        if uid not in self._bank_cache:
            self._bank_cache[uid] = get_bank(uid)
        return self._bank_cache[uid]

    def _get_vbank(self, uid):
        k = f"v_{uid}"
        if k not in self._bank_cache:
            self._bank_cache[k] = get_vector_bank(uid)
        return self._bank_cache[k]

    def auto_retrieve(self, missing, uid, uinput):
        results = {}
        vbank = self._get_vbank(uid)
        bank = self._get_bank(uid)
        for field in missing:
            r = []
            v = vbank.inject(f"{field} {uinput}")
            if v and len(v.strip()) > 10:
                r.append(RetrievalResult(field, v, "VectorBank", 0.8))
            m = bank.recall(field, limit=3)
            if m and len(m.strip()) > 10 and "未找到" not in m:
                r.append(RetrievalResult(field, m, "MemoryBank", 0.6))
            if r:
                results[field] = r
        return results


class CortexValidator:
    VALID_ACTIONS = [
        "greeting",
        "identity",
        "memory",
        "recall",
        "code",
        "write",
        "analyze",
        "translate",
        "calculate",
        "task",
        "chat",
    ]
    REQUIRED_FIELDS = {
        "identity": ["名字"],
        "memory": ["key", "value"],
        "recall": ["query"],
        "code": ["功能描述"],
        "analyze": ["数据"],
        "translate": ["原文"],
        "calculate": ["表达式"],
        "task": ["任务名"],
    }

    def __init__(self):
        self.retriever = SystemRetriever()

    def validate(self, reasoning, uinput, uid):
        extracted = reasoning.get("extracted") or {}
        action = reasoning.get("action", "")
        if action not in self.VALID_ACTIONS:
            return {"status": "invalid"}
        if action in ("greeting", "chat"):
            return {"status": "success"}
        if extracted.get("需要澄清"):
            return {"status": "success"}  # 需要澄清时跳过检查
        needs = self.REQUIRED_FIELDS.get(action, [])
        missing = [f for f in needs if f not in extracted or not extracted[f]]
        return {"status": "missing", "missing": missing} if missing else {"status": "success"}


class AgentCortex:
    """v4.0 极简架构：意图识别→上下文检索→Agent执行→回复生成"""

    def __init__(self):
        self._stats = {"total": 0, "success": 0}
        self._agent_cache: Dict[str, Any] = {}
        self._last_action = "chat"
        self.validator = CortexValidator()
        self._session_context: Dict[str, str] = {}  # user_id → mode
        self._agent_capabilities = self._load_agent_capabilities()
        # 初始化向量语义索引
        self._index_agent_capabilities()
        logger.info("🧠 AgentCortex v4.0")
        self._fatigue = {"consecutive_errors": 0, "durations": [], "recent_inputs": [], "baseline": None}

    def _index_agent_capabilities(self):
        """把 Agent 能力描述索引到向量库（异步，不阻塞启动）"""
        import threading as _th_idx

        def _do_index():
            try:
                from core.lib.vector_bank import get_vector_bank

                vbank = get_vector_bank("system")
                for name, info in self._agent_capabilities.items():
                    if info.get("type") == "agent":
                        desc = info.get("description", "")
                        actions = " ".join(info.get("actions", []))
                        vbank.remember("agent_capability", f"{name} {actions} {desc}", name)
            except Exception as e:
                print(f"[向量索引] 失败: {e}")

        _th_idx.Thread(target=_do_index, daemon=True).start()

    def process(self, user_input: str, user_id: str = "default", context: Dict = None) -> Dict:
        print(f"[DEBUG] process START: user_input={user_input[:50]}, user_id={user_id}")
        start_time = time.time()
        self._stats["total"] += 1
        self._fatigue["recent_inputs"].append(user_input)
        if len(self._fatigue["recent_inputs"]) > 5:
            self._fatigue["recent_inputs"].pop(0)
        if not user_input or len(user_input.strip()) == 0:
            return {"success": True, "response": "请输入您的问题", "method": "empty"}

        # 第0层：加载会话模式配置 + 检测当前模式
        session_modes = self._load_session_modes()
        current_mode = self._session_context.get(user_id, "")

        # 退出指令：从配置读取退出关键词
        if current_mode and current_mode in session_modes:
            exit_keywords = session_modes[current_mode].get("exit_keywords", ["退出", "结束"])
        else:
            exit_keywords = ["退出", "结束", "停止", "关闭"]
        if current_mode and any(kw in user_input for kw in exit_keywords):
            old_mode = current_mode
            self._session_context.pop(user_id, None)
            return {
                "success": True,
                "response": f"👋 已退出{old_mode}模式",
                "method": "session_exit",
                "intent": "chat",
                "agents_used": ["chat_agent"],
            }

        # 第1层：意图识别
        action, confidence = self._infer_action(user_input)
        extracted = self._extract(user_input, action)

        # 模式切换检测（使用已加载的 session_modes）
        for mode_name, mode_config in session_modes.items():
            for kw in mode_config.get("keywords", []):
                if kw in user_input:
                    self._session_context[user_id] = mode_name
                    # 查找该模式对应的 agent action
                    agent_name = mode_config.get("agent", "")
                    agent_actions = self._agent_capabilities.get(agent_name, {}).get("actions", [])
                    if agent_actions:
                        action = agent_actions[0]  # 用第一个注册的 action
                    break

        # 会话上下文覆盖：如果用户在某个模式中
        if current_mode and current_mode in session_modes:
            extracted["_mode"] = current_mode
            agent_name = session_modes[current_mode].get("agent", "")
            agent_actions = self._agent_capabilities.get(agent_name, {}).get("actions", [])
            if agent_actions:
                action = agent_actions[0]
        self._last_action = action
        print(f"[DEBUG] final action={action}, extracted={extracted}")

        # 第1.5层：改动点：根据action决定是否检索上下文 =====
        # WRITE类action：跳过上下文检索，不补全extracted
        WRITE_ACTIONS = {"identity", "memory", "forget", "clear"}
        READ_ACTIONS = {"recall", "question"}

        if action in WRITE_ACTIONS:
            # 写操作：不检索历史，不补全
            context_data = {"补全": {}}

        elif action in READ_ACTIONS:
            context_data = self._retrieve_context(action, extracted, user_input, user_id)
            # 额外：用 MemoryBank 做语义预检索
            query = extracted.get("query", "") or extracted.get("key", "")
            if query:
                bank = get_bank(user_id, "memory_agent_v4")
                pre_fetched = bank.semantic_search(query)
                if pre_fetched:
                    context_data["补全"]["pre_fetched"] = pre_fetched

        else:
            # chat/greeting 等：轻量上下文
            # 需要澄清时不补全，避免补全数据干扰澄清判断
            if not extracted.get("需要澄清"):
                context_data = self._retrieve_context(action, extracted, user_input, user_id)
            else:
                context_data = {"补全": {}}
            if context_data.get("补全"):
                for k, v in context_data["补全"].items():
                    if not extracted.get(k):
                        extracted[k] = v
        # ===== 改动结束 =====

        # 验收
        validation = self.validator.validate({"action": action, "extracted": extracted}, user_input, user_id)
        if validation.get("status") == "missing":
            retrieved = self.validator.retriever.auto_retrieve(validation.get("missing", []), user_id, user_input)
            if retrieved:
                for field, results in retrieved.items():
                    if results and not extracted.get(field):
                        extracted[field] = results[0].content
            else:
                return {
                    "success": True,
                    "response": f"我还需要知道：{'、'.join(validation['missing'])}。",
                    "method": "ask_user",
                    "intent": action,
                    "agents_used": [],
                }

        # V5 决策编排已取消，统一走 V8 @ 提及路由

        # 第2层：Agent执行
        agents = self._infer_agents(action, extracted)
        agent_result = None
        print(f"[DEBUG] agents={agents}, action={action}")
        if agents and action not in ("greeting", "chat"):
            print(f"[DEBUG] 需要澄清检查: extracted={extracted}")
            if extracted and extracted.get("需要澄清"):
                agent_result = {"success": True, "response": "需要澄清"}
            else:
                agent_result = self._execute_single(agents[0], user_input, user_id, context_data, extracted)
        # 更新疲劳度：连续错误计数
        if agent_result is not None and not agent_result.get("success", True):
            self._fatigue["consecutive_errors"] += 1
        else:
            self._fatigue["consecutive_errors"] = 0
        self._sync_fatigue_to_living_agent()

        # 第3层：回复生成
        print(f"[DEBUG] process->generate_reply: agent_result={agent_result}, extracted={extracted}")
        reply = self._generate_reply(user_input, action, extracted, context_data, user_id, agent_result)

        latency_ms = (time.time() - start_time) * 1000
        self._learn(user_input, action, extracted, reply, latency_ms, user_id, context_data)
        self._stats["success"] += 1

        # 主动服务：生成建议
        proactive = ""
        try:
            from core.agents.wisdom.wisdom_factory import wisdom_factory

            pa = wisdom_factory.get_agent("proactive_agent", user_id)
            summary = reply[:80]
            if agent_result and agent_result.get("videos"):
                summary = f"返回了{len(agent_result['videos'])}个搜索结果"
            ctx = {"user_id": user_id, "action": action, "result_summary": summary}
            skip = action in ("vision",) or (agent_result and agent_result.get("videos"))
            if not skip:
                proactive = pa.process(user_input, ctx).get("response", "")[:300]
                print(f"[DEBUG] proactive: action={action}, summary={summary}, result={proactive[:100]}")
        except Exception as e:
            print(f"[DEBUG] proactive error: {e}")

        # 疲劳度管理：计算步骤耗时
        step_duration = time.time() - start_time
        self._fatigue["durations"].append(step_duration)
        if len(self._fatigue["durations"]) > 10:
            self._fatigue["durations"].pop(0)
        self._sync_fatigue_to_living_agent()
        if self._should_review():
            review = self._execute_global_review(user_input)
            if review:
                reply = review + "\n" + reply
        return {
            "success": True,
            "response": reply,
            "output_content": reply,
            "intent": action,
            "confidence": confidence,
            "method": "v4",
            "agents_used": agents,
            "extracted": extracted,
            "proactive": proactive,
            "videos": agent_result.get("videos", []) if agent_result else [],
            "tokens": self._stats.get("total_tokens", 0),
            "model": llm_client.config.default_model,
        }

    # ========== 意图识别 ==========

    def _infer_action(self, user_input: str) -> Tuple[str, float]:
        """意图识别 - 规则优先 → fastText → 正则 → chat"""
        # 意图识别缓存
        cache_key = f"{hash(user_input)}"
        cached = _INTENT_CACHE.get(cache_key)
        if cached and time.time() - cached["ts"] < 300:
            return cached["action"], cached["confidence"]
        text = user_input.strip().lower()
        import sys

        if text.endswith(".mp4") or "分析视频" in text:
            return "vision", 0.90
        # 第0层：规则优先（最高优先级）
        # 0.0 图片/图表分析
        if any(kw in text for kw in ["分析图片", "图片分析", "分析图像", "识别图片", "分析图表", "图表分析", "分析截图"]):
            return "vision", 0.90
        if any(kw in text for kw in ["导出报告", "导出分析报告"]):
            return "vision", 0.90
        # 0.1 YouTube URL
        if "youtube.com" in text or "youtu.be" in text:
            return "youtube", 0.95
        # 0.1.1 YouTube 搜索/分析（无URL）—— 必须在 recall 之前
        if any(w in text for w in ["搜索", "搜", "找", "查"]) and any(w in text for w in ["youtube", "yt", "油管"]):
            return "youtube", 0.90
        if any(w in text for w in ["分析频道", "频道分析"]):
            return "youtube", 0.90
        # 0.2 特殊查询
        if re.search(r"我叫(?:什么|来着)", text):
            return "recall", 0.90
        if re.search(r"上次.*密码|密码.*多少|那个密码", text):
            return "recall", 0.90

        # 第1层：fastText 分类
        try:
            model = _get_ft_model()
            if model:
                label, conf = model.predict(user_input.strip())
                action = label[0].replace("__label__", "")
                if conf[0] > 0.8:
                    _INTENT_CACHE[cache_key] = {"action": action, "confidence": conf[0], "ts": time.time()}
                    return action, conf[0]
        except Exception:
            pass

        # 第1.5层：向量语义匹配
        try:
            from core.lib.vector_bank import get_vector_bank

            vbank = get_vector_bank("system")
            results = vbank.recall(text, bucket="agent_capability", limit=1)
            if results:
                agent_name = results[0].get("content", "")
                for action, info in self._agent_capabilities.items():
                    if info.get("type") == "agent" and info.get("name") == agent_name:
                        if info.get("actions"):
                            _INTENT_CACHE[cache_key] = {"action": action, "confidence": conf[0], "ts": time.time()}
                            return info["actions"][0], 0.75
        except Exception:
            pass

        # 第2层：正则匹配
        # greeting
        greet = ["^你好", "^嗨", "^hi", "^hello", "^你是谁", "^你叫什么", "^你是哪位", "^介绍一下"]
        for p in greet:
            if re.search(p, text):
                return "greeting", 0.95

        # identity
        if re.search(r"^我是[^谁]", text) or re.search(r"^我叫[^什来]", text) or re.search(r"^叫我", text):
            return "identity", 0.90
        if "名字叫" in text and not any(w in text for w in ["什么", "来着", "呢"]):
            return "identity", 0.88

        # memory
        if any(w in text for w in ["记住", "保存", "存储", "记一下", "记下", "帮我记", "帮我存", "存一下"]):
            if any(w in text for w in ["是多少", "是什么", "什么", "多少"]):
                return "recall", 0.80
            return "memory", 0.90

        # 精准查询：我的密码/名字等
        if re.search(r"(我的|我.*的)\s*(密码|名字|姓名|昵称|账号|语言|偏好|爱好|兴趣|年龄|地址|电话|职业)", text):
            return "recall", 0.85

        # recall
        recall_words = ["还记得", "记不记得", "记得吗", "你忘了吗", "回忆", "上次说过", "之前说过", "之前聊过"]
        if any(w in text for w in recall_words):
            return "recall", 0.80

        # 能力规则表
        from core.lib.ability_rules import ABILITY_REGEX, PRIORITY

        for action in PRIORITY:
            if action in ("greeting", "identity", "memory", "recall"):
                continue
            rules = ABILITY_REGEX.get(action, {})
            for pattern in rules.get("patterns", []):
                m = re.search(pattern, text)
                if m:
                    _conf = min(0.85 + (len(m.group()) / max(len(text), 1)) * 0.1, 0.98)
                    _INTENT_CACHE[cache_key] = {"action": action, "confidence": _conf, "ts": time.time()}
                    return action, _conf
                    # v8 岗位专线：查花名册
        try:
            from core.lib.v8.roster_engine import roster_engine

            members = roster_engine.list_active("default")
            positions = {m["position"]: m for m in members}
            if "分析师" in positions and any(kw in text for kw in ["分析", "报告", "数据", "竞品", "市场", "趋势"]):
                return "analyze", 0.85
            if "设计师" in positions and any(kw in text for kw in ["设计", "logo", "海报", "图片", "画", "图"]):
                return "vision", 0.85
            if "程序员" in positions and any(kw in text for kw in ["写代码", "写程序", "写函数", "修复", "bug", "编程", "开发"]):
                return "code", 0.85
            if "作家" in positions and any(kw in text for kw in ["撰写", "写作", "创作", "写文章", "写脚本", "写文案", "写方案"]):
                return "write", 0.85
        except Exception:
            pass
        _INTENT_CACHE[cache_key] = {"action": "chat", "confidence": 0.50, "ts": time.time()}
        return "chat", 0.50

    def _extract(self, user_input: str, action: str) -> Dict:
        text = user_input.strip()
        extracted = {}

        if action == "translate":
            # 提取原文（和目标语言），支持 "把X翻译成Y" / "将X翻译成Y" / "翻译X" 等
            m = re.search(r"(?:把|将|请把|请将)?(.+?)(?:翻译成|翻译为|译成|翻成)(.+)", text)
            if m:
                extracted["原文"] = m.group(1).strip()
                extracted["目标语言"] = m.group(2).strip()
            else:
                for p in ["翻译一下", "翻译", "译"]:
                    if text.startswith(p):
                        extracted["原文"] = text[len(p) :].strip()
                        break
            if not extracted.get("原文"):
                cleaned = re.sub(r"翻译|把|将|成|为|中文|英文", "", text).strip()
                if cleaned:
                    extracted["原文"] = cleaned
            return extracted

        if action == "calculate":
            expr = re.sub(r"[^0-9+\-*/().]", "", text)
            if expr:
                extracted["表达式"] = expr
            return extracted

        if action == "memory":
            content = text
            # 智能识别 "记住我叫xxx"
            m = re.search(r"(?:记住|记一下|记下|帮我记)\s*我(?:叫|是)\s*(.+)", text)
            if m:
                extracted["key"] = "名字"
                extracted["value"] = m.group(1).strip()
                return extracted
            # 智能识别 "记住我的密码是xxx"
            m = re.search(r"(?:记住|记一下|记下|帮我记)\s*我的\s*(密码|名字|账号)\s*(?:是|为|：|:)\s*(.+)", text)
            if m:
                extracted["key"] = m.group(1).strip()
                extracted["value"] = m.group(2).strip()
                return extracted
            prefixes = ["帮我存一下", "帮我存", "帮我记一下", "帮我记", "记一下", "记下", "记住", "保存", "存储"]
            for p in sorted(prefixes, key=len, reverse=True):
                if text.startswith(p):
                    content = text[len(p) :].strip()
                    break
            content = re.sub(r"^(一下|一个)\s*", "", content)
            # 数字分离前循环清前缀
            import re as _re

            clean = content.strip()
            for _ in range(3):
                new_clean = _re.sub(r"^(你|我|我的|帮我|帮我记|记一下|记|存|一下|一个|下|的)\s*", "", clean)
                if new_clean == clean:
                    break
                clean = new_clean
            # 分隔符
            for sep in ["是", "=", "为", "：", ":"]:
                if sep in clean:
                    k, v = clean.split(sep, 1)
                    extracted["key"] = k.strip()
                    extracted["value"] = v.strip()
                    return extracted
            # 数字分离
            m = _re.search(r"^(.+?)(\d{2,})$", clean)
            if m:
                extracted["key"] = m.group(1).strip()
                extracted["value"] = m.group(2).strip()
                return extracted
            if _re.match(r"^\d+$", clean):
                extracted["value"] = clean
                return extracted
            if clean:
                extracted["key"] = clean
            return extracted

        if action == "identity":
            if "名字叫" in text:
                clean = text.replace("我的", "").replace("名字叫", "").strip()
                if clean:
                    extracted["名字"] = clean
                    return extracted
            if text.startswith("我叫"):
                extracted["名字"] = text[len("我叫") :].strip()
            elif text.startswith("我是"):
                extracted["名字"] = text[len("我是") :].strip()
            return extracted

        if action == "recall":
            query = text
            for p in ["回忆", "查询", "查一下", "找一下", "搜索"]:
                if text.startswith(p):
                    query = text[len(p) :].strip()
                    break
            for kw in ["什么", "哪些", "哪里", "怎么", "如何", "谁", "我的", "来着", "呀", "呢", "吗"]:
                query = query.replace(kw, "")
            if "我叫" in text and ("什么" in text or "来着" in text):
                query = "名字"
            query = re.sub(r"[？?！!。，,、\s]+", "", query)
            extracted["query"] = query.strip() or "信息"
            return extracted

        if action == "code":
            for p in ["写", "编写"]:
                if p in text:
                    extracted["功能描述"] = text[text.index(p) + len(p) :].strip()
                    break
            if not extracted.get("功能描述"):
                extracted["功能描述"] = text.strip()
            if len(extracted.get("功能描述", "")) <= 3:
                extracted["需要澄清"] = True
            return extracted

        return extracted

    # ========== 上下文检索 ==========

    def _retrieve_context(self, action, extracted, user_input, user_id):
        context = {"补全": {}, "_meta": {}}

        needs_key = action == "memory" and not extracted.get("key")
        needs_value = action == "memory" and extracted.get("key") and not extracted.get("value")
        needs_query = action == "recall" and not extracted.get("query")
        needs_name = action == "identity" and not extracted.get("名字")

        # 主数据源：SAG 查询 user_memory
        try:
            import psycopg2

            from core.lib.code_entity_extractor import extractor

            conn = psycopg2.connect(extractor.db_url)
            cur = None
            try:
                cur = conn.cursor()
                if needs_name:
                    cur.execute(
                        "SELECT signature FROM code_entities WHERE entity_type='user_profile' AND entity_name=%s LIMIT 1",
                        (f"profile:{user_id}",),
                    )
                    row = cur.fetchone()
                    if row:
                        sig = json.loads(row[0])
                        if sig.get("名字"):
                            context["补全"]["名字"] = sig["名字"]
                if needs_key:
                    cur.execute(
                        "SELECT signature FROM code_entities WHERE entity_type='user_memory' AND entity_name ILIKE %s LIMIT 1",
                        (f"%{user_id}%",),
                    )
                    row = cur.fetchone()
                    if row:
                        sig = json.loads(row[0])
                        if sig.get("key"):
                            context["补全"]["key"] = sig["key"]
                if needs_value and extracted.get("key"):
                    cur.execute(
                        "SELECT signature FROM code_entities WHERE entity_type='user_memory' AND entity_name=%s LIMIT 1",
                        (f"memory:{user_id}:{extracted['key']}",),
                    )
                    row = cur.fetchone()
                    if row:
                        sig = json.loads(row[0])
                        if sig.get("value"):
                            context["补全"]["value"] = sig["value"]
                if any(context["补全"].values()):
                    context["_meta"] = {"source": "sag", "confidence": 0.9, "freshness": "fresh"}
                    return context
            finally:
                if cur:
                    cur.close()
                conn.close()
        except Exception:
            pass

        # 兜底：MemoryBank + VectorBank
        bank = get_bank(user_id, "memory_agent_v4")
        history = []
        raw = bank.recall("history", limit=10)
        if raw and "未找到" not in raw:
            try:
                for line in raw.split("\n"):
                    if line.strip():
                        try:
                            history.append(json.loads(line.strip()))
                        except Exception:
                            pass
            except Exception:
                pass

        if needs_key:
            for item in reversed(history[-5:]):
                if item.get("action") in ["memory", "identity"]:
                    ext = item.get("extracted", {})
                    if ext.get("key"):
                        context["补全"]["key"] = ext["key"]
                        break
                    if ext.get("名字"):
                        context["补全"]["key"] = ext["名字"]
                        break

        if needs_value and extracted.get("key"):
            r = bank.recall(extracted["key"], limit=1)
            if r and "未找到" not in r and len(r) < 50 and "{" not in r:
                context["补全"]["value"] = r

        if needs_query:
            for item in reversed(history[-3:]):
                if item.get("action") in ["memory", "identity"]:
                    ext = item.get("extracted", {})
                    if ext.get("key"):
                        context["补全"]["query"] = ext["key"]
                        break

        if needs_name:
            r = bank.recall("名字", limit=1)
            if r and "未找到" not in r and "{" not in r:
                context["补全"]["名字"] = r

        if action == "greeting":
            r = bank.recall("名字", limit=1)
            if r and "未找到" not in r and len(r) < 30 and "{" not in r:
                context["user_name"] = r

        context["_meta"] = {"source": "memory_bank", "confidence": 0.6, "freshness": "cached"}
        # SAG 补充查询：system_hypothesis + plan
        try:
            import psycopg2

            from core.lib.code_entity_extractor import extractor

            conn2 = psycopg2.connect(extractor.db_url)
            cur2 = conn2.cursor()
            # 查 system_hypothesis（最近3条）
            cur2.execute(
                "SELECT entity_name, signature, created_at FROM code_entities "
                "WHERE entity_type='system_hypothesis' ORDER BY created_at DESC LIMIT 3"
            )
            rows = cur2.fetchall()
            if rows:
                context["system_hypotheses"] = [{"name": r[0], "content": r[1], "created_at": str(r[2])} for r in rows]
            # 查 plan_discussion（按 action 模糊匹配，最近1条）
            cur2.execute(
                "SELECT entity_name, signature, created_at FROM code_entities "
                "WHERE entity_type='plan_discussion' "
                "AND entity_name ILIKE %s ORDER BY created_at DESC LIMIT 1",
                (f"%{action}%",),
            )
            row = cur2.fetchone()
            if row:
                context["plan"] = {"name": row[0], "content": row[1], "created_at": str(row[2])}
            cur2.close()
            conn2.close()
        except Exception:
            pass

        return context

    # ========== Agent路由 ==========

    def _infer_agents(self, action, extracted):
        """SAG 动态查询：意图标签 → 能力声明 → Agent 路由"""
        try:
            import psycopg2

            from core.lib.code_entity_extractor import extractor

            conn = psycopg2.connect(extractor.db_url)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT entity_name, signature, related_entities
                FROM code_entities
                WHERE entity_type = 'capability'
                AND (entity_name ILIKE %s OR %s = ANY(related_entities))
                LIMIT 5
            """,
                (f"%{action}%", action),
            )
            caps = cur.fetchall()
            cur.close()
            conn.close()
            if caps:
                agents = []
                for cap in caps:
                    # 自动注册 capability 实体
                    try:
                        extractor.upsert_entity(
                            {
                                "entity_type": "capability",
                                "entity_name": cap[0],
                                "signature": cap[1] or "",
                                "related_entities": list(cap[2]) if cap[2] else [action],
                                "file_path": "",
                            }
                        )
                    except Exception:
                        pass
                    for rel in cap[2]:
                        if rel.endswith("_agent") or rel.endswith("_skill"):
                            agents.append(rel)
                if agents:
                    return agents[:1]
        except Exception:
            pass
        # SAG 不可用时降级：静态映射
        fallback_map = {
            "calculate": "calculator_agent",
            "translate": "translate_agent",
            "code": "code_agent",
            "greeting": "chat_agent",
            "chat": "chat_agent",
            "analyze": "analysis_agent",
            "write": "writer_agent",
            "recall": "memory_agent",
            "memory": "memory_agent",
            "identity": "memory_agent",
            "vision": "vision_agent",
        }
        return [fallback_map.get(action, "chat_agent")]

    def _load_agent_capabilities(self) -> Dict:
        """从配置加载 Agent + Skill 能力声明"""
        caps = {}
        import yaml

        cap_dir = Path("config/agents/capabilities")
        if cap_dir.exists():
            for f in cap_dir.glob("*.yaml"):
                try:
                    data = yaml.safe_load(f.read_text(encoding="utf-8"))
                    agent = data.get("agent", data)
                    name = agent.get("name", f.stem)
                    actions = agent.get("actions", [])
                    for cap in agent.get("capabilities", []):
                        if isinstance(cap, dict):
                            actions.append(cap.get("name", ""))
                        elif isinstance(cap, str):
                            actions.append(cap)
                    if actions:
                        caps[name] = {"type": "agent", "actions": actions}
                except Exception:
                    pass
        skill_cap_dir = Path("config/capabilities/skills")
        if skill_cap_dir.exists():
            for f in skill_cap_dir.glob("*.yaml"):
                try:
                    data = yaml.safe_load(f.read_text(encoding="utf-8"))
                    name = data.get("name", f.stem)
                    actions = data.get("actions", [])
                    if actions:
                        caps[name] = {"type": "skill", "actions": actions}
                except Exception:
                    pass
        return caps

    def _load_session_modes(self) -> Dict:
        """加载会话模式配置"""
        import yaml

        config_path = Path("config/session_modes.yaml")
        if config_path.exists():
            data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            return data.get("modes", {})
        return {}

    # ========== Agent执行 ==========

    def _execute_single(
        self, agent_name: str, user_input: str, user_id: str, context_data: Dict = None, extracted: Dict = None
    ) -> Dict:
        # V8 花名册覆盖：查员工是否有 API Key，有则走适配器
        try:
            from core.lib.v8.adapters.factory import get_adapter
            from core.lib.v8.roster_engine import roster_engine

            for m in roster_engine.list_active("default"):
                mapping = m.get("agent_mapping", "")
                if mapping and mapping in agent_name and m.get("api_key"):
                    adapter = get_adapter(m.get("model", ""), api_key=m["api_key"])
                    result = adapter.execute(user_input)
                    if result.get("success"):
                        return {"success": True, "response": result["content"], "tokens": result.get("tokens", 0)}
        except Exception:
            pass

        # 降级：ClawsJoy 内置 Agent
        agent = self._get_agent(agent_name, user_id)
        if not agent:
            return {"success": False, "response": f"Agent不可用"}

        ctx = {
            "user_id": user_id,
            "action": self._last_action,
            "extracted": extracted or {},
            "pre_fetched": context_data.get("补全", {}).get("pre_fetched", []) if context_data else [],
        }

        try:
            if hasattr(agent, "process"):
                return agent.process(user_input, ctx)
        except Exception as e:
            return {"success": False, "response": str(e)}
        return {"success": False, "response": "无可用方法"}

    def _get_agent(self, agent_name, user_id):
        k = f"{agent_name}:{user_id}"
        if k in self._agent_cache:
            return self._agent_cache[k]
        try:
            from core.agents.wisdom.wisdom_factory import wisdom_factory

            a = wisdom_factory.get_agent(agent_name, user_id)
        except Exception:
            pass
            a = None
        if a:
            self._agent_cache[k] = a
        return a

    # ========== 回复生成 ==========

    def _generate_reply(self, user_input, action, extracted, context, user_id, agent_result=None):
        print(f"[DEBUG] _generate_reply: agent_result={agent_result}, extracted={extracted}")
        if agent_result and agent_result.get("videos"):
            return agent_result.get("response", "")
        if agent_result and agent_result.get("success") and agent_result.get("response"):
            raw = str(agent_result.get("response"))
            if (
                action == "vision"
                and raw
                and (raw.startswith("🔍") or raw.startswith("📹") or raw.startswith("📄") or raw.startswith("🖼"))
            ):
                return raw
            if '{"user"' not in raw and '{"assistant"' not in raw:
                if (extracted and extracted.get("需要澄清")) or raw == "需要澄清":
                    try:
                        clarify = llm_client.generate(
                            f"用户说：{user_input}\n信息不够，请用一句话反问用户补充细节。",
                            model=MODEL_MAIN,
                            max_tokens=50,
                            task_type="clarify",
                            timeout=60,
                        )
                        if clarify and len(clarify.strip()) > 2:
                            return clarify.strip()
                    except Exception:
                        pass
                ctx_parts = []
                if context.get("user_name"):
                    ctx_parts.append(f"用户叫{context['user_name']}")
                if action:
                    ctx_parts.append(f"当前操作:{action}")
                ctx_text = " | ".join(ctx_parts)
                try:
                    polished = llm_client.generate(
                        f"{ctx_text}\n将以下系统回复润色为自然对话。{'这是记忆查询结果，不要改变任何信息。' if action in ('recall','identity') else '不要改变事实。'}\n{raw}",
                        model=MODEL_MAIN,
                        max_tokens=100,
                        task_type="polish",
                        timeout=60,
                    )
                    if polished and len(polished.strip()) > 2:
                        return polished.strip()
                except Exception:
                    pass
                return raw
        ctx_parts = []
        if context.get("补全"):
            ctx_parts.append(f"系统补全:{json.dumps(context['补全'],ensure_ascii=False)}")
        if context.get("user_name"):
            ctx_parts.append(f"用户名字:{context['user_name']}")
        ctx_text = " | ".join(ctx_parts)

        prompt = f"""你是ClawsJoy本地AI系统。
{ctx_text}
用户: {user_input}
意图: {action}
回复:"""

        try:
            resp = llm_client.generate(
                f"用户说：{user_input}\n请简短回复。", model=MODEL_MAIN, max_tokens=200, task_type="reply", timeout=60
            )
            if resp and len(resp.strip()) > 2:
                return resp.strip()
        except Exception:
            pass

        return self._fallback(action, extracted, context)

    def _fallback(self, action, extracted, context):
        if action == "greeting":
            return "你好！我是ClawsJoy。"
        if action == "memory":
            k = extracted.get("key", "信息")
            v = extracted.get("value") or context.get("补全", {}).get("value", "")
            return f"已记住{k}" + (f"={v}" if v else "")
        if action == "chat":
            return "我在，请继续。"
        if action == "identity":
            n = extracted.get("名字") or context.get("补全", {}).get("名字", "")
            return f"你好，{n}！" if n else "好的。"
        if action == "recall":
            return f"查一下{extracted.get('query','信息')}..."
        return "好的。"

    # ========== 学习 ==========

    def _learn(self, user_input, action, extracted, response, latency_ms, user_id, context=None):
        # 主存储：agent_actions 表
        try:
            from core.lib.code_entity_extractor import extractor

            _sid = (context or {}).get("server_id") or (context or {}).get("session_id") or user_id
            extractor.insert_agent_action(
                session_id=_sid,
                task_name=f"cortex:{action}",
                tool_name="agent_cortex",
                result="success" if latency_ms < 5000 else "slow",
                file_type="cortex",
                agent_reaction="",
                detail=json.dumps(
                    {"input": user_input[:100], "response": response[:100], "latency_ms": latency_ms},
                    ensure_ascii=False,
                ),
            )
        except Exception:
            pass

        # SAG 入库：user_memory / user_profile
        if extracted:
            try:
                from core.lib.code_entity_extractor import extractor

                for k, v in extracted.items():
                    if v and len(str(v)) < 100:
                        extractor.upsert_entity(
                            {
                                "entity_type": "user_profile" if k in ("名字", "姓名") else "user_memory",
                                "entity_name": f"profile:{user_id}" if k in ("名字", "姓名") else f"memory:{user_id}:{k}",
                                "signature": json.dumps({k: v}, ensure_ascii=False),
                                "related_entities": [f"user:{user_id}", action],
                                "file_path": "",
                            }
                        )
            except Exception:
                pass

        # 兜底：保留旧存储（MemoryBank + VectorBank + history.jsonl）
        try:
            bank = get_bank(user_id, "memory_agent_v4")
            ctx_mgr = get_context(user_id)
            entry = {
                "user": user_input[:300],
                "assistant": response[:300],
                "action": action,
                "extracted": extracted,
                "ts": datetime.now().isoformat(),
            }
            with open(Path(f"data/users/{user_id}/history.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            ctx_mgr.add_turn(user_input, response, action, extracted)
            if extracted:
                for k, v in extracted.items():
                    if v and len(str(v)) < 100:
                        ctx_mgr.update_entity(k, str(v))
        except Exception:
            pass

        # fastText 训练数据自动累积
        try:
            if action and action not in ("greeting", "chat", "farewell", "thanks"):
                train_file = Path("data/fasttext_training_live.txt")
                train_file.parent.mkdir(parents=True, exist_ok=True)
                label = f"__label__{action}"
                line = f"{label} {user_input[:200].strip()}\n"
                if not train_file.exists() or line not in train_file.read_text(encoding="utf-8"):
                    with open(train_file, "a", encoding="utf-8") as f:
                        f.write(line)
        except Exception:
            pass

    def get_learning_stats(self, user_id: str = None) -> Dict:
        feedback_file = Path("data/feedback.json")
        if feedback_file.exists():
            data = json.loads(feedback_file.read_text(encoding="utf-8"))
            return {
                "total": len(data.get("success", [])) + len(data.get("failure", [])),
                "success_rate": round(
                    len(data.get("success", []))
                    / max(len(data.get("success", [])) + len(data.get("failure", [])), 1)
                    * 100,
                    1,
                ),
            }
        return {"total": 0, "success_rate": 0}

    def get_stats(self):
        stats = {**self._stats}
        stats["cached_agents"] = len(self._agent_cache)
        stats["success_rate"] = round(stats["success"] / max(stats["total"], 1) * 100, 1)
        stats["agents"] = {}
        for k in self._agent_cache:
            name = k.split(":")[0]
            stats["agents"][name] = stats["agents"].get(name, 0) + 1
        return stats

    def clear_cache(self):
        self._agent_cache.clear()

    # ========== 疲劳度管理 ==========

    def _sync_fatigue_to_living_agent(self):
        """_fatigue 更新后同步到 LivingAgent 感知层（真实指标）"""
        try:
            if getattr(self, "_living_agent", None) is None:
                from core.agents.builtin.living_agent import LivingAgent

                self._living_agent = LivingAgent("default")
            self._living_agent.update_from_cortex(
                {
                    "consecutive_errors": self._fatigue["consecutive_errors"],
                    "efficiency_decline": self._calc_efficiency_decline(),
                    "repetition_rate": self._calc_repetition_rate(),
                    "baseline": self._fatigue["baseline"],
                }
            )
        except Exception as e:
            logger.debug(f"[疲劳度同步] 跳过 LivingAgent 同步: {e}")

    def _calc_efficiency_decline(self) -> float:
        """最近5步平均耗时 / baseline"""
        dur = self._fatigue["durations"]
        if len(dur) < 5:
            return 1.0
        baseline = self._fatigue["baseline"]
        if baseline is None or baseline == 0:
            baseline = sum(dur) / len(dur)
            self._fatigue["baseline"] = baseline
        recent = sum(dur[-5:]) / 5
        return recent / baseline if baseline > 0 else 1.0

    def _calc_repetition_rate(self) -> float:
        """当前输入与 recent_inputs 的 n-gram 重叠率"""
        inputs = self._fatigue["recent_inputs"]
        if len(inputs) < 2:
            return 0.0
        current = inputs[-1]

        def ngrams(s, n=2):
            return set(s[i : i + n] for i in range(len(s) - n + 1))

        cur_ng = ngrams(current)
        if not cur_ng:
            return 0.0
        total_overlap = 0
        for prev in inputs[:-1]:
            prev_ng = ngrams(prev)
            if prev_ng:
                overlap = len(cur_ng & prev_ng) / len(cur_ng)
                total_overlap += overlap
        return total_overlap / max(len(inputs) - 1, 1)

    def _should_review(self) -> bool:
        """任一指标达阈值返回 True"""
        if self._fatigue["consecutive_errors"] >= 3:
            return True
        if self._calc_efficiency_decline() >= 2.0:
            return True
        if self._calc_repetition_rate() >= 0.6:
            return True
        return False

    def _execute_global_review(self, user_input: str) -> str:
        """调 llm_client 复盘"""
        fatigue = self._fatigue
        prompt = (
            f"【疲劳度复盘】\n"
            f"连续错误次数: {fatigue['consecutive_errors']}\n"
            f"效率衰退率: {self._calc_efficiency_decline():.2f}\n"
            f"重复率: {self._calc_repetition_rate():.2f}\n"
            f"用户输入: {user_input}\n"
            f"请分析当前 Agent 执行状态并给出优化建议。"
        )
        try:
            result = llm_client.chat([{"role": "user", "content": prompt}])
            if isinstance(result, str):
                return result
            if isinstance(result, dict):
                return result.get("content", "") or result.get("response", "")
            return str(result)
        except Exception:
            return ""


agent_cortex = AgentCortex()
