#!/usr/bin/env python3
"""v8 记账钩子 — 集成 ledger + 适配器"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from core.lib.v8.roster_engine import roster_engine
from core.lib.v8.ledger import ledger
from core.lib.v8.adapters.factory import get_adapter


def check_token_budget(
    server_id: str,
    agent_name: Optional[str] = None,
    scope: str = "per_session",
) -> dict:
    """检查 token 预算是否已用尽

    读取 audit_rules.yaml 的 token_budget 配置，查询 ledger 累计 token，
    达到上限返回 blocked，未达到返回 allowed。
    Ollama 本地模型的 token 不计入预算消耗。

    Args:
        server_id: 服务器 ID
        agent_name: Agent 名称（per_session / per_channel 按 agent 维度检查时需要）
        scope: 预算范围 — "per_session" | "per_channel" | "per_day"

    Returns:
        {
            "status": "allowed" | "blocked",
            "used": int,          # 已消耗 token 数（不含 Ollama）
            "limit": int,         # 预算上限
            "remaining": int,     # 剩余可用
            "warning": bool,      # 是否接近上限（>= warn_at 阈值）
        }
    """
    # 1. 读取 audit_rules.yaml 配置
    config_path = Path("config/v8/audit_rules.yaml")
    if not config_path.exists():
        return {"status": "allowed", "used": 0, "limit": 0,
                "remaining": 0, "warning": False}

    with open(config_path) as f:
        config = yaml.safe_load(f)

    token_budget = config.get("token_budget", {})
    limit = token_budget.get(scope, 0)

    warn_at = token_budget.get("warn_at", 0.8)

    # 2. 查询 ledger 累计 token（跳过 Ollama 本地模型的消耗）
    used = 0

    def _is_ollama(e):
        """判断条目是否为 Ollama 本地模型调用"""
        return "ollama" in (e.get("model", "") or "").lower()

    if scope == "per_session":
        # 当月所有条目（get_billing 按本月过滤）
        billing = ledger.get_billing(server_id)
        entries = billing.get("entries", [])
        if agent_name:
            used = sum(e["tokens"] for e in entries
                       if e.get("agent") == agent_name and not _is_ollama(e))
        else:
            used = sum(e["tokens"] for e in entries if not _is_ollama(e))

    elif scope == "per_channel":
        billing = ledger.get_billing(server_id)
        by_agent = billing.get("by_agent", {})
        if agent_name:
            agent_data = by_agent.get(agent_name, {})
            used = agent_data.get("tokens", 0)
        else:
            used = sum(d["tokens"] for d in by_agent.values())

    else:  # per_day
        today = datetime.now().strftime("%Y-%m-%d")
        billing_file = ledger._billing_file(server_id)
        if billing_file.exists():
            with open(billing_file) as f:
                for line in f:
                    try:
                        e = json.loads(line)
                        if e["timestamp"].startswith(today):
                            if (agent_name is None or e.get("agent") == agent_name) and not _is_ollama(e):
                                used += e["tokens"]
                    except Exception:
                        pass

    remaining = limit - used

    if limit > 0 and used >= limit:
        return {"status": "blocked", "used": used, "limit": limit,
                "remaining": remaining, "warning": True}

    warning = (limit > 0 and used / limit >= warn_at)
    return {"status": "allowed", "used": used, "limit": limit,
            "remaining": remaining, "warning": warning}


def execute_with_ledger(server_id: str, agent_name: str, prompt: str,
                        system_prompt: str = "", history: list = None,
                        workspace: str = "/sandbox/default") -> dict:
    """
    统一执行入口：
    1. 查花名册 → 获取模型和 Key
    2. 获取适配器 → 执行
    3. 记账 + 记事
    """
    member = roster_engine.get(server_id, agent_name)
    if not member:
        # 降级：走本地 Ollama
        from core.lib.llm_client import llm_client
        result = llm_client.generate(prompt)
        if result and len(str(result)) > 2:
            return {"success": True, "content": result, "tokens": 0, "model": "ollama"}
        else:
            return {"success": False, "content": "本地模型响应超时，请稍后重试。", "tokens": 0, "model": "ollama"}

    model = member.get("model", "")
    api_key = member.get("api_key", "")
    unit_price = member.get("unit_price", 0)

    # Ollama 本地模型豁免费用
    if "ollama" in model.lower():
        unit_price = 0

    adapter = get_adapter(model, api_key=api_key)
    if adapter is None:
        # 本地 Ollama
        from core.lib.llm_client import llm_client
        result = llm_client.generate(prompt)
        if result and len(str(result)) > 2:
            return {"success": True, "content": result, "tokens": 0, "model": "ollama"}
        else:
            return {"success": False, "content": "本地模型响应超时，请稍后重试。", "tokens": 0, "model": "ollama"}

    result = adapter.execute(prompt, system_prompt, history)

    # 记账
    if result["success"] and result["tokens"] > 0:
        cost = ledger.record_cost(
            server_id=server_id,
            agent_name=agent_name,
            position=member.get("position", ""),
            model=model,
            tokens=result["tokens"],
            unit_price=unit_price,
            summary=prompt[:100],
        )
        result["cost"] = cost["cost"]

    # 记事
    ledger.record_event(
        server_id=server_id,
        agent_name=agent_name,
        position=member.get("position", ""),
        action=prompt[:50],
        summary=result.get("content", "")[:200],
        cost=result.get("cost", 0),
        status="completed" if result["success"] else "failed",
    )

    return result


def record_if_roster_member(server_id, agent_name, tokens, model, cost=0):
    """查花名册确认 Agent 存在后记账。存在则调 ledger.record_cost，不存在则返回 None。"""
    member = roster_engine.get(server_id, agent_name)
    if not member:
        return None

    position = member.get("position", "")
    unit_price = member.get("unit_price", cost)

    # Ollama 本地模型豁免费用
    if "ollama" in model.lower():
        unit_price = 0

    return ledger.record_cost(
        server_id=server_id,
        agent_name=agent_name,
        position=position,
        model=model,
        tokens=tokens,
        unit_price=unit_price,
    )
