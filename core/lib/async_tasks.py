"""异步任务定义"""

import time
from core.lib.celery_app import app


@app.task(bind=True, max_retries=3)
def long_running_task(self, task_name: str, data: dict):
    """长时间运行的任务"""
    try:
        # 模拟耗时操作
        time.sleep(1)
        result = f"任务 {task_name} 完成，处理数据: {data}"
        return {"status": "success", "result": result}
    except Exception as e:
        self.retry(exc=e, countdown=60)
        return {"status": "failed", "error": str(e)}


@app.task
def send_notification(user_id: str, message: str):
    """发送通知"""
    # 实际发送逻辑
    return {"status": "sent", "user_id": user_id}


@app.task
def process_video(video_path: str, operations: list):
    """视频处理任务"""
    # 视频转码、剪辑等耗时操作
    return {"status": "processing", "video_path": video_path}
