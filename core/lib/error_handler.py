#!/usr/bin/env python3
"""统一错误处理"""

import logging
import traceback
from functools import wraps

from flask import current_app, jsonify, request
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """应用自定义异常"""

    def __init__(self, message, status_code=400, error_code=None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


def register_error_handlers(app):
    """注册全局错误处理器"""

    @app.errorhandler(AppError)
    def handle_app_error(e):
        response = {"success": False, "error": e.message, "status_code": e.status_code}
        if e.error_code:
            response["error_code"] = e.error_code
        logger.warning(f"AppError: {e.message}")
        return jsonify(response), e.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """PM-011v17 §一 裁：werkzeug 的 HTTP 语义错（400 等）⛔ 不许被下面的 `Exception` 兜成 500。

        依据（一手活日志）：`request.json` 解析失败 ⇒ werkzeug 抛 `BadRequest`（**400 语义**），
        却被 `@app.errorhandler(Exception)` 按 MRO 接走 ⇒ 对外 500 ⇒ 全库 POST 路由的坏 body 一律 500。
        判据（PM 原文）：非法 JSON ⇒ **400 ＋ 路由定位**（⛔ 不是裸 400）。
        """
        locator = ""
        try:
            rule = getattr(request, "url_rule", None)
            locator = str(rule.rule if rule is not None else (request.path or "")).lstrip("/")
        except Exception:
            locator = ""
        code = getattr(e, "code", None) or 500
        cause = getattr(e, "__cause__", None)
        if code == 400 and type(cause).__name__ == "BadRequest":
            msg = "body 不是合法 JSON"
        else:
            msg = (getattr(e, "description", "") or "").strip() or ("HTTP %s" % code)
        error_text = ("%s: %s" % (locator, msg)).rstrip(": ") if locator else msg
        logger.warning("HTTPException %s -> %s", code, error_text)
        return jsonify({"success": False, "error": error_text, "status_code": code}), code

    @app.errorhandler(Exception)
    def handle_generic_error(e):
        logger.error(f"Unhandled error: {traceback.format_exc()}")
        return (
            jsonify(
                {"success": False, "error": "Internal server error", "status_code": 500}
            ),
            500,
        )

    @app.errorhandler(404)
    def handle_not_found(e):
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Endpoint '{request.path}' not found",
                    "status_code": 404,
                }
            ),
            404,
        )

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Method {request.method} not allowed for {request.path}",
                    "status_code": 405,
                }
            ),
            405,
        )

    @app.errorhandler(429)
    def handle_rate_limit(e):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Rate limit exceeded. Please try again later.",
                    "status_code": 429,
                    "retry_after": 60,
                }
            ),
            429,
        )

    logger.info("✅ 全局错误处理器已注册")


def safe_execute(func):
    """安全执行装饰器"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AppError:
            raise
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {traceback.format_exc()}")
            raise AppError(str(e), status_code=500)

    return wrapper
