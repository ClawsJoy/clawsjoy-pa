# -*- coding: utf-8 -*-
"""agent_client WS 客户端 — 复用 V9 桥接协议(hello/exec/result/state/ping)

协议(与 web/browser-extension bridge 一致):
  client→V9  hello  {user_id, tag:"python-client"}
  V9→client  exec   {cmd_id, action, params}
  client→V9  result {cmd_id, ok, data}
  client→V9  state  {user_id, state, url}
  client→V9  closed {user_id}
新增:
  client→V9  login_status    {platform, logged_in}
  client→V9  verify_required {platform, url}

线程模型(关键):
  WS 收帧线程只做协议(入队 exec); playwright 浏览器操作必须在主线程执行
  (playwright sync API 非线程安全) — 主循环 next_exec() 取指令执行后 send_result。
"""
import json
import logging
import queue
import threading

from websockets.sync.client import connect

log = logging.getLogger("agent_client.ws")


class AgentWsClient:
    def __init__(self, url, user_id, tag="python-client"):
        self.url = url
        self.user_id = user_id
        self.tag = tag
        self.ws = None
        self._stop = threading.Event()
        self._thread = None
        self._exec_queue = queue.Queue()  # (cmd_id, action, params)

    # ---- 生命周期 ----
    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True, name="agent-ws")
        self._thread.start()

    def stop(self):
        self._stop.set()
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass

    def _loop(self):
        delay = 1.0
        while not self._stop.is_set():
            try:
                with connect(self.url, open_timeout=5, close_timeout=2) as ws:
                    self.ws = ws
                    delay = 1.0
                    log.info("WS 已连接 %s", self.url)
                    self.send({"type": "hello", "user_id": self.user_id, "tag": self.tag})
                    for raw in ws:
                        if self._stop.is_set():
                            break
                        try:
                            msg = json.loads(raw)
                        except Exception:
                            continue
                        self._handle(msg)
                    self.ws = None
            except Exception as e:
                log.warning("WS 连接失败/断开: %s (%.1fs 后重连)", str(e)[:120], delay)
            if not self._stop.is_set():
                self._stop.wait(delay)
                delay = min(delay * 1.5, 15.0)
        self.ws = None

    # ---- 消息(收帧线程) ----
    def _handle(self, msg):
        mtype = msg.get("type")
        if mtype == "exec":
            self._exec_queue.put((msg.get("cmd_id", ""), msg.get("action", ""), msg.get("params") or {}))
        elif mtype == "ping":
            self.send({"type": "pong"})

    # ---- 主线程接口 ----
    def next_exec(self, timeout=1.0):
        """取一条待执行指令(主线程轮询); 无则 None。"""
        try:
            return self._exec_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def send_result(self, cmd_id, ok, data):
        self.send({"type": "result", "cmd_id": cmd_id, "ok": ok, "data": data})

    # ---- 发送 ----
    def send(self, obj):
        if self.ws:
            try:
                self.ws.send(json.dumps(obj, ensure_ascii=False))
                return True
            except Exception:
                pass
        return False

    def send_state(self, state, url=""):
        self.send({"type": "state", "user_id": self.user_id, "state": state, "url": url})

    def send_login_status(self, platform, logged_in):
        self.send({"type": "login_status", "platform": platform, "logged_in": bool(logged_in)})

    def send_verify_required(self, platform, url=""):
        self.send({"type": "verify_required", "platform": platform, "url": url})
