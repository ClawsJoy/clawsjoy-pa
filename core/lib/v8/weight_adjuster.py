#!/usr/bin/env python3
"""WeightAdjuster — 基于注入反馈动态调整边权重"""

import os
import math
from typing import Dict, List, Optional, Any

import psycopg2
import psycopg2.extras


class WeightAdjuster:
    """基于 injection_feedback 表数据动态调整 code_edges 的权重。

    策略:
        - used_count 每 +1 → weight *= 1.05（小幅提升）
        - ignored_count 每 +1 → weight *= 0.8（显著降低）
        - thumbs_up → weight *= 1.2
        - thumbs_down → weight *= 0.5
        - 权重范围 [0.01, 10.0]，防止极端值
    """

    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv(
            "DATABASE_URL",
            "postgresql://clawsjoy:clawsjoy_secret@localhost:5432/clawsjoy_dev",
        )
        # 权重调整因子
        self.factors = {
            "used": 1.05,
            "ignored": 0.8,
            "thumbs_up": 1.2,
            "thumbs_down": 0.5,
        }
        # 权重范围
        self.min_weight = 0.01
        self.max_weight = 10.0

    def adjust(
        self,
        edge_id: int = None,
        task_name: str = None,
        session_id: str = None,
        batch: bool = False,
    ) -> bool:
        """调整指定边或批量调整边的权重。

        Args:
            edge_id: 单条边 ID（batch=False 时使用）
            task_name: 关联任务名
            session_id: 关联会话 ID
            batch: 是否批量调整所有边

        Returns:
            bool: 是否成功
        """
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            if batch:
                # 批量调整所有有反馈记录的边
                cur.execute("""
                    SELECT DISTINCT e.id, e.weight,
                           COALESCE(e.used_count, 0) as used_count,
                           COALESCE(e.ignored_count, 0) as ignored_count
                    FROM code_edges e
                    WHERE e.used_count > 0 OR e.ignored_count > 0
                """)
            elif edge_id:
                cur.execute(
                    "SELECT id, weight, used_count, ignored_count FROM code_edges WHERE id = %s",
                    (edge_id,),
                )
            else:
                # 按任务/会话筛选
                conditions = []
                params = []
                if task_name:
                    conditions.append("f.task_name = %s")
                    params.append(task_name)
                if session_id:
                    conditions.append("f.session_id = %s")
                    params.append(session_id)
                where = " AND ".join(conditions) if conditions else "1=1"
                cur.execute(f"""
                    SELECT DISTINCT e.id, e.weight,
                           COALESCE(e.used_count, 0) as used_count,
                           COALESCE(e.ignored_count, 0) as ignored_count
                    FROM code_edges e
                    JOIN injection_feedback f ON e.id = f.edge_id
                    WHERE {where}
                """, params)

            edges = cur.fetchall()
            cur.close()
            conn.close()

            if not edges:
                print(f"[WeightAdjuster.adjust] 没有需要调整的边")
                return True

            adjusted = 0
            for edge in edges:
                new_weight = self._compute_weight(
                    edge["weight"] or 1.0,
                    edge["used_count"] or 0,
                    edge["ignored_count"] or 0,
                )
                if new_weight != (edge["weight"] or 1.0):
                    self._update_weight(edge["id"], new_weight)
                    adjusted += 1

            print(f"[WeightAdjuster.adjust] 调整了 {adjusted}/{len(edges)} 条边")
            return True

        except Exception as e:
            print(f"[WeightAdjuster.adjust] 失败: {e}")
            return False

    def adjust_by_feedback(
        self, feedback_records: List[Dict[str, Any]]
    ) -> bool:
        """根据反馈记录直接调整权重（实时调整用）"""
        try:
            for fb in feedback_records:
                edge_id = fb.get("edge_id")
                fb_type = fb.get("feedback_type", "used")
                if not edge_id:
                    continue

                factor = self.factors.get(fb_type, 1.0)
                self._apply_factor(edge_id, factor)

            return True
        except Exception as e:
            print(f"[WeightAdjuster.adjust_by_feedback] 失败: {e}")
            return False

    def _compute_weight(
        self, current_weight: float, used_count: int, ignored_count: int
    ) -> float:
        """根据统计数据计算新权重"""
        w = current_weight
        # used_count 提升权重（但提升幅度递减）
        for _ in range(used_count):
            w *= self.factors["used"]
        # ignored_count 显著降低权重
        for _ in range(ignored_count):
            w *= self.factors["ignored"]
        # 限制范围
        return max(self.min_weight, min(self.max_weight, w))

    def _apply_factor(self, edge_id: int, factor: float) -> None:
        """对单条边应用权重因子"""
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()
            cur.execute(
                "UPDATE code_edges SET weight = GREATEST(%s, LEAST(%s, weight * %s)) WHERE id = %s",
                (self.min_weight, self.max_weight, factor, edge_id),
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[WeightAdjuster._apply_factor] 失败: {e}")

    def _update_weight(self, edge_id: int, new_weight: float) -> None:
        """更新单条边的权重"""
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()
            cur.execute(
                "UPDATE code_edges SET weight = %s WHERE id = %s",
                (new_weight, edge_id),
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[WeightAdjuster._update_weight] 失败: {e}")


# 全局实例
weight_adjuster = WeightAdjuster()
