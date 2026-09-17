"""Celery 异步任务配置"""

import os
from celery import Celery

# RabbitMQ 或 Redis 作为 broker
broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

app = Celery(
    "clawsjoy",
    broker=broker_url,
    backend=result_backend,
    include=["core.lib.async_tasks"]
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
)

if __name__ == "__main__":
    app.start()
