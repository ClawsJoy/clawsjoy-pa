"""V8 Notifications + Discussions + Discord 路由"""

import logging
from flask import request, jsonify
from core.lib.v8.notifications import unread_count, list_notifications, mark_read, mark_all_read
import json
from pathlib import Path

logger = logging.getLogger(__name__)


def _v8_resp_ok(data, message="ok"):
    return jsonify({"success": True, "data": data, "message": message})

def _v8_resp_err(message, code=1):
    return jsonify({"success": False, "error": message, "status_code": 500 if code == 1 else code}), 500 if code == 1 else code

def v8_notifications():
    # GET /v8/notifications?limit=50&offset=0
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        result = list_notifications(limit=limit, offset=offset)
        return _v8_resp_ok(result)
    except Exception as e:
        return _v8_resp_err(str(e))


def v8_notifications_list():
    # GET /v8/notifications/list?limit=50&offset=0
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        result = list_notifications(limit=limit, offset=offset)
        return _v8_resp_ok(result)
    except Exception as e:
        return _v8_resp_err(str(e))


def v8_notifications_read():
    # POST /v8/notifications/read  body: {"id": "..."}
    try:
        data = request.json or {}
        nid = data.get("id", "")
        if not nid:
            return _v8_resp_err("missing id")
        result = mark_read(nid)
        return _v8_resp_ok(result)
    except Exception as e:
        return _v8_resp_err(str(e))


def v8_notifications_read_all():
    # POST /v8/notifications/read-all
    try:
        result = mark_all_read()
        return _v8_resp_ok(result)
    except Exception as e:
        return _v8_resp_err(str(e))


def v8_notifications_unread_count():
    # GET /v8/notifications/unread-count
    try:
        result = unread_count()
        return _v8_resp_ok(result)
    except Exception as e:
        return _v8_resp_err(str(e))


def v8_notifications_stream():
    """#8 SSE 主动推送: 新通知实时推送(EventSource; 15s 心跳注释行)。"""
    from flask import Response, stream_with_context
    from core.lib.v8.notifications import subscribe_sse
    q, unsub = subscribe_sse()

    def _gen():
        try:
            yield "retry: 3000\n\n"
            while True:
                try:
                    item = q.get(timeout=15)
                    yield "data: " + json.dumps(item, ensure_ascii=False) + "\n\n"
                except Exception:
                    yield ": heartbeat\n\n"
        finally:
            unsub()

    return Response(
        stream_with_context(_gen()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ========== v8 Discussions API ==========

def v8_discussions_list():
    """列出所有已保存的讨论记录，按时间倒序"""
    discussions_dir = Path("data/v8/discussions")
    if not discussions_dir.exists():
        return jsonify({"success": True, "records": []})
    records = []
    for f in sorted(discussions_dir.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text())
            records.append({
                "topic": data.get("topic", ""),
                "timestamp": data.get("timestamp") or data.get("time", f.stem),
                "consensus": data.get("consensus", False),
                "decision": data.get("decision", ""),
                "rounds": data.get("rounds_count", data.get("rounds", 0)),
                "participants": data.get("participants", []),
            })
        except Exception:
            continue
    return jsonify({"success": True, "records": records})


def v8_discussions_save():
    """保存讨论记录到 data/v8/discussions/ 目录"""
    data = request.json or {}
    import time as _time
    discussions_dir = Path("data/v8/discussions")
    discussions_dir.mkdir(parents=True, exist_ok=True)
    record_id = str(int(_time.time() * 1000))
    record = {
        "topic": data.get("topic", ""),
        "timestamp": datetime.now().isoformat(),
        "time": data.get("time", int(_time.time() * 1000)),
        "consensus": data.get("consensus", False),
        "decision": data.get("decision", ""),
        "rounds_count": data.get("rounds_count", data.get("rounds", 0)),
        "participants": data.get("participants", []),
        "rounds": data.get("rounds", []),
        "history": data.get("history", []),
    }
    filepath = discussions_dir / f"{record_id}.json"
    filepath.write_text(json.dumps(record, ensure_ascii=False, indent=2))
    return jsonify({"success": True, "id": record_id})


def v8_discussions_get():
    """获取单条讨论记录的完整数据"""
    record_id = request.args.get("id", "")
    if not record_id:
        return jsonify({"success": False, "error": "id 参数必填"}), 400
    filepath = Path("data/v8/discussions") / f"{record_id}.json"
    if not filepath.exists():
        return jsonify({"success": False, "error": "记录不存在"}), 404
    try:
        data = json.loads(filepath.read_text())
        return jsonify({"success": True, "record": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def v8_discord_notify():
    """接收内部通知，通过 Webhook 转发到 Discord（支持多身份）"""
    data = request.json or {}
    channel_id = data.get("channel_id", "")
    content = data.get("message", "")
    username = data.get("username", "")
    avatar_url = data.get("avatar_url", "")

    if not channel_id or not content:
        return jsonify({"success": False})

    import requests as _r
    payload = {"content": content}
    if username:
        payload["username"] = username
    if avatar_url:
        payload["avatar_url"] = avatar_url

    try:
        r = _r.post("https://discord.com/api/webhooks/1521526206518792482/B0kL_EdzmGFoaq6nuRTx-kVPjKB9AF4yBpBUgXl0nvFiSepXUNHpT7WF1kpy23zC8fQt",
                    json=payload, timeout=10)
        return jsonify({"success": r.status_code == 204})
    except Exception:
        return jsonify({"success": False})


def register_misc_routes(app):
    app.add_url_rule("/v8/notifications", view_func=v8_notifications, methods=["GET", "POST"])
    app.add_url_rule("/v8/notifications/list", view_func=v8_notifications_list, methods=["GET", "POST"])
    app.add_url_rule("/v8/notifications/read", view_func=v8_notifications_read, methods=["POST"])
    app.add_url_rule("/v8/notifications/read-all", view_func=v8_notifications_read_all, methods=["POST"])
    app.add_url_rule("/v8/notifications/unread-count", view_func=v8_notifications_unread_count, methods=["GET"])
    app.add_url_rule("/v8/notifications/stream", view_func=v8_notifications_stream, methods=["GET"])
    app.add_url_rule("/v8/discussions/list", view_func=v8_discussions_list, methods=["GET", "POST"])
    app.add_url_rule("/v8/discussions/save", view_func=v8_discussions_save, methods=["POST"])
    app.add_url_rule("/v8/discussions/get", view_func=v8_discussions_get, methods=["GET", "POST"])
    app.add_url_rule("/v8/discord/notify", view_func=v8_discord_notify, methods=["POST"])
