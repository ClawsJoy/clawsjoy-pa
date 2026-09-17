"""用户上下文管理器 - 线程级别的用户数据隔离"""

import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Optional


class UserContext:
    """用户上下文 - 线程本地存储"""
    
    _local = threading.local()
    
    @classmethod
    def set_current_user(cls, user_id: str):
        """设置当前线程的用户"""
        cls._local.user_id = user_id
        cls._local.user_dir = Path(f"data/users/{user_id}")
    
    @classmethod
    def get_current_user(cls) -> Optional[str]:
        """获取当前线程的用户"""
        return getattr(cls._local, 'user_id', None)
    
    @classmethod
    def get_user_dir(cls) -> Optional[Path]:
        """获取当前用户的目录"""
        user_dir = getattr(cls._local, 'user_dir', None)
        if user_dir and user_dir.exists():
            return user_dir
        return None
    
    @classmethod
    def clear(cls):
        """清除当前线程的用户"""
        if hasattr(cls._local, 'user_id'):
            delattr(cls._local, 'user_id')
        if hasattr(cls._local, 'user_dir'):
            delattr(cls._local, 'user_dir')


@contextmanager
def user_context(user_id: str):
    """用户上下文管理器"""
    try:
        UserContext.set_current_user(user_id)
        yield
    finally:
        UserContext.clear()


def get_user_workspace(user_id: str = None) -> Path:
    """获取用户工作区路径"""
    if user_id is None:
        user_id = UserContext.get_current_user()
    if user_id is None:
        raise ValueError("No user context")
    return Path(f"data/users/{user_id}")
