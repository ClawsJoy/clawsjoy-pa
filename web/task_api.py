#!/usr/bin/env python3
"""Task Api - Task Api 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

"""定时任务 API"""
import json
import sys
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS
from lib.smart_config import smart_config

sys.path.insert(0, str(smart_config.ROOT))

app = Flask(__name__)
CORS(app)

from skills.scheduler import scheduler


@app.route("/api/tasks", methods=["GET"])
def list_tasks():
    return jsonify({"tasks": scheduler.list_tasks()})


@app.route("/api/tasks", methods=["POST"])
def add_task():
    data = request.json
    result = scheduler.add_task(
        data.get("name"),
        data.get("schedule"),
        data.get("type", "skill"),
        data.get("params"),
    )
    return jsonify(result)


@app.route("/api/tasks/<name>", methods=["DELETE"])
def remove_task(name):
    result = scheduler.remove_task(name)
    return jsonify(result)


@app.route("/api/tasks/history", methods=["GET"])
def task_history():
    log_file = Path("logs/task_history.jsonl")
    history = []
    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    history.append(json.loads(line))
                except Exception as e:
                    pass
    return jsonify({"history": history[-50:]})


if __name__ == "__main__":
    print(f"⏰ 定时任务 API 启动: http://{smart_config.HOST}:5023")
    app.run(host="0.0.0.0", port=smart_config.PORTS.get("web_task", 5023), debug=False)
