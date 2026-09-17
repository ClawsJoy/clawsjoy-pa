"""V8 Billing/Ledger 路由 — 从 agent_gateway_enhanced.py 抽取"""

import logging
from flask import request, jsonify

def v8_billing_realtime():
    server_id = request.args.get("server_id", "default")
    members = roster_engine.list(server_id)
    billing = []
    total = 0
    for m in members:
        billing.append({
            "name": m["name"],
            "position": m["position"],
            "spent": m.get("spent", 0),
            "budget": m.get("budget", 0),
            "task_count": m.get("task_count", 0),
            "status": m["status"],
        })
        total += m.get("spent", 0)
    return jsonify({"total": round(total, 4), "members": billing})

# ========== v8 Ledger API ==========
from core.lib.v8.ledger import ledger

logger = logging.getLogger(__name__)

def v8_ledger_billing():
    server_id = request.args.get("server_id", "default")
    month = request.args.get("month", None)
    return jsonify(ledger.get_billing(server_id, month))

def v8_ledger_timeline():
    server_id = request.args.get("server_id", "default")
    limit = int(request.args.get("limit", 30))
    return jsonify(ledger.get_timeline(server_id, limit))



def register_billing_routes(app):
    app.add_url_rule("/v8/billing/realtime", view_func=v8_billing_realtime)
    app.add_url_rule("/v8/ledger/billing", view_func=v8_ledger_billing)
    app.add_url_rule("/v8/ledger/timeline", view_func=v8_ledger_timeline)
