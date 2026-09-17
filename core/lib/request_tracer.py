"""请求追踪 - 为每个请求生成唯一 ID"""

import logging
import uuid
from functools import wraps

from flask import g, request

logger = logging.getLogger(__name__)


def generate_request_id() -> str:
    """生成请求 ID"""
    return str(uuid.uuid4())[:8]


def trace_request(f):
    """请求追踪装饰器"""

    @wraps(f)
    def wrapped(*args, **kwargs):
        # 生成请求 ID
        request_id = request.headers.get("X-Request-ID", generate_request_id())
        g.request_id = request_id

        # 添加到响应头
        from flask import make_response

        response = make_response(f(*args, **kwargs))
        response.headers["X-Request-ID"] = request_id

        return response

    return wrapped


class TraceLogger:
    """带追踪的日志器"""

    def __init__(self):
        self.logger = logging.getLogger("clawsjoy.trace")

    def _get_context(self):
        from flask import g

        return {
            "request_id": getattr(g, "request_id", None),
            "user_id": getattr(g, "user_id", None),
        }

    def info(self, msg: str):
        ctx = self._get_context()
        extra = {k: v for k, v in ctx.items() if v}
        self.logger.info(msg, extra=extra)

    def warning(self, msg: str):
        ctx = self._get_context()
        extra = {k: v for k, v in ctx.items() if v}
        self.logger.warning(msg, extra=extra)

    def error(self, msg: str):
        ctx = self._get_context()
        extra = {k: v for k, v in ctx.items() if v}
        self.logger.error(msg, extra=extra)


trace_logger = TraceLogger()
