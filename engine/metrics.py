#!/usr/bin/env python3
"""Metrics - Metrics 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""Prometheus 监控指标"""

import time

from prometheus_client import REGISTRY, Counter, Gauge, Histogram, generate_latest

# 定义指标
REQUEST_COUNT = Counter(
    "clawsjoy_requests_total", "Total requests", ["method", "endpoint", "status"]
)
REQUEST_DURATION = Histogram(
    "clawsjoy_request_duration_seconds", "Request duration", ["method", "endpoint"]
)
ACTIVE_AGENTS = Gauge("clawsjoy_active_agents", "Number of active agents")
SKILL_COUNT = Gauge("clawsjoy_skill_count", "Number of skills")
MEMORY_VECTORS = Gauge("clawsjoy_memory_vectors", "Number of vector memories")
SUCCESS_RATE = Gauge("clawsjoy_success_rate", "System success rate")


def update_metrics(active_agents, skill_count, memory_vectors, success_rate):
    """更新指标"""
    ACTIVE_AGENTS.set(active_agents)
    SKILL_COUNT.set(skill_count)
    MEMORY_VECTORS.set(memory_vectors)
    SUCCESS_RATE.set(success_rate)


def get_metrics():
    """获取指标"""
    return generate_latest(REGISTRY)
