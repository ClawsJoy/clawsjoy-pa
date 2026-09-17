#!/usr/bin/env python3
"""Agent Api - Agent Api 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""Agent API - 统一调用接口"""
import sys

from flask import Flask, jsonify, request

from core.lib.unified_config import unified_config

sys.path.insert(0, "str(unified_config.ROOT)")

from agents.agent_manager import AgentManager

from core.lib.config_manager import config_manager

app = Flask(__name__)
manager = AgentManager()


@app.route("/agents", methods=["GET"])
def list_agents():
    return jsonify({"agents": manager.list_agents(), "stats": manager.get_stats()})


@app.route("/agents/<name>", methods=["GET"])
def get_agent(name):
    agent = manager.get_agent(name)
    if agent:
        return jsonify(
            {
                "name": name,
                "type": agent["type"],
                "config": agent.get("config", {}),
                "memory_stats": {
                    "conversations": len(
                        agent.get("memory", {}).get("conversations", [])
                    )
                },
            }
        )
    return jsonify({"error": "Agent not found"}), 404


if __name__ == "__main__":
    app.run(port=unified_config.get("services.agent_api.port", 5010))
