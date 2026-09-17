#!/usr/bin/env python3
#!/usr/bin/env python3
"""Plugin Api - Plugin Api 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import json
from io import BytesIO

from flask import Blueprint, jsonify, send_file

plugin_bp = Blueprint("plugin", __name__, url_prefix="/api/plugin")


@plugin_bp.route("/plugin.js", methods=["GET"])
def get_plugin():
    """返回轻量插件本体"""
    plugin_code = """
// ClawsJoy 轻量插件 v1.0.0
(function() {
    class ClawsJoyPlugin {
        constructor() {
            this.serverUrl = window.location.origin;
            this.cache = new Map();
        }
        
        async process(userInput) {
            // 脱敏
            const sanitized = userInput.replace(/1[3-9]\\d{9}/g, '[手机号]');
            
            // 调用服务器
            const res = await fetch(this.serverUrl + '/api/v4/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message: sanitized})
            });
            const data = await res.json();
            return data.response;
        }
    }
    
    window.ClawsJoy = new ClawsJoyPlugin();
})();
"""
    return send_file(
        BytesIO(plugin_code.encode()),
        mimetype="application/javascript",
        download_name="clawsjoy-plugin.js",
    )


@plugin_bp.route("/manifest", methods=["GET"])
def get_manifest():
    """获取能力清单"""
    return jsonify(
        {
            "version": "1.0.0",
            "plugins": [
                {"name": "core", "url": "/api/plugin/plugin.js", "size": 50000},
                {
                    "name": "ai-image-gen",
                    "url": "/api/driver/get/skill/ai-image-gen",
                    "size": 8000,
                },
                {
                    "name": "scheduler",
                    "url": "/api/driver/get/skill/scheduler",
                    "size": 3000,
                },
            ],
        }
    )
