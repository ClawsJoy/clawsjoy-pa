# -*- coding: utf-8 -*-
"""统计与监控路由（P3-A 拆出，Blueprint）—— 薄包装 → response_cache / perf / rate_limiter"""

from flask import Blueprint, jsonify, request

bp = Blueprint("stats_routes", __name__)


@bp.route("/api/v5/stats/cache", methods=["GET"])
def cache_stats():
    from core.lib.response_cache import response_cache

    return jsonify(response_cache.get_stats())


@bp.route("/api/v5/stats/performance", methods=["GET"])
def performance_stats():
    from core.lib.performance_middleware import get_perf_stats

    return jsonify(get_perf_stats())


@bp.route("/api/v5/stats/ratelimit", methods=["GET"])
def ratelimit_stats():
    from core.lib.rate_limiter import rate_limiter

    return jsonify(rate_limiter.get_stats(request.args.get("user_id")))
