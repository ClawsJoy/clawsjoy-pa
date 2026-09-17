#!/usr/bin/env python3
"""Gateway 辅助函数 - 从主网关抽出的业务逻辑"""

import json
import os
import re
import time as _gw_time
import uuid
from pathlib import Path
from core.lib.paths import playwright_browsers_path

_intercept_cache = {}


def last_user_task_msg(messages):
    """取最后一条真实用户任务消息 — 跳过 [系统] 前缀的注入上下文
    (运行时快照/steer/空回复重试等), 防守卫/配额/任务分类误读注入文本。

    基准回归修复: #2 快照 user 消息含"修改/写入"等词, 导致 ForcedToolGuard
    拒绝全部读工具 + _classify_task_type 误判 code_modify。
    """
    for _m in reversed(messages or []):
        if _m.get("role") == "user":
            _c = str(_m.get("content") or "")
            if not _c.startswith("[系统]"):
                return _c
    return ""


def _resolve_project_root_read(filepath, sandbox_target, user_id, session_id):
    """P0 沙箱路径映射: 只读回退 — 沙箱内不存在时, 相对路径回退解析到项目根(_PROJECT_ROOT)。

    只读白名单: 候选必须落在项目根内且不含 .git; 写路径不调用本函数(写只进沙箱)。
    返回项目根 Path 或 None(沙箱已存在/不可回退)。
    """
    try:
        _base = _get_sandbox_base(user_id, session_id)
        # 项目根以文件位置推导(与网关 _PROJECT_ROOT 变量同源)。
        # 注意: 不能用 os.environ PROJECT_ROOT — config/.env 的 override 会把它改成 live 根,
        # 沙箱网关会解析到错误根(live), 导致回退失败。
        _proj_root = Path(__file__).resolve().parent.parent.parent
        try:
            _rel = str(sandbox_target.relative_to(_base))
        except Exception:
            _rel = ""
        if not _rel or _rel in (".", ""):
            return None
        _cand = _proj_root / _rel
        _cand_res = _cand.resolve()
        _root_res = _proj_root.resolve()
        # 只读白名单: 必须落在项目根内(或等于根), 且不含 .git
        if str(_cand_res) != str(_root_res) and not str(_cand_res).startswith(str(_root_res) + os.sep):
            return None
        if ".git" in _cand_res.parts:
            return None
        return _cand
    except Exception:
        return None


def should_auto_correct(session_id, reason, ttl=120):
    """120 秒内同 session 同原因不重复拦截，自动纠正"""
    if not session_id or not reason:
        return False
    key = f"{session_id}:{reason}"
    now = _gw_time.time()
    if key in _intercept_cache and now - _intercept_cache[key] < ttl:
        return True
    _intercept_cache[key] = now
    return False


# ========== 精准投喂缓存通知（GrowthEngine 规则更新闭环） ==========

_growth_rules_mtime: dict = {}  # user_id -> rules.jsonl mtime


def notify_precision_feed_refresh():
    """GrowthEngine 规则更新后调用：使精准投喂缓存失效，下次 _load_asset 加载最新数据。

    延迟 import 避免与 precision_feed 循环依赖。
    """
    try:
        from core.lib.precision_feed import invalidate_precision_feed_cache

        invalidate_precision_feed_cache()
        return True
    except Exception as e:
        print(f"[GATEWAY_HELPERS] 精准投喂缓存刷新失败: {e}")
        return False


def check_growth_rule_refresh(user_id: str = "default") -> bool:
    """检测 GrowthEngine 规则库（data/users/{user_id}/growth/rules.jsonl）是否更新。

    GrowthEngine._add_rule 写入/重写规则后，rules.jsonl mtime 变化；
    本函数被精准投喂 _load_asset('learning_insight') 调用，检测到变化即自动
    通知精准投喂缓存刷新，实现"规则更新 → 下次投喂注入最新学习结果"闭环。
    """
    rules_file = Path(f"data/users/{user_id}/growth/rules.jsonl")
    try:
        if not rules_file.exists():
            _growth_rules_mtime[user_id] = 0.0
            return False
        mtime = rules_file.stat().st_mtime
        prev = _growth_rules_mtime.get(user_id, 0.0)
        if prev > 0.0 and mtime > prev:
            _growth_rules_mtime[user_id] = mtime
            refreshed = notify_precision_feed_refresh()
            print(f"[GATEWAY_HELPERS] 检测到 GrowthEngine 规则更新（{user_id}），缓存刷新={refreshed}")
            return True
        _growth_rules_mtime[user_id] = mtime
        return False
    except Exception as e:
        print(f"[GATEWAY_HELPERS] check_growth_rule_refresh 失败: {e}")
        return False


from datetime import datetime
from typing import Any, Dict, List, Optional

# ========== 用户状态管理 ==========


class ProjectUserState:
    """项目级用户状态"""

    def __init__(self, project_id: str = None, user_id: str = "default"):
        self.project_id = project_id
        self.user_id = user_id
        self._state: Dict[str, Any] = {}
        self._load()

    def _get_state_path(self) -> Path:
        if self.project_id:
            try:
                from core.lib.code_repo import get_code_repo

                repo = get_code_repo(self.user_id)
                project = repo.get_project(self.project_id)
                if project:
                    project_path = Path(project["path"])
                    state_dir = project_path / ".clawsjoy"
                    state_dir.mkdir(exist_ok=True)
                    return state_dir / "user_state.json"
            except Exception:
                pass
        state_dir = Path(f"data/user_states/{self.user_id}")
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir / "state.json"

    def _load(self):
        path = self._get_state_path()
        if path.exists():
            try:
                self._state = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                self._state = {}
        else:
            self._state = {}

    def _save(self):
        self._get_state_path().write_text(json.dumps(self._state, indent=2, ensure_ascii=False), encoding="utf-8")

    def get(self, key: str, default=None):
        return self._state.get(key, default)

    def set(self, key: str, value):
        self._state[key] = value
        self._save()

    def get_all(self) -> Dict:
        return self._state.copy()


_USER_STATE_CACHE: Dict[str, ProjectUserState] = {}


def get_user_state(project_id: str = None, user_id: str = "default") -> Dict:
    key = f"{project_id or 'global'}_{user_id}"
    if key not in _USER_STATE_CACHE:
        _USER_STATE_CACHE[key] = ProjectUserState(project_id, user_id)
    return _USER_STATE_CACHE[key].get_all()


def set_user_state(project_id: str, user_id: str, key: str, value):
    state_key = f"{project_id or 'global'}_{user_id}"
    if state_key not in _USER_STATE_CACHE:
        _USER_STATE_CACHE[state_key] = ProjectUserState(project_id, user_id)
    _USER_STATE_CACHE[state_key].set(key, value)


# ========== 记忆管理 ==========

MEMORY_FILE = Path("data/memory_simple.json")
MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_memories(user_id: str) -> list:
    try:
        from agents.memory_agent.agent_v4 import MemoryAgentV4

        agent = MemoryAgentV4(user_id)
        result = agent.recall_forever("all_memories")
        if result:
            return result if isinstance(result, list) else [result]
    except Exception:
        pass

    if MEMORY_FILE.exists():
        all_memories = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        return all_memories.get(user_id, [])
    return []


def save_memory(user_id: str, fact: str):
    try:
        from agents.memory_agent.agent_v4 import MemoryAgentV4

        agent = MemoryAgentV4(user_id)
        agent.remember_forever("fact", fact)
        return
    except Exception:
        pass

    all_memories = {}
    if MEMORY_FILE.exists():
        all_memories = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    memories = all_memories.get(user_id, [])
    memories.append({"fact": fact, "timestamp": datetime.now().isoformat()})
    all_memories[user_id] = memories[-100:]
    MEMORY_FILE.write_text(json.dumps(all_memories, indent=2), encoding="utf-8")


def search_memories(user_id: str, query: str) -> list:
    try:
        from agents.memory_agent.agent_v4 import MemoryAgentV4

        agent = MemoryAgentV4(user_id)
        result = agent.process(f"搜索记忆: {query}")
        if result and result.get("response"):
            return [result.get("response")]
    except Exception:
        pass

    memories = load_memories(user_id)
    results = []
    for m in memories:
        fact = m.get("fact", "")
        if query in fact or fact in query:
            results.append(fact)
    return results[:10]


# ========== 用户信息提取 ==========


def extract_user_info(message: str, user_id: str, project_id: str = None) -> bool:
    m = re.search(r"我叫([\u4e00-\u9fa5]{2,4})", message)
    if m:
        name = m.group(1)
        set_user_state(project_id, user_id, "user_name", name)
        save_memory(user_id, f"用户名字: {name}")
        return True
    return False


def answer_from_state(message: str, user_id: str, project_id: str = None) -> Optional[str]:
    if "我叫什么名字" in message or "我的名字" in message:
        state = get_user_state(project_id, user_id)
        name = state.get("user_name")
        if name:
            return f"您叫{name}呀，我记着呢！"
        memories = load_memories(user_id)
        for m in memories:
            fact = m.get("fact", "")
            if "用户名字:" in fact:
                return f"您叫{fact.replace('用户名字: ', '')}呀"
        return "您还没告诉我您的名字呢"
    return None


# ========== 文件内容读取 ==========


def extract_file_content(project_id: str, file_path: str, user_id: str) -> tuple:
    try:
        from core.lib.code_repo import get_code_repo

        repo = get_code_repo(user_id)
        content = repo.get_file_content(project_id, file_path)
        if content:
            return content, f"文件: {file_path} ({len(content)} 字符)"
        return "", "文件为空或不存在"
    except Exception as e:
        return "", f"读取失败: {e}"


# ========== 学习统计 ==========

LEARNING_FILE = Path("data/learning_data/learning_stats.json")
LEARNING_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_learning_stats() -> dict:
    if LEARNING_FILE.exists():
        data = json.loads(LEARNING_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            if "total_learnings" not in data:
                data["total_learnings"] = data.get("learned", 0)
            return data
    return {"total_learnings": 0, "successful_learnings": 0, "failed_learnings": 0}


def record_learning(fact: str, success: bool = True):
    stats = load_learning_stats()
    stats["total_learnings"] = stats.get("total_learnings", 0) + 1
    if success:
        stats["successful_learnings"] = stats.get("successful_learnings", 0) + 1
    else:
        stats["failed_learnings"] = stats.get("failed_learnings", 0) + 1
    LEARNING_FILE.write_text(json.dumps(stats, indent=2), encoding="utf-8")


# ========== 用户目录创建 ==========


def create_user_directories(username: str, user_id: str, email: str = ""):
    user_dir = Path(f"data/users/{username}")
    if user_dir.exists():
        return
    user_dir.mkdir(parents=True)
    for sub in ["encrypted", "workspace", "logs"]:
        (user_dir / sub).mkdir(parents=True, exist_ok=True)
    profile = {
        "user_id": user_id,
        "username": username,
        "email": email,
        "role": "user",
        "created_at": datetime.now().isoformat(),
    }
    (user_dir / "profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")


# ========== V9 Agent 工作区 → StandardJSON 协议适配器 ==========


def tool_calls_to_standard_json(tool_calls: list, user_id: str = "default", session_id: str = "default") -> dict:
    """将 OpenAI tool_calls 格式转换为 StandardJSON v1.1

    Args:
        tool_calls: OpenAI 格式的工具调用列表
        user_id: 用户ID
        session_id: 会话ID

    Returns:
        StandardJSON 格式的请求字典
    """
    from core.lib.json_builder import StandardJSONBuilder
    from core.lib.json_standard import StandardJSON

    if not tool_calls:
        return StandardJSON().to_dict()

    if len(tool_calls) > 1:
        builder = StandardJSONBuilder()
        builder.simple("workflow", "multi_tool")
        builder.with_user(user_id, session_id)
        builder.with_params(
            tool_count=len(tool_calls), tools=[tc.get("function", {}).get("name", "") for tc in tool_calls]
        )
        return builder.build().to_dict()

    first_call = tool_calls[0]
    func_name = first_call.get("function", {}).get("name", "chat")
    args = first_call.get("function", {}).get("arguments", "{}")

    try:
        import json as _json

        params = _json.loads(args) if isinstance(args, str) else args
    except Exception:
        params = {}

        # 展平 raw_arguments
        if func_name == "execute_command" and "raw_arguments" in params and "command" not in params:
            _raw = params.pop("raw_arguments")
            try:
                _parsed = _json.loads(_raw)
                params["command"] = _parsed.get("command", "")
            except Exception:
                import re

                _match = re.search(r'"command"\\s*:\\s*"(.+?)\'PYEOF\'', _raw, re.DOTALL)
                if _match:
                    params["command"] = _match.group(1).rstrip() + "'PYEOF'"

    # 映射 tool_name → StandardJSON action/target
    tool_action_map = {
        "read_file": ("read", "file"),
        "write_file": ("write", "file"),
        "write_large": ("write", "file"),
        "list_dir": ("list", "directory"),
        "execute_command": ("execute", "command"),
        "query_index": ("query", "index"),
        "search_files": ("search", "file"),
        "call_api": ("call", "api"),
        "notify_boss": ("notify", "boss"),
    }

    action, target = tool_action_map.get(func_name, ("chat", "text"))

    builder = StandardJSONBuilder()
    builder.simple(action, target)
    builder.with_params(**params)
    builder.with_user(user_id, session_id)

    return builder.build().to_dict()


def standard_json_to_tool_result(standard_response: dict, tool_call_id: str = "") -> dict:
    """将 StandardJSON 响应转换为 OpenAI tool_result 格式（带 tool_call_id）"""
    _content = (
        standard_response.get("output_content")
        or standard_response.get("content")
        or standard_response.get("response", "")
    )
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": _content,
        "status": standard_response.get("status", "completed"),
    }


# ========== V9 网关业务层（从主网关迁移）==========


def _add_project_prefix(result):
    """给沙箱工具返回值统一加 _project_prefix"""
    if isinstance(result, dict):
        result["_project_prefix"] = "clawsjoy_dev/"
    return result


def _unified_preprocess(data):
    """统一中间件：展平 raw_arguments + 路径自动纠正"""
    # 防御：request.json 可能返回 str（body 为 JSON 字符串/裸字符串），统一规范为 dict，避免 .get 崩溃
    if not isinstance(data, dict):
        if isinstance(data, str):
            try:
                _parsed = json.loads(data)
                if isinstance(_parsed, dict):
                    data = _parsed
                else:
                    data = {}
            except Exception:
                data = {}
        else:
            data = {}
    # 路径自动纠正：clawsjoy-dev → clawsjoy_dev
    for _key in ("path", "file_path", "command"):
        if _key in data and isinstance(data[_key], str):
            data[_key] = _auto_correct_path(data[_key])
    if data.get("raw_arguments") and not data.get("command"):
        _raw = data["raw_arguments"]
        try:
            _parsed = json.loads(_raw)
            if isinstance(_parsed, dict):
                data["command"] = _parsed.get("command", "")
                print(
                    f"[UNI] json.loads 成功, keys: {list(_parsed.keys())[:5]}, command: {repr(_parsed.get('command', 'MISSING'))[:100]}"
                )
            else:
                data["command"] = str(_parsed)
        except Exception as _e_uni:
            import re as _re_uni

            print(f"[UNI] json.loads 失败: {_e_uni}, raw前100字符: {_raw[:100]}")
            _match = _re_uni.search(r'"command"\s*:\s*"(.+?)\'PYEOF\'', _raw, _re_uni.DOTALL)
            if _match:
                data["command"] = _match.group(1).rstrip() + "'PYEOF'"
    return data


def _get_sandbox_base(user_id, session_id):
    """统一沙箱根推导：所有工具共用此函数。返回 data/projects/{uid}/{sid}/clawsjoy_dev

    批187 · 缺陷1 修复（假失败）：PA 线程（`pa_*`）传入的 `user_id` 可能是 `'default'`，
    直接拼会得到 `data/projects/default/{sid}/clawsjoy_dev`（**并不存在**）⇒ 产物核验/路径解析 100%
    报「产物不存在」，老板每次任务都看到「核验未通过」（实测：`pa_mu2mw715` 的真实沙箱在
    `data/projects/web_1783219071801/pa_mu2mw715/clawsjoy_dev`）。

    **回退规则（最小侵入）**：原路径存在 ⇒ 原样返回（**66 个调用点行为不变**）；不存在 ⇒ 按 session_id
    在 `data/projects/*/` 下反查，**唯一命中**才采用；否则返回原路径（保持旧行为，不猜）。
    """
    p = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev")
    try:
        if p.exists():
            return p
        import glob as _g

        _hits = _g.glob(f"data/projects/*/{session_id}/clawsjoy_dev")
        if len(_hits) == 1:
            return Path(_hits[0])
    except Exception:
        pass
    return p


def read_agent_state(user_id, session_id):
    """读取 session 沙箱 .agent_state.json(防御性; 走 _get_sandbox_base, 与文件服务一致)。"""
    try:
        _f = _get_sandbox_base(user_id, session_id) / ".agent_state.json"
        if _f.exists():
            return json.loads(_f.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _auto_correct_path(path_str: str) -> str:
    """自动纠正常见路径错误，系统负责路径格式统一"""
    if not isinstance(path_str, str) or not path_str:
        return path_str
    # 1. clawsjoy-dev -> clawsjoy_dev
    path_str = path_str.replace("clawsjoy-dev", "clawsjoy_dev")
    # 2. 项目裸路径加前缀
    if path_str.startswith("clawsjoy-platform/") or path_str.startswith("clawsjoy-platform\\"):
        path_str = "clawsjoy_dev/" + path_str
    # 3. 子目录裸路径加前缀
    for _sub in ("frontend/", "backend/", "pages/", "api/", "db/", "migrations/"):
        if path_str.startswith(_sub) and "clawsjoy_dev/" not in path_str:
            path_str = "clawsjoy_dev/clawsjoy-platform/" + path_str
            break
    # 4. 双重前缀检测
    if "clawsjoy_dev/" in path_str:
        parts = path_str.split("clawsjoy_dev/")
        if len(parts) > 2:
            path_str = "clawsjoy_dev/" + parts[-1]
        return path_str
    # 5. 兜底：路径不包含 clawsjoy_dev/ 时不做纠正，返回原始路径
    return path_str


def _get_agent_tools():
    tools = None
    try:
        import psycopg2
        import psycopg2.extras

        from core.lib.code_entity_extractor import searcher

        conn = psycopg2.connect(searcher.db_url)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT entity_name, signature, related_entities FROM code_entities WHERE entity_type='tool' AND status='active' ORDER BY entity_name"
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        if rows:
            tools = [_sag_tool_to_openai_format(t) for t in rows]
    except Exception:
        pass
    if not tools:
        tools = _get_default_tools()
    # 合并 _TOOL_REGISTRY 已注册插件的 schema(单一事实源): 注册了工具就必须让 LLM 看到
    try:
        from core.gateway.tool_router import _TOOL_REGISTRY as _reg

        _known = {t.get("function", {}).get("name") for t in tools}
        for _name, _cls in _reg.items():
            if _name in _known:
                continue
            _schema = getattr(_cls, "schema", None)
            if _schema:
                tools.append(_schema)
    except Exception:
        pass
    return tools


def _get_default_tools():
    """SAG 不可用时的默认工具集"""
    _defaults = [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "strict": True,
                "description": "读取沙箱内文件（data/、data/reports/、core/、config/ 等相对路径）。注意：Obsidian vault（/mnt/d/... 绝对路径）在沙箱外，本工具读不了——读 vault 用 obsidian_knowledge 工具(action=read)，不要用本工具读绝对路径。",
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "path": {"type": "string"},
                        "search": {"type": "string"},
                        "lines_start": {"type": "integer"},
                        "lines_end": {"type": "integer"},
                        "verify_line": {"type": "integer"},
                        "verify_expected": {"type": "string"},
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "strict": True,
                "description": "写入文件",
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "line": {"type": "integer", "description": "按行修改：指定行号"},
                        "reason": {"type": "string", "description": "写该文件的理由（必填，给老板审批看；说明写给谁/为什么/影响范围）"},
                    },
                    "required": ["path", "reason"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_dir",
                "strict": True,
                "description": "列出目录",
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_files",
                "strict": True,
                "description": "搜索文件",
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"query": {"type": "string"}, "path": {"type": "string"}},
                    "required": ["query", "path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "execute_command",
                "strict": True,
                "description": "执行命令",
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "call_api",
                "strict": True,
                "description": "调用第三方 REST API（仅允许 HTTPS）",
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "url": {"type": "string", "description": "目标 URL，必须以 https:// 开头"},
                        "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
                        "headers": {"type": "object", "description": "请求头（可选）"},
                        "body": {"type": "object", "description": "请求体（可选）"},
                    },
                    "required": ["url", "method"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "notify_boss",
                "strict": True,
                "description": "写通知到 data/v8/notifications.json",
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "message": {"type": "string", "description": "通知内容"},
                        "level": {"type": "string", "enum": ["info", "warning", "error"]},
                        "channel": {"type": "string", "description": "通知渠道（可选）"},
                    },
                    "required": ["message"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "query_index",
                "strict": True,
                "description": "查询代码索引",
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "browse_web",
                "strict": True,
                "description": "读取网页内容并返回纯文本（已去标签，适合抓取新闻/文章正文），返回页面文本前 10000 字符。仅允许 HTTPS，禁止 localhost/内网地址。",
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"url": {"type": "string", "description": "目标网页 URL，必须以 https:// 开头"}},
                    "required": ["url"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_web",
                "strict": True,
                "description": "获取外部网页原始内容（HTML/JSON/文本直通），仅适合服务端渲染的静态页面/API/数据接口；JS 动态渲染的 SPA 页面会拿到空壳，请改用 playwright_browser。返回前 10000 字符。仅允许 http/https 公网地址，禁止 localhost/内网。",
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"url": {"type": "string", "description": "要获取的网页 URL(http/https)"}},
                    "required": ["url"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "strict": True,
                "description": "搜索引擎查询（Bing RSS），返回标题+链接+摘要列表。用于按标题/关键词找原文：当你有新闻标题但只有 news.google.com 混淆链接（fetch 拿不到原文）时，用标题搜原文来源站（如新浪/量子位）。支持 site 站点限定提升准确率。返回前 8 条结果，每条含 title/url/snippet。仅允许公网搜索，禁止 localhost/内网。",
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "query": {"type": "string", "description": "搜索关键词（建议用原文标题中的独特短语，如 'Anthropic 被指控侵权训练 Claude'）"},
                        "site": {"type": "string", "description": "可选：限定搜索站点（如 sina.com.cn / qbitai.com），提高新闻原文命中率"},
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "playwright_browser",
                "strict": True,
                "description": "浏览器自动化，适合 JS 动态渲染的 SPA 页面（React/Vue 等）与交互式页面（填表/点击/截图/取渲染后正文）。action=open 打开 url 并返回标题；action=content 获取渲染后页面正文文本（自动等待 JS 渲染，空壳会重试）；action=click 用 CSS selector 点击元素；action=fill 用 CSS selector 填写表单 text；action=screenshot 截图保存到 screenshot_path。click/fill/screenshot/content 可搭配 url 参数在同一次调用内先导航再操作。仅允许 http/https 公网地址，禁止 localhost/内网。",
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["open", "content", "click", "fill", "screenshot"],
                            "description": "要执行的操作",
                        },
                        "url": {"type": "string", "description": "目标 URL（action=open 必填；其他 action 可选，提供时先导航再操作）"},
                        "selector": {"type": "string", "description": "CSS 选择器（action=click/fill 必填）"},
                        "text": {"type": "string", "description": "表单填写内容（action=fill 必填）"},
                        "screenshot_path": {
                            "type": "string",
                            "description": "截图保存路径（action=screenshot 可选，默认 data/screenshots/playwright_<pid>.png）",
                        },
                        "wait_ms": {"type": "integer", "description": "操作前等待毫秒数（可选）"},
                    },
                    "required": ["action"],
                },
            },
        },
        # browser_hybrid(2026-09-04, Computer Use 混合方案, 设计 docs/reports/computer_use_agent_design_20260904.md):
        # enumerate 枚举可交互元素(id|role|label|sel|bbox, 坐标仅供展示) → Agent/LLM 按任务选序号
        # → click/fill/type/press/select_option/hover 用 DOM 选择器执行并验证; observe 检查当前页。
        # 坐标从不作点击依据; page_id 保留页面状态(唯一短标识, <=64, 字母数字_-); 仅 http/https 公网。
        {
            "type": "function",
            "function": {
                "name": "browser_hybrid",
                "strict": True,
                "description": "Computer Use 混合方案(网页自动化): action=enumerate 枚举页面可交互元素, 返回序号清单(items)与 items_text(每行 序号|role|稳定名称), 你(Agent)根据任务意图从清单选目标序号 — 不要编坐标; action=click/fill/type/press/select_option/hover 用所选序号(index, 1-based)对应的 DOM 选择器执行(引擎会做 role 校验与结果验证); action=observe 断言 url_contains/text_visible/field_value(多步流程逐步验证); action=close 释放页面。page_id 每次给唯一短标识(如 p_任务号_步骤号)以跨步骤保留页面状态; 新开页时带 url。注意: 输入框稳定名称来自 a11y 标签策略, 占位文本若为新闻式内容会被降级为 文本输入框/搜索框; 若元素不可见或 DOM 变化, 先重新 enumerate。坐标 x/y 只用于截图标注与展示, 不用于点击。仅允许 http/https 公网地址。",
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "enumerate",
                                "click",
                                "fill",
                                "type",
                                "press",
                                "select_option",
                                "hover",
                                "screenshot",
                                "observe",
                                "close",
                            ],
                            "description": "enumerate=枚举; click/fill/type/press/select_option/hover/screenshot=执行(index 必填); observe=断言; close=释放页面",
                        },
                        "url": {"type": "string", "description": "enumerate 打开的目标(可选; 复用 page_id 已有页面时省略)"},
                        "page_id": {"type": "string", "description": "页面句柄(唯一短标识, 字母数字_- <=64; 跨步骤保留状态)"},
                        "roles": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "enumerate 可选: 只枚举这些 role(button/link/input/textarea/select/checkbox...)",
                        },
                        "max_items": {"type": "integer", "description": "enumerate 可选: 返回上限(默认40)"},
                        "index": {"type": "integer", "description": "click/fill/... 必填: enumerate 清单中的序号(1-based)"},
                        "value": {"type": "string", "description": "fill/type 的输入内容; press 的按键(默认 Enter)"},
                        "check": {
                            "type": "string",
                            "enum": ["url_contains", "text_visible", "field_value"],
                            "description": "observe 的检查类型",
                        },
                        "target": {"type": "string", "description": "observe/verify 目标值(url 片段 / 页面文本 / 期望字段值)"},
                        "screenshot_path": {"type": "string", "description": "可选: 截图保存路径(沙箱内)"},
                        "viewport_w": {"type": "integer", "description": "可选: 视口宽(默认1280)"},
                        "viewport_h": {"type": "integer", "description": "可选: 视口高(默认810)"},
                        "intent": {
                            "type": "string",
                            "description": "关键动作必填(double_check=true 时): 本步操作意图(如 点击「百度一下」按钮)",
                        },
                        "double_check": {
                            "type": "boolean",
                            "description": "关键动作(提交/发布/删除/付款): true=本地 qwen2.5:7b 对打乱清单独立再选, 两次一致才执行",
                        },
                        "fallback": {
                            "type": "string",
                            "enum": ["none", "vision"],
                            "description": "双检冲突处理: vision=截图编号让 qwen2.5vl 仲裁(实测不可靠, 默认 none→ask 老板)",
                        },
                        "checker_model": {
                            "type": "string",
                            "description": "可选: 双检本地模型(默认 qwen2.5:7b-instruct-q4_0-gpu)",
                        },
                        "checker_port": {"type": "integer", "description": "可选: 双检模型端口(默认11435)"},
                    },
                    "required": ["action"],
                },
            },
        },
        # cu_learning(P4 学习循环 + SOP 生成器, 2026-09-04): 浏览器任务编排/防假完成/SOP
        {
            "type": "function",
            "function": {
                "name": "cu_learning",
                "strict": True,
                "description": "Computer Use 学习循环编排: 浏览器多步任务按此记录与收尾。action=start: 任务开始显式给出 objective + completion(可验证完成条件[{check:url_contains|text_visible|field_value, target}]) + fail_if(失败判据); action=log_step: 每步操作(成功/失败)写入 data/computer_use/plans/ 供学习, 返回是否触发停止(同一意图失败>2 / 连续3步失败 / 累计>3 → 停止并出失败报告); action=complete: 提交证据(url/text/字段), 所有 completion 条件无证据则拒绝(防假完成), 同任务成功>=2 次自动具备 SOP 生成资格; action=count: 查该任务成功次数; action=telemetry: 汇总 plans 目录成功率/耗时/失败分类; action=sop: 生成 CU-SOP markdown(步骤含 意图/锚点=role+label+sel/动作)并尽力写 vault ComputerUseSOPs/。完成每一步务必用 browser_hybrid observe 拿证据再 log_step(ok=true); 失败先给 category(选择错/执行错/风控/选择器失效/超时)。",
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["start", "log_step", "state", "complete", "abort", "count", "telemetry", "sop"],
                            "description": "start/log_step/state/complete/abort/count/telemetry/sop",
                        },
                        "task_id": {"type": "string", "description": "任务标识(建议 短横线+日期, 如 publish-xhs-20260904)"},
                        "task_key": {"type": "string", "description": "可复用流程键(同流程多次运行共用; 默认=task_id)。SOP 按此聚合成功次数"},
                        "objective": {"type": "string", "description": "start: 任务目标一句话(将写入 SOP task)"},
                        "target_url": {"type": "string", "description": "start: 目标页面 URL(SOP 前置)"},
                        "completion": {
                            "type": "array",
                            "items": {"type": "object", "additionalProperties": True},
                            "description": "start: 可验证完成条件, 如 [{check:url_contains,target:success},{check:text_visible,target:已发布}]",
                        },
                        "fail_if": {
                            "type": "array",
                            "items": {"type": "object", "additionalProperties": True},
                            "description": "start: 失败判据(可选)",
                        },
                        "plan_id": {
                            "type": "string",
                            "description": "log_step/state/complete/abort: start 返回的 plan_id",
                        },
                        "op": {"type": "string", "description": "log_step: 本步动作(click/fill/press/...)"},
                        "intent": {"type": "string", "description": "log_step: 本步意图(如 点击「发布」按钮)"},
                        "index": {"type": "integer", "description": "log_step: 选择的元素序号"},
                        "sel": {"type": "string", "description": "log_step: 选择器"},
                        "role": {"type": "string", "description": "log_step: 元素角色"},
                        "label": {"type": "string", "description": "log_step: 元素稳定名称"},
                        "ok": {"type": "boolean", "description": "log_step: 本步是否成功"},
                        "category": {"type": "string", "description": "log_step(失败时): 选择错/执行错/风控/选择器失效/超时/歧义"},
                        "error": {"type": "string", "description": "log_step(失败时): 错误信息"},
                        "evidence": {
                            "type": "object",
                            "additionalProperties": True,
                            "description": "complete: 完成证据 {url, head/text, field_value}",
                        },
                        "report": {"type": "string", "description": "complete: 最终报告摘要"},
                        "reason": {"type": "string", "description": "abort: 停止原因"},
                        "title": {"type": "string", "description": "sop: SOP 文件名(默认 task_key-cu-sop)"},
                        "plan_dir": {"type": "string", "description": "可选: 计划目录(vault 镜像/沙箱调试用)"},
                    },
                    "required": ["action"],
                },
            },
        },
        # browser_local(本地浏览器操作, Manus 模式): 从工具插件导入 schema, 单一来源防漂移
        _get_browser_local_schema(),
        # 知识维护(2026-08-30): Obsidian 常驻知识文件(SOPs + 避坑清单.md)常态更新
        {
            "type": "function",
            "function": {
                "name": "obsidian_knowledge",
                "strict": True,
                "description": "**本工具只读 Obsidian vault 的知识文件**(在沙箱外由网关代读代写)。沙箱内文件(data/、data/reports/、data/screenshots/、data/tmp/ 等)请用 read_file 读取, 不要用本工具。动作: list 列知识文件; read 读文件全文(sop_key: 固定键或 vault 相对路径); search 检索知识库; update_sop 更新 SOP 小节; append_pitfall 写避坑清单; sync 同步 SOP 到沙箱镜像。草稿箱(2026-08-31): write_draft 新建草稿到 vault 草稿箱/平台/(今天日期前缀文件名); update_draft(2026-09-06) 就地更新已有草稿(draft_path=目标文件路径, content=修改后全文, 保留原 frontmatter)——「修改/调整/更新草稿」任务必须用 update_draft 而不是 write_draft, 否则会新建文件而非改原稿; archive_media(2026-09-07) 归档媒体文件(视频/图片/音频)到 草稿箱/{platform}/assets/ — Agent 不需要知道 vault 物理路径, 归档一律用 archive_media(files=[沙箱内路径], platform=目标平台), 返回 vault 相对路径; 禁止读源码找 vault 路径或 cp 绝对路径; mark_published 把已发布草稿更新状态并移入已发布/(**本地文件操作, 直接传用户给的 post_url 即可, 不要用 browse/fetch 验证链接**); list_drafts 列草稿。多模态学习(2026-09-01): process_media 处理收件箱/媒体文件(video/audio→whisper 转录; pdf→PyPDF2 提取; image→llava 读图), LLM 总结后写笔记到 vault 学习笔记/{类型}/, 原文件复制 assets/ 嵌入。process_youtube 处理 YouTube 剪藏/链接: 检测已有字幕→跳过; 无字幕→yt-dlp 下载音频+whisper 转录→字幕写入笔记(下载失败降级标注需手动下载)。write_note(2026-09-03, R15.1 2026-09-04): 写任意技术/评估/总结/复盘笔记到 vault(非平台稿用这个; write_draft 只用于草稿箱平台稿, 必须给 platform)。content 直接写正文(**不要自带 yaml frontmatter 或 # 一级标题** — 工具自动生成 frontmatter+标题, 自带部分会被自动清洗); 系统提示行/[系统]回声/截断残留/重复段落会被自动清洗, 清洗后为空则拒绝写入; 超长内容分多次调用(append=true 追加续写同一标题, 防单次输出过长被截断); 成功后返回 path+verified(bytes/行数/头部预览) 可直接核对。",
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "list",
                                "read",
                                "search",
                                "update_sop",
                                "append_pitfall",
                                "sync",
                                "write_draft",
                                "update_draft",
                                "archive_media",
                                "mark_published",
                                "list_drafts",
                                "process_media",
                                "process_youtube",
                                "write_note",
                            ],
                            "description": "要执行的操作。草稿箱(2026-08-31): write_draft 新建草稿到 vault 草稿箱/平台/(今天日期前缀文件名); update_draft(2026-09-06) 就地更新已有草稿(draft_path=目标文件路径, content=修改后全文, 保留原 frontmatter)——「修改/调整/更新草稿」任务必须用 update_draft 而不是 write_draft, 否则会新建文件而非改原稿; mark_published 用户发布后回传链接更新状态+移入已发布/; list_drafts 列草稿。多模态学习(2026-09-01): process_media 处理收件箱/媒体文件(video/audio→whisper 转录→LLM 总结→写学习笔记; pdf→PyPDF2 提取→总结; image→复制原文件), 笔记写 vault 学习笔记/{类型}/, 原文件复制 assets/",
                        },
                        "sop_key": {
                            "type": "string",
                            "description": "read 目标: 固定键(平台发布工作流/番茄推广SOP/视频制作SOP/避坑清单) 或任意 vault 相对路径(如 微信公众号/公众号.md、Clippings/xxx.md, 可先用 search 查 rel_path); update_sop 仅固定 SOP 键",
                        },
                        "query": {"type": "string", "description": "search 的检索词"},
                        "limit": {"type": "integer", "description": "search 返回条数上限(默认3)"},
                        "section_title": {"type": "string", "description": "update_sop 小节标题(如 '抖音图文发布 2026-08-26')"},
                        "content": {
                            "type": "string",
                            "description": "update_sop 小节正文 / write_note 笔记正文(markdown, 支持表格/代码块/链接)",
                        },
                        "pitfall": {"type": "string", "description": "append_pitfall 的坑描述(现象+规避)"},
                        "platform": {
                            "type": "string",
                            "description": "write_draft/update_draft(必填)/archive_media(必填)/mark_published/list_drafts 平台: 公众号/小红书/知乎/B站/抖音; 非平台笔记请用 write_note 不要传 platform",
                        },
                        "files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "archive_media 待归档文件路径列表(沙箱内; 支持视频/图片/音频; 复制到 草稿箱/{platform}/assets/)",
                        },
                        "subdir": {"type": "string", "description": "archive_media 归档子目录(可选, 默认 assets)"},
                        "title": {"type": "string", "description": "write_draft 草稿标题"},
                        "media_files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "write_draft 媒体文件路径列表(沙箱内; 图片复制进 assets/, 视频相对路径引用)",
                        },
                        "summary": {"type": "string", "description": "write_draft 摘要(公众号 120 字)"},
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "write_draft 标签(小红书 3-5 话题)",
                        },
                        "分区": {"type": "string", "description": "write_draft B站分区(知识/科技等)"},
                        "draft_path": {"type": "string", "description": "mark_published 草稿路径(绝对或 vault 相对)"},
                        "post_url": {"type": "string", "description": "mark_published 发布链接(用户回传)"},
                        "status": {"type": "string", "description": "list_drafts 状态过滤(draft/published)"},
                        "file_path": {
                            "type": "string",
                            "description": "process_media 要处理的文件路径(vault 收件箱/ 内或沙箱内; 如 收件箱/xxx.mp4)",
                        },
                        "media_type": {
                            "type": "string",
                            "description": "process_media 文件类型(auto 自动推断/video/audio/image/pdf)",
                        },
                        "title": {"type": "string", "description": "process_media/process_youtube 笔记标题(可选)"},
                        "source_url": {"type": "string", "description": "process_youtube YouTube 链接(剪藏 source 或纯链接)"},
                        "note_path": {"type": "string", "description": "process_youtube 对应剪藏笔记路径(可选; 无则新建笔记)"},
                        "folder": {
                            "type": "string",
                            "description": "write_note 目标目录(vault 相对路径, 可选; 空=vault 根目录; 如 收件箱/学习笔记/调研报告/Harness专栏/修复报告/Harness专栏/自学习; Harness 修复经验可在 Harness专栏 全库检索)",
                        },
                        "append": {
                            "type": "boolean",
                            "description": "write_note 可选: true=追加续写同名笔记(长文分块); 默认 false=新建(重名自动 -2/-3)",
                        },
                    },
                    "required": ["action"],
                },
            },
        },
        # 确定性表格提取(2026-09-07): 从工具插件导入 schema, 单一来源防漂移
        _get_table_extract_schema(),
    ]
    # 过滤导入失败产生的 None(防御)
    return [t for t in _defaults if t is not None]


def _get_browser_local_schema():
    """browser_local 工具 schema(复用 core/tools/browser_local.BROWSER_LOCAL_SCHEMA)"""
    try:
        from core.tools.browser_local import BROWSER_LOCAL_SCHEMA

        return BROWSER_LOCAL_SCHEMA
    except Exception:
        return None


def _get_table_extract_schema():
    """table_extract 工具 schema(复用 core/tools/table_extract.TABLE_EXTRACT_SCHEMA, 单一来源)"""
    try:
        from core.tools.table_extract import TABLE_EXTRACT_SCHEMA

        return TABLE_EXTRACT_SCHEMA
    except Exception:
        return None


def _sag_tool_to_openai_format(tool: dict) -> dict:
    """将 SAG 中的工具实体转换为 OpenAI function calling 格式"""
    import json

    _sig = tool.get("signature", "")
    _params = {"type": "object", "properties": {}, "required": []}
    if _sig:
        try:
            _data = json.loads(_sig)
            if isinstance(_data, dict):
                _p = _data.get("parameters")
                if isinstance(_p, dict) and isinstance(_p.get("properties"), dict):
                    _params = {
                        "type": "object",
                        "properties": _p["properties"],
                        "required": _p.get("required", []),
                    }
        except Exception:
            pass
    return {
        "type": "function",
        "function": {
            "name": tool["entity_name"],
            "description": _sig,
            "parameters": _params,
        },
    }


def cleanup_task_context(messages, task_name="", user_id="default", session_id="default", max_summary_items=None):
    """统一上下文清理：切除历史任务残留 + 注入已完成步骤摘要 + 历史警告"""
    if len(messages) <= 10:
        return messages
    # #166 摘要注入条数限制：优先调用方显式传入，否则读 V9 routing config summary_layer.max_steps，默认 5
    if max_summary_items is None:
        try:
            import yaml as _yaml

            _p = Path("config/v9/message_routing.yaml")
            if _p.exists():
                with open(_p, "r", encoding="utf-8") as _f:
                    _cfg = _yaml.safe_load(_f) or {}
                max_summary_items = int(_cfg.get("summary_layer", {}).get("max_steps") or 5)
            else:
                max_summary_items = 5
        except Exception:
            max_summary_items = 5
    max_summary_items = max(1, max_summary_items)
    # 1. 任务边界切分：找当前任务的起点
    current_task_start = None
    for i in range(len(messages) - 1, -1, -1):
        m = messages[i]
        if m.get("role") == "user" and len(m.get("content", "")) > 20:
            _task_kw = ["修改", "创建", "添加", "修复", "实现", "任务", "验证", "查询", "发布"]
            if any(kw in m.get("content", "") for kw in _task_kw):
                current_task_start = i
                break
    if current_task_start is not None and current_task_start > 1:
        cleaned = [m for m in messages if m.get("role") == "system"]
        cleaned += messages[current_task_start:]
        if len(cleaned) < len(messages) * 0.7:
            cleaned.append({"role": "system", "content": f"[系统] 已清除 {len(messages) - len(cleaned)} 条历史任务残留。"})
        messages = cleaned
    # 2. 已完成步骤摘要 + 历史警告注入
    if task_name:
        try:
            import psycopg2

            from core.lib.code_entity_extractor import extractor

            conn = psycopg2.connect(extractor.db_url)
            cur = conn.cursor()
            cur.execute(
                "SELECT step_number, tool_name, file_path, status FROM task_progress WHERE task_name=%s AND status='completed' AND (tool_name LIKE '%write%' OR tool_name LIKE '%exec%' OR file_path != '') ORDER BY step_number",
                (task_name,),
            )
            completed = [f"步骤{r[0]}: {r[1]} → {r[2]}" for r in cur.fetchall()]
            if completed:
                messages.insert(
                    1, {"role": "system", "content": "[已完成步骤]\n" + "\n".join(completed[:max_summary_items])}
                )
            cur.execute(
                "SELECT signature FROM code_entities WHERE entity_type='system_hypothesis' ORDER BY created_at DESC LIMIT 3"
            )
            warnings = []
            for r in cur.fetchall():
                try:
                    sig = json.loads(r[0])
                    if sig.get("inefficiency_rate", 0) > 0.3:
                        warnings.append(f"⚠ {sig.get('problem_type', '')}: {sig.get('insight', '')}")
                except Exception:
                    pass
            if warnings:
                messages.insert(1, {"role": "system", "content": "[历史警告]\n" + "\n".join(warnings)})
            cur.close()
            conn.close()
        except Exception:
            pass
    return messages


def inject_related_context(task_name, current_step_keywords, max_inject=3, step_number=None, relevance_threshold=0.3):
    """过滤网关联度匹配：摘要 ↔ 全文精准关联。

    1. 提取当前步骤的关键词（current_step_keywords）
    2. 从 steps_summary 查询前面步骤的摘要（step_number 之前；未指定则查全部）
    3. 按 SAG 遍历距离计算关联度评分：
       relevance = 0.5 * 距离分(1/(1+depth)) + 0.3 * 边权重分 + 0.2 * 关键词全文命中分
    4. 只注入关联度 > relevance_threshold 的内容
    5. 返回的上下文附带 relevance 评分，供 Agent 判断优先级
    6. 返回值改为 (context_text, edge_keys) 元组：
       context_text 为格式化上下文文本；
       edge_keys 为 [(source_name, target_name, edge_type), ...] 使用边列表，
       供调用方调 searcher.record_edge_feedback 标记使用反馈。
    """
    import psycopg2
    import psycopg2.extras

    from core.lib.code_entity_extractor import searcher

    # --- Step 1: 从 steps_summary 查询（前面步骤的）摘要 ---
    try:
        conn = psycopg2.connect(searcher.db_url)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if step_number is not None:
            cur.execute(
                "SELECT step_number, summary_json FROM steps_summary "
                "WHERE task_name=%s AND step_number < %s ORDER BY step_number",
                (task_name, step_number),
            )
        else:
            cur.execute(
                "SELECT step_number, summary_json FROM steps_summary WHERE task_name=%s ORDER BY step_number",
                (task_name,),
            )
        steps = cur.fetchall()
        cur.close()
        conn.close()
    except Exception:
        return "", []

    if not steps:
        return "", []

    # --- Step 2: 提取当前步骤关键词（归一化去重）---
    keywords = []
    for kw in current_step_keywords or []:
        k = str(kw).strip().lower()
        if k and k not in keywords:
            keywords.append(k)

    # 从摘要中提取当前任务实体名（作为图遍历起点）
    entity_name = None
    for step in steps:
        summary = step.get("summary_json", {})
        if isinstance(summary, str):
            try:
                summary = json.loads(summary)
            except Exception:
                summary = {}
        if isinstance(summary, dict):
            for key in ("entity_name", "target", "file", "modified", "name", "subject"):
                val = summary.get(key)
                if val and isinstance(val, str) and len(val) > 2:
                    entity_name = val
                    break
        if entity_name:
            break

    if not entity_name:
        entity_name = task_name
    if not entity_name and keywords:
        entity_name = keywords[0]

    # --- Step 3: 按 SAG 遍历距离计算关联度评分 ---
    # 3a. 沿 code_edges BFS 图遍历，记录 (实体, 深度, 累计权重, 签名, 文件)
    graph_nodes = {}  # entity_name -> {depth, acc_weight, entity_type, signature, file_path}
    try:
        _gconn = psycopg2.connect(searcher.db_url)
        _gcur = _gconn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        visited = set()
        queue = [(entity_name, 0, 1.0)]
        visited.add(entity_name)
        while queue:
            queue.sort(key=lambda x: -x[2])
            current, depth, acc_weight = queue.pop(0)
            if depth > 3:
                break

            if current != entity_name and current not in graph_nodes:
                _gcur.execute(
                    "SELECT entity_name, entity_type, signature, file_path FROM code_entities "
                    "WHERE entity_name = %s AND project_id = 'default' LIMIT 1",
                    (current,),
                )
                ent = _gcur.fetchone()
                graph_nodes[current] = {
                    "depth": depth,
                    "acc_weight": acc_weight,
                    "entity_type": ent["entity_type"] if ent else "",
                    "signature": ent["signature"] if ent else "",
                    "file_path": ent["file_path"] if ent else "",
                }

            if depth < 3:
                _gcur.execute(
                    "SELECT target_name, weight FROM code_edges " "WHERE source_name = %s AND project_id = 'default'",
                    (current,),
                )
                for row in _gcur.fetchall():
                    tgt = row["target_name"]
                    w = row.get("weight", 1.0) or 1.0
                    if tgt and tgt not in visited:
                        visited.add(tgt)
                        queue.append((tgt, depth + 1, acc_weight * w))
                _gcur.execute(
                    "SELECT source_name, weight FROM code_edges " "WHERE target_name = %s AND project_id = 'default'",
                    (current,),
                )
                for row in _gcur.fetchall():
                    src = row["source_name"]
                    w = row.get("weight", 1.0) or 1.0
                    if src and src not in visited:
                        visited.add(src)
                        queue.append((src, depth + 1, acc_weight * w))
        _gcur.close()
        _gconn.close()
    except Exception:
        pass

    # 3b. 摘要全文序列化，用于关键词全文精准匹配
    step_summaries = []
    for step in steps:
        summary = step.get("summary_json", {})
        if isinstance(summary, str):
            try:
                summary = json.loads(summary)
            except Exception:
                summary = {}
        step_summaries.append(
            {
                "step_number": step["step_number"],
                "summary": summary,
                "text": json.dumps(summary, ensure_ascii=False).lower(),
            }
        )

    # 3c. 关键词全文命中率
    def _kw_score(text):
        if not keywords:
            return 0.0
        hits = sum(1 for kw in keywords if kw in text)
        return hits / len(keywords)

    # 候选 1: 图遍历实体（按 SAG 距离 + 边权重 + 关键词命中综合评分）
    candidates = []
    for en, info in graph_nodes.items():
        depth = info["depth"]
        depth_score = 1.0 / (1.0 + depth)  # 距离越近分越高
        weight_score = min(1.0, info["acc_weight"] / 5.0)
        text = " ".join([info["signature"] or "", en or "", info["file_path"] or ""]).lower()
        kw_score = _kw_score(text)
        relevance = round(0.5 * depth_score + 0.3 * weight_score + 0.2 * kw_score, 4)
        candidates.append(
            {
                "step_number": 0,
                "edge_id": None,
                "weight": info["acc_weight"],
                "summary": {
                    "entity_name": en,
                    "entity_type": info["entity_type"],
                    "signature": info["signature"],
                    "file_path": info["file_path"],
                },
                "relevance": relevance,
                "sag_distance": depth,
            }
        )

    # 候选 2: 步骤摘要（全文关键词命中率即关联度）
    for s in step_summaries:
        kw_score = _kw_score(s["text"])
        if kw_score > 0:
            candidates.append(
                {
                    "step_number": s["step_number"],
                    "edge_id": None,
                    "weight": 1.0,
                    "summary": s["summary"],
                    "relevance": round(kw_score, 4),
                    "sag_distance": 0,
                }
            )

    # --- Step 4: 只注入关联度 > 阈值的内容 ---
    filtered = [c for c in candidates if c["relevance"] > relevance_threshold]

    # --- Step 5: 按关联度降序返回，附带 relevance 评分供 Agent 判断优先级 ---
    filtered.sort(key=lambda x: x["relevance"], reverse=True)
    top = filtered[:max_inject]

    # --- Step 6: 格式化上下文文本 + 提取使用边（供调用方 record_edge_feedback）---
    lines = []
    for i, item in enumerate(top, 1):
        rel = item.get("relevance", 0)
        if item.get("step_number"):
            summary_text = json.dumps(item.get("summary", {}), ensure_ascii=False)
            lines.append(f"[{i}] 步骤 {item.get('step_number')} 摘要 (relevance={rel}): {summary_text[:600]}")
        else:
            _sum = item.get("summary", {}) or {}
            lines.append(
                f"[{i}] 实体 {_sum.get('entity_name')} ({_sum.get('entity_type')}) (relevance={rel}): "
                f"{_sum.get('signature') or ''} @ {_sum.get('file_path')}"
            )

    edge_keys = []
    if entity_name:
        _names = []
        for _it in top:
            _s = _it.get("summary") or {}
            _en = _s.get("entity_name")
            if _en and _en not in _names:
                _names.append(_en)
        if _names:
            try:
                _ec = psycopg2.connect(searcher.db_url)
                _ecur = _ec.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                _ph = ",".join(["%s"] * len(_names))
                _ecur.execute(
                    "SELECT source_name, target_name, edge_type FROM code_edges "
                    "WHERE project_id = 'default' "
                    f"AND ((source_name = %s AND target_name IN ({_ph})) "
                    f"OR (target_name = %s AND source_name IN ({_ph})))",
                    [entity_name] + _names + [entity_name] + _names,
                )
                for _row in _ecur.fetchall():
                    edge_keys.append((_row["source_name"], _row["target_name"], _row["edge_type"]))
                _ecur.close()
                _ec.close()
            except Exception:
                pass
    # 去重（保持顺序）
    _seen = set()
    edge_keys = [k for k in edge_keys if not (k in _seen or _seen.add(k))]

    return "\n".join(lines), edge_keys


def retrieve_step_fulltext(task_name, keywords, max_inject=3):
    """全文检索步骤上下文：调 extractor.query_fulltext_by_keywords，按关联度取前 max_inject 条，格式化上下文。

    返回格式：
      步骤 N 摘要 (relevance=0.67): <摘要全文前 600 字>
      实体 xxx (context_summary) (relevance=0.5): <签名> @ <file_path>
    无命中时返回空字符串。
    """
    from core.lib.code_entity_extractor import searcher

    try:
        results = searcher.query_fulltext_by_keywords(keywords or [], task_name)
    except Exception as e:
        print(f"[retrieve_step_fulltext] 失败: {e}")
        return ""
    if not results:
        return ""

    lines = []
    for i, item in enumerate(results[:max_inject], 1):
        rel = item.get("relevance", 0)
        if item.get("source") == "steps_summary":
            summary_text = json.dumps(item.get("summary", {}), ensure_ascii=False)
            lines.append(f"[{i}] 步骤 {item.get('step_number')} 摘要 (relevance={rel}): {summary_text[:600]}")
        else:
            lines.append(
                f"[{i}] 实体 {item.get('entity_name')} ({item.get('entity_type')}) (relevance={rel}): "
                f"{item.get('signature') or ''} @ {item.get('file_path')}"
            )
    return "\n".join(lines)


def recap_checkpoint(task_name: str, step_number: int) -> str:
    # 每步执行前，从 steps_summary 获取前面步骤摘要，生成当前目标复述文本
    # 防止长任务中注意力漂移

    import psycopg2

    from core.lib.code_entity_extractor import searcher

    try:
        conn = psycopg2.connect(searcher.db_url)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT step_number, summary_json, tool_name, status FROM steps_summary WHERE task_name=%s AND step_number < %s ORDER BY step_number",
            (task_name, step_number),
        )
        steps = cur.fetchall()
        steps = _filter_redundant_steps(steps, threshold=0.8)
        cur.close()
        conn.close()
    except Exception:
        return ""

    if not steps:
        return f"[目标复述] 当前为任务「{task_name}」的首个步骤（#{step_number}），尚无已完成步骤。"

    recap_parts = []
    for step in steps:
        summary = step.get("summary_json", {})
        if isinstance(summary, str):
            try:
                summary = json.loads(summary)
            except Exception:
                summary = {}
        step_num = step["step_number"]
        tool = step.get("tool_name", "?")
        status = step.get("status", "?")
        summary_text = ""
        if isinstance(summary, dict):
            summary_text = summary.get("summary", "") or summary.get("goal", "") or str(summary)[:200]
        else:
            summary_text = str(summary)[:200]
        recap_parts.append(f"  步骤{step_num}[{tool}]({status}): {summary_text[:150]}")

    recap = f"[目标复述] 任务「{task_name}」当前步骤 #{step_number}，已完成 {len(steps)} 步：\n" + "\n".join(recap_parts)
    return recap


def preserve_error_context(step_context: dict, task_name: str, step_number: int) -> bool:
    # 失败步骤的上下文不入摘要，但保留到 code_entities（entity_type='error_context'）
    # 供后续步骤和元认知学习使用

    import psycopg2

    from core.lib.code_entity_extractor import extractor

    try:
        conn = psycopg2.connect(extractor.db_url)
        cur = conn.cursor()
        error_info = {
            "step_number": step_number,
            "tool_name": step_context.get("tool_name", ""),
            "file_path": step_context.get("file_path", ""),
            "error": step_context.get("error", ""),
            "input_summary": step_context.get("input_summary", ""),
            "timestamp": datetime.now().isoformat(),
        }
        entity_name = f"error_{task_name}_step_{step_number}"
        file_path = "session/error_context"
        signature = json.dumps(error_info, ensure_ascii=False)
        cur.execute(
            "INSERT INTO code_entities (entity_type, entity_name, file_path, signature, created_at) VALUES (%s, %s, %s, %s, %s)",
            ("error_context", entity_name, file_path, signature, datetime.now()),
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception:
        return False


# ========== 文件系统外部记忆：遮蔽而非移除 ==========


def _archive_compressed_messages(old_messages, session_id, step_number):
    """将被压缩的旧消息写入外部存档文件，返回存档路径。
    实现"遮蔽而非移除"：被压缩的消息不删除，移到外部文件，
    Agent 可通过路径引用恢复（Manus 经验——可恢复不可逆）。
    """
    if not old_messages:
        return ""
    archive_dir = Path("data/v8/context_archive")
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"{session_id}_step{step_number}.json"
    archive_data = {
        "session_id": session_id,
        "step_number": step_number,
        "timestamp": datetime.utcnow().isoformat(),
        "total_messages": len(old_messages),
        "archived_messages": old_messages,
    }
    try:
        with open(archive_path, "w", encoding="utf-8") as f:
            json.dump(archive_data, f, ensure_ascii=False, indent=2)
        return str(archive_path)
    except Exception:
        return ""


def restore_context_from_archive(archive_path):
    """从外部存档文件恢复上下文消息，供 RETRIEVING 阶段使用。
    路径格式: data/v8/context_archive/{session_id}_step{N}.json
    """
    path = Path(archive_path)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("archived_messages", [])
    except Exception:
        return None


def _compress_messages(messages, user_id, session_id="default", keep=30, step_number=0):
    if len(messages) <= keep:
        return messages
    from core.lib.context_manager import get_context

    ctx = get_context(user_id)
    if not hasattr(ctx, "_last_session_id") or ctx._last_session_id != session_id:
        ctx.clear()
        ctx._last_session_id = session_id
    system_msg = messages[0] if messages[0]["role"] == "system" else None
    # 保护任务目标：始终保留第一条 user 消息
    _first_user = None
    for _m in messages:
        if _m["role"] == "user":
            _first_user = _m
            break
    recent = messages[-keep:]
    # === 修复 tool 消息配对丢失：recent 首条为 tool 时找回对应 assistant 消息 ===
    if recent and recent[0].get("role") == "tool":
        _tool_call_id = recent[0].get("tool_call_id")
        _matched = None
        for _m in messages:
            if _m.get("role") == "assistant" and _m.get("tool_calls"):
                if any(isinstance(_tc, dict) and _tc.get("id") == _tool_call_id for _tc in _m["tool_calls"]):
                    _matched = _m
                    break
        if _matched is None:
            recent.pop(0)
        elif _matched not in recent:
            recent.insert(0, _matched)
    old_messages = messages[1:-6] if system_msg else messages[:-6]
    # === 存档被压缩的消息到外部文件（遮蔽而非移除）===
    _archive_path = _archive_compressed_messages(old_messages, session_id, step_number) if old_messages else ""
    summary = ctx.inject() or ""
    compressed = []
    if system_msg:
        compressed.append(system_msg)
    if summary:
        compressed.append(
            {"role": "system", "content": f"【历史摘要】{summary}" + (f" 【存档:{_archive_path}】" if _archive_path else "")}
        )
    if _first_user and _first_user not in recent:
        compressed.append({"role": "system", "content": f"【任务目标】{_first_user['content'][:500]}"})
    compressed.extend(recent)
    return compressed


# ========== 上下文温度监控：步骤去重与合并 ==========


def summary_overlap_rate(s1: dict, s2: dict) -> float:
    """计算两个步骤摘要的重叠率（0.0 ~ 1.0），用于上下文温度监控"""
    import json as _json

    text1 = _json.dumps(s1.get("summary_json", {}), ensure_ascii=False)
    text2 = _json.dumps(s2.get("summary_json", {}), ensure_ascii=False)
    if not text1 or not text2:
        return 0.0
    set1 = set(text1.split())
    set2 = set(text2.split())
    if not set1 or not set2:
        return 0.0
    intersection = set1 & set2
    union = set1 | set2
    return len(intersection) / len(union)


def _filter_redundant_steps(steps: list, threshold: float = 0.8) -> list:
    """过滤掉与上一步摘要重叠率超过 threshold 的冗余步骤

    用于上下文温度监控：当相邻步骤的摘要内容高度重复时，
    保留前者，丢弃后者，防止上下文被冗余信息膨胀。
    """
    if not steps:
        return steps
    filtered = [steps[0]]
    for step in steps[1:]:
        overlap = summary_overlap_rate(filtered[-1], step)
        if overlap < threshold:
            filtered.append(step)
        else:
            import logging as _logging

            _logging.info(
                f"[CONTEXT_TEMP] 过滤冗余步骤 #{step.get('step_number', '?')}" f"（与上一步重叠率 {overlap:.2f} >= {threshold}）"
            )
    return filtered


def _merge_steps(steps: list, threshold: float = 0.8) -> list:
    """合并重叠率高的相邻步骤（保留前者，合并摘要内容到前者）

    比 _filter_redundant_steps 更温和：不直接丢弃，
    而是将后一步的摘要并入前一步的 summary_json 中，
    保留信息量、压缩格式。
    """
    if not steps:
        return steps
    merged = [dict(steps[0])]
    for step in steps[1:]:
        overlap = summary_overlap_rate(merged[-1], step)
        if overlap >= threshold:
            prev = merged[-1]
            prev_summary = prev.get("summary_json", {})
            cur_summary = step.get("summary_json", {})
            if isinstance(prev_summary, str):
                try:
                    prev_summary = json.loads(prev_summary)
                except Exception:
                    prev_summary = {}
            if isinstance(cur_summary, str):
                try:
                    cur_summary = json.loads(cur_summary)
                except Exception:
                    cur_summary = {}
            if isinstance(prev_summary, dict) and isinstance(cur_summary, dict):
                merged_steps = prev_summary.get("_merged_from", [prev["step_number"]])
                merged_steps.append(step["step_number"])
                prev_summary["_merged_from"] = merged_steps
                ps = prev_summary.get("summary", "")
                cs = cur_summary.get("summary", "")
                if ps and cs:
                    prev_summary["summary"] = ps + " | " + cs
                elif cs:
                    prev_summary["summary"] = cs
            prev["summary_json"] = prev_summary
            import logging as _logging

            _logging.info(
                f"[CONTEXT_TEMP] 合并步骤 #{prev['step_number']} <- #{step['step_number']}"
                f"（重叠率 {overlap:.2f} >= {threshold}）"
            )
        else:
            merged.append(dict(step))
    return merged


# =========================================================================
# 工具路由：call_api / notify_boss（追加于 _merge_steps 之后）
# =========================================================================


def _handle_call_api(params):
    # 实际发 HTTPS 请求，返回响应。
    # 支持 url/method/headers/data(dict 自动 JSON 序列化)/timeout。
    # 使用标准库 urllib.request（无第三方依赖）。
    # 返回 {success, status, body, json?}；异常捕获返回 {success: False, error}。
    import json as _json
    import urllib.error as _urllib_error
    import urllib.request as _urllib_request

    params = params or {}
    url = params.get("url")
    if not url:
        return {"success": False, "error": "missing required param: url"}
    method = str(params.get("method") or "GET").upper()
    headers = dict(params.get("headers") or {})
    timeout = float(params.get("timeout") or 15)
    data = params.get("data")

    body = None
    if data is not None:
        if isinstance(data, (dict, list)):
            body = _json.dumps(data).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")
        elif isinstance(data, str):
            body = data.encode("utf-8")
        else:
            body = bytes(data)

    req = _urllib_request.Request(url, data=body, headers=headers, method=method)
    try:
        with _urllib_request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            status = resp.status if hasattr(resp, "status") else resp.getcode()
            text = raw.decode("utf-8", errors="replace")
    except _urllib_error.HTTPError as exc:
        raw = exc.read()
        status = exc.code
        text = raw.decode("utf-8", errors="replace")
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}

    result = {"success": status < 400, "status": status, "body": text}
    try:
        result["json"] = _json.loads(text)
    except Exception:
        pass
    return result


def _handle_notify_boss(params):
    # 追加通知到 data/v8/notifications.json。
    # 自动建目录、保留最近 200 条，生成 id/ts/time 字段。
    # 返回 {success, id, count, path}。
    import json as _json
    import os as _os
    import time as _time
    import uuid as _uuid

    params = params or {}
    path = _os.path.join("data", "v8", "notifications.json")
    _os.makedirs(_os.path.dirname(path), exist_ok=True)

    now = _time.time()
    record = {
        "id": _uuid.uuid4().hex[:12],
        "ts": now,
        "time": _time.strftime("%Y-%m-%d %H:%M:%S", _time.localtime(now)),
        "message": params.get("message", ""),
        "level": params.get("level", "info"),
        "extra": params.get("extra") or {},
    }

    notifications = []
    if _os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                loaded = _json.load(fh)
            if isinstance(loaded, list):
                notifications = loaded
        except Exception:
            notifications = []

    notifications.append(record)
    notifications = notifications[-200:]

    with open(path, "w", encoding="utf-8") as fh:
        _json.dump(notifications, fh, ensure_ascii=False, indent=2)

    return {
        "success": True,
        "id": record["id"],
        "count": len(notifications),
        "path": path,
    }


def _handle_obsidian_knowledge(params, user_id="", session_id=""):
    """S4: obsidian_knowledge 统一 handler(由 tool_router elif 迁移; 插件单轨经 _TOOL_REGISTRY 调用)。"""
    try:
        from core.gateway.precision_inject import append_pitfall as _ap
        from core.gateway.precision_inject import list_knowledge_files as _lk
        from core.gateway.precision_inject import read_knowledge_file as _rk
        from core.gateway.precision_inject import search_vault as _sv
        from core.gateway.precision_inject import sync_knowledge_to_sandbox as _sync_kb
        from core.gateway.precision_inject import update_sop as _us

        _act = params.get("action")

        # #166 补全(2026-09-06): vault 写类 action 计入会话写入追踪器 —
        # 之前只有 write_file/edit_file/execute_command(sandbox 写)更新 _session_write_tracker,
        # obsidian_knowledge 写(write_draft/write_note/update_sop/append_pitfall)不进 tracker →
        # 「改 vault 草稿」任务 3 步(搜到→说要读→✅完成)被放行, 草稿实际未改(假完成)。
        def _mark_vault_write(_wp, _action=""):
            """vault 写成功后计入 tracker: vault_write_count + files_written。
            与 sandbox_write/execute_command 的 tracker 同构, 供假完成判定识别真实产出。

            2026-09-13 修(bug #6 写后读缓存不失效):
            此前只有 sandbox_write/sandbox_ops 会调 _invalidate_read_content_cache,
            **vault 写不调** → 而 obsidian_knowledge 同时被算作「读类」进了 _tool_exec_cache,
            且 _tool_stat_sig 不认它(返回 None, 永不做 mtime 校验)
            → vault 读缓存**整会话永不失效**: 写完再读, 拿到的是写前快照。
            实测后果: PA 追加完 P11–P13 后连续 3 次回读都是追加前的 4362 字符,
            只能诚实报告「不能作为已就位的证据」—— 即 agent 无法自证交付。
            这里写成功即失效该 session 读缓存(清整个 session 是既有语义, 保守防漏)。"""
            try:
                from core.gateway.shared_state import _invalidate_read_content_cache as _inv_vw

                _inv_vw(session_id)
            except Exception:
                pass
            try:
                from core.gateway.shared_state import _session_write_tracker as _trk_s
                from core.gateway.shared_state import _tracker_setdefault as _tsd

                _tk = _tsd(
                    _trk_s,
                    session_id,
                    lambda: {
                        "write_count": 0,
                        "execute_write_count": 0,
                        "vault_write_count": 0,
                        "files_written": [],
                        "_seen": set(),
                    },
                )
                _tk.setdefault("_seen", set())
                _tk["vault_write_count"] = _tk.get("vault_write_count", 0) + 1
                _tk["write_count"] = _tk.get("write_count", 0) + 1
                _fp = str(_wp or "")
                if _fp and _fp not in _tk["_seen"]:
                    _tk["_seen"].add(_fp)
                    _tk.setdefault("files_written", []).append(_fp)
            except Exception:
                pass
            return True

        if _act == "list":
            return {"success": True, "files": _lk()}
        if _act == "sync":
            try:
                from core.lib.gateway_helpers import _get_sandbox_base as _gsb_sync2

                _sb2 = _gsb_sync2(user_id, session_id)
                return {"success": True, "sync": _sync_kb(_sb2)}
            except Exception as _se2:
                return {"success": False, "error": "同步失败: %s" % _se2}
        if _act == "read":
            _d = _rk(params.get("sop_key"))
            if _d is None:
                return {
                    "success": False,
                    "error": "未知知识键或 vault 未启用。可选固定键: 平台发布工作流/番茄推广SOP/视频制作SOP/避坑清单; 或用 vault 相对路径(如 微信公众号/公众号.md、Clippings/xxx.md)",
                }
            # ⑪(2026-09-13) 路径解析到了但文件不存在 → 明确失败。
            # 旧行为返回 {"success": True, "exists": False, "content": ""} → "没读到"被伪装成
            # "读到了空文件", Agent 无法区分(掩盖型失败: 以为查过 SOP 其实什么也没读到)。
            if _d.get("exists") is False:
                return {
                    "success": False,
                    "exists": False,
                    "path": _d.get("path", ""),
                    "error": "知识文件不存在: %s（用 obsidian_knowledge action=list 查看 vault 里可用的文件）" % _d.get("path", ""),
                }
            _d["success"] = True
            return _d
        if _act == "search":
            _q = str(params.get("query") or "").strip()
            if not _q:
                return {"success": False, "error": "search 需要 query"}
            return {"success": True, "results": _sv(_q, limit=int(params.get("limit") or 3))}
        if _act == "update_sop":
            _p = _us(params.get("sop_key"), params.get("section_title"), params.get("content"))
            if _p:
                _mark_vault_write(_p, _act)
                return {"success": True, "path": str(_p)}
            return {"success": False, "error": "SOP 更新失败(检查 sop_key/section_title/content 或 vault 配置)"}
        if _act == "append_pitfall":
            _p = _ap(str(params.get("pitfall") or ""))
            if _p:
                _mark_vault_write(_p, _act)
                return {"success": True, "path": str(_p)}
            return {"success": False, "error": "踩坑追加失败(检查 pitfall 或 vault 配置)"}
        if _act == "write_draft":
            from core.plugins.draft_box import get_draft_plugin as _gdp

            _pl = _gdp(str(params.get("platform") or ""))
            if _pl is None:
                return {"success": False, "error": "未知平台: " + str(params.get("platform")) + ", 可选: 公众号/小红书/知乎/B站/抖音"}
            _media = params.get("media_files") or []
            if isinstance(_media, str):
                _media = [_media]
            _r = _pl.write_draft(
                str(params.get("title") or ""),
                str(params.get("content") or ""),
                media_files=_media,
                summary=str(params.get("summary") or ""),
                tags=params.get("tags") or [],
                extra={"分区": params.get("分区") or "知识"},
            )
            _r["success"] = bool(_r.get("success"))
            if _r.get("success"):
                _mark_vault_write(str(_r.get("path") or _r.get("draft_path") or ""), _act)
            return _r
        if _act == "update_draft":
            # 2026-09-06: 就地更新已有草稿(write_draft 是新建语义, 改旧草稿必须用 update_draft)
            from core.plugins.draft_box import get_draft_plugin as _gdp_ud

            _pl_ud = _gdp_ud(str(params.get("platform") or ""))
            if _pl_ud is None:
                return {"success": False, "error": "未知平台: " + str(params.get("platform")) + ", 可选: 公众号/小红书/知乎/B站/抖音"}
            _ud_path = str(params.get("draft_path") or params.get("path") or "").strip()
            _ud_content = str(params.get("content") or "").strip()
            if not _ud_path or not _ud_content:
                return {
                    "success": False,
                    "error": "update_draft 需要 draft_path(目标草稿路径)和 content(修改后全文, markdown 正文, 不带 yaml frontmatter)",
                }
            _r_ud = _pl_ud.update_draft(_ud_path, _ud_content, title=str(params.get("title") or "").strip())
            _r_ud["success"] = bool(_r_ud.get("success"))
            if _r_ud.get("success"):
                _mark_vault_write(str(_r_ud.get("path") or ""), _act)
            return _r_ud
        if _act == "archive_media":
            # 2026-09-07: 媒体归档 — Agent 归档视频/图片/音频到 草稿箱/{platform}/assets/
            # (Agent 不知道 vault 物理路径, 归档一律走这里, 不读源码找路径)
            from core.plugins.draft_box import get_draft_plugin as _gdp_am

            _pl_am = _gdp_am(str(params.get("platform") or ""))
            if _pl_am is None:
                return {"success": False, "error": "未知平台: " + str(params.get("platform")) + ", 可选: 公众号/小红书/知乎/B站/抖音"}
            _am_files = params.get("files") or params.get("file") or []
            if isinstance(_am_files, str):
                _am_files = [_am_files]
            if not _am_files:
                return {"success": False, "error": "archive_media 需要 files(文件路径列表)或 file(单路径)"}
            _am_subdir = str(params.get("subdir") or "assets").strip() or "assets"
            # 2026-09-07 修复: files 相对路径须拼沙箱 base(Agent 传 data/videos/xxx.mp4 是相对沙箱,
            # 网关 cwd 是项目根, Path.cwd() 解析会错 → missing)。
            try:
                from core.lib.gateway_helpers import _get_sandbox_base as _gsb_am

                _sb_am = Path(_gsb_am(user_id, session_id)).resolve()
            except Exception:
                _sb_am = Path(".").resolve()
            _am_resolved = []
            for _amf in _am_files:
                _amfp = Path(str(_amf))
                if _amfp.is_absolute():
                    _am_resolved.append(str(_amfp))
                else:
                    _am_resolved.append(str(_sb_am / _amfp))
            _r_am = _pl_am.archive_media(_am_resolved, subdir=_am_subdir)
            _r_am["success"] = bool(_r_am.get("success"))
            if _r_am.get("success") and _r_am.get("archived"):
                _mark_vault_write(str(_r_am.get("dir_vault_rel") or ""), _act)
            return _r_am
        if _act == "mark_published":
            from core.plugins.draft_box import get_draft_plugin as _gdp2

            _pl2 = _gdp2(str(params.get("platform") or ""))
            if _pl2 is None:
                return {"success": False, "error": "未知平台: " + str(params.get("platform"))}
            return _pl2.mark_published(str(params.get("draft_path") or ""), str(params.get("post_url") or ""))
        if _act == "list_drafts":
            from core.plugins.draft_box import get_draft_plugin as _gdp3

            _pl3 = _gdp3(str(params.get("platform") or ""))
            if _pl3 is None:
                return {"success": False, "error": "未知平台: " + str(params.get("platform"))}
            return {"success": True, "drafts": _pl3.list_drafts(str(params.get("status") or "draft"))}
        if _act == "process_media":
            from core.plugins.media_processor import process_media as _pm

            _r = _pm(
                str(params.get("file_path") or ""),
                str(params.get("media_type") or "auto"),
                str(params.get("title") or ""),
            )
            _r["success"] = bool(_r.get("success"))
            return _r
        if _act == "process_youtube":
            from core.plugins.media_processor import process_youtube as _py

            _r = _py(
                str(params.get("source_url") or ""), str(params.get("note_path") or ""), str(params.get("title") or "")
            )
            _r["success"] = bool(_r.get("success"))
            return _r
        if _act == "write_note":
            from core.gateway.precision_inject import write_vault_note as _wvn

            _wn_title = str(params.get("title") or "").strip()
            _wn_content = str(params.get("content") or "").strip()
            if not _wn_title or not _wn_content:
                return {"success": False, "error": "write_note 需要 title 和 content(markdown 正文)"}
            _wn_append = bool(params.get("append") or False)
            _wn_p = _wvn(
                _wn_title,
                _wn_content,
                tags=params.get("tags") or [],
                folder=str(params.get("folder") or ""),
                append=_wn_append,
            )
            if _wn_p:
                import os as _os_wvn

                try:
                    _wn_stat = _os_wvn.stat(_wn_p)
                    with open(_wn_p, encoding="utf-8") as _wf_v:
                        _wn_text = _wf_v.read()
                    _wn_verify = {
                        "bytes": _wn_stat.st_size,
                        "lines": _wn_text.count(chr(10)) + (0 if _wn_text.endswith(chr(10)) else 1),
                        "head": _wn_text[:160],
                    }
                except Exception:
                    _wn_verify = {}
                _mark_vault_write(_wn_p, _act)
                return {
                    "success": True,
                    "path": str(_wn_p),
                    "verified": _wn_verify,
                    "hint": "技术/评估笔记已写入 vault; content 已自动清洗; 长文可分块 append=true 续写; 平台草稿请用 write_draft(platform=公众号/小红书/知乎/B站/抖音)",
                }
            return {"success": False, "error": "write_note 写入失败(vault 未启用、目录非法或内容清洗后为空(仅系统回声/截断残留))"}
        return {
            "success": False,
            "error": "未知 action: %s, 可选: list/read/search/update_sop/append_pitfall/write_draft/mark_published/list_drafts/process_media/process_youtube/write_note"
            % _act,
        }
    except Exception as _ke:
        return {"success": False, "error": "知识维护失败: %s" % _ke}


def _is_private_host(hostname: str) -> bool:
    # 判断主机名是否为 localhost / 内网 / 回环 / 链路本地地址。
    # 用于 browse_web 的安全限制，禁止访问内网资源。
    import ipaddress as _ipaddress
    import socket as _socket

    if not hostname:
        return True
    lowered = hostname.lower().rstrip(".")
    if lowered in ("localhost", "localhost.localdomain"):
        return True
    try:
        addr = _ipaddress.ip_address(lowered)
        return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_multicast
    except ValueError:
        pass
    # 域名：解析后检查任一 IP 是否命中内网/回环。
    # W2 修复(2026-08-30): 解析失败不再保守拒绝(返回 True 会把 DNS 临时故障/畸形 URL 误判为内网,
    # 日志: browse_web/fetch_web 反复 "localhost/内网地址不允许访问") — 返回 False 交由 HTTP 层超时/错误处理。
    try:
        infos = _socket.getaddrinfo(hostname, None)
    except Exception:
        return False
    for info in infos:
        ip = info[4][0]
        try:
            addr = _ipaddress.ip_address(ip)
            if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_multicast:
                return True
        except ValueError:
            continue
    return False


import html as _html_unescape_mod
import re as _re_html


def _html_to_text(html, limit=10000):
    """HTML → 纯文本(去 script/style/标签 + 反转义 + 压缩空白), 截断 limit。

    browse_web 返回给 Agent 的关键文本统一走此函数, 保证纯文本而非原始 HTML。
    """
    try:
        text = _re_html.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</(script|style|noscript)>", " ", html or "")
        text = _re_html.sub(r"<[^>]+>", " ", text)
        text = _html_unescape_mod.unescape(text)
        text = _re_html.sub(r"\s+", " ", text).strip()
        return text[:limit]
    except Exception:
        return str(html or "")[:limit]


def _refresh_project_structure(user_id, session_id):
    """扫描 session 沙箱根的项目结构, 更新 ContextManager 记忆(写工具后调用)。

    覆盖: 一级目录(非隐藏/非 goals/非 data/v8) + 一级文件(*.py/*.md/config 等)
    排除: .git/、goals/、data/v8/、内部状态文件 — 与文件中心口径一致。
    失败静默(记忆刷新不影响工具执行)。
    """
    try:
        from pathlib import Path as _PS

        from core.lib.context_manager import get_context

        _sb = _PS(_get_sandbox_base(user_id, session_id))
        _struct = {"dirs": [], "files": []}
        if _sb.exists():
            for _p in sorted(_sb.iterdir()):
                if _p.name.startswith("."):
                    continue
                if _p.name in ("goals",):
                    continue
                if _p.is_dir():
                    _struct["dirs"].append(_p.name)
                elif _p.is_file():
                    _struct["files"].append(_p.name)
        _ctx = get_context(user_id or "default")
        _ctx.update_project_structure(_struct)
        return _struct
    except Exception:
        return None


def _handle_browse_web(params):
    # 只读浏览网页：改为调用 WebCache.query()，复用本地缓存与 SAG 入库能力。
    # 先查 SAG/本地缓存，未命中才抓取并提取元数据（标题/路由/API 路径/关键文本）。
    # 仅允许 HTTPS，禁止 localhost/内网地址。不做任何业务写操作。
    import urllib.parse as _urllib_parse

    params = params or {}
    url = params.get("url")
    if not url:
        return {"success": False, "error": "missing required param: url"}
    url = str(url).strip()
    parsed = _urllib_parse.urlparse(url)
    if parsed.scheme != "https":
        return {"success": False, "error": "only https URLs are allowed"}
    if _is_private_host(parsed.hostname or ""):
        return {"success": False, "error": "localhost/内网地址不允许访问"}

    try:
        from core.lib.web_cache import WebCache

        cache = WebCache()
        result = cache.query(url)
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}

    metadata = result.get("metadata") or {}
    key_text = metadata.get("key_text", "") or ""
    # 纯文本化: 缓存/SAG 返回的 key_text 也可能是 HTML, 统一去标签(幂等)
    content = _html_to_text(key_text, limit=10000)
    return {
        "success": True,
        "source": result.get("source", "fetch"),
        "url": url,
        "title": metadata.get("title", ""),
        "routes": metadata.get("routes", []),
        "api_paths": metadata.get("api_paths", []),
        "content": content,
        "truncated": len(key_text) > 10000,
        "length": len(key_text),
        "save_path": metadata.get("save_path", ""),
    }


def _handle_playwright_browser(params):
    """Playwright 浏览器工具处理函数。

    支持操作（action）:
      - open:       打开 URL，返回页面标题与最终 URL
      - content:    获取页面正文文本（body inner_text，截断 10000 字符）
      - click:      用 CSS selector 点击元素
      - fill:       用 CSS selector 填写表单输入框
      - screenshot: 页面截图保存到 screenshot_path（默认 data/screenshots/）
    每次调用启动独立 headless Chromium；click/fill/screenshot/content
    可携带 url 参数在同一次调用内"先导航再操作"。仅允许 http/https
    公网地址，禁止 localhost/内网地址。
    """
    import os as _os

    params = params or {}
    action = (params.get("action") or "").strip()
    url = (params.get("url") or "").strip()
    selector = params.get("selector")
    text = params.get("text")
    shot_path = params.get("screenshot_path")
    try:
        wait_ms = int(params.get("wait_ms") or 0)
    except (TypeError, ValueError):
        wait_ms = 0

    valid_actions = {"open", "content", "click", "fill", "screenshot"}
    if action not in valid_actions:
        return {"success": False, "error": "unsupported action: %r, supported: %s" % (action, sorted(valid_actions))}
    if action == "open" and not url:
        return {"success": False, "error": "missing required param: url (action=open)"}
    if action in ("click", "fill") and not selector:
        return {"success": False, "error": "missing required param: selector (action=%s)" % action}
    if action == "fill" and text is None:
        return {"success": False, "error": "missing required param: text (action=fill)"}

    if url:
        import urllib.parse as _up

        parsed = _up.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return {"success": False, "error": "only http/https URLs are allowed"}
        if _is_private_host(parsed.hostname or ""):
            return {"success": False, "error": "localhost/内网地址不允许访问"}

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return {"success": False, "error": "playwright 未安装: %s" % exc}

    # 部署环境 chromium 缓存路径(可被 shell env 覆盖); 避免 "Executable doesn't exist" 类路径问题
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", playwright_browsers_path())

    try:
        from core.tools import browser_runtime as _brt  # 批197：唯一出口

        with _brt.browser_ctx() as browser:
            page = browser.new_page()
            try:
                if wait_ms > 0:
                    page.wait_for_timeout(wait_ms)
                if url:
                    # SPA 支持: load 后再等 JS 渲染(domcontentloaded 会拿到空壳/打包 JS)
                    try:
                        page.goto(url, wait_until="load", timeout=30000)
                    except Exception:
                        # load 超时(长轮询/持续连接)也继续: 页面主体可能已可用
                        pass
                    # React/Vue 首屏渲染: 额外等待让客户端 hydrate(幂等, 已等待过也最多 3s)
                    page.wait_for_timeout(2000)

                if action == "open":
                    return {"success": True, "action": action, "url": page.url, "title": page.title() or ""}

                if action == "content":
                    try:
                        text_content = page.inner_text("body")
                    except Exception:
                        text_content = ""
                    text_content = (text_content or "").strip()
                    _waited = 0
                    # SPA 空壳防护: inner_text 过短(<60)说明 JS 未渲染完, 等 2s 重试
                    while len(text_content) < 60 and _waited < 4:
                        page.wait_for_timeout(2000)
                        _waited += 2
                        try:
                            text_content = (page.inner_text("body") or "").strip()
                        except Exception:
                            break
                    _note = ""
                    if _waited > 0:
                        _note = f"（页面为动态渲染，已额外等待 {_waited} 秒）"
                    return {
                        "success": True,
                        "action": action,
                        "content": text_content[:10000],
                        "truncated": len(text_content) > 10000,
                        "url": page.url,
                        "wait_extra_s": _waited,
                        "note": _note,
                    }

                if action == "click":
                    page.click(selector, timeout=10000)
                    return {"success": True, "action": action, "selector": selector, "url": page.url}

                if action == "fill":
                    page.fill(selector, text)
                    return {"success": True, "action": action, "selector": selector, "filled": True, "url": page.url}

                if action == "screenshot":
                    if not shot_path:
                        _os.makedirs("data/screenshots", exist_ok=True)
                        shot_path = "data/screenshots/playwright_%d.png" % _os.getpid()
                    _os.makedirs(_os.path.dirname(shot_path) or ".", exist_ok=True)
                    page.screenshot(path=shot_path, full_page=True)
                    return {"success": True, "action": action, "path": shot_path, "url": page.url}

                return {"success": False, "error": "unsupported action: %s" % action}
            finally:
                browser.close()
    except Exception as exc:
        return {"success": False, "error": "%s: %s" % (type(exc).__name__, exc)}


def _handle_browser_hybrid(params):
    """browser_hybrid(Computer Use 混合方案, 2026-09-04): 委托实现模块。

    enumerate/click/fill/type/press/select_option/hover/observe/close;
    页面状态按 page_id 保留(TTL 10min); SSRF 校验在实现内(url http/https 公网)。
    """
    from core.tools.browser_hybrid_impl import handle as _hb_handle

    return _hb_handle(params or {})


def _handle_cu_learning(params):
    """cu_learning(P4 学习循环/SOP 生成器, 2026-09-04): 委托实现模块。

    start(记录可验证完成条件)/log_step(操作序列 jsonl + 重试/停止规则)/
    complete(证据门禁, 防假完成)/count/sop(生成 CU-SOP 并尽力写 vault ComputerUseSOPs/)。
    """
    from core.tools.cu_learning_impl import run_action

    return run_action(params or {})


def _handle_web_search(params):
    """搜索引擎查询(Bing RSS, 无需 key): 按标题/关键词找原文。

    W1 增强(2026-08-30): 支持 site 站点限定; 标题含 query 关键词的结果优先;
    空结果给出更具体建议(换标题短语/加 site)。解决 Google News 混淆 URL 死胡同:
    Agent 拿到 news.google.com/articles/CBM... 无法 fetch 原文(400/跨源), 用标题搜原文来源站。
    """
    import re as _re_ws
    import urllib.parse as _up_ws
    import urllib.request as _ur_ws

    params = params or {}
    query = str(params.get("query", "") or "").strip()
    if not query:
        return {"success": False, "error": "missing required param: query"}
    _site = str(params.get("site", "") or "").strip()
    _q_full = query
    if _site:
        _q_full = f"site:{_site} {query}"
    # Bing RSS 格式(实测): URL 直接可访问, 无 ck/a 跳转; 中文/英文都支持
    _url = "https://www.bing.com/search?q=" + _up_ws.quote(_q_full) + "&format=rss"
    _req = _ur_ws.Request(
        _url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
        },
    )
    try:
        with _ur_ws.urlopen(_req, timeout=20) as _resp:
            _html = _resp.read(300000).decode("utf-8", errors="ignore")
    except Exception as exc:
        return {"success": False, "error": f"search failed: {exc}"}

    # RSS: <item><title>..</title><link>..</link><description>..</description></item>
    results = []
    for _m in _re_ws.finditer(
        r"<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>.*?<description>(.*?)</description>", _html, _re_ws.S
    ):
        _title_t = _re_ws.sub(r"<[^>]+>", "", _m.group(1)).strip()
        _href = _m.group(2).strip()
        _snip_t = _re_ws.sub(r"<[^>]+>", "", _m.group(3) or "").strip()
        if _href and _title_t:
            results.append({"title": _title_t[:120], "url": _href, "snippet": _snip_t[:200]})
        if len(results) >= 8:
            break
    if not results:
        return {
            "success": False,
            "error": "no results (Bing RSS 可能反爬/索引差)。建议: 1) 用标题中的独特短语作 query "
            "(如 'Anthropic 被指控侵权训练 Claude') 2) 加 site 限定(如 site:sina.com.cn) "
            "3) 直接 browse_web 访问已知来源站。",
            "query": query,
        }
    return {"success": True, "query": query, "site": _site or None, "results": results}


# ========== V5 OS 路径认知修复：tool_schema_hint 注入 cwd ==========

_READONLY_TASK_TYPES = ("analysis", "readonly", "read-only", "analyze", "查询", "分析", "只读")


def build_tool_schema_hint(sandbox_dir=None, base_hint=None):
    """构建 tool_schema_hint 并注入当前工作目录，纠正 Agent 路径认知。

    - sandbox_dir: 沙箱/工作目录，缺省取 os.getcwd()
    - base_hint: 已有提示文本（可选），cwd 提示追加在其后

    追加内容: 当前工作目录(cwd)=<sandbox_dir>，所有文件操作请在 cwd 内使用相对路径，
    禁止使用 /home、/root 等绝对路径
    """
    import os as _os

    if sandbox_dir is None:
        sandbox_dir = _os.getcwd()
    cwd_hint = "当前工作目录(cwd)=%s，所有文件操作请在 cwd 内使用相对路径，" "禁止使用 /home、/root 等绝对路径" % sandbox_dir
    if base_hint:
        return "%s\n%s" % (base_hint, cwd_hint)
    return cwd_hint


def verify_node_result(task_type="", content="", target_keywords=None, git_changes=None):
    """节点验证器：按任务类型区分判定策略。

    - analysis/readonly 类任务：取消 git 变更硬门槛，改为校验回复内容包含目标关键词
      （无关键词要求时，回复内容非空即通过，不依赖 LLM 语义判定）。
    - 其他任务：保留 git 变更硬门槛——无代码变更直接失败，有变更时交由 LLM 语义判定。

    返回: {"ok": bool, "detail": str}；非 readonly 且未提供 git_changes 时返回
    {"ok": None, "require_git_change": True}，由调用方核对 git 变更。
    """
    task_type = (task_type or "").lower()
    content = content or ""
    is_readonly = any(t in task_type for t in _READONLY_TASK_TYPES)

    if is_readonly:
        kws = target_keywords or []
        if isinstance(kws, str):
            kws = [kws]
        kws = [k for k in kws if k]
        if kws:
            missing = [k for k in kws if k not in content]
            if missing:
                return {"ok": False, "detail": "readonly 任务回复缺少目标关键词: %s" % missing}
            return {"ok": True, "detail": "readonly 任务通过: 回复包含全部目标关键词 %s" % kws}
        if content.strip():
            return {"ok": True, "detail": "readonly 任务通过: 回复内容非空"}
        return {"ok": False, "detail": "readonly 任务失败: 回复内容为空"}

    if git_changes is None:
        return {"ok": None, "require_git_change": True, "detail": "非 readonly 任务需调用方核对 git 变更"}
    if not git_changes:
        return {"ok": False, "detail": "git 无代码文件变更，判定失败（不调用 LLM）"}
    return {"ok": None, "require_git_change": True, "detail": "git 存在 %d 个代码文件变更，交由 LLM 语义判定" % len(git_changes)}


# ========== V5 OS 路径认知修复（根因 3/4）：失败错误追加 cwd 提示 + 执行规则路径约束 ==========


def append_cwd_hint_on_error(error_msg="", sandbox_dir=None):
    """给 _atomic_write / mkdir 等文件操作失败的错误信息追加 cwd 提示。

    - sandbox_dir: 沙箱/工作目录，缺省取 os.getcwd()
    - error_msg: 原始错误信息（可为空字符串）

    返回: 追加后的错误信息；若 error_msg 已包含 cwd 提示则不重复追加。
    """
    import os as _os

    if sandbox_dir is None:
        sandbox_dir = _os.getcwd()
    cwd_hint = "当前工作目录是 %s，请使用相对路径，禁止使用 /home、/root" % sandbox_dir
    if not error_msg:
        return cwd_hint
    if cwd_hint in error_msg:
        return error_msg
    return "%s\n%s" % (error_msg, cwd_hint)


def build_path_retry_rule(sandbox_dir=None):
    """构建执行规则中的路径约束文本。

    - sandbox_dir: 沙箱/工作目录，缺省取 os.getcwd()

    返回: 完整路径约束规则文本，供执行规则注入。
    """
    import os as _os

    if sandbox_dir is None:
        sandbox_dir = _os.getcwd()
    return (
        "执行规则-路径约束：同类文件操作失败 ≥2 次时，必须检查路径是否在 cwd 内，"
        "切换为相对路径。当前 cwd=%s，所有文件操作请在 cwd 内使用相对路径，"
        "禁止使用 /home、/root 等绝对路径" % sandbox_dir
    )


def build_path_constraint_block(sandbox_dir=None, base_hint=None):
    """组合入口：一次性生成 cwd 提示 + 失败错误追加提示 + 执行规则路径约束。

    - sandbox_dir: 沙箱/工作目录，缺省取 os.getcwd()
    - base_hint: 已有提示文本（可选），路径约束块追加在其后

    返回: 完整路径约束提示文本。
    """
    import os as _os

    if sandbox_dir is None:
        sandbox_dir = _os.getcwd()
    block = "\n".join(
        [
            append_cwd_hint_on_error("", sandbox_dir),
            build_path_retry_rule(sandbox_dir),
        ]
    )
    if base_hint:
        return "%s\n%s" % (base_hint, block)
    return block
