#!/usr/bin/env python3
"""通知层 — Discord Webhook"""

import os
import time
from dotenv import load_dotenv

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(_PROJECT_ROOT, "config", ".env"))
DEFAULT_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "")


def notify(who: str, message: str, channel_id: str = None):
    """发 Discord 通知，失败自动重试 3 次"""
    import requests as _r
    ch = channel_id or DEFAULT_CHANNEL_ID
    if not ch:
        return
    for attempt in range(3):
        try:
            _r.post("http://localhost:5002/v8/discord/notify",
                    json={"channel_id": ch, "message": message, "username": who},
                    timeout=30)
            return
        except:
            if attempt < 2:
                time.sleep(2)
