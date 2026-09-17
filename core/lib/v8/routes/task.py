"""V8 Task 路由"""

import logging
from flask import request, jsonify
from core.lib.v8.task_engine import task_engine

logger = logging.getLogger(__name__)


def v8_task_create():
    data = request.json or {}
    result = task_engine.create(
        server_id=data.get("server_id", "default"),
        title=data.get("title", ""),
        assigned_to=data.get("assigned_to", ""),
        assigned_position=data.get("assigned_position", ""),
        created_by=data.get("created_by", "老板"),
    )
    return jsonify(result)

def v8_task_transition():
    data = request.json or {}
    result = task_engine.transition(
        server_id=data.get("server_id", "default"),
        task_id=data.get("task_id", ""),
        new_state=data.get("new_state", ""),
        comment=data.get("comment", ""),
    )
    return jsonify(result)

def v8_task_list():
    server_id = request.args.get("server_id", "default")
    status = request.args.get("status", None)
    created_by = request.args.get("created_by", None)
    tasks = task_engine.list(server_id, status)
    if created_by:
        tasks = [t for t in tasks if t.get("created_by") == created_by]
    return jsonify(tasks)


def register_task_routes(app):
    app.add_url_rule("/v8/task/create", view_func=v8_task_create, methods=["POST"])
    app.add_url_rule("/v8/task/transition", view_func=v8_task_transition, methods=["POST"])
    app.add_url_rule("/v8/task/list", view_func=v8_task_list)
