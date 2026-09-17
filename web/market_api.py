#!/usr/bin/env python3
"""Market Api - Market Api 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from lib.smart_config import smart_config

"""技能市场 API"""
import sys

from lib.smart_config import smart_config

sys.path.insert(0, "str(smart_config.ROOT)")

from pathlib import Path

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

from lib.skill_market import skill_market

app = Flask(__name__)
CORS(app)


@app.route("/api/market/skills", methods=["GET"])
def list_market_skills():
    local = skill_market.list_local()
    return jsonify({"skills": local, "total": len(local)})


@app.route("/api/market/skills", methods=["POST"])
def publish_skill():
    data = request.json
    result = skill_market.publish(
        data.get("name"),
        data.get("author", "anonymous"),
        data.get("description", ""),
        data.get("version", "1.0.0"),
    )
    return jsonify(result)


@app.route("/api/market/skills/<name>/download", methods=["GET"])
def download_skill(name):
    skill_path = Path(f"skills/{name}.py")
    if skill_path.exists():
        return send_file(skill_path, as_attachment=True)
    return jsonify({"error": "技能不存在"}), 404


@app.route("/api/market/install", methods=["POST"])
def install_skill():
    data = request.json
    result = skill_market.install(data.get("name"), data.get("source_url"))
    return jsonify(result)


if __name__ == "__main__":
    print("🏪 技能市场 API 启动: http://smart_config.HOST:5024")
    app.run(
        host="0.0.0.0", port=smart_config.PORTS.get("web_market", 5024), debug=False
    )
