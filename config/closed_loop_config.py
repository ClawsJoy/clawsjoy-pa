"""闭环系统配置 - 采集 → 分析 → 建议 → 执行 → 反馈 → 学习"""

# 闭环配置
CLOSED_LOOP_CONFIG = {
    "version": "1.0.0",
    # 采集配置
    "collector": {
        "enabled": True,
        "interval": 60,  # 秒
        "sources": ["logs", "metrics", "user_interaction", "system_health"],
        "batch_size": 100,
    },
    # 分析配置
    "analyzer": {
        "enabled": True,
        "models": ["pattern_recognition", "anomaly_detection", "trend_analysis"],
        "threshold": 0.7,
    },
    # 建议配置
    "suggester": {
        "enabled": True,
        "max_suggestions": 5,
        "priority_levels": ["high", "medium", "low"],
    },
    # 执行配置
    "executor": {
        "enabled": True,
        "auto_execute": False,  # 需要确认才执行
        "max_retries": 3,
    },
    # 反馈配置
    "feedback": {"enabled": True, "collect_user_feedback": True, "auto_learn": True},
    # 学习配置
    "learning": {
        "enabled": True,
        "model": "qwen2.5:7b-instruct-q4_0-gpu",
        "retrain_interval": 3600,  # 秒
        "min_samples": 10,
    },
}


def get_config():
    return CLOSED_LOOP_CONFIG
