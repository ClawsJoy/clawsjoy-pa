#!/usr/bin/env python3
#!/usr/bin/env python3
"""Intelligence Api - Intelligence Api 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from flask import Blueprint, jsonify

from lib.dynamic_threshold import dynamic_threshold
from lib.smart_scheduler import smart_scheduler
from lib.success_predictor import success_predictor

intelligence_bp = Blueprint("intelligence", __name__)


@intelligence_bp.route("/api/intelligence/stats")
def get_intelligence_stats():
    """获取智能化统计"""
    return jsonify(
        {
            "predictor": success_predictor.get_stats(),
            "scheduler": smart_scheduler.get_schedule_stats(),
            "threshold": dynamic_threshold.get_stats(),
        }
    )


@intelligence_bp.route("/api/intelligence/best-tasks")
def get_best_tasks():
    """获取最佳任务"""
    return jsonify(success_predictor.get_best_tasks(20))


@intelligence_bp.route("/api/intelligence/worst-tasks")
def get_worst_tasks():
    """获取最差任务"""
    return jsonify(success_predictor.get_worst_tasks(20))


@intelligence_bp.route("/api/intelligence/predict/<task_name>")
def predict_task(task_name):
    """预测单个任务"""
    return jsonify(success_predictor.predict_task_success_rate(task_name))


@intelligence_bp.route("/api/intelligence/adjust")
def apply_adjustments():
    """应用动态调整"""
    result = dynamic_threshold.apply_adjustments()
    return jsonify(result)


if __name__ == "__main__":
    print("智能化 API 模块")
