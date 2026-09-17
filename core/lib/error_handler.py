#!/usr/bin/env python3
"""统一错误处理"""

import logging
import traceback
from functools import wraps

from flask import current_app, jsonify, request

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
