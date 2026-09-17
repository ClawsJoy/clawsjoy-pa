"""V8 Roster 路由 — 从 agent_gateway_enhanced.py 抽取"""

import logging
from flask import request, jsonify
from pathlib import Path
import yaml
from core.lib.v8.roster_engine import roster_engine

logger = logging.getLogger(__name__)

def v8_roster_list():
    server_id = request.args.get("server_id", "default")
    return jsonify(roster_engine.list(server_id))

def _get_model_context_window(model):
    """读取模型实际 context_window。

    优先从 config/v8/available_models.yaml 的模型条目中读取 context_window 配置；
    未配置时回退默认值：deepseek-v4-flash 默认 65536。
    """
    try:
        import yaml
        with open("config/v8/available_models.yaml") as f:
            data = yaml.safe_load(f)
        for m in (data or {}).get("models", []) or []:
            if m.get("value") == model and m.get("context_window"):
                return int(m["context_window"])
    except Exception:
        pass
    # deepseek-v4-flash 默认 context_window
    return 65536


def v8_models_list():
    import yaml
    with open("config/v8/available_models.yaml") as f:
        data = yaml.safe_load(f)
    return jsonify(data.get("models", []))

def v8_roster_hire():
    data = request.json or {}
    server_id = data.get("server_id", "default")
    name = data.get("name", "")
    position_id = data.get("position", "")
    model = data.get("model", "")
    budget = data.get("budget", 0)
    try:
        with open(f"config/v8/positions/{position_id}.yaml") as f:
            pos = yaml.safe_load(f)
        if model:
            pos["model"] = model
        if budget:
            pos["budget"] = float(budget)
        pos["system_prompt"] = f"你是{name}，ClawsJoy 的{pos.get('position', '员工')}，负责完成老板分配的任务。"
        result = roster_engine.hire(server_id, name, pos)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

def v8_roster_fire():
    data = request.json or {}
    result = roster_engine.fire(data.get("server_id", "default"), data.get("name", ""))
    return jsonify(result)

def v8_roster_update():
    data = request.json or {}
    server_id = data.get("server_id", "default")
    name = data.get("name", "")
    if not name:
        return jsonify({"success": False, "error": "name is required"})
    try:
        member = roster_engine.get(server_id, name)
        if not member:
            return jsonify({"success": False, "error": f"员工 {name} 不存在"})
        updatable = ["model", "api_key", "budget", "system_prompt",
                     "position", "permissions", "constraints", "unit_price", "status"]
        members = roster_engine.roster[server_id]["members"]
        for field in updatable:
            if field in data:
                value = float(data[field]) if field == "budget" else data[field]
                members[name][field] = value
        roster_engine._save(server_id)
        return jsonify({"success": True, "member": members[name]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


def v8_roster_pause():
    data = request.json or {}
    result = roster_engine.pause(data.get("server_id", "default"), data.get("name", ""))
    return jsonify(result)

def v8_roster_resume():
    data = request.json or {}
    result = roster_engine.resume(data.get("server_id", "default"), data.get("name", ""))
    return jsonify(result)

def v8_roster_permissions():
    data = request.json or {}
    result = roster_engine.update_permissions(
        data.get("server_id", "default"), data.get("name", ""), data.get("permissions", {})
    )
    return jsonify(result)

def v8_roster_budget():
    data = request.json or {}
    result = roster_engine.update_budget(
        data.get("server_id", "default"), data.get("name", ""), float(data.get("budget", 0))
    )
    return jsonify(result)

def v8_positions_list():
    """岗位列表：合并模板定义 + 花名册实时状态"""
    server_id = request.args.get("server_id", "default")
    positions = []
    pos_dir = Path("config/v8/positions")
    # 获取已聘用员工的状态
    hired = {}
    try:
        for m in roster_engine.list(server_id):
            hired[m["name"]] = {
                "status": m.get("status", "active"),
                "model": m.get("model", ""),
                "spent": m.get("spent", 0),
                "task_count": m.get("task_count", 0),
            }
    except Exception:
        pass
    for f in pos_dir.glob("*.yaml"):
        with open(f) as fp:
            pos = yaml.safe_load(fp)
            pos["id"] = f.stem
            # 合并花名册实时状态
            pos["hired"] = hired.get(pos.get("position", ""), None)
            positions.append(pos)
    return jsonify(positions)



def register_roster_routes(app):
    app.add_url_rule("/v8/roster/list", view_func=v8_roster_list)
    app.add_url_rule("/v8/models/list", view_func=v8_models_list)
    app.add_url_rule("/v8/roster/hire", view_func=v8_roster_hire, methods=["POST"])
    app.add_url_rule("/v8/roster/fire", view_func=v8_roster_fire, methods=["POST"])
    app.add_url_rule("/v8/roster/update", view_func=v8_roster_update, methods=["POST"])
    app.add_url_rule("/v8/roster/pause", view_func=v8_roster_pause, methods=["POST"])
    app.add_url_rule("/v8/roster/resume", view_func=v8_roster_resume, methods=["POST"])
    app.add_url_rule("/v8/roster/permissions", view_func=v8_roster_permissions, methods=["POST"])
    app.add_url_rule("/v8/roster/budget", view_func=v8_roster_budget, methods=["POST"])
    app.add_url_rule("/v8/positions/list", view_func=v8_positions_list)
