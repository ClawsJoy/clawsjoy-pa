#!/usr/bin/env python3
"""事件处理器 - 响应各类事件"""

import os
import subprocess
from datetime import datetime
from pathlib import Path

# 直接从模块导入类并创建实例
from core.lib.event_bus import ConditionalEventBus

# 创建条件事件总线实例
conditional_bus = ConditionalEventBus()

# ========== 条件检查函数 ==========


def check_memory_size():
    """检查记忆文件大小 (MB)"""
    memory_file = Path("data/memory_simple.json")
    if memory_file.exists():
        size_mb = memory_file.stat().st_size / (1024 * 1024)
        return size_mb
    return 0


def check_error_rate():
    """检查错误率"""
    log_dir = Path("logs")
    error_count = 0
    total_count = 0
    for log_file in log_dir.glob("*.log"):
        if log_file.exists():
            content = log_file.read_text(encoding="utf-8", errors="ignore")
            error_count += content.count("ERROR")
            total_count += len(content.split("\n"))
    if total_count > 0:
        return error_count / total_count
    return 0


def check_hot_topics_count():
    """检查热点话题数量"""
    topics_file = Path("data/topics/hot_topics.json")
    if topics_file.exists():
        import json

        with open(topics_file, "r") as f:
            data = json.load(f)
            return len(data) if isinstance(data, list) else 0
    return 0


# ========== 事件处理器 ==========


def on_memory_large(event, data):
    """记忆过大时触发学习"""
    print(f"[{datetime.now()}] 📚 记忆文件过大，触发学习循环")
    subprocess.Popen(["python3", "scripts/learning_loop.py"], cwd=os.getcwd())


def on_high_error_rate(event, data):
    """高错误率时触发自愈"""
    print(f"[{datetime.now()}] 🔧 错误率过高，触发自愈")
    subprocess.Popen(["bash", "scripts/auto_evolve.sh"], cwd=os.getcwd())


def on_topics_full(event, data):
    """话题过多时触发清理"""
    print(f"[{datetime.now()}] 🧹 热点话题过多，触发清理")
    subprocess.Popen(["python3", "scripts/cleanup_hot_topics.py"], cwd=os.getcwd())


# ========== 注册条件触发 ==========


def register_all():
    """注册所有条件触发"""

    # 注册事件处理器
    conditional_bus.on("memory.large", on_memory_large)
    conditional_bus.on("error.high", on_high_error_rate)
    conditional_bus.on("topics.full", on_topics_full)

    # 注册阈值触发
    conditional_bus.when_threshold(
        name="memory_size",
        get_value=check_memory_size,
        threshold=10.0,
        operator=">",
        trigger_event="memory.large",
        interval=300,
    )

    conditional_bus.when_threshold(
        name="error_rate",
        get_value=check_error_rate,
        threshold=0.05,
        operator=">",
        trigger_event="error.high",
        interval=60,
    )

    conditional_bus.when_threshold(
        name="topics_count",
        get_value=check_hot_topics_count,
        threshold=500,
        operator=">",
        trigger_event="topics.full",
        interval=3600,
    )

    print("✅ 事件处理器注册完成")
    print("   监听: 记忆>10MB, 错误率>5%, 话题>500")

    # 启动监控
    conditional_bus.start_monitoring()


if __name__ == "__main__":
    register_all()
