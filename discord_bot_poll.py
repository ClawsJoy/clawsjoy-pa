#!/usr/bin/env python3
"""ClawsJoy Discord Bot — 多轮上下文 + 多 Agent 路由"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv("config/.env")

# ========== 配置 ==========
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
CLAWSJOY_URL = "http://localhost:5002/v5/execute"
API_BASE = "https://discord.com/api/v10"

# PID 锁：同一 Token 禁止多开
import hashlib
PID_FILE = f"/tmp/clawsjoy_bot_{hashlib.md5(DISCORD_TOKEN.encode()).hexdigest()[:8]}.pid"
if os.path.exists(PID_FILE):
    with open(PID_FILE) as f:
        old_pid = f.read().strip()
    try:
        os.kill(int(old_pid), 0)
        print(f"❌ Bot 已在运行 (PID: {old_pid})，禁止多开")
        exit(1)
    except (OSError, ValueError):
        os.remove(PID_FILE)
with open(PID_FILE, "w") as f:
    f.write(str(os.getpid()))

if not DISCORD_TOKEN:
    print("❌ 请在 config/.env 中设置 DISCORD_BOT_TOKEN")
    exit(1)

HEADERS = {
    "Authorization": f"Bot {DISCORD_TOKEN}",
    "Content-Type": "application/json",
}

last_message_id = {}


def get_messages(channel_id, limit=3):
    url = f"{API_BASE}/channels/{channel_id}/messages?limit={limit}"
    r = requests.get(url, headers=HEADERS, timeout=10)
    return r.json() if r.status_code == 200 else []


def send_message(channel_id, content, username=None, avatar_url=None):
    url = f"{API_BASE}/channels/{channel_id}/messages"
    json_data = {"content": content}
    if username:
        json_data["username"] = username
        json_data["avatar_url"] = avatar_url or ""
    r = requests.post(url, headers=HEADERS, json=json_data, timeout=10)
    return r.status_code == 200

def get_me():
    r = requests.get(f"{API_BASE}/users/@me", headers=HEADERS, timeout=10)
    return r.json() if r.status_code == 200 else {}


def get_guild_channels(guild_id):
    url = f"{API_BASE}/guilds/{guild_id}/channels"
    r = requests.get(url, headers=HEADERS, timeout=10)
    return [c for c in r.json() if c["type"] == 0] if r.status_code == 200 else []


def ask_clawsjoy(user_input, user_id, channel_id):
    payload = {
        "raw_input": user_input,
        "user_id": f"discord_{user_id}",
        "session_id": f"discord_ch_{channel_id}",
        "channel_id": channel_id,  # 新增
    }

    # 前缀路由
    if user_input.startswith("!yt"):
        payload["agent"] = "youtube_agent"
        payload["raw_input"] = user_input[3:].strip()
    elif any(kw in user_input for kw in ["记住", "记一下", "记下", "我叫"]):
        payload["agent"] = "memory_agent"

    try:
        print(f"[BOT] 即将发送请求: {user_input[:50]}", flush=True)
        r = requests.post(CLAWSJOY_URL, json=payload, timeout=90)
        result = r.json()
        return result.get("response") or result.get("output_content", "嗯？")
    except Exception as e:
        return f"出错了：{e}"

# ========== 主循环 ==========
if __name__ == "__main__":
    me = get_me()
    print(f"✅ {me.get('username', 'Bot')} 已上线（多轮上下文）")

    guilds = requests.get(f"{API_BASE}/users/@me/guilds", headers=HEADERS, timeout=10).json()
    if not guilds:
        print("❌ Bot 不在任何服务器中")
        exit(1)

    channels = get_guild_channels(guilds[0]["id"])
    print(f"📡 监听 {len(channels)} 个频道: {[c['name'] for c in channels]}")
    # 初始化：记录每个频道最新消息ID，跳过历史消息
    for ch in channels:
        cid = ch["id"]
        msgs = get_messages(cid, limit=1)
        if msgs:
            last_message_id[cid] = msgs[0]["id"]
    
    while True:
        try:
            for ch in channels:
                cid = ch["id"]
                messages = get_messages(cid, limit=3)
                for msg in reversed(messages):
                    mid = msg["id"]
                    if msg["author"]["id"] == me["id"]:
                        continue
                    if msg["author"].get("bot"):
                        continue
                    if cid in last_message_id and int(mid) <= int(last_message_id[cid]):
                        continue
                    last_message_id[cid] = mid
                    content = msg["content"].strip()
                    if not content:
                        continue

                    print(f"📥 {msg['author']['username']}: {content}")
                    reply = ask_clawsjoy(content, msg["author"]["id"], cid)
                    print(f"📤 → {msg['author']['username']}: {reply[:80]}...")

                    if len(reply) <= 2000:
                        send_message(cid, reply)
                    else:
                        for i in range(0, len(reply), 2000):
                            send_message(cid, reply[i:i+2000])
            time.sleep(2)
        except Exception as e:
            print(f"⚠️ 轮询异常: {e}，3秒后重试...")
            time.sleep(3)
