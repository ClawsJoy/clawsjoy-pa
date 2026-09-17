"""数据库连接池"""

import sqlite3
import threading
from contextlib import contextmanager


class ConnectionPool:
    def __init__(self, db_path: str, max_connections: int = 5):
        self.db_path = db_path
        self.max_connections = max_connections
        self._pool = []
        self._lock = threading.Lock()
        self._created_count = 0

    def _create_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        self._created_count += 1
        return conn

    def get_connection(self):
        with self._lock:
            if self._pool:
                return self._pool.pop()
            if self._created_count < self.max_connections:
                return self._create_connection()
        return None

    def return_connection(self, conn):
        if conn is None:
            return
        with self._lock:
            if len(self._pool) < self.max_connections:
                self._pool.append(conn)
            else:
                conn.close()
                self._created_count -= 1

    @contextmanager
    def connection(self):
        conn = self.get_connection()
        if conn is None:
            raise Exception("无法获取数据库连接")
        try:
            yield conn
        finally:
            self.return_connection(conn)


class AutoReconnectPool(ConnectionPool):
    """自动重连的连接池"""

    def get_connection(self):
        """获取连接，失败时自动重连"""
        conn = super().get_connection()
        if conn is None:
            # 等待并重试
            time.sleep(0.1)
            conn = super().get_connection()

        if conn is None:
            # 创建新连接
            conn = self._create_connection()

        # 测试连接
        try:
            conn.execute("SELECT 1").fetchone()
        except Exception:
            # 连接失效，重新创建
            try:
                conn.close()
            except:
                pass
            conn = self._create_connection()

        return conn
