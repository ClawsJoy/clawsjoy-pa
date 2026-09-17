#!/usr/bin/env python3
"""FeedbackCollector — 收集注入结果反馈，记录到 injection_feedback 表"""

import os
import json
from typing import Dict, List, Optional, Any

import psycopg2
import psycopg2.extras


class FeedbackCollector:
    """收集注入结果反馈，用于调整边权重和优化上下文注入策略。

    职责:
        1. 记录每次注入的结果（被使用/被忽略）
        2. 记录用户显式反馈（点赞/点踩）
        3. 为 WeightAdjuster 提供数据源
    """

    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv(
            "DATABASE_URL",
            "postgresql://clawsjoy:clawsjoy_secret@localhost:5432/clawsjoy_dev",
        )

    def collect(
        self,
        task_name: str,
        session_id: str,
        edge_id: Optional[int] = None,
        source_name: Optional[str] = None,
        target_name: Optional[str] = None,
        edge_type: Optional[str] = None,
        feedback_type: str = "used",
        feedback_value: float = 1.0,
        context: Optional[str] = None,
    ) -> bool:
        """收集一次注入反馈记录。

        Args:
            task_name: 当前任务名
            session_id: 当前会话 ID
            edge_id: 关联的边 ID（可选）
            source_name: 源实体名（可选）
            target_name: 目标实体名（可选）
            edge_type: 边类型（可选）
            feedback_type: 反馈类型 — "used"|"ignored"|"thumbs_up"|"thumbs_down"
            feedback_value: 反馈数值（1.0 = 正面, -1.0 = 负面）
            context: 反馈上下文说明

        Returns:
            bool: 是否写入成功
        """
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO injection_feedback
                    (task_name, session_id, edge_id, source_name, target_name,
                     edge_type, feedback_type, feedback_value, context)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    task_name,
                    session_id,
                    edge_id,
                    source_name,
                    target_name,
                    edge_type,
                    feedback_type,
                    feedback_value,
                    context,
                ),
            )
            conn.commit()
            cur.close()
            conn.close()

            # 同步更新 code_edges 的 used_count / ignored_count
            if edge_id:
                self._sync_edge_count(edge_id, feedback_type)

            return True
        except Exception as e:
            print(f"[FeedbackCollector.collect] 失败: {e}")
            return False

    def _sync_edge_count(self, edge_id: int, feedback_type: str) -> None:
        """同步更新 code_edges 的 used_count 或 ignored_count"""
        try:
            column = "used_count" if feedback_type == "used" else "ignored_count"
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()
            cur.execute(
                f"UPDATE code_edges SET {column} = {column} + 1 WHERE id = %s",
                (edge_id,),
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[FeedbackCollector._sync_edge_count] 失败: {e}")

    def get_feedback_summary(
        self, task_name: str = None, session_id: str = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """查询反馈汇总"""
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            conditions = []
            params = []
            if task_name:
                conditions.append("task_name = %s")
                params.append(task_name)
            if session_id:
                conditions.append("session_id = %s")
                params.append(session_id)

            where = ""
            if conditions:
                where = "WHERE " + " AND ".join(conditions)

            cur.execute(
                f"SELECT * FROM injection_feedback {where} ORDER BY created_at DESC LIMIT %s",
                params + [limit],
            )
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            print(f"[FeedbackCollector.get_feedback_summary] 失败: {e}")
            return []

    def get_edge_stats(self, edge_id: int) -> Optional[Dict[str, Any]]:
        """查询单条边的统计信息"""
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(
                "SELECT id, source_name, target_name, edge_type, weight, "
                "used_count, ignored_count FROM code_edges WHERE id = %s",
                (edge_id,),
            )
            row = cur.fetchone()
            cur.close()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            print(f"[FeedbackCollector.get_edge_stats] 失败: {e}")
            return None


# 全局实例
feedback_collector = FeedbackCollector()
