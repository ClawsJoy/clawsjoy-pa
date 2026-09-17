"""OS 事件监控 — 从 agent_gateway_enhanced.py 抽取

每小时读取 OS 事件，触发元认知分析 + 花名册模型探活。
"""

import logging
import json
import time
from pathlib import Path


def _os_event_monitor():
    """每小时读取 OS 事件，触发元认知分析 + 花名册模型探活"""
    import time
    from core.lib.os_event_logger import read_recent_os_events
    from core.lib.metacognition import Metacognition
    from core.lib.v8.roster_engine import roster_engine

    meta = Metacognition("os_monitor")

    while True:
        # 花名册模型探活
        try:
            members = roster_engine.list_active("default")
            for m in members:
                model = m.get("model", "")
                if not model:
                    continue
                # 只探活 DeepSeek 云端模型，Ollama 本地模型跳过
                if "ollama" in model.lower() or "qwen" in model.lower():
                    continue
                # 发最小请求验证模型
                import requests as _req
                api_key = os.getenv("DEEPSEEK_API_KEY", "")
                if not api_key:
                    continue
                resp = _req.post(
                    "https://api.deepseek.com/chat/completions",
                    json={"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10,
                    proxies={"http": None, "https": None}
                )
                if resp.status_code != 200:
                    # 模型不可用，写入 os_events
                    from core.lib.os_event_logger import write_os_event
                    write_os_event(
                        event_type="probe",
                        operation="execute",
                        os_action="blocked",
                        reason="model_deprecated",
                        command=f"roster:{m.get('name', 'unknown')}",
                        detail={"model": model, "status": resp.status_code, "error": resp.text[:200]},
                        agent_name=m.get("name", "")
                    )
        except Exception:
            pass  # 探活失败不影响主流程

        # 讨论分支归档逻辑：加载配置，扫描 orchestrations.json 的讨论记录
        try:
            _audit_rules_path = Path("config/v8/audit_rules.yaml")
            _timeout_minutes = 30
            _ttl_hours = 72
            if _audit_rules_path.exists():
                _rules = yaml.safe_load(_audit_rules_path.read_text()) or {}
                _timeout_minutes = _rules.get("discussion", {}).get("timeout_minutes", 30)
                _ttl_hours = _rules.get("archive", {}).get("discussion_ttl_hours", 72)
            _orch_path = Path("data/v8/orchestrations.json")
            if _orch_path.exists():
                _orch = json.loads(_orch_path.read_text())
                _modified = False
                for _channel, _entry in _orch.items():
                    _discussion = _entry.get("_discussion", [])
                    if not _discussion:
                        continue
                    _last_msg = _discussion[-1]
                    _ts = _last_msg.get("timestamp", "")
                    if not _ts:
                        continue
                    _last_time = datetime.fromisoformat(_ts)
                    _elapsed_minutes = (datetime.now() - _last_time).total_seconds() / 60.0
                    if _elapsed_minutes > _timeout_minutes:
                        _entry["plan_status"] = "confirmed"
                        _entry["_discussion"] = []
                        _modified = True
                        from core.lib.os_event_logger import write_os_event
                        write_os_event(event_type="archive", operation="execute", os_action="blocked", reason="discussion_timeout", command=f"archive:{_channel}", detail={"channel": _channel, "elapsed_minutes": round(_elapsed_minutes, 1), "timeout_minutes": _timeout_minutes, "archived_at": datetime.now().isoformat()})
                        continue
                    _created_at_str = _entry.get("created_at", "")
                    if _created_at_str:
                        _created_time = datetime.fromisoformat(_created_at_str)
                        _age_hours = (datetime.now() - _created_time).total_seconds() / 3600.0
                        if _age_hours > _ttl_hours:
                            _entry["_discussion"] = []
                            _entry["plan_status"] = "timeout"
                            _modified = True
                            from core.lib.os_event_logger import write_os_event
                            write_os_event(event_type="archive", operation="execute", os_action="blocked", reason="discussion_ttl_expired", command=f"archive:{_channel}", detail={"channel": _channel, "age_hours": round(_age_hours, 1), "ttl_hours": _ttl_hours, "archived_at": datetime.now().isoformat()})
                if _modified:
                    _orch_path.write_text(json.dumps(_orch, ensure_ascii=False, indent=2))
        except Exception:
            pass

        time.sleep(3600)  # 每小时
        try:
            events = read_recent_os_events(max_lines=50)
            if events:
                meta.reflect(
                    user_input="[OS自动分析]",
                    response="[OS自动分析]",
                    os_events=events
                )
        except Exception:
            pass  # 监控自身的失败不影响主流程

import threading as _threading
_thread = _threading.Thread(target=_os_event_monitor, daemon=True)
_thread.start()

# ========== 核心入口 ==========
from core.agents.cortex import agent_cortex
from core.lib.llm_client import llm_client

logger = logging.getLogger(__name__)

# ========== 中间件 ==========
