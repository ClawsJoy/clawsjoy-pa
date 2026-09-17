#!/usr/bin/env python3
"""LLM Service - 工作版本"""
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# 使用 phi3:mini 模型
MODEL = "phi3:mini"
OLLAMA_URL = "http://localhost:11434"

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": MODEL})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}
    message = data.get("message", "")
    if not message:
        return jsonify({"response": ""})
    
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": MODEL, "prompt": message, "stream": False, "options": {"temperature": 0.7}},
            timeout=60
        )
        if resp.status_code == 200:
            result = resp.json()
            reply = result.get("response", "")
            return jsonify({"response": reply, "success": True})
        else:
            return jsonify({"response": f"服务错误", "success": False})
    except Exception as e:
        return jsonify({"response": f"服务繁忙", "success": False})

@app.route("/generate", methods=["POST"])
def generate():
    return chat()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5012, debug=False)
